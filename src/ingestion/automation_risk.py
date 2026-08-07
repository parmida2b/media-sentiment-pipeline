"""
automation_risk.py — lightweight automation/spam risk heuristic (Parmida)

Project brief section 16: the goal is measuring sample-distortion risk, NOT
proving a given user is a bot. Output is a continuous automation_risk_score
in [0, 1], never a "this is a bot" verdict.

Important limitation (must be reported, not hidden - section 16/45): the
YouTube Data API does not expose account age, follower/following ratio, or
cross-video posting history, so this heuristic is necessarily weaker than
what the brief describes as "possible features". It only uses signals
available within a single video's fetched comment batch:
  - near-duplicate text ratio (near-identical comments repeated in the batch)
  - rapid-fire posting (same author, multiple comments, short time gap)
  - link/hashtag density in the text

Call score_batch() once per video with all Record-shaped comment dicts for
that video (top-level + replies together), after fetching them.
"""

import re
from collections import defaultdict
from datetime import datetime

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"#\w+")
_WHITESPACE_RE = re.compile(r"\s+")

RAPID_FIRE_WINDOW_SECONDS = 60
RAPID_FIRE_MIN_COUNT = 3

_WEIGHT_DUPLICATE = 0.5
_WEIGHT_RAPID_FIRE = 0.35
_WEIGHT_LINK_DENSITY = 0.15


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def _parse_ts(published_at: str) -> datetime | None:
    try:
        return datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


def _duplicate_text_scores(comments: list[dict]) -> dict[str, float]:
    """content_id -> fraction of the ratio of (how many other comments share
    this exact normalized text) capped at 1.0. A comment alone in the batch
    scores 0; a comment appearing 4+ times scores 1.0."""
    normalized_by_id = {c["content_id"]: _normalize_text(c["text"]) for c in comments if c.get("text")}
    counts: dict[str, int] = defaultdict(int)
    for norm in normalized_by_id.values():
        if norm:
            counts[norm] += 1

    scores = {}
    for content_id, norm in normalized_by_id.items():
        occurrences = counts.get(norm, 1)
        # occurrences=1 (unique) -> 0.0 ; occurrences>=5 -> 1.0
        scores[content_id] = min(1.0, max(0.0, (occurrences - 1) / 4))
    return scores


def _rapid_fire_scores(comments: list[dict]) -> dict[str, float]:
    """content_id -> risk contribution from posting several comments in the
    same video within RAPID_FIRE_WINDOW_SECONDS of each other, keyed by
    author_channel_id."""
    by_author: dict[str, list[dict]] = defaultdict(list)
    for c in comments:
        author_id = (c.get("author_channel_id") or "").strip()
        ts = _parse_ts(c.get("date", ""))
        if author_id and ts is not None:
            by_author[author_id].append({"content_id": c["content_id"], "ts": ts})

    scores: dict[str, float] = {}
    for entries in by_author.values():
        entries.sort(key=lambda e: e["ts"])
        for i, entry in enumerate(entries):
            window_start = max(0, i - (RAPID_FIRE_MIN_COUNT - 1))
            nearby = [
                e for e in entries[window_start:i + 1]
                if (entry["ts"] - e["ts"]).total_seconds() <= RAPID_FIRE_WINDOW_SECONDS
            ]
            burst_size = len(nearby)
            scores[entry["content_id"]] = min(1.0, max(0.0, (burst_size - 1) / (RAPID_FIRE_MIN_COUNT)))
    return scores


def _link_density_score(text: str) -> float:
    if not text:
        return 0.0
    url_count = len(_URL_RE.findall(text))
    hashtag_count = len(_HASHTAG_RE.findall(text))
    # 3+ links/hashtags combined in one comment is the saturation point.
    return min(1.0, (url_count + hashtag_count) / 3)


def score_batch(comments: list[dict]) -> dict[str, float]:
    """comments: list of dicts each with at least content_id, text, date,
    author_channel_id. Returns {content_id: automation_risk_score}."""
    comments = [c for c in comments if c.get("content_id")]
    if not comments:
        return {}

    duplicate_scores = _duplicate_text_scores(comments)
    rapid_fire_scores = _rapid_fire_scores(comments)

    result = {}
    for c in comments:
        content_id = c["content_id"]
        score = (
            _WEIGHT_DUPLICATE * duplicate_scores.get(content_id, 0.0)
            + _WEIGHT_RAPID_FIRE * rapid_fire_scores.get(content_id, 0.0)
            + _WEIGHT_LINK_DENSITY * _link_density_score(c.get("text", ""))
        )
        result[content_id] = round(min(1.0, score), 4)
    return result
