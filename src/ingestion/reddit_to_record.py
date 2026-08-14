"""
reddit_to_record.py — converts already-collected Reddit raw data into the
project's shared Record schema (config/schema.py), the same path YouTube's
collector writes into. (Parmida, Day 5)

Why this exists
----------------
reddit_parent_post_collector.py + reddit_raw_json_pipeline.py already collect
Reddit posts/comments (Selenium-driven, raw-first: parent-post URLs -> raw
.json per post -> parsed comments CSV). Neither of those scripts touches
config/schema.py or produces a raw_schema_columns.py-shaped export - Reddit's
output currently dead-ends after reddit_raw_json_pipeline.py's weekly
coverage audit. This script is the missing bridge: it reads that already-
collected CSV output and produces the same two artifacts YouTube's collector
produces:
    data/raw/reddit/reddit_comments_v1.jsonl   (Record.to_json_line() per row)
    data/raw/reddit/reddit_raw_export.csv      (config/raw_schema_columns.py shape)
so join_and_clean.py can pick Reddit up the same way it already picks up
YouTube (see the matching edit there).

It does NOT re-collect anything and does NOT touch the Selenium scripts'
existing output files - purely a read-existing-CSVs -> write-Record step,
safe to re-run.

Since 2026-08-12 (follow-up pass) this also:
  - Reads submissions_from_raw_json.csv (reddit_raw_json_pipeline.py now
    parses data[0], the submission's own Listing, not just data[1]'s
    comments - see that file's parse_submission()) and emits one additional
    Record per self-post that actually has body text (content_type=
    "submission"). Link/image/video posts with no selftext do NOT get a
    Record - there is no opinion text to annotate, same principle as the
    project's "a repost without opinion text isn't Opinion content" rule
    for X (docs/legacy_data_intake_and_harmonization_plan_v1.md §8).
  - Calls geo_tagger.tag_video_cached() once per unique post_id (title +
    selftext as the description, same call shape as youtube_extract.py's
    "Tier 0" relevance/perspective pre-filter), caching results in
    data/raw/reddit/video_geo_metadata.jsonl exactly like YouTube's
    video_geo_metadata.jsonl. Deliberately does NOT write perspective/
    is_relevant/confidence onto Record itself - geo_tagger.py's own
    docstring is explicit that this metadata "lives in its own side file
    and gets joined by video_id/post_id at analysis time", so this follows
    that same contract rather than growing Record with YouTube-shaped
    fields. join_and_clean.py joins it in for both platforms the same way.

Still deliberately NOT done (a content/domain decision, not a technical
one - see decision_log.md):
  - author_geo.tag_geo's channel_hint (curated per-source country/category,
    "source_community" geo_method) is passed as None - Reddit's
    SOURCE_REGISTRY (in reddit_parent_post_collector.py) has no country/
    category fields the way YouTube's channel registry does. Every Reddit
    comment therefore currently resolves to text_place (rare) or
    language_weak, never source_community. Adding a subreddit->country
    mapping needs team sign-off, not something to invent here.

Usage:
    python src/ingestion/reddit_to_record.py
    python src/ingestion/reddit_to_record.py --limit 200   # smoke-test on a subset
    python src/ingestion/reddit_to_record.py --skip-automation-risk --skip-geo --skip-relevance-tagging
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.schema import AuthorMetadata, Record  # noqa: E402
from config.raw_schema_columns import RAW_SCHEMA_COLUMNS  # noqa: E402
from config.raw_schema_columns_v05 import RAW_SCHEMA_V05_COLUMNS  # noqa: E402
from config import config_loader  # noqa: E402 - CONFIG.topic, same relevance-judging topic string YouTube's collector uses

import author_hash  # noqa: E402 - sibling module in src/ingestion/, see backfill_author_hash_v05.py for the same import convention
import author_geo  # noqa: E402
import automation_risk  # noqa: E402
import geo_tagger  # noqa: E402 - only used here for its _detect_text_language heuristic, not the LLM relevance tagger (see module docstring)
# Deliberately NOT `import reddit_parent_post_collector` just for its
# QUERY_VERSION constant: that module imports selenium/webdriver_manager at
# module level (real browser-automation deps), so importing it here would
# force anyone running this pure CSV->Record conversion step to also have
# Selenium installed for no reason. Kept as a local copy instead - MUST be
# bumped in lockstep with reddit_parent_post_collector.py's QUERY_VERSION.
QUERY_VERSION = "v3.0"

import reddit_raw_json_pipeline as reddit_pipeline  # noqa: E402 - PROJECT_START/END, week_label, file paths (this one also imports selenium at module level - see decision_log.md; left as-is since it also owns the file-path constants this script needs, cheaper to accept than to duplicate 15 path constants)

COLLECTOR_VERSION = "reddit_to_record.py:v1"

OUTPUT_DIR = reddit_pipeline.PROJECT_ROOT / "data" / "raw" / "reddit"
RAW_HARMONIZED_DIR = reddit_pipeline.PROJECT_ROOT / "data" / "raw_harmonized" / "reddit"
JSONL_OUTPUT = OUTPUT_DIR / "reddit_comments_v1.jsonl"
CSV_OUTPUT = OUTPUT_DIR / "reddit_raw_export.csv"

CONFIG = config_loader.load_config()


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def to_z_format(iso_string: str | None) -> str:
    """reddit_raw_json_pipeline.unix_to_iso() produces "...+00:00"; every
    other Record producer in this project (YouTube) uses the "...Z" form
    (see config/schema.py's own docstring example). Normalizing here also
    fixes a real compatibility bug: automation_risk._parse_ts() only accepts
    the exact "%Y-%m-%dT%H:%M:%SZ" format, so without this the rapid-fire
    signal would silently score 0 for every single Reddit comment (parse
    failure, not a crash - see automation_risk.py's _parse_ts)."""
    parsed = reddit_pipeline.parse_datetime(iso_string)
    if parsed is None:
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def project_week_metadata(z_format_date: str) -> tuple[str, bool, bool]:
    """(project_week, in_window, is_partial_week), reusing
    reddit_raw_json_pipeline.week_label() as the single source of truth for
    the project's W01..W21 window rather than re-deriving it here. Records
    outside the window are KEPT (in_window=False, project_week="OUT"), same
    policy as YouTube's collector - never silently dropped."""
    week = reddit_pipeline.week_label(z_format_date)
    if not week:
        return "OUT", False, False
    # PROJECT_START=2026-02-28, PROJECT_END=2026-07-22 -> W21 is the only
    # short week (2026-07-18..2026-07-22, 5 days instead of 7); every other
    # week is a full 7-day block from PROJECT_START. Fixed for this project's
    # window, same as youtube_extract.py's equivalent constant window.
    is_partial = week == "W21"
    return week, True, is_partial


def parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def build_permalink(subreddit: str, post_id: str, comment_id: str) -> str:
    return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/comment/{comment_id}/"


def hash_permalink(url: str) -> str:
    # Same one-line pattern already used by src/ingestion/x_scraper.py's
    # permalink_hash() - reused rather than reinvented.
    import hashlib
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def author_hash_and_status(author: str, author_fullname: str) -> tuple[str | None, str]:
    """Returns (author_hash, author_id_status).

    Deliberately hashes author_fullname (Reddit's stable "t2_xxxxx" id), NOT
    the username in `author` - a username can change; hashing it would
    repeat the exact mistake YouTube's author_hash formula dropped (see
    src/ingestion/author_hash.py's module docstring)."""
    if author in ("[deleted]", ""):
        return None, "deleted" if author == "[deleted]" else "unavailable"
    if not author_fullname:
        # Real username present but Reddit's JSON didn't include the stable
        # id this time (has happened for suspended/shadowbanned accounts) -
        # don't fabricate a hash from the mutable username instead.
        return None, "not_provided"
    return author_hash.hash_author("reddit", author_fullname), "available"


def content_status_for(text: str) -> str:
    if text == "[deleted]":
        return "deleted"
    if text == "[removed]":
        return "removed"
    return "active"


# ---------------------------------------------------------------------------
# load already-collected reddit CSVs
# ---------------------------------------------------------------------------

def load_parent_lookup(master_parent_file: Path) -> dict[str, dict[str, str]]:
    if not master_parent_file.exists():
        raise FileNotFoundError(
            f"{master_parent_file} not found - run reddit_raw_json_pipeline.py's "
            "merge_parent_posts() (i.e. run that script) before this one."
        )
    with master_parent_file.open("r", encoding="utf-8-sig", newline="") as fh:
        return {row["post_id"]: row for row in csv.DictReader(fh) if row.get("post_id")}


def load_comment_rows(comments_file: Path, limit: int | None) -> list[dict[str, str]]:
    if not comments_file.exists():
        raise FileNotFoundError(
            f"{comments_file} not found - run reddit_raw_json_pipeline.py first "
            "(it produces this file as part of rebuild_offline_outputs())."
        )
    with comments_file.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows[:limit] if limit else rows


def load_submission_rows(submissions_file: Path) -> list[dict[str, str]]:
    """Unlike load_comment_rows, no FileNotFoundError here: submissions_from_
    raw_json.csv is a newer output (added 2026-08-12) that older
    reddit_raw_json_pipeline.py runs won't have produced yet. Missing simply
    means "no submission-level Records this run" rather than a hard failure -
    comments alone are still a complete, valid run."""
    if not submissions_file.exists():
        print(f"[info] {submissions_file} not found - skipping submission-level Records (comments still processed).")
        return []
    with submissions_file.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# automation_risk (Tier A - per submission, matches YouTube's "per video")
# ---------------------------------------------------------------------------

def compute_automation_risk_scores(comment_rows: list[dict[str, str]]) -> dict[str, float]:
    """automation_risk.score_batch() is already platform-agnostic (just wants
    content_id/text/date/author_channel_id per comment) - reused verbatim,
    batched per submission (post_id) the same way youtube_extract.py batches
    per video, not across the whole dataset at once."""
    by_post: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comment_rows:
        by_post[row["post_id"]].append(
            {
                "content_id": row["comment_id"],
                "text": row.get("comment", ""),
                "date": to_z_format(row.get("comment_created_at_utc")),
                "author_channel_id": row.get("author_fullname") or row.get("author", ""),
            }
        )

    scores: dict[str, float] = {}
    for post_comments in by_post.values():
        scores.update(automation_risk.score_batch(post_comments))
    return scores


# ---------------------------------------------------------------------------
# per-submission LLM relevance/perspective tagging ("Tier 0", geo_tagger.py)
# ---------------------------------------------------------------------------

def compute_relevance_tags(submission_rows: list[dict[str, str]]) -> int:
    """Calls geo_tagger.tag_video_cached() once per unique post_id, same as
    youtube_extract.py does once per video. Side-effecting only (writes/
    updates data/raw/reddit/video_geo_metadata.jsonl via geo_tagger's own
    cache) - deliberately returns nothing to attach to Record, see module
    docstring. Returns how many posts were actually tagged this run (cache
    hits don't count, matching what a reader would want to know: "how much
    new Groq usage did this run cause")."""
    cache = geo_tagger.load_tagged_metadata(OUTPUT_DIR)
    newly_tagged = 0

    for row in submission_rows:
        post_id = row["post_id"]
        already_cached = post_id in cache
        channel_hint = None  # no subreddit->country/category registry yet - see module docstring
        try:
            geo_tagger.tag_video_cached(
                post_id, row.get("title", ""), row.get("selftext", ""),
                channel_hint, cache, CONFIG.topic, OUTPUT_DIR,
            )
        except geo_tagger.GroqQuotaExceeded as e:
            print(
                f"[warn] Groq daily quota exhausted during relevance tagging "
                f"({newly_tagged} newly tagged this run before stopping) - "
                f"already-tagged posts stay cached, safe to resume later. ({e})"
            )
            break
        if not already_cached:
            newly_tagged += 1

    return newly_tagged


# ---------------------------------------------------------------------------
# build one Record
# ---------------------------------------------------------------------------

def build_record(
    row: dict[str, str],
    parent: dict[str, str] | None,
    risk_score: float | None,
    compute_geo: bool,
) -> Record:
    text = row.get("comment", "") or ""
    date = to_z_format(row.get("comment_created_at_utc"))
    project_week, in_window, is_partial_week = project_week_metadata(date)

    author = row.get("author", "") or ""
    author_fullname = row.get("author_fullname", "") or ""
    a_hash, a_status = author_hash_and_status(author, author_fullname)

    subreddit = row.get("subreddit", "") or (parent or {}).get("subreddit", "")
    permalink = build_permalink(subreddit, row["post_id"], row["comment_id"])
    is_top_level = parse_bool(row.get("is_top_level"))

    if compute_geo:
        detected_language = geo_tagger._detect_text_language(text)
        geo = author_geo.tag_geo(text, channel_hint=None, detected_language=detected_language)
    else:
        detected_language, geo = None, {
            "geo_method": None, "geo_confidence": None,
            "geo_granularity": None, "country_or_region": None, "geo_limitations": None,
        }

    author_metadata = AuthorMetadata(
        author_channel_id=author_fullname or None,
        author_hash=a_hash,
        author_id_status=a_status,
    )

    return Record(
        text=text,
        date=date,
        source="reddit",
        platform="reddit",
        author_metadata=author_metadata,
        language=detected_language,
        post_id=row["post_id"],
        post_title=(parent or {}).get("title") or None,
        is_reply=not is_top_level,
        content_id=row["comment_id"],
        parent_id=row.get("parent_id") or None,
        collected_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        collection_run_id=None,  # not carried in the CSVs this reads from - see decision_log.md
        query_id=row.get("matched_query_ids") or None,
        automation_risk_score=risk_score,
        content_type="comment" if is_top_level else "reply",
        matched_query_ids=row.get("matched_query_ids") or None,
        discovery_route=(parent or {}).get("discovery_routes") or None,
        source_id=row.get("matched_source_ids") or None,
        source_container=subreddit or None,
        source_container_id=row.get("subreddit_id") or None,
        permalink_hash=hash_permalink(permalink),
        sampling_method="none",  # reddit_raw_json_pipeline.py collects everything it can reach, no cap
        sampling_applied=False,
        project_week=project_week,
        in_window=in_window,
        is_partial_week=is_partial_week,
        query_version=QUERY_VERSION,
        content_status=content_status_for(text),
        geo_method=geo["geo_method"],
        geo_confidence=geo["geo_confidence"],
        geo_granularity=geo["geo_granularity"],
        country_or_region=geo["country_or_region"],
        geo_limitations=geo["geo_limitations"],
    )


def build_submission_record(
    row: dict[str, str],
    compute_geo: bool,
) -> Record | None:
    """One Record for a self-post's own body text (content_type=
    "submission"). Returns None for link/image/video posts with no selftext
    - there is no opinion text to build a Record from (see module
    docstring). automation_risk_score is deliberately left None: Tier A's
    duplicate-text/rapid-fire signals compare same-type items within one
    post's comment batch, and a single submission has no such batch to
    compare against."""
    text = row.get("selftext", "") or ""
    if not text:
        return None

    date = to_z_format(row.get("created_at_utc"))
    project_week, in_window, is_partial_week = project_week_metadata(date)

    author = row.get("author", "") or ""
    author_fullname = row.get("author_fullname", "") or ""
    a_hash, a_status = author_hash_and_status(author, author_fullname)

    subreddit = row.get("subreddit", "") or ""
    post_id = row["post_id"]
    permalink = (
        f"https://www.reddit.com{row['permalink']}"
        if row.get("permalink")
        else f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/"
    )

    if compute_geo:
        detected_language = geo_tagger._detect_text_language(text)
        geo = author_geo.tag_geo(text, channel_hint=None, detected_language=detected_language)
    else:
        detected_language, geo = None, {
            "geo_method": None, "geo_confidence": None,
            "geo_granularity": None, "country_or_region": None, "geo_limitations": None,
        }

    author_metadata = AuthorMetadata(
        author_channel_id=author_fullname or None,
        author_hash=a_hash,
        author_id_status=a_status,
    )

    return Record(
        text=text,
        date=date,
        source="reddit",
        platform="reddit",
        author_metadata=author_metadata,
        language=detected_language,
        post_id=post_id,
        post_title=row.get("title") or None,
        is_reply=False,
        content_id=post_id,
        parent_id=None,
        collected_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        collection_run_id=None,
        query_id=row.get("matched_query_ids") or None,
        automation_risk_score=None,
        content_type="submission",
        matched_query_ids=row.get("matched_query_ids") or None,
        discovery_route=None,  # submissions_from_raw_json.csv doesn't carry discovery_routes (that's on the parent-post CSV, not the submission JSON) - see reddit_raw_json_pipeline.py's parse_submission
        source_id=row.get("matched_source_ids") or None,
        source_container=subreddit or None,
        source_container_id=row.get("subreddit_id") or None,
        permalink_hash=hash_permalink(permalink),
        sampling_method="none",
        sampling_applied=False,
        project_week=project_week,
        in_window=in_window,
        is_partial_week=is_partial_week,
        query_version=QUERY_VERSION,
        content_status=content_status_for(text),
        geo_method=geo["geo_method"],
        geo_confidence=geo["geo_confidence"],
        geo_granularity=geo["geo_granularity"],
        country_or_region=geo["country_or_region"],
        geo_limitations=geo["geo_limitations"],
    )


# ---------------------------------------------------------------------------
# Record -> raw_schema_columns.py CSV row
# ---------------------------------------------------------------------------

def record_to_raw_schema_row(record: Record, raw_score: str) -> dict[str, str]:
    """Every RAW_SCHEMA_COLUMNS entry explicitly, "" for genuinely
    unavailable data (Reddit's public .json never fabricated as anything
    else) rather than omitted - config/raw_schema_columns.py's own
    docstring requires every column present even when empty."""
    am = record.author_metadata
    return {
        "platform": record.platform,
        "platform_content_id": record.content_id or "",
        "content_type": record.content_type or "",
        "created_at_utc": record.date,
        "collected_at_utc": record.collected_at_utc or "",
        "text_raw": record.text,
        "author_hash": am.author_hash or "",
        "project_week": record.project_week or "",
        "in_window": str(bool(record.in_window)),
        "is_partial_week": str(bool(record.is_partial_week)),
        "query_id": record.query_id or "",
        "collection_run_id": record.collection_run_id or "",
        "source_id": record.source_id or "",
        "source_container": record.source_container or "",
        "source_container_id": record.source_container_id or "",
        "source_parent_id": record.post_id or "",
        "source_parent_title": record.post_title or "",
        "parent_id": record.parent_id or "",
        "query_version": record.query_version or "",
        "discovery_route": record.discovery_route or "",
        "matched_query_ids": record.matched_query_ids or "",
        "collector_version": COLLECTOR_VERSION,
        "permalink_hash": record.permalink_hash or "",
        "source_total_available": "",
        "sampling_method": record.sampling_method or "",
        "sampling_applied": str(bool(record.sampling_applied)),
        "items_kept": "",
        "random_seed": "",
        "engagement_score": raw_score,
        "engagement_replies": "",  # reply_count not computed upstream yet for Reddit - left blank, not fabricated as 0
        "engagement_shares": "",
        "engagement_quotes": "",
        "engagement_views": "",
        "engagement_collected_at_utc": record.collected_at_utc or "",
        "author_is_verified": "",
        "author_follower_count": "",
        "author_account_age_days": "",
        "author_is_submitter": "",  # available in Reddit's raw JSON (is_submitter) but not captured upstream yet
        "automation_risk_score": "" if record.automation_risk_score is None else str(record.automation_risk_score),
        "language_reported": "",
        "language_detected": record.language or "",
        "language_confidence": "" if record.language_confidence is None else str(record.language_confidence),
        "content_status": record.content_status or "",
        "geo_method": record.geo_method or "",
        "country_or_region": record.country_or_region or "",
        "geo_confidence": record.geo_confidence or "",
        "geo_granularity": record.geo_granularity or "",
        "geo_limitations": record.geo_limitations or "",
    }


# ---------------------------------------------------------------------------
# raw_harmonized export (raw_schema_v05.md)
# Mirrors youtube_extract.py's record_to_raw_harmonized_row() /
# export_to_raw_harmonized() — same pattern, Reddit-specific mappings.
# See docs/schema_mapping_template.csv rows for "reddit" for the source
# of each decision below.
# ---------------------------------------------------------------------------

# reddit_to_record.py uses "submission" for self-posts; v05 §8 calls the
# same concept "original_post" (the enum value for Reddit's top-level post).
_CONTENT_TYPE_V05_MAP = {"submission": "original_post"}


def _empty_to_none(value):
    """raw_schema_v05.md §1.1 point 5: missing field stays null, not "".
    Mirrors youtube_extract.py's _empty_to_none() helper."""
    if value in (None, ""):
        return None
    return value


def _parse_z_datetime(s: str | None) -> datetime | None:
    """Parse a Z-format ISO string produced by reddit_to_record.py's
    to_z_format() into a tz-aware datetime UTC. Handles both
    '2026-03-05T12:00:00Z' and '2026-03-05T12:00:00.000000Z' (microseconds) —
    found 2026-08-14 (see docs/decision_log.md): the strict no-microseconds
    strptime format silently returned None on every row of
    data/raw/reddit/reddit_comments_v1.jsonl (which does carry '.000000Z'),
    which meant record_to_raw_harmonized_row() wrote created_at_utc=NaT for
    ALL 158,959 Reddit records — apply_eligibility.py then classified nearly
    all of them as opinion_untimed (no usable timestamp), silently dropping
    Reddit out of every time-series/trend/event analysis."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def record_to_raw_harmonized_row(r: Record) -> dict:
    """One row of the raw_harmonized export, keyed exactly to
    RAW_SCHEMA_V05_COLUMNS (config/raw_schema_columns_v05.py). Mirrors
    youtube_extract.py's record_to_raw_harmonized_row() but with
    Reddit-specific field sources — see docs/schema_mapping_template.csv
    rows for 'reddit' for the decision behind each mapping."""
    am = r.author_metadata
    ct_v05 = _CONTENT_TYPE_V05_MAP.get(r.content_type or "", r.content_type)
    is_submission = ct_v05 == "original_post"
    return {
        # --- §3 Core ----------------------------------------------------------
        "platform": r.platform,
        "platform_content_id": _empty_to_none(r.content_id),
        "content_type": _empty_to_none(ct_v05),
        "created_at_utc": _parse_z_datetime(r.date) if r.date else None,
        "collected_at_utc": _parse_z_datetime(r.collected_at_utc) if r.collected_at_utc else None,
        "text_raw": r.text,
        "collection_run_id": _empty_to_none(r.collection_run_id),
        "collector_version": COLLECTOR_VERSION,
        "schema_version": "5.0",
        "project_week": _empty_to_none(r.project_week),
        "in_window": r.in_window,
        "is_partial_week": r.is_partial_week,

        # --- §4 Provenance and parent structure --------------------------------
        "query_id": _empty_to_none(r.query_id),
        "matched_query_ids": _empty_to_none(r.matched_query_ids),
        "query_version": _empty_to_none(r.query_version),
        "source_id": _empty_to_none(r.source_id),
        # No Source Registry versioning exists for Reddit yet.
        "source_registry_version": None,
        "discovery_route": _empty_to_none(r.discovery_route),
        # mapping: source_container = subreddit name (§9).
        "source_container": _empty_to_none(r.source_container),
        "source_container_id": _empty_to_none(r.source_container_id),
        # For original_post (submission) the content IS the root-level item;
        # source_parent_id only makes sense for comments/replies (= submission id).
        "source_parent_id": None if is_submission else _empty_to_none(r.post_id),
        "source_parent_title": _empty_to_none(r.post_title),
        "parent_id": _empty_to_none(r.parent_id),
        "permalink_hash": _empty_to_none(r.permalink_hash),

        # --- §4.1 Historical-data audit fields --------------------------------
        # not_applicable: reddit_to_record.py is a live-collector bridge reading
        # from Selenium-produced CSVs, not a legacy-file intake (no delivered
        # file to hash/index), same as youtube_extract.py's live-collector path.
        "original_file_name": None,
        "original_file_sha256": None,
        "original_row_number": None,
        "source_schema_version": None,
        "source_query_registry_version": None,
        "record_uid": None,
        # comment_id/post_id always come from Reddit's real API response.
        "id_origin": "observed",
        # timestamp always from UNIX epoch in Reddit's JSON (unix_to_iso).
        "timestamp_origin": "observed",
        "provenance_quality": None,
        "field_origin": None,
        "missing_reason": None,

        # --- §5 Author and privacy -------------------------------------------
        "author_hash": _empty_to_none(am.author_hash),
        "author_id_status": _empty_to_none(am.author_id_status),
        "author_type": None,
        # Reddit API does not expose a verified-account flag.
        "author_is_verified": None,
        "author_account_age_days": am.account_age_days,

        # --- §6 Engagement snapshot -------------------------------------------
        # Reddit score (upvotes) is not on Record — it comes from the source CSV
        # row in the live pipeline (record_to_raw_schema_row's `raw_score` param)
        # but is not propagated to Record or JSONL. Left None here.
        "engagement_score": None,
        # Reddit API does not return reply_count for nested comments.
        "engagement_replies": None,
        # Reddit has no Share/Repost or Quote concept.
        "engagement_shares": None,
        "engagement_quotes": None,
        "engagement_views": None,
        "engagement_collected_at_utc": _parse_z_datetime(r.collected_at_utc) if r.collected_at_utc else None,

        # --- §7 Language, status and location --------------------------------
        # Reddit API does not report content language.
        "language_reported": None,
        "language_detected": _empty_to_none(r.language),
        "language_confidence": r.language_confidence,
        "content_status": _empty_to_none(r.content_status),
        "geo_method": _empty_to_none(r.geo_method),
        "country_or_region": _empty_to_none(r.country_or_region),
        "geo_confidence": _empty_to_none(r.geo_confidence),
    }


_V05_BOOL_COLUMNS = ["in_window", "is_partial_week", "author_is_verified"]
_V05_INT_COLUMNS = [
    "engagement_replies", "engagement_shares", "engagement_quotes",
    "engagement_views", "author_account_age_days", "original_row_number",
]
_V05_FLOAT_COLUMNS = ["engagement_score", "language_confidence"]
_V05_DATETIME_COLUMNS = ["created_at_utc", "collected_at_utc", "engagement_collected_at_utc"]


def export_to_raw_harmonized(records: list[Record], run_id: str | None = None) -> pd.DataFrame:
    """Builds the raw_harmonized/reddit output: exactly the column set of
    docs/raw_schema_v05.md §3-§7 (RAW_SCHEMA_V05_COLUMNS), written as
    Parquet to data/raw_harmonized/reddit/{run_id}.parquet.

    Mirrors youtube_extract.py's export_to_raw_harmonized() — same dtype
    coercions and Parquet-write logic, Reddit-specific output path.

    `run_id` names the output file. When omitted, the function attempts to
    derive it from a single non-None collection_run_id shared by all records.
    Reddit records typically have collection_run_id=None (the Selenium
    pipeline doesn't carry it), so callers must pass run_id explicitly —
    typically a synthetic backfill id like 'backfill_reddit_v1'."""
    if not records:
        raise ValueError("export_to_raw_harmonized: no records given — nothing to export.")

    if run_id is None:
        non_null_runs = {r.collection_run_id for r in records if r.collection_run_id}
        if len(non_null_runs) == 1:
            run_id = non_null_runs.pop()
        elif len(non_null_runs) > 1:
            raise ValueError(
                f"export_to_raw_harmonized: records span {len(non_null_runs)} distinct "
                "collection_run_id values; call this once per run or pass run_id explicitly."
            )
        else:
            raise ValueError(
                "export_to_raw_harmonized: records have no collection_run_id set and "
                "run_id was not provided. Pass run_id='backfill_reddit_v1' or similar."
            )

    rows = [record_to_raw_harmonized_row(r) for r in records]
    df = pd.DataFrame(rows, columns=RAW_SCHEMA_V05_COLUMNS)

    for col in _V05_BOOL_COLUMNS:
        df[col] = df[col].astype("boolean")
    for col in _V05_INT_COLUMNS:
        df[col] = df[col].astype("Int64")
    for col in _V05_FLOAT_COLUMNS:
        df[col] = df[col].astype("float64")
    for col in _V05_DATETIME_COLUMNS:
        df[col] = pd.to_datetime(df[col], utc=True)

    output_path = RAW_HARMONIZED_DIR / f"{run_id}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"raw_harmonized: wrote {len(df)} row(s) to {output_path}")

    return df


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N comment rows (smoke-testing).")
    parser.add_argument("--skip-automation-risk", action="store_true", help="Skip automation_risk.score_batch (faster iteration).")
    parser.add_argument("--skip-geo", action="store_true", help="Skip author_geo.tag_geo (faster iteration).")
    parser.add_argument(
        "--skip-relevance-tagging", action="store_true",
        help="Skip geo_tagger.tag_video_cached (avoids Groq API calls entirely, e.g. for schema-only smoke-testing).",
    )
    args = parser.parse_args()

    parent_lookup = load_parent_lookup(reddit_pipeline.MASTER_PARENT_FILE)
    comment_rows = load_comment_rows(reddit_pipeline.COMMENTS_FILE, args.limit)
    submission_rows = load_submission_rows(reddit_pipeline.SUBMISSIONS_FILE)

    print(
        f"Loaded {len(parent_lookup)} parent post(s), {len(comment_rows)} comment row(s), "
        f"{len(submission_rows)} submission row(s)."
    )

    if args.skip_automation_risk:
        risk_scores: dict[str, float] = {}
    else:
        risk_scores = compute_automation_risk_scores(comment_rows)
        print(f"automation_risk_score computed for {len(risk_scores)} comment(s).")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.skip_relevance_tagging or not submission_rows:
        newly_tagged = 0
    else:
        newly_tagged = compute_relevance_tags(submission_rows)
        print(f"Relevance/perspective tagging: {newly_tagged} post(s) newly tagged this run (rest were cache hits).")

    # (source_row, record) pairs, comments first then submissions - kept
    # together so CSV writing below stays a single generic loop instead of
    # two near-duplicate ones.
    pairs: list[tuple[dict[str, str], Record]] = []

    for row in comment_rows:
        parent = parent_lookup.get(row["post_id"])
        record = build_record(
            row,
            parent,
            risk_scores.get(row["comment_id"]),
            compute_geo=not args.skip_geo,
        )
        pairs.append((row, record))

    submission_records_built = 0
    for row in submission_rows:
        record = build_submission_record(row, compute_geo=not args.skip_geo)
        if record is not None:
            pairs.append((row, record))
            submission_records_built += 1

    with JSONL_OUTPUT.open("w", encoding="utf-8") as fh:
        for _row, record in pairs:
            fh.write(record.to_json_line() + "\n")

    with CSV_OUTPUT.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()
        for row, record in pairs:
            score_raw = row.get("score", "")
            writer.writerow(record_to_raw_schema_row(record, score_raw))

    records = [record for _row, record in pairs]
    deleted_or_removed = sum(1 for r in records if r.content_status != "active")
    hashed = sum(1 for r in records if r.author_metadata.author_hash)

    print(f"\nWrote {len(records)} record(s) ({submission_records_built} of them submissions):")
    print(f"  JSONL: {JSONL_OUTPUT}")
    print(f"  CSV:   {CSV_OUTPUT}")
    print(f"  author_hash populated: {hashed}/{len(records)}")
    print(f"  content_status != active (deleted/removed): {deleted_or_removed}/{len(records)}")


if __name__ == "__main__":
    main()
