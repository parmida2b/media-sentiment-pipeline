"""
checkpoint.py — quota-budget tracking for youtube_extract.py (Parmida)

YouTube Data API v3 quota resets at midnight Pacific Time, not local
midnight, and search.list (100 units) is ~100x the cost of videos.list or
commentThreads.list (1 unit each). This module tracks how much of the daily
budget has been spent so a run can stop cleanly and a later run can pick up
where it left off, without ever overspending the real API's daily quota.

The v1 collector (retired - see docs/decision_log.md) used to also track
per-combo discovery state and per-video comments_fetched/geo_tagged flags
here; youtube_extract.py's incremental/watermark design (incremental_state.py)
replaced that, so this module is quota-tracking only now.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
    }


def load_checkpoint(data_dir: Path) -> dict:
    checkpoint_path = data_dir / "checkpoint.json"
    if not checkpoint_path.exists():
        return _empty_state()

    with open(checkpoint_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    if state.get("quota_date_pt") != _today_pt():
        # Google's quota reset happened since we last ran — start today's
        # spend counter over, but keep discovered/fetched progress.
        state["quota_date_pt"] = _today_pt()
        state["quota_used_today"] = 0

    return state


def save_checkpoint(state: dict, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = data_dir / "checkpoint.json"
    tmp_path = checkpoint_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # On Windows, cloud-sync clients (OneDrive) or antivirus real-time
    # scanning can briefly hold a lock on checkpoint_path, making
    # os.replace fail with a transient PermissionError (WinError 5)
    # even though nothing is actually wrong. Retry a few times before
    # giving up, since this is a resumable job and losing a checkpoint
    # write mid-run would silently drop discovery progress.
    last_error = None
    for attempt in range(5):
        try:
            os.replace(tmp_path, checkpoint_path)
            return
        except PermissionError as e:
            last_error = e
            time.sleep(0.2 * (attempt + 1))
    raise last_error


def has_budget(state: dict, cost: int) -> bool:
    return state["quota_used_today"] + cost <= MAX_DAILY_QUOTA


def spend(state: dict, cost: int) -> None:
    state["quota_used_today"] += cost
