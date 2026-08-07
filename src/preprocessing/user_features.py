"""
user_features.py — per-user (cross-video) bot-risk features for YouTube
comment/reply records (Parmida).

This is "Tier B" from docs/cross_platform_alignment_guide_fa.md §4:
src/ingestion/automation_risk.py ("Tier A") only ever sees one video's
comments at a time, so it can't tell that the same author repeated the
exact same text across 40 different videos. This module looks at a single
author's *entire* history across every video/week already collected, which
is only possible after extraction — see §4 of that doc for why this can't
happen before/during collection.

It implements the shared "core" feature set from
users_dataframe_variables_explained_fa.md, adapted to the field names
actually present in YouTube Record JSONL output (config/schema.py) — see
that file's "chiz-haee ke moshtarekan" table for which of these are
platform-agnostic and could later be reused for Reddit/X.

Known gaps (documented, not hidden — same spirit as automation_risk.py):
  - Most data collected so far (data/raw/iran_us_war/youtube_comments_
    *.jsonl) predates the v2/v3 schema fields, so `content_id`, `parent_id`,
    and the per-comment `automation_risk_score` (Tier A) are often missing
    (None) on older records. Anything that needs them degrades gracefully
    (returns None / skips that signal) instead of raising.
  - YouTube's reply structure is flat (comment -> reply, one level), so the
    reference doc's max_depth/avg_depth don't apply here and aren't
    computed.
  - self_reply_ratio / unique_parent_authors need `parent_id` to look up the
    parent's author, which most current data lacks — not implemented yet;
    revisit once more v2/v3-shaped data exists.
  - Grouping key is `author_hash` when present, else falls back to the raw
    `author_channel_id` (older records) — same PII caveat already tracked
    in docs/project_brief_for_llm.md's v1 remediation TODO.

The final automation_risk_score_user is a heuristic weighted score, not a
bot verdict — see docs/cross_platform_alignment_guide_fa.md §4 for the
"how do we pick weights" / "how do we know it's decent" reasoning.
"""

import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestion"))
# Reuse, don't reimplement: same text-normalization/timestamp-parsing/URL
# logic Tier A already uses, so a comment counted as "duplicate text" means
# the same thing at both tiers.
from automation_risk import _normalize_text, _parse_ts, _URL_RE  # noqa: E402

# ---- weights for automation_risk_score_user -------------------------------
# Picked from users_dataframe_variables_explained_fa.md's "most important
# features for bot detection" list. NOT validated against ground truth
# (none exists) - a starting point, meant to be tuned after the manual
# spot-check described in cross_platform_alignment_guide_fa.md §4.
_WEIGHT_EXACT_DUPLICATE = 0.35
_WEIGHT_RAPID_ACTIVITY = 0.25
_WEIGHT_URL_RATIO = 0.15
_WEIGHT_HOUR_COVERAGE = 0.10
_WEIGHT_COMMENT_LEVEL_MEAN = 0.15  # bridges in Tier A's per-comment score, when available

_RAPID_ACTIVITY_WINDOW_SECONDS = 60

FLAG_THRESHOLD = 0.7  # suggested review threshold, not an auto-exclude rule


def _user_key(record: dict) -> str | None:
    meta = record.get("author_metadata") or {}
    return meta.get("author_hash") or meta.get("author_channel_id")


def build_user_table(records: Iterable[dict]) -> list[dict]:
    """Group Record-shaped dicts by author and compute the Tier-B feature
    set. Returns a plain list of dicts (not a DataFrame) so this module
    stays importable without a hard pandas dependency."""
    by_user: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        key = _user_key(r)
        if key:
            by_user[key].append(r)
    return [_features_for_user(key, items) for key, items in by_user.items()]


def _features_for_user(user_key: str, items: list[dict]) -> dict:
    n = len(items)

    texts_norm = [_normalize_text(r["text"]) for r in items if r.get("text")]
    text_counts: dict[str, int] = defaultdict(int)
    for t in texts_norm:
        text_counts[t] += 1
    duplicate_count = sum(1 for t in texts_norm if text_counts[t] > 1)
    exact_duplicate_ratio = duplicate_count / len(texts_norm) if texts_norm else 0.0
    unique_text_ratio = len(text_counts) / len(texts_norm) if texts_norm else 0.0

    post_ids = {r["post_id"] for r in items if r.get("post_id")}
    replies = sum(1 for r in items if r.get("is_reply"))
    reply_ratio = replies / n if n else 0.0

    word_counts = [len((r.get("text") or "").split()) for r in items]
    mean_word_count = statistics.fmean(word_counts) if word_counts else 0.0
    median_word_count = statistics.median(word_counts) if word_counts else 0

    like_counts = [(r.get("author_metadata") or {}).get("like_count") or 0 for r in items]
    mean_like_count = statistics.fmean(like_counts) if like_counts else 0.0

    url_flags = [bool(_URL_RE.search(r.get("text") or "")) for r in items]
    url_interaction_ratio = sum(url_flags) / n if n else 0.0

    timestamps = sorted(ts for ts in (_parse_ts(r.get("date", "")) for r in items) if ts)
    interarrivals = [(b - a).total_seconds() for a, b in zip(timestamps, timestamps[1:])]
    median_interarrival_seconds = statistics.median(interarrivals) if interarrivals else None
    rapid_activity_ratio = (
        sum(1 for gap in interarrivals if gap <= _RAPID_ACTIVITY_WINDOW_SECONDS) / len(interarrivals)
        if interarrivals
        else 0.0
    )
    active_utc_hours = len({ts.hour for ts in timestamps})
    hour_coverage_ratio = active_utc_hours / 24 if timestamps else 0.0

    # Tier A's per-comment automation_risk_score, when the collector already
    # wrote one (v2/v3 data only) - folded in as one more signal, optional.
    comment_scores = [
        r["automation_risk_score"] for r in items if r.get("automation_risk_score") is not None
    ]
    mean_comment_level_score = statistics.fmean(comment_scores) if comment_scores else None

    return {
        "user_key": user_key,
        "total_interactions": n,
        "posts_participated": len(post_ids),
        "replies": replies,
        "reply_ratio": round(reply_ratio, 4),
        "mean_word_count": round(mean_word_count, 2),
        "median_word_count": median_word_count,
        "mean_like_count": round(mean_like_count, 2),
        "url_interaction_ratio": round(url_interaction_ratio, 4),
        "exact_duplicate_ratio": round(exact_duplicate_ratio, 4),
        "unique_text_ratio": round(unique_text_ratio, 4),
        "median_interarrival_seconds": median_interarrival_seconds,
        "rapid_activity_ratio_60s": round(rapid_activity_ratio, 4),
        "active_utc_hours": active_utc_hours,
        "hour_coverage_ratio": round(hour_coverage_ratio, 4),
        "mean_comment_level_automation_risk": (
            round(mean_comment_level_score, 4) if mean_comment_level_score is not None else None
        ),
        "first_activity_utc": timestamps[0].isoformat() if timestamps else None,
        "last_activity_utc": timestamps[-1].isoformat() if timestamps else None,
    }


def score_users(user_rows: list[dict]) -> list[dict]:
    """Adds automation_risk_score_user ([0,1]) and is_flagged_bot_suspect to
    each row, in place, and returns the same list. Heuristic risk score,
    NOT a bot verdict - see docs/cross_platform_alignment_guide_fa.md §4;
    filtering on it is a separate, team-reviewed downstream decision, never
    automatic here."""
    for row in user_rows:
        comment_level = row["mean_comment_level_automation_risk"] or 0.0
        score = (
            _WEIGHT_EXACT_DUPLICATE * row["exact_duplicate_ratio"]
            + _WEIGHT_RAPID_ACTIVITY * row["rapid_activity_ratio_60s"]
            + _WEIGHT_URL_RATIO * row["url_interaction_ratio"]
            + _WEIGHT_HOUR_COVERAGE * row["hour_coverage_ratio"]
            + _WEIGHT_COMMENT_LEVEL_MEAN * comment_level
        )
        row["automation_risk_score_user"] = round(min(1.0, score), 4)
        row["is_flagged_bot_suspect"] = row["automation_risk_score_user"] >= FLAG_THRESHOLD
    return user_rows
