from __future__ import annotations

import csv
import json
import math
import re
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily

from reddit_live import (
    COMMENTS_FILE,
    COMMENTS_WINDOW_FILE,
    FETCH_LOG_FILE,
    MASTER_PARENT_FILE,
    RAW_JSON_DIR,
    fetch_log_rows,
    parent_source_files,
    reddit_handoff_stats,
    unique_parent_rows,
)
from settings import LOG_DIR, BUILD_ID


ERROR_PATTERNS = (
    re.compile(r"\bERROR\b", re.I),
    re.compile(r"Traceback \(most recent call last\)", re.I),
    re.compile(r"\bException\b", re.I),
)
WARNING_PATTERNS = (
    re.compile(r"\bWARN(?:ING)?\b", re.I),
    re.compile(r"timeout", re.I),
    re.compile(r"rate.?limit", re.I),
)


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except Exception:
        return None


def _latest_mtime(paths) -> float | None:
    values = [x for x in (_mtime(p) for p in paths) if x is not None]
    return max(values) if values else None


def _age(ts: float | None, now: float) -> float | None:
    if ts is None:
        return None
    return max(0.0, now - ts)


def _tail_counts(path: Path, max_lines: int = 2500) -> dict[str, int]:
    if not path.exists():
        return {"errors": 0, "warnings": 0}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
    except Exception:
        return {"errors": 0, "warnings": 0}
    # Keep health local to the latest overlay run instead of carrying old errors forever.
    starts = [i for i, line in enumerate(lines) if "===== OVERLAY START" in line]
    if starts:
        lines = lines[starts[-1]:]
    errors = sum(any(p.search(line) for p in ERROR_PATTERNS) for line in lines)
    warnings = sum(any(p.search(line) for p in WARNING_PATTERNS) for line in lines)
    return {"errors": int(errors), "warnings": int(warnings)}


def _safe_process(processes: Mapping | None, name: str) -> dict:
    row = dict((processes or {}).get(name) or {})
    return {
        "running": bool(row.get("running")),
        "pid": row.get("pid"),
        "last_status": row.get("last_status") or "unknown",
        "exit_code": row.get("exit_code"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "duration": row.get("duration"),
    }


def build_reddit_realtime_snapshot(
    process_provider: Callable[[], Mapping] | None = None,
    chain_provider: Callable[[], Mapping] | None = None,
) -> dict:
    """Build a read-only Reddit observability snapshot from native pipeline outputs.

    Nothing in this function writes to the group pipeline. It is intentionally
    computed from the native parent CSVs, audit CSVs, raw JSON files and overlay
    process metadata so every Prometheus scrape reflects the current filesystem.
    """
    now = time.time()
    handoff = reddit_handoff_stats()
    parents = unique_parent_rows()
    fetches = fetch_log_rows()
    process_map = process_provider() if process_provider else {}
    chain = dict(chain_provider() if chain_provider else {})

    parent_files = parent_source_files()
    raw_files = list(RAW_JSON_DIR.glob("*.json")) if RAW_JSON_DIR.exists() else []

    parent_by_subreddit = Counter()
    parent_by_query = Counter()
    for row in parents:
        subreddit = (row.get("subreddit") or row.get("source_container") or "unknown").strip() or "unknown"
        query_id = (row.get("query_id") or "unknown").strip() or "unknown"
        parent_by_subreddit[subreddit] += 1
        parent_by_query[query_id] += 1

    fetch_status = Counter()
    for row in fetches:
        fetch_status[(row.get("status") or "unknown").strip() or "unknown"] += 1

    success = sum(n for st, n in fetch_status.items() if st == "saved_raw_json")
    skipped = sum(n for st, n in fetch_status.items() if st.startswith("skip_"))
    failed = sum(
        n
        for st, n in fetch_status.items()
        if st not in {"saved_raw_json"} and not st.startswith("skip_")
    )

    parent_ts = _latest_mtime(parent_files)
    raw_ts = _latest_mtime(raw_files)
    fetch_ts = _mtime(FETCH_LOG_FILE)
    final_comments_ts = _mtime(COMMENTS_FILE)
    window_comments_ts = _mtime(COMMENTS_WINDOW_FILE)
    master_ts = _mtime(MASTER_PARENT_FILE)

    discovery = _safe_process(process_map, "reddit_discovery")
    comments = _safe_process(process_map, "reddit_comments")
    chain_running = bool(chain.get("running"))
    any_running = discovery["running"] or comments["running"] or chain_running

    dlog = _tail_counts(LOG_DIR / "reddit_discovery.log")
    clog = _tail_counts(LOG_DIR / "reddit_comments.log")

    process_failed = any(
        p.get("last_status") == "failed" for p in (discovery, comments)
    ) or chain.get("last_status") == "failed"

    # When a collector is actively running, a stale output is a useful health signal.
    # Five minutes is deliberately conservative because Selenium may legitimately wait.
    running_stale = False
    if discovery["running"] and parent_ts is not None and _age(parent_ts, now) > 300:
        running_stale = True
    if comments["running"]:
        activity_ts = max([x for x in (raw_ts, fetch_ts) if x is not None], default=None)
        if activity_ts is not None and _age(activity_ts, now) > 300:
            running_stale = True

    health_ok = not process_failed and not running_stale
    health_state = "healthy" if health_ok else ("stale" if running_stale else "failed")

    raw_bytes = 0
    for p in raw_files:
        try:
            raw_bytes += p.stat().st_size
        except Exception:
            pass

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_timestamp": now,
        "health": {
            "ok": health_ok,
            "state": health_state,
            "process_failed": process_failed,
            "running_stale": running_stale,
            "active": any_running,
        },
        "counts": {
            "parent_files": int(handoff.get("parent_files") or 0),
            "parent_rows": int(handoff.get("parent_rows") or 0),
            "parent_unique": int(handoff.get("parent_unique") or 0),
            "master_unique": int(handoff.get("master_unique") or 0),
            "eligible": int(handoff.get("eligible") or 0),
            "pending_json": int(handoff.get("pending_json") or 0),
            "raw_json_files": int(handoff.get("raw_json_files") or 0),
            "raw_json_bytes": int(raw_bytes),
            "fetch_events": int(handoff.get("fetch_log_rows") or 0),
            "fetch_success": int(success),
            "fetch_failed": int(failed),
            "fetch_skipped": int(skipped),
            "comments_live": int(handoff.get("comments_live_raw_json") or 0),
            "comments_final": int(handoff.get("comments_final") or 0),
            "comments_window": int(handoff.get("comments_window_final") or 0),
        },
        "fetch_status": dict(fetch_status),
        "parent_by_subreddit": dict(parent_by_subreddit),
        "parent_by_query": dict(parent_by_query),
        "freshness": {
            "parent_posts": {"timestamp": parent_ts, "age_seconds": _age(parent_ts, now)},
            "master_parent": {"timestamp": master_ts, "age_seconds": _age(master_ts, now)},
            "raw_json": {"timestamp": raw_ts, "age_seconds": _age(raw_ts, now)},
            "fetch_log": {"timestamp": fetch_ts, "age_seconds": _age(fetch_ts, now)},
            "comments_final": {"timestamp": final_comments_ts, "age_seconds": _age(final_comments_ts, now)},
            "comments_window": {"timestamp": window_comments_ts, "age_seconds": _age(window_comments_ts, now)},
        },
        "processes": {
            "discovery": discovery,
            "json_comments": comments,
            "full_flow": {
                "running": chain_running,
                "last_status": chain.get("last_status") or "unknown",
                "stage": chain.get("stage") or "idle",
                "message": chain.get("message") or "",
            },
        },
        "logs": {
            "discovery": dlog,
            "json_comments": clog,
        },
    }


class RedditRealtimeCollector:
    """Dynamic collector: values are recomputed on *every* Prometheus scrape."""

    def __init__(self, process_provider=None, chain_provider=None):
        self.process_provider = process_provider
        self.chain_provider = chain_provider

    def collect(self):
        s = build_reddit_realtime_snapshot(self.process_provider, self.chain_provider)
        c = s["counts"]

        yield GaugeMetricFamily("reddit_realtime_exporter_up", "1 when the Reddit realtime collector can build a snapshot", value=1)
        build_info = GaugeMetricFamily(
            "reddit_realtime_build_info",
            "Identity of the Control Center / Reddit realtime exporter build",
            labels=["build_id"],
        )
        build_info.add_metric([BUILD_ID], 1)
        yield build_info
        yield GaugeMetricFamily("reddit_realtime_system_health", "1 when Reddit monitoring sees no failed/stale active stage", value=1 if s["health"]["ok"] else 0)
        yield GaugeMetricFamily("reddit_realtime_active", "1 when any Reddit stage/full flow is running", value=1 if s["health"]["active"] else 0)
        yield GaugeMetricFamily("reddit_realtime_snapshot_timestamp_seconds", "Unix timestamp of this scrape snapshot", value=s["generated_at_timestamp"])

        simple = {
            "reddit_realtime_parent_files": ("Native Reddit parent CSV files", c["parent_files"]),
            "reddit_realtime_parent_rows": ("Rows across native Reddit parent CSV files", c["parent_rows"]),
            "reddit_realtime_parent_posts": ("Unique Reddit parent posts discovered", c["parent_unique"]),
            "reddit_realtime_json_eligible": ("Parent posts eligible for JSON collection", c["eligible"]),
            "reddit_realtime_json_pending": ("Eligible Reddit JSON URLs still pending", c["pending_json"]),
            "reddit_realtime_raw_json_files": ("Native raw Reddit JSON files saved", c["raw_json_files"]),
            "reddit_realtime_raw_json_bytes": ("Bytes in native raw Reddit JSON files", c["raw_json_bytes"]),
            "reddit_realtime_fetch_events": ("Native Reddit JSON fetch-log rows", c["fetch_events"]),
            "reddit_realtime_fetch_success": ("Successful raw JSON saves", c["fetch_success"]),
            "reddit_realtime_fetch_failed": ("JSON fetch events that are neither success nor skip", c["fetch_failed"]),
            "reddit_realtime_fetch_skipped": ("JSON fetch events skipped by native pipeline", c["fetch_skipped"]),
            "reddit_realtime_comments_live": ("Comments visible by read-only parsing of saved raw JSON", c["comments_live"]),
            "reddit_realtime_comments_final": ("Rows in native comments_from_raw_json.csv", c["comments_final"]),
            "reddit_realtime_comments_window": ("Rows in native comments_project_window.csv", c["comments_window"]),
        }
        for name, (help_text, value) in simple.items():
            yield GaugeMetricFamily(name, help_text, value=value)

        fetch_family = GaugeMetricFamily(
            "reddit_realtime_fetch_status",
            "JSON fetch events grouped by native pipeline status",
            labels=["status"],
        )
        for status, value in sorted(s["fetch_status"].items()):
            fetch_family.add_metric([status], value)
        yield fetch_family

        subreddit_family = GaugeMetricFamily(
            "reddit_realtime_parent_posts_by_subreddit",
            "Unique discovered parent posts grouped by subreddit",
            labels=["subreddit"],
        )
        for subreddit, value in sorted(s["parent_by_subreddit"].items()):
            subreddit_family.add_metric([subreddit], value)
        yield subreddit_family

        query_family = GaugeMetricFamily(
            "reddit_realtime_parent_posts_by_query",
            "Unique discovered parent posts grouped by query_id",
            labels=["query_id"],
        )
        for query_id, value in sorted(s["parent_by_query"].items()):
            query_family.add_metric([query_id], value)
        yield query_family

        freshness_family = GaugeMetricFamily(
            "reddit_realtime_output_age_seconds",
            "Age in seconds of the latest native Reddit output by output kind",
            labels=["output"],
        )
        timestamp_family = GaugeMetricFamily(
            "reddit_realtime_output_timestamp_seconds",
            "Unix mtime of latest native Reddit output by output kind",
            labels=["output"],
        )
        for output, row in sorted(s["freshness"].items()):
            age = row.get("age_seconds")
            ts = row.get("timestamp")
            if age is not None and not math.isnan(age):
                freshness_family.add_metric([output], age)
            if ts is not None:
                timestamp_family.add_metric([output], ts)
        yield freshness_family
        yield timestamp_family

        proc_running = GaugeMetricFamily(
            "reddit_realtime_process_running",
            "1 when the Reddit process/stage is running",
            labels=["stage"],
        )
        proc_exit = GaugeMetricFamily(
            "reddit_realtime_process_last_exit_code",
            "Last exit code for a Reddit subprocess",
            labels=["stage"],
        )
        proc_started = GaugeMetricFamily(
            "reddit_realtime_process_started_timestamp_seconds",
            "Last start Unix timestamp for a Reddit subprocess",
            labels=["stage"],
        )
        for stage in ("discovery", "json_comments"):
            row = s["processes"][stage]
            proc_running.add_metric([stage], 1 if row.get("running") else 0)
            if row.get("exit_code") is not None:
                proc_exit.add_metric([stage], row["exit_code"])
            if row.get("started_at") is not None:
                proc_started.add_metric([stage], row["started_at"])
        proc_running.add_metric(["full_flow"], 1 if s["processes"]["full_flow"].get("running") else 0)
        yield proc_running
        yield proc_exit
        yield proc_started

        log_errors = GaugeMetricFamily(
            "reddit_realtime_log_error_lines",
            "Error-like lines in the recent overlay log tail",
            labels=["collector"],
        )
        log_warnings = GaugeMetricFamily(
            "reddit_realtime_log_warning_lines",
            "Warning/timeout-like lines in the recent overlay log tail",
            labels=["collector"],
        )
        for collector, row in s["logs"].items():
            log_errors.add_metric([collector], row.get("errors", 0))
            log_warnings.add_metric([collector], row.get("warnings", 0))
        yield log_errors
        yield log_warnings


_REGISTER_LOCK = threading.Lock()
_REGISTERED = False


def register_reddit_realtime_collector(process_provider=None, chain_provider=None):
    global _REGISTERED
    with _REGISTER_LOCK:
        if not _REGISTERED:
            REGISTRY.register(RedditRealtimeCollector(process_provider, chain_provider))
            _REGISTERED = True


def start_reddit_realtime_metrics_server(port: int, process_provider=None, chain_provider=None):
    """Start a Prometheus server explicitly on all interfaces for Docker Desktop.

    The values are dynamic on scrape; no background cache is involved for the
    reddit_realtime_* series.
    """
    register_reddit_realtime_collector(process_provider, chain_provider)
    return start_http_server(port, addr="0.0.0.0", registry=REGISTRY)
