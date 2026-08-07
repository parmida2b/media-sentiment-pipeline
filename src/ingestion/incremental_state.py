"""
incremental_state.py — watermark-based resumable state for
youtube_extract_incremental.py (Parmida)

Deliberately separate from the discovery/fetch state checkpoint.py already
tracks for youtube_extract.py (v1) - this module never touches the
`discovered` / `comments_fetched` / `geo_tagged` keys v1 owns.

It DOES reuse checkpoint.py's load/save/has_budget/spend for quota
accounting (quota_used_today / quota_date_pt), because that tracks a real
shared constraint: both scripts hit the same YouTube API key's daily quota,
so two independent counters would let them collectively overspend it. This
module just adds its own namespaced keys (under STATE_KEY) to the same
checkpoint.json.

v2 doesn't need a persistent "have we searched this query+region combo
before" flag the way v1 does: v2's discovery search always uses
`publishedAfter=<current watermark>`, so each run's search is naturally
scoped to the new time window already - safe and cheap to just re-run every
time rather than caching "already searched" forever.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import checkpoint

STATE_KEY = "v2_incremental"


def _empty_v2_state(default_watermark_iso: str) -> dict:
    return {
        "global_search_watermark": default_watermark_iso,
        "known_video_ids": [],
        "video_comment_watermarks": {},  # video_id -> ISO8601 UTC of the newest comment fetched so far for that video
        "last_run_completed_at_utc": None,
        "run_history": [],  # [{collection_run_id, completed_at_utc, records_received}, ...]
    }


def load_state(data_dir: Path, default_watermark_iso: str) -> dict:
    """Loads the shared checkpoint.json and ensures the v2 namespace exists."""
    state = checkpoint.load_checkpoint(data_dir)
    if STATE_KEY not in state:
        state[STATE_KEY] = _empty_v2_state(default_watermark_iso)
    return state


def save_state(state: dict, data_dir: Path) -> None:
    checkpoint.save_checkpoint(state, data_dir)


def v2(state: dict) -> dict:
    """Shorthand accessor for this module's namespace within the shared state dict."""
    return state[STATE_KEY]


def mark_video_known(state: dict, video_id: str) -> None:
    known = v2(state)["known_video_ids"]
    if video_id not in known:
        known.append(video_id)


def get_video_watermark(state: dict, video_id: str, fallback_iso: str) -> str:
    return v2(state)["video_comment_watermarks"].get(video_id, fallback_iso)


def update_video_watermark(state: dict, video_id: str, newest_comment_iso: str) -> None:
    watermarks = v2(state)["video_comment_watermarks"]
    current = watermarks.get(video_id)
    if current is None or newest_comment_iso > current:
        watermarks[video_id] = newest_comment_iso


def update_global_search_watermark(state: dict, newest_seen_iso: str, overlap_buffer_seconds: int) -> None:
    """Advances the discovery-search cursor to just before the newest content
    seen this run, minus a buffer (comment moderation/indexing can lag, so a
    small re-check window each run catches stragglers; content_id dedup at
    write time makes the overlap safe)."""
    v2_state = v2(state)
    current = v2_state["global_search_watermark"]
    newest_dt = datetime.strptime(newest_seen_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    buffered = (newest_dt - timedelta(seconds=overlap_buffer_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if buffered > current:
        v2_state["global_search_watermark"] = buffered


def record_run(state: dict, collection_run_id: str, records_received: int) -> None:
    v2_state = v2(state)
    v2_state["last_run_completed_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    v2_state["run_history"].append({
        "collection_run_id": collection_run_id,
        "completed_at_utc": v2_state["last_run_completed_at_utc"],
        "records_received": records_received,
    })
