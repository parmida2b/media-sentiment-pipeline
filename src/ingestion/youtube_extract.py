"""
youtube_extract.py — consolidated YouTube collector (Parmida, Day 4+)

Single entrypoint replacing the earlier split between youtube_extract.py
(v1) and youtube_extract_incremental.py (v2) — see docs/decision_log.md.
v1 is retired: its `order=relevance` search, raw author_display_name
storage, and missing content_id/manifest were all superseded by v2's
watermark-based design, which this file now IS (not "wraps"). v1's own
already-collected data (~75k records under youtube_comments_1404-*.jsonl)
is untouched by this rewrite; remediating it is a separate, still-open task
(docs/project_brief_for_llm.md item 4).

Implements docs/raw_schema_v03.md (record/export/manifest contract) and
docs/source_registry_v3.md (allowed sources + more specific execution
rules). Notable behaviors driven by those two docs:
  - order="date" for video search, order="time" for comments — never
    relevance/top/viewCount (raw_schema_v03 §12.5, source_registry_v3 §4-1).
  - publishedAfter AND publishedBefore both pinned to the fixed project
    window (project_calendar.py) on every search.list call
    (source_registry_v3 §4-1) — not just publishedAfter like the old code.
  - author_hash (salted), never a raw display name (raw_schema_v03 §11/§12.1).
  - content_id/parent_id/collected_at_utc/collection_run_id/query_id/geo_*/
    automation_risk_score/content_type/project_week/in_window on every
    record.
  - Quota-Triage Pre-filter (raw_schema_v03 §12.3): geo_tagger's relevance
    check still gates comment-fetching per video (real quota constraint),
    but every skip is now logged to youtube_skipped_videos.csv
    (source_registry_v3 §4-1) instead of silently disappearing.
  - Comments newer than the project window are KEPT with in_window=false,
    project_week="OUT" (raw_schema_v03 §12.4) — not dropped.
  - The 300-comment-per-video cap is enforced by TRUE random sampling with
    a fixed seed (source_registry_v3, closing note + RANDOM_SEED=42), not
    "newest N" truncation.
  - Three outputs beyond the working jsonl: youtube_raw_export.csv (the
    raw_schema_v03 §0 export contract), youtube_runs.csv (the §13 manifest,
    one row per query×week), youtube_skipped_videos.csv (Quota-Triage log).

Usage:
    python src/ingestion/youtube_extract.py
"""

import csv
import hashlib
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.schema import Record, AuthorMetadata
from config import config_loader, query_registry_loader
from config.raw_schema_columns import RAW_SCHEMA_COLUMNS
from config.raw_schema_columns_v05 import RAW_SCHEMA_V05_COLUMNS

import author_geo
import author_hash
import automation_risk
import channels
import checkpoint
import geo_tagger
import incremental_state
import project_calendar

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

COLLECTOR_VERSION = "youtube_extract v3.0 (raw_schema_v03 + source_registry_v3)"

# source_registry_v3.md's closing note: a fixed seed so re-running the same
# collection produces the same 300-comment sample from the same candidate
# pool — shared in spirit with Reddit's RANDOM_SEED=42 in that same doc.
RANDOM_SEED = 42

# Re-check the last 2 days on every run (comment moderation/indexing can lag
# a video's publish time) - content_id dedup at write time makes this safe.
OVERLAP_BUFFER_SECONDS = 2 * 24 * 3600

# We fetch a larger candidate pool than the final per-video cap so the
# random sample in _sample_comments() is actually drawn from more than just
# "whatever the API handed us first" — still bounded, since commentThreads
# pagination is cheap (1 quota unit/page) but not free, and a single viral
# video shouldn't be allowed to consume unbounded run time. This pool is
# itself not the video's TRUE full comment population (source_registry_v3's
# own reasoning: "طول بازه غیرممکن یا پرهزینه است") - see _sample_comments()
# docstring for that limitation.
COMMENT_POOL_MULTIPLIER = 5

CONFIG = config_loader.load_config()

PUBLISHED_AFTER_RFC3339 = project_calendar.START.strftime("%Y-%m-%dT%H:%M:%SZ")
PUBLISHED_BEFORE_RFC3339 = project_calendar.END.strftime("%Y-%m-%dT%H:%M:%SZ")

# Search queries used to discover relevant news videos, combined across
# languages. keywords_ar intentionally excluded from config.yaml itself
# (see that file's comment) per source_registry_v3.md SR-006.
SEARCH_QUERIES_FALLBACK = [*CONFIG.keywords_en, *CONFIG.keywords_fa]

REGION_CODES = [tuple(pair) for pair in CONFIG.youtube.get("regions", [])]

# Region rotation (see docs/decision_log.md 2026-08-08 incident +
# config/query_registry.yaml 2026-08-11 note): all active queries x all of
# REGION_CODES in one run is too much search.list quota (29 queries x 5
# regions x 100 units = 14,500, against an 8,000/day budget). Rather than
# permanently pausing queries to fit, only REGIONS_PER_DAY regions run per
# day, rotating through REGION_CODES over a ceil(len/REGIONS_PER_DAY)-day
# cycle - full region coverage still happens, just spread across days.
REGIONS_PER_DAY = int(os.getenv("YOUTUBE_REGIONS_PER_DAY", "2"))


def regions_for_today(all_regions: list[tuple[str, str]], regions_per_day: int, today) -> list[tuple[str, str]]:
    """Picks today's slice of all_regions for the discovery loop.

    Deterministic by calendar date (proleptic Gregorian ordinal), not by run
    count or weekday - so running twice on the same day picks the same
    regions (idempotent), and a day with no run at all doesn't shift which
    regions later days cover.
    """
    if not all_regions or regions_per_day <= 0:
        return all_regions
    group_count = -(-len(all_regions) // regions_per_day)  # ceil division
    group_index = today.toordinal() % group_count
    start = group_index * regions_per_day
    return all_regions[start:start + regions_per_day]

CHANNEL_SEARCH_QUERY = CONFIG.youtube.get("channel_search_query", CONFIG.topic)
EXPLICIT_VIDEO_IDS = CONFIG.youtube.get("explicit_video_ids", [])
MAX_VIDEOS_PER_QUERY = CONFIG.youtube.get("max_videos_per_query", 5)
MAX_COMMENTS_PER_VIDEO = CONFIG.youtube.get("max_comments_per_video", 300)
COMMENT_POOL_CAP = MAX_COMMENTS_PER_VIDEO * COMMENT_POOL_MULTIPLIER

# Conservative reservation for a video's comment pagination against
# COMMENT_POOL_CAP (worst case: one page of up to 100 per quota unit),
# checked once before starting a video rather than interrupted mid-pagination.
COMMENT_FETCH_QUOTA_RESERVE = -(-COMMENT_POOL_CAP // 100) * checkpoint.QUOTA_COSTS["comment_threads"]

CHANNEL_REGISTRY = CONFIG.youtube.get("channels", {})
CHANNEL_PRIORITY_ORDER = CONFIG.youtube.get("channel_priority_order", list(CHANNEL_REGISTRY.keys()))

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / CONFIG.topic_id
RESOLVED_CHANNELS_PATH = DATA_DIR / "resolved_channels.json"

OUTPUT_JSONL_PATH = DATA_DIR / "youtube_comments_v2.jsonl"
OUTPUT_CSV_PATH = DATA_DIR / "youtube_raw_export.csv"
MANIFEST_PATH = DATA_DIR / "youtube_runs.csv"
SKIPPED_VIDEOS_PATH = DATA_DIR / "youtube_skipped_videos.csv"

# raw_schema_v05.md §14: harmonized output lives in its own top-level
# folder, NOT under DATA_DIR (data/raw/{topic_id}/...) - that folder keeps
# playing the untouched-raw-original role (§1: "Raw data پس از ذخیره تغییر
# نمی‌کند") and is never written to by export_to_raw_harmonized() below.
# Not topic_id-scoped either: raw_schema_v05.md's proposed layout is
# data/raw_harmonized/{platform}/..., and "youtube" (the platform) is what
# the user asked to key this on, not this project's topic_id.
RAW_HARMONIZED_DIR = PROJECT_ROOT / "data" / "raw_harmonized" / "youtube"

DEFAULT_WATERMARK_ISO = PUBLISHED_AFTER_RFC3339

MANIFEST_COLUMNS = [
    "collection_run_id", "platform", "query_id", "query_text", "query_version",
    "project_week", "discovery_route", "source_id", "sort_mode",
    "started_at_utc", "finished_at_utc", "returned_count", "stored_count",
    "records_in_window", "sampling_cap", "records_sampled_out",
    "oldest_record_utc", "newest_record_utc", "quota_consumed", "error_count",
    "prefiltered_sources_count", "prefiltered_sources_log_ref", "notes",
]


# ---------------------------------------------------------------------------
# language detection
# ---------------------------------------------------------------------------

def has_persian_only_chars(text: str) -> bool:
    persian_only = set("پچژگی‌ک")
    return any(ch in persian_only for ch in text)


def has_arabic_script(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


def detect_language(text: str) -> str:
    if not has_arabic_script(text):
        return "en"
    return "fa" if has_persian_only_chars(text) else "ar"


def detect_language_with_confidence(text: str) -> tuple[str, float]:
    """detect_language() is a deterministic script-range heuristic, not a
    probabilistic model - raw_schema_v03.md §6 explicitly allows a
    documented heuristic tiering instead of a real model confidence. Short
    or whitespace-only text makes the script signal unreliable (e.g. a
    single emoji or "ok" gives no real evidence either way), so it's tiered
    lower; anything with enough non-whitespace characters to have a clear
    script signal is tiered high."""
    lang = detect_language(text or "")
    meaningful_chars = len((text or "").strip())
    confidence = 0.9 if meaningful_chars >= 3 else 0.5
    return lang, confidence


# ---------------------------------------------------------------------------
# channel resolution (unchanged behavior from the old v1 module)
# ---------------------------------------------------------------------------

def load_resolved_channels() -> dict[str, str]:
    if not RESOLVED_CHANNELS_PATH.exists():
        return {}
    with open(RESOLVED_CHANNELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_resolved_channels(resolved: dict[str, str]) -> None:
    RESOLVED_CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESOLVED_CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)


def _is_quota_error(e: HttpError) -> bool:
    status = getattr(getattr(e, "resp", None), "status", None)
    return status == 403 and "quota" in str(e).lower()


def find_channel_id(youtube, name: str, expected_handle: str, state: dict) -> str | None:
    # channels.list's forHandle param resolves a handle directly to its
    # channel (1 unit, exact match) - a wrong handle just logs a warning and
    # is skipped, it never crashes the run (source_registry_v3.md §9's own
    # pending "verify real channel_id" checklist item assumes this).
    try:
        response = youtube.channels().list(part="snippet", forHandle=expected_handle).execute()
    except HttpError as e:
        print(f"[warn] channel lookup failed for {name!r} (@{expected_handle}): {e}")
        if _is_quota_error(e):
            raise
        return None
    checkpoint.spend(state, checkpoint.QUOTA_COSTS["channels_list"])

    items = response.get("items", [])
    if items:
        channel_id = items[0]["id"]
        title = items[0]["snippet"]["title"]
        print(f"  resolved channel {name!r} -> {title!r} ({channel_id})")
        return channel_id
    print(f"[warn] could not confirm official channel for {name!r} (expected handle @{expected_handle})")
    return None


def resolve_all_channels(youtube, state: dict) -> dict[str, str]:
    resolved = load_resolved_channels()
    for category, channel in channels.iter_channels(CHANNEL_REGISTRY, CHANNEL_PRIORITY_ORDER):
        key = f"{category}/{channel['handle']}"
        if key in resolved:
            continue
        if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["channels_list"]):
            continue
        try:
            channel_id = find_channel_id(youtube, channel["name"], channel["handle"], state)
        except HttpError:
            print("[quota] real API quota appears exhausted — stopping channel resolution early "
                  "(nothing marked as checked, safe to resume later).")
            break
        checkpoint.save_checkpoint(state, DATA_DIR)
        resolved[key] = channel_id  # cache the miss too (as None) so it isn't retried forever
        save_resolved_channels(resolved)
    return resolved


def _build_source_id_lookup(resolved_channels: dict[str, str]) -> dict[str, dict]:
    """resolved channel_id -> {"source_id", "name", "handle"} for every
    registry channel that resolved successfully. Used so a video discovered
    via generic query search (not channel-scoped) still gets tagged with
    source_id/source_container when it happens to belong to a registered
    channel — not just videos found via source-scoped channel search."""
    lookup: dict[str, dict] = {}
    for category, channel in channels.iter_channels(CHANNEL_REGISTRY, CHANNEL_PRIORITY_ORDER):
        key = f"{category}/{channel['handle']}"
        channel_id = resolved_channels.get(key)
        if channel_id:
            lookup[channel_id] = {
                "source_id": channel.get("source_id", ""),
                "name": channel["name"],
                "country": channel["country"],
                "category": category,
            }
    return lookup


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------

def search_video_ids_since(youtube, query: str, max_results: int, state: dict,
                            published_after_rfc3339: str, channel_id: str | None = None,
                            region_code: str | None = None, relevance_language: str | None = None) -> list[str] | None:
    """order="date" (never relevance/top - raw_schema_v03 §12.5) with BOTH
    publishedAfter and publishedBefore pinned to the fixed project window
    (source_registry_v3.md §4-1), regardless of config.yaml's own
    date_range.end ("auto" only controls how far incremental re-checking of
    already-known videos' comments reaches, not video discovery)."""
    kwargs = dict(
        q=query, part="id", type="video", order="date",
        maxResults=max_results,
        publishedAfter=published_after_rfc3339,
        publishedBefore=PUBLISHED_BEFORE_RFC3339,
    )
    if channel_id:
        kwargs["channelId"] = channel_id
    if region_code:
        kwargs["regionCode"] = region_code
    if relevance_language:
        kwargs["relevanceLanguage"] = relevance_language

    try:
        response = youtube.search().list(**kwargs).execute()
    except HttpError as e:
        print(f"[warn] search failed for query {query!r}: {e}")
        if _is_quota_error(e):
            raise
        return None
    checkpoint.spend(state, checkpoint.QUOTA_COSTS["search"])
    return [item["id"]["videoId"] for item in response.get("items", [])]


def get_video_details(youtube, video_ids: list[str], state: dict) -> dict[str, dict]:
    """Also captures channelId/channelTitle (already present in the
    snippet part we were already fetching, zero extra quota) so every
    video - not just channel-scoped discoveries - can be tagged with
    source_container/source_container_id, and (via the resolved-channel
    reverse lookup) source_id."""
    details = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["videos_list"]):
            print("[quota] budget exhausted — stopping video-details fetch.")
            break
        try:
            response = youtube.videos().list(part="snippet", id=",".join(chunk)).execute()
        except HttpError as e:
            print(f"[warn] videos.list failed: {e}")
            continue
        checkpoint.spend(state, checkpoint.QUOTA_COSTS["videos_list"])
        for item in response.get("items", []):
            snippet = item["snippet"]
            details[item["id"]] = {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
            }
    return details


# ---------------------------------------------------------------------------
# comment fetch + sampling
# ---------------------------------------------------------------------------

def fetch_comment_pool_since(youtube, video_id: str, max_pool: int,
                              state: dict, since_dt: datetime) -> tuple[list[dict], int | None]:
    """Raw comment dicts (top-level + replies) newer than since_dt, up to
    max_pool - a candidate POOL for _sample_comments() below, not yet the
    final per-video record set. No upper date bound here: comments newer
    than the project window are still fetched and later written with
    in_window=false (raw_schema_v03 §12.4) rather than skipped.

    Note (shared limitation with the old code): commentThreads.list orders
    by the TOP-LEVEL comment's time, so once a thread older than since_dt is
    hit, its replies are not re-checked even though a reply could technically
    be newer - a YouTube API ordering limitation.
    """
    comments: list[dict] = []
    page_token = None
    total_available = None
    while len(comments) < max_pool:
        try:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_pool - len(comments)),
                textFormat="plainText",
                order="time",
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            if _is_quota_error(e):
                raise
            print(f"[warn] could not fetch comments for video {video_id}: {e}")
            break
        checkpoint.spend(state, checkpoint.QUOTA_COSTS["comment_threads"])
        if total_available is None:
            total_available = response.get("pageInfo", {}).get("totalResults")

        hit_older_comment = False
        for item in response.get("items", []):
            top_comment = item["snippet"]["topLevelComment"]
            top_snippet = top_comment["snippet"]
            top_id = top_comment["id"]
            ts = _parse_rfc3339(top_snippet.get("publishedAt", ""))

            if ts is not None and ts < since_dt:
                hit_older_comment = True
            elif ts is not None:
                comments.append({
                    "content_id": top_id, "parent_id": None,
                    "text": top_snippet.get("textOriginal", top_snippet.get("textDisplay", "")),
                    "date": top_snippet.get("publishedAt", ""),
                    "author_display_name": top_snippet.get("authorDisplayName"),
                    "author_channel_id": (top_snippet.get("authorChannelId") or {}).get("value"),
                    "like_count": top_snippet.get("likeCount", 0),
                    "is_reply": False, "reply_count": item["snippet"].get("totalReplyCount", 0),
                    "video_id": video_id,
                })

            for reply in item.get("replies", {}).get("comments", []):
                r_snippet = reply["snippet"]
                r_ts = _parse_rfc3339(r_snippet.get("publishedAt", ""))
                if r_ts is None or r_ts < since_dt:
                    continue
                comments.append({
                    "content_id": reply["id"], "parent_id": r_snippet.get("parentId") or top_id,
                    "text": r_snippet.get("textOriginal", r_snippet.get("textDisplay", "")),
                    "date": r_snippet.get("publishedAt", ""),
                    "author_display_name": r_snippet.get("authorDisplayName"),
                    "author_channel_id": (r_snippet.get("authorChannelId") or {}).get("value"),
                    "like_count": r_snippet.get("likeCount", 0),
                    "is_reply": True, "reply_count": 0,
                    "video_id": video_id,
                })

        if hit_older_comment:
            break  # order=time desc -> everything after this is even older
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments[:max_pool], total_available


def _sample_comments(pool: list[dict], cap: int, video_id: str) -> tuple[list[dict], list[dict], str]:
    """Splits pool into (kept, sampled_out, sampling_method). If pool fits
    under cap, everything is kept and sampling_method="none". Otherwise
    exactly `cap` items are chosen uniformly at random, seeded
    deterministically per-video (RANDOM_SEED + video_id) so re-running
    produces the identical sample from the identical pool.

    Known limitation (documented, not silently glossed over): because
    collection is incremental/watermark-based, `pool` is only this run's
    newly-fetched batch for this video, not its full historical comment
    population - if a video receives a burst of >cap new comments between
    two runs, this samples from that burst, not from "all comments this
    video has ever had". True population-random-sampling and incremental
    collection are in structural tension; see docs/decision_log.md.
    """
    if len(pool) <= cap:
        return list(pool), [], "none"
    rng = random.Random(f"{RANDOM_SEED}:{video_id}")
    kept_idx = set(rng.sample(range(len(pool)), cap))
    kept = [c for i, c in enumerate(pool) if i in kept_idx]
    sampled_out = [c for i, c in enumerate(pool) if i not in kept_idx]
    return kept, sampled_out, "random"


def _parse_rfc3339(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _permalink_hash(video_id: str, content_id: str) -> str:
    url = f"https://youtube.com/watch?v={video_id}&lc={content_id}"
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# skipped-video log (Quota-Triage Pre-filter — raw_schema_v03 §12.3)
# ---------------------------------------------------------------------------

def append_skipped_video(video_id: str, tag: dict) -> None:
    SKIPPED_VIDEOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not SKIPPED_VIDEOS_PATH.exists()
    with open(SKIPPED_VIDEOS_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["video_id", "reason", "perspective", "confidence", "checked_at_utc"])
        if is_new:
            writer.writeheader()
        writer.writerow({
            "video_id": video_id,
            "reason": "geo_tagger judged not relevant to topic",
            "perspective": tag.get("perspective", ""),
            "confidence": tag.get("confidence", ""),
            "checked_at_utc": _utc_now_rfc3339(),
        })


# ---------------------------------------------------------------------------
# CSV export row mapping (raw_schema_v03 §0/§1 contract)
# ---------------------------------------------------------------------------

def record_to_csv_row(r: Record) -> dict:
    row = {col: "" for col in RAW_SCHEMA_COLUMNS}
    row.update({
        "platform": r.platform,
        "platform_content_id": r.content_id or "",
        "content_type": r.content_type or "",
        "created_at_utc": r.date,
        "collected_at_utc": r.collected_at_utc or "",
        "text_raw": r.text,
        "author_hash": r.author_metadata.author_hash or "",
        "project_week": r.project_week or "",
        "in_window": r.in_window if r.in_window is not None else "",
        "is_partial_week": r.is_partial_week if r.is_partial_week is not None else "",
        "query_id": r.query_id or "",
        "collection_run_id": r.collection_run_id or "",
        "source_id": r.source_id or "",
        "source_container": r.source_container or "",
        "source_container_id": r.source_container_id or "",
        "source_parent_id": r.post_id or "",
        "source_parent_title": r.post_title or "",
        "parent_id": r.parent_id or "",
        "query_version": r.query_version or "",
        "discovery_route": r.discovery_route or "",
        "matched_query_ids": r.matched_query_ids or "",
        "collector_version": COLLECTOR_VERSION,
        "permalink_hash": r.permalink_hash or "",
        "source_total_available": r.source_total_available if r.source_total_available is not None else "",
        "sampling_method": r.sampling_method or "",
        "sampling_applied": r.sampling_applied if r.sampling_applied is not None else "",
        "items_kept": r.items_kept if r.items_kept is not None else "",
        "random_seed": r.random_seed or "",
        "engagement_score": r.author_metadata.like_count,
        "engagement_replies": r.reply_count,
        "engagement_collected_at_utc": r.collected_at_utc or "",
        "automation_risk_score": r.automation_risk_score if r.automation_risk_score is not None else "",
        "language_detected": r.language or "",
        "language_confidence": r.language_confidence if r.language_confidence is not None else "",
        "geo_method": r.geo_method or "",
        "country_or_region": r.country_or_region or "",
        "geo_confidence": r.geo_confidence or "",
        "geo_granularity": r.geo_granularity or "",
        "geo_limitations": r.geo_limitations or "",
        # engagement_shares/quotes/views, author_is_verified/follower_count/
        # account_age_days/is_submitter, language_reported, content_status:
        # left blank - not available from the YouTube comment API (see
        # module docstring + docs/raw_schema_v03.md §6 content_status note).
    })
    return row


def append_csv_rows(records: list[Record]) -> None:
    if not records:
        return
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not OUTPUT_CSV_PATH.exists()
    with open(OUTPUT_CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_SCHEMA_COLUMNS)
        if is_new:
            writer.writeheader()
        for r in records:
            writer.writerow(record_to_csv_row(r))


# ---------------------------------------------------------------------------
# raw_harmonized export (raw_schema_v05.md §3-§7 contract, Parquet)
#
# This is a SEPARATE output from everything above: OUTPUT_JSONL_PATH/
# OUTPUT_CSV_PATH (data/raw/{topic_id}/...) keep being written exactly as
# before, untouched, playing the raw_schema_v05.md §1 "raw_original"
# role ("Raw data پس از ذخیره تغییر نمی‌کند"). export_to_raw_harmonized()
# below reads already-built Record objects and produces the *mapped*
# layer (raw_harmonized) alongside them, per §14's proposed path
# data/raw_harmonized/{platform}/... - never the other way around, and
# never mutating the Record objects or the raw/ files themselves.
#
# Column-by-column mapping decisions below follow docs/schema_mapping_
# template.csv's youtube rows (already filled in and reviewed - see that
# file for the full rationale/example values). A handful of columns are
# left as genuinely open team questions in that template (enum crosswalks,
# a §4 vs §9 naming conflict); those are called out inline rather than
# guessed at here.
# ---------------------------------------------------------------------------

def _empty_to_none(value):
    """raw_schema_v05.md §1.1 point 5: a missing field stays `null`, not
    "" - unlike record_to_csv_row() above, which writes "" for CSV. Record's
    producers (this module) use both None and "" to mean "no value" in
    different places, so both collapse to None here."""
    if value in (None, ""):
        return None
    return value


def record_to_raw_harmonized_row(r: Record) -> dict:
    """One row of the raw_harmonized export, keyed exactly to
    RAW_SCHEMA_V05_COLUMNS (config/raw_schema_columns_v05.py). Mirrors
    record_to_csv_row()'s v03 mapping but retyped/renulled for v05 - see
    docs/schema_mapping_template.csv rows for "youtube" for the source of
    each decision below (row numbers refer to that file)."""
    am = r.author_metadata
    return {
        # --- §3 Core ------------------------------------------------------
        "platform": r.platform,
        "platform_content_id": _empty_to_none(r.content_id),
        "content_type": _empty_to_none(r.content_type),
        "created_at_utc": _parse_rfc3339(r.date) if r.date else None,
        "collected_at_utc": _parse_rfc3339(r.collected_at_utc) if r.collected_at_utc else None,
        "text_raw": r.text,
        "collection_run_id": _empty_to_none(r.collection_run_id),
        # mapping row 11: current value still names raw_schema_v03 -
        # updating the string itself is explicitly out of scope for this
        # mapping (a separate collector-version decision).
        "collector_version": COLLECTOR_VERSION,
        # mapping row 12: constant, stamped at harmonization time - NOT
        # what the collector actually ran (that's source_schema_version
        # below, which is not_applicable for a live collector).
        "schema_version": "5.0",
        "project_week": _empty_to_none(r.project_week),
        "in_window": r.in_window,
        "is_partial_week": r.is_partial_week,

        # --- §4 Provenance and parent structure ----------------------------
        "query_id": _empty_to_none(r.query_id),
        # mapping row 17: kept as the existing ";"-joined string rather than
        # split into a real list - v05's column type is "list/string", and
        # whether it must become an actual List is an open decision, not
        # made here.
        "matched_query_ids": _empty_to_none(r.matched_query_ids),
        "query_version": _empty_to_none(r.query_version),
        "source_id": _empty_to_none(r.source_id),
        # mapping row 20: no versioning exists for the Source Registry
        # (channels.py / config/query_registry.yaml's channel entries) in
        # the current code - genuinely not producible yet.
        "source_registry_version": None,
        # mapping row 21: current "source_scope" value passed through
        # unchanged - whether it should rename to v05's "channel_scope" is
        # an open team decision (neither doc gives an explicit crosswalk).
        "discovery_route": _empty_to_none(r.discovery_route),
        # mapping row 22: raw_schema_v05.md §4 vs §9 disagree on whether
        # this should be the channel's readable title or its channel_id;
        # current code (and this mapping) keeps producing channel_title
        # unchanged rather than guessing which the document intended.
        "source_container": _empty_to_none(r.source_container),
        "source_container_id": _empty_to_none(r.source_container_id),
        "source_parent_id": _empty_to_none(r.post_id),
        "source_parent_title": _empty_to_none(r.post_title),
        "parent_id": _empty_to_none(r.parent_id),
        "permalink_hash": _empty_to_none(r.permalink_hash),

        # --- §4.1 Historical-data audit fields ------------------------------
        # mapping rows 28-33: all not_applicable - this is a live API
        # collector, not a legacy-file intake (no delivered file to hash/
        # index), and the record_uid fallback path never triggers because
        # the YouTube API always returns a real comment id for
        # platform_content_id.
        "original_file_name": None,
        "original_file_sha256": None,
        "original_row_number": None,
        "source_schema_version": None,
        "source_query_registry_version": None,
        "record_uid": None,
        # mapping row 34: platform_content_id always comes from a real API
        # response for this collector, never a derived row key.
        "id_origin": "observed",
        # mapping row 35: created_at_utc always comes straight from the
        # API's publishedAt field, never parsed from a nonstandard format.
        "timestamp_origin": "observed",
        # mapping rows 36-38: grading criteria (provenance_quality) and the
        # per-record aggregation logic (field_origin/missing_reason) aren't
        # implemented yet - see those rows' notes for why.
        "provenance_quality": None,
        "field_origin": None,
        "missing_reason": None,

        # --- §5 Author and privacy ---------------------------------------
        "author_hash": _empty_to_none(am.author_hash),
        # mapping row 40: AuthorMetadata carries this field (config/schema.py
        # v4), but youtube_extract.py never sets it when building Record -
        # always None today, referenced directly (not hardcoded) so it
        # starts flowing automatically if that ever changes.
        "author_id_status": _empty_to_none(am.author_id_status),
        # mapping row 41: no author-type classification logic exists.
        "author_type": None,
        # mapping row 42: never returned by the YouTube Comment API.
        "author_is_verified": None,
        # mapping row 43: AuthorMetadata.account_age_days is never
        # populated by this collector - not available from the API.
        "author_account_age_days": am.account_age_days,

        # --- §6 Engagement snapshot ----------------------------------------
        "engagement_score": float(am.like_count) if am.like_count is not None else None,
        "engagement_replies": r.reply_count,
        # mapping rows 46-47: no Share/Repost or Quote concept exists for
        # YouTube comments.
        "engagement_shares": None,
        "engagement_quotes": None,
        # mapping row 48: get_video_details() only requests part=snippet,
        # never part=statistics, so viewCount is never fetched.
        "engagement_views": None,
        "engagement_collected_at_utc": _parse_rfc3339(r.collected_at_utc) if r.collected_at_utc else None,

        # --- §7 Language, status and location --------------------------------
        # mapping row 50: the platform doesn't report a language field;
        # language_detected below is a local heuristic, not platform-reported.
        "language_reported": None,
        "language_detected": _empty_to_none(r.language),
        "language_confidence": r.language_confidence,
        # mapping row 53: Record carries content_status (config/schema.py
        # v4), but youtube_extract.py never sets it - always None today,
        # referenced directly for the same forward-compat reason as
        # author_id_status above.
        "content_status": _empty_to_none(r.content_status),
        # mapping row 54: current 6-value geo_method vocabulary
        # (geotag/profile/timezone/text_place/source_community/
        # language_weak) passed through unchanged - collapsing it to v05's
        # 4-value enum (geotag/profile/self_reported/other) needs an
        # explicit team crosswalk that neither doc provides, not a guess
        # made here.
        "geo_method": _empty_to_none(r.geo_method),
        "country_or_region": _empty_to_none(r.country_or_region),
        "geo_confidence": _empty_to_none(r.geo_confidence),
    }


# Columns that need an explicit nullable dtype so a missing value round-
# trips as a real Parquet null instead of pandas silently upcasting
# (e.g. an int column with any None becoming float64 NaN, or a bool column
# becoming object dtype).
_V05_BOOL_COLUMNS = ["in_window", "is_partial_week", "author_is_verified"]
_V05_INT_COLUMNS = [
    "engagement_replies", "engagement_shares", "engagement_quotes",
    "engagement_views", "author_account_age_days", "original_row_number",
]
_V05_FLOAT_COLUMNS = ["engagement_score", "language_confidence"]
_V05_DATETIME_COLUMNS = ["created_at_utc", "collected_at_utc", "engagement_collected_at_utc"]


def export_to_raw_harmonized(records: list[Record]) -> pd.DataFrame:
    """Builds the raw_harmonized/youtube output: exactly the column set of
    docs/raw_schema_v05.md §3-§7 (RAW_SCHEMA_V05_COLUMNS), written as
    Parquet to data/raw_harmonized/youtube/{collection_run_id}.parquet.

    Does not read or write OUTPUT_JSONL_PATH/OUTPUT_CSV_PATH (data/raw/...)
    at all - that raw-original output is untouched by this function, per
    raw_schema_v05.md §1's "Raw data پس از ذخیره تغییر نمی‌کند" and this
    project's own data/raw_original vs data/raw_harmonized separation
    (§14). Call this with the same `records` list already passed to
    append_csv_rows(), after append_csv_rows() has run - never instead of it.

    All `records` must share one collection_run_id (this collector's
    convention: one run, one id), since that id names the output file.
    """
    if not records:
        raise ValueError("export_to_raw_harmonized: no records given - nothing to export.")

    run_ids = {r.collection_run_id for r in records}
    if len(run_ids) != 1:
        raise ValueError(
            f"export_to_raw_harmonized: records span {len(run_ids)} distinct "
            f"collection_run_id values ({sorted(filter(None, run_ids))}); "
            "call this once per run with records from a single run."
        )
    collection_run_id = run_ids.pop()
    if not collection_run_id:
        raise ValueError("export_to_raw_harmonized: records have no collection_run_id set.")

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

    output_path = RAW_HARMONIZED_DIR / f"{collection_run_id}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"raw_harmonized: wrote {len(df)} row(s) to {output_path}")

    return df


# ---------------------------------------------------------------------------
# manifest (raw_schema_v03 §13 — one row per query x project_week)
# ---------------------------------------------------------------------------

def write_manifest(buckets: dict, collection_run_id: str, started_at_utc: str,
                    finished_at_utc: str, active_queries: list, registry_version: str,
                    prefiltered_count: int, error_count: int) -> None:
    """buckets: {(query_id, project_week): {...aggregates...}} as built by
    main() while writing records. Only buckets with at least one record
    considered this run get a row - query x week combos untouched this run
    are not represented (documented simplification, see plan)."""
    query_text_by_id = {q.query_id: q.query_text for q in active_queries}

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not MANIFEST_PATH.exists()
    sorted_keys = sorted(buckets.keys())
    first_key = sorted_keys[0] if sorted_keys else None
    with open(MANIFEST_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        if is_new:
            writer.writeheader()
        for query_id, week in sorted_keys:
            agg = buckets[(query_id, week)]
            is_first = (query_id, week) == first_key
            writer.writerow({
                "collection_run_id": collection_run_id,
                "platform": "youtube",
                "query_id": query_id,
                "query_text": query_text_by_id.get(query_id, ""),
                "query_version": registry_version,
                "project_week": week,
                "discovery_route": agg["discovery_route"],
                "source_id": agg["source_id"],
                "sort_mode": "time",  # commentThreads.list order - what actually produced these rows
                "started_at_utc": started_at_utc,
                "finished_at_utc": finished_at_utc,
                "returned_count": agg["returned_count"],
                "stored_count": agg["stored_count"],
                "records_in_window": agg["records_in_window"],
                "sampling_cap": MAX_COMMENTS_PER_VIDEO,
                "records_sampled_out": agg["records_sampled_out"],
                "oldest_record_utc": agg["oldest_record_utc"] or "",
                "newest_record_utc": agg["newest_record_utc"] or "",
                "quota_consumed": "",  # shared across the whole run, not attributable per-bucket - see notes
                "error_count": error_count if is_first else 0,
                "prefiltered_sources_count": prefiltered_count if is_first else 0,
                "prefiltered_sources_log_ref": "youtube_skipped_videos.csv",
                "notes": "quota_consumed/error_count/prefiltered_sources_count reported once on the first row of this run, not per bucket (they are run-level, not query x week - level).",
            })


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if not API_KEY:
        print("YOUTUBE_API_KEY is not set in .env — aborting.")
        return

    collection_run_id = f"yt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    started_at_utc = _utc_now_rfc3339()
    print(f"[{collection_run_id}] starting YouTube collection")
    print(f"Project window: {PUBLISHED_AFTER_RFC3339} -> {PUBLISHED_BEFORE_RFC3339} (fixed, project_calendar.py)")
    print(f"Outputs: {OUTPUT_JSONL_PATH.name}, {OUTPUT_CSV_PATH.name}, {MANIFEST_PATH.name}, {SKIPPED_VIDEOS_PATH.name}\n")

    state = incremental_state.load_state(DATA_DIR, DEFAULT_WATERMARK_ISO)
    v2_state = incremental_state.v2(state)
    published_after = v2_state["global_search_watermark"]
    print(f"Search watermark: {published_after} "
          f"(quota used today: {state['quota_used_today']}/{checkpoint.MAX_DAILY_QUOTA})\n")

    active_queries = [q for q in query_registry_loader.load_active_queries() if q.language != "ar"]
    query_pairs = [(q.query_id, q.query_text) for q in active_queries]
    if not query_pairs:
        query_pairs = [(f"cfg_{i}", kw) for i, kw in enumerate(SEARCH_QUERIES_FALLBACK)]
        print("[warn] config/query_registry.yaml has no active non-Arabic entries — "
              "falling back to config.yaml's flat keyword lists.\n")
    registry_version = query_registry_loader.get_registry_version() if active_queries else "config.yaml-fallback"

    today_pt = datetime.now(checkpoint.PT).date()
    todays_regions = regions_for_today(REGION_CODES, REGIONS_PER_DAY, today_pt)
    region_cycle_length = -(-len(REGION_CODES) // REGIONS_PER_DAY) if REGIONS_PER_DAY else 1
    cycle_day = today_pt.toordinal() % region_cycle_length + 1
    print(f"Region rotation: day {cycle_day}/{region_cycle_length} of cycle — "
          f"today's regions: {[code for code, _ in todays_regions]} "
          f"(all: {[code for code, _ in REGION_CODES]})\n")

    youtube = build("youtube", "v3", developerKey=API_KEY)

    rate_limit_events = 0
    error_count = 0
    known_gaps: list[str] = []
    video_matched_queries: dict[str, list[str]] = defaultdict(list)  # video_id -> ordered unique query_ids
    video_discovery_route: dict[str, str] = {}
    quota_exhausted = False
    newest_seen_overall: str | None = None

    for vid in EXPLICIT_VIDEO_IDS:
        incremental_state.mark_video_known(state, vid)
        video_discovery_route.setdefault(vid, "source_scope")

    print("Discovery pass (query x region)...")
    for query_id, query_text in query_pairs:
        if quota_exhausted:
            break
        for region_code, relevance_language in todays_regions:
            if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
                known_gaps.append("Search budget exhausted before all query x region combos were checked this run.")
                quota_exhausted = True
                break
            try:
                video_ids = search_video_ids_since(
                    youtube, query_text, MAX_VIDEOS_PER_QUERY, state,
                    published_after, region_code=region_code, relevance_language=relevance_language,
                )
            except HttpError:
                rate_limit_events += 1
                error_count += 1
                known_gaps.append("Real API quota appears exhausted during query discovery — stopped early, safe to resume next run.")
                quota_exhausted = True
                break
            if video_ids is None:
                error_count += 1
                continue
            for vid in video_ids:
                incremental_state.mark_video_known(state, vid)
                video_discovery_route.setdefault(vid, "query_search")
                if query_id not in video_matched_queries[vid]:
                    video_matched_queries[vid].append(query_id)
            if video_ids:
                print(f"  query:{query_id}|region:{region_code}: {len(video_ids)} video(s)")
            incremental_state.save_state(state, DATA_DIR)

    if not quota_exhausted:
        print("\nResolving/searching curated channels...")
        resolved = resolve_all_channels(youtube, state)
        for category, channel in channels.iter_channels(CHANNEL_REGISTRY, CHANNEL_PRIORITY_ORDER):
            if quota_exhausted:
                break
            reg_key = f"{category}/{channel['handle']}"
            channel_id = resolved.get(reg_key)
            if not channel_id:
                continue
            if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
                known_gaps.append("Search budget exhausted before all curated channels were checked this run.")
                quota_exhausted = True
                break
            try:
                video_ids = search_video_ids_since(
                    youtube, CHANNEL_SEARCH_QUERY, MAX_VIDEOS_PER_QUERY, state,
                    published_after, channel_id=channel_id,
                )
            except HttpError:
                rate_limit_events += 1
                error_count += 1
                known_gaps.append("Real API quota appears exhausted during channel discovery — stopped early, safe to resume next run.")
                quota_exhausted = True
                break
            if video_ids is None:
                error_count += 1
                continue
            for vid in video_ids:
                incremental_state.mark_video_known(state, vid)
                video_discovery_route.setdefault(vid, "source_scope")
            if video_ids:
                print(f"  channel:{reg_key}: {len(video_ids)} video(s)")
            incremental_state.save_state(state, DATA_DIR)
    else:
        resolved = load_resolved_channels()

    source_id_lookup = _build_source_id_lookup(resolved)

    known_video_ids = list(v2_state["known_video_ids"])
    print(f"\n{len(known_video_ids)} known video(s) total. Fetching details + geo/relevance tags...")

    details = get_video_details(youtube, known_video_ids, state)
    tagged_cache = geo_tagger.load_tagged_metadata(DATA_DIR)

    existing_content_ids = _load_existing_content_ids(OUTPUT_JSONL_PATH)
    written_this_run: set[str] = set()
    new_records: list[Record] = []
    skipped_irrelevant = 0
    collected_at = _utc_now_rfc3339()

    # (query_id, project_week) -> aggregate dict, for the manifest
    buckets: dict = defaultdict(lambda: {
        "discovery_route": "", "source_id": "", "returned_count": 0, "stored_count": 0,
        "records_in_window": 0, "records_sampled_out": 0,
        "oldest_record_utc": None, "newest_record_utc": None,
    })

    def _touch_bucket(query_id: str, week: str, route: str, source_id: str):
        b = buckets[(query_id, week)]
        if not b["discovery_route"]:
            b["discovery_route"] = route
            b["source_id"] = source_id
        return b

    print("\nChecking known videos for new comments...")
    for i, video_id in enumerate(known_video_ids, 1):
        if not checkpoint.has_budget(state, COMMENT_FETCH_QUOTA_RESERVE):
            known_gaps.append(f"Comment-fetch budget exhausted after {i - 1}/{len(known_video_ids)} known videos this run.")
            break

        detail = details.get(video_id, {"title": "", "description": "", "channel_id": "", "channel_title": ""})
        route = video_discovery_route.get(video_id, "query_search")
        matched_queries = video_matched_queries.get(video_id, [])
        primary_query_id = matched_queries[0] if matched_queries else ""
        matched_query_ids_str = ";".join(matched_queries)

        channel_source = source_id_lookup.get(detail["channel_id"], {})
        source_id = channel_source.get("source_id", "")
        channel_hint = {
            "category": channel_source.get("category", ""),
            "channel_name": detail["channel_title"] or channel_source.get("name", ""),
            "country": channel_source.get("country", ""),
        } if (detail["channel_title"] or channel_source) else None

        try:
            tag = geo_tagger.tag_video_cached(
                video_id, detail["title"], detail["description"], channel_hint,
                tagged_cache, CONFIG.topic, DATA_DIR,
            )
        except geo_tagger.GroqQuotaExceeded as e:
            known_gaps.append(
                f"Groq daily quota exhausted while geo-tagging videos "
                f"({i - 1}/{len(known_video_ids)} known videos processed) — stopped early, "
                f"safe to resume next run (already-tagged videos are cached). ({e})"
            )
            break
        if not tag["is_relevant"]:
            skipped_irrelevant += 1
            append_skipped_video(video_id, tag)
            continue

        since_iso = incremental_state.get_video_watermark(state, video_id, DEFAULT_WATERMARK_ISO)
        since_dt = _parse_rfc3339(since_iso)

        try:
            pool, total_available = fetch_comment_pool_since(youtube, video_id, COMMENT_POOL_CAP, state, since_dt)
        except HttpError:
            rate_limit_events += 1
            error_count += 1
            known_gaps.append(
                f"Real API quota appears exhausted while fetching comments "
                f"({i - 1}/{len(known_video_ids)} known videos processed) — stopped early, safe to resume next run."
            )
            break

        if not pool:
            continue

        kept, sampled_out, sampling_method = _sample_comments(pool, MAX_COMMENTS_PER_VIDEO, video_id)
        risk_scores = automation_risk.score_batch(pool)

        video_new_count = 0
        for c in kept:
            week, in_window, is_partial = project_calendar.project_week_from_iso(c["date"])
            _touch_bucket(primary_query_id, week, route, source_id)["returned_count"] += 1

            content_id = c["content_id"]
            if content_id in existing_content_ids or content_id in written_this_run:
                continue
            written_this_run.add(content_id)
            video_new_count += 1

            detected_language, lang_confidence = detect_language_with_confidence(c["text"])
            geo = author_geo.tag_geo(c["text"], channel_hint, detected_language)

            record = Record(
                text=c["text"], date=c["date"], source="youtube", platform="youtube",
                author_metadata=AuthorMetadata(
                    author_channel_id=c["author_channel_id"], like_count=c["like_count"],
                    author_hash=author_hash.hash_author("youtube", c["author_channel_id"]),
                ),
                language=detected_language, post_id=video_id, post_title=detail["title"],
                reply_count=c["reply_count"], is_reply=c["is_reply"],
                content_id=content_id, parent_id=c["parent_id"],
                collected_at_utc=collected_at, collection_run_id=collection_run_id,
                query_id=primary_query_id,
                geo_method=geo["geo_method"], geo_confidence=geo["geo_confidence"],
                geo_granularity=geo["geo_granularity"], country_or_region=geo["country_or_region"],
                geo_limitations=geo["geo_limitations"],
                automation_risk_score=risk_scores.get(content_id),
                content_type="reply" if c["is_reply"] else "comment",
                matched_query_ids=matched_query_ids_str,
                query_version=registry_version,
                discovery_route=route,
                source_id=source_id,
                source_container=detail["channel_title"],
                source_container_id=detail["channel_id"],
                permalink_hash=_permalink_hash(video_id, content_id),
                source_total_available=total_available,
                sampling_method=sampling_method,
                sampling_applied=(sampling_method != "none"),
                items_kept=len(kept),
                random_seed=str(RANDOM_SEED) if sampling_method == "random" else None,
                language_confidence=lang_confidence,
                project_week=week, in_window=in_window, is_partial_week=is_partial,
            )
            new_records.append(record)

            b = _touch_bucket(primary_query_id, week, route, source_id)
            b["stored_count"] += 1
            if in_window:
                b["records_in_window"] += 1
            if b["oldest_record_utc"] is None or c["date"] < b["oldest_record_utc"]:
                b["oldest_record_utc"] = c["date"]
            if b["newest_record_utc"] is None or c["date"] > b["newest_record_utc"]:
                b["newest_record_utc"] = c["date"]

        for c in sampled_out:
            week, _, _ = project_calendar.project_week_from_iso(c["date"])
            b = _touch_bucket(primary_query_id, week, route, source_id)
            b["returned_count"] += 1
            b["records_sampled_out"] += 1

        if video_new_count:
            newest_for_video = max(c["date"] for c in pool)
            incremental_state.update_video_watermark(state, video_id, newest_for_video)
            if newest_seen_overall is None or newest_for_video > newest_seen_overall:
                newest_seen_overall = newest_for_video
            print(f"  [{i}/{len(known_video_ids)}] {video_id} — {detail['title'][:50]!r}: "
                  f"{video_new_count} new comment(s) (pool={len(pool)}, sampling={sampling_method})")

        incremental_state.save_state(state, DATA_DIR)
        time.sleep(0.2)  # be polite to the API

    if skipped_irrelevant:
        known_gaps.append(f"{skipped_irrelevant} video(s) skipped by the Quota-Triage Pre-filter — see {SKIPPED_VIDEOS_PATH.name}.")

    OUTPUT_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL_PATH, "a", encoding="utf-8") as f:
        for record in new_records:
            f.write(record.to_json_line() + "\n")
    append_csv_rows(new_records)
    if new_records:
        export_to_raw_harmonized(new_records)

    if newest_seen_overall:
        incremental_state.update_global_search_watermark(state, newest_seen_overall, OVERLAP_BUFFER_SECONDS)

    finished_at_utc = _utc_now_rfc3339()
    incremental_state.record_run(state, collection_run_id, len(new_records))
    incremental_state.save_state(state, DATA_DIR)

    if buckets:
        write_manifest(buckets, collection_run_id, started_at_utc, finished_at_utc,
                        active_queries, registry_version, skipped_irrelevant, error_count)

    print(f"\nWrote {len(new_records)} new record(s) to {OUTPUT_JSONL_PATH.name} + {OUTPUT_CSV_PATH.name}")
    print(f"Manifest: {MANIFEST_PATH.name} ({len(buckets)} query x week row(s) this run)")
    print(f"Skipped-video log: {SKIPPED_VIDEOS_PATH.name} ({skipped_irrelevant} this run)")
    print(f"Quota used today: {state['quota_used_today']}/{checkpoint.MAX_DAILY_QUOTA}")
    if known_gaps:
        print("Known gaps this run:")
        for gap in known_gaps:
            print(f"  - {gap}")


def _load_existing_content_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            content_id = record.get("content_id")
            if content_id:
                ids.add(content_id)
    return ids


if __name__ == "__main__":
    main()
