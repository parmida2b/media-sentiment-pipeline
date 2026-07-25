"""
checkpoint.py — resumable state + quota-budget tracking for youtube_extract.py (Parmida)

YouTube Data API v3 quota resets at midnight Pacific Time, not local
midnight, and search.list (100 units) is ~100x the cost of videos.list or
commentThreads.list (1 unit each). This module lets a single logical
extraction job span multiple process runs / calendar days by persisting:
  - which (channel/query, regionCode) combos have already been searched
    (the expensive part), separately from
  - which discovered video_ids have had comments fetched / geo-tagged
    (the cheap part) —
so if the search budget runs out mid-run, a rerun can still spend the
remaining budget fetching comments for already-discovered videos instead
of stopping dead.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "checkpoint.json"

QUOTA_COSTS = {
    "search": 100,
    "videos_list": 1,
    "comment_threads": 1,
    "channels_list": 1,
}

MAX_DAILY_QUOTA = int(os.getenv("YOUTUBE_DAILY_QUOTA_BUDGET", "8000"))

PT = ZoneInfo("America/Los_Angeles")


def _today_pt() -> str:
    return datetime.now(PT).date().isoformat()


def _empty_state() -> dict:
    return {
        "quota_date_pt": _today_pt(),
        "quota_used_today": 0,
        "discovered": {},       # combo_key -> list[video_id]
        "comments_fetched": [], # list[video_id]
        "geo_tagged": [],       # list[video_id]
    }


def load_checkpoint() -> dict:
    if not CHECKPOINT_PATH.exists():
        return _empty_state()

    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    if state.get("quota_date_pt") != _today_pt():
        # Google's quota reset happened since we last ran — start today's
        # spend counter over, but keep discovered/fetched progress.
        state["quota_date_pt"] = _today_pt()
        state["quota_used_today"] = 0

    return state


def save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CHECKPOINT_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # On Windows, cloud-sync clients (OneDrive) or antivirus real-time
    # scanning can briefly hold a lock on CHECKPOINT_PATH, making
    # os.replace fail with a transient PermissionError (WinError 5)
    # even though nothing is actually wrong. Retry a few times before
    # giving up, since this is a resumable job and losing a checkpoint
    # write mid-run would silently drop discovery progress.
    last_error = None
    for attempt in range(5):
        try:
            os.replace(tmp_path, CHECKPOINT_PATH)
            return
        except PermissionError as e:
            last_error = e
            time.sleep(0.2 * (attempt + 1))
    raise last_error


def has_budget(state: dict, cost: int) -> bool:
    return state["quota_used_today"] + cost <= MAX_DAILY_QUOTA


def spend(state: dict, cost: int) -> None:
    state["quota_used_today"] += cost


def mark_discovered(state: dict, combo_key: str, video_ids: list[str]) -> None:
    state["discovered"][combo_key] = video_ids


def all_discovered_video_ids(state: dict) -> list[str]:
    seen = []
    seen_set = set()
    for video_ids in state["discovered"].values():
        for vid in video_ids:
            if vid not in seen_set:
                seen_set.add(vid)
                seen.append(vid)
    return seen


def mark_comments_fetched(state: dict, video_id: str) -> None:
    if video_id not in state["comments_fetched"]:
        state["comments_fetched"].append(video_id)


def mark_geo_tagged(state: dict, video_id: str) -> None:
    if video_id not in state["geo_tagged"]:
        state["geo_tagged"].append(video_id)
