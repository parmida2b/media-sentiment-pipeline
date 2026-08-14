from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from settings import PIPELINE_ROOT

PARENT_DIR = PIPELINE_ROOT / "data" / "raw" / "reddit" / "parent_posts"
AUDIT_DIR = PIPELINE_ROOT / "data" / "interim" / "reddit" / "raw_json_audit"
RAW_JSON_DIR = AUDIT_DIR / "raw_reddit_json"
MASTER_PARENT_FILE = AUDIT_DIR / "master_parent_posts_dedup.csv"
FETCH_LOG_FILE = AUDIT_DIR / "raw_json_fetch_log.csv"
COMMENTS_FILE = AUDIT_DIR / "comments_from_raw_json.csv"
COMMENTS_WINDOW_FILE = AUDIT_DIR / "comments_project_window.csv"


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return 0


def build_json_url(post_url: str) -> str:
    if not post_url:
        return ""
    parts = urlsplit(post_url)
    path = parts.path.rstrip("/")
    if not path.endswith(".json"):
        path += ".json"
    return urlunsplit(("https", "www.reddit.com", path, "", ""))


def parent_source_files() -> list[Path]:
    if not PARENT_DIR.exists():
        return []
    return sorted(PARENT_DIR.glob("*_reddit_parent_posts.csv"))


def unique_parent_rows() -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for path in parent_source_files():
        for row in _csv_rows(path):
            post_id = (row.get("post_id") or row.get("platform_content_id") or "").strip()
            if not post_id:
                continue
            old = merged.get(post_id)
            if old is None or (row.get("collected_at_utc") or "") >= (old.get("collected_at_utc") or ""):
                item = dict(row)
                item["source_file"] = path.name
                item["json_url"] = build_json_url(item.get("url") or "")
                merged[post_id] = item
    rows = list(merged.values())
    rows.sort(key=lambda r: (r.get("collected_at_utc") or r.get("created_at_utc") or ""), reverse=True)
    return rows


def master_parent_rows() -> list[dict[str, str]]:
    rows = _csv_rows(MASTER_PARENT_FILE)
    for row in rows:
        row["json_url"] = build_json_url(row.get("url") or "")
    return rows


def fetch_log_rows() -> list[dict[str, str]]:
    rows = _csv_rows(FETCH_LOG_FILE)
    rows.sort(key=lambda r: (r.get("finished_at_utc") or r.get("started_at_utc") or ""), reverse=True)
    return rows


def _iso_utc(value) -> str:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _walk_comments(children, post_id: str, subreddit: str, out: list[dict]):
    if not isinstance(children, list):
        return
    for child in children:
        if not isinstance(child, dict) or child.get("kind") != "t1":
            continue
        data = child.get("data") or {}
        comment_id = str(data.get("id") or "")
        out.append({
            "comment_id": comment_id,
            "post_id": post_id,
            "subreddit": str(data.get("subreddit") or subreddit or ""),
            "author": str(data.get("author") or ""),
            "comment": str(data.get("body") or ""),
            "comment_created_at_utc": _iso_utc(data.get("created_utc")),
            "score": data.get("score", ""),
            "depth": data.get("depth", ""),
            "parent_id": str(data.get("parent_id") or ""),
            "is_top_level": str(data.get("parent_id") or "").startswith("t3_"),
        })
        replies = data.get("replies")
        if isinstance(replies, dict):
            _walk_comments(((replies.get("data") or {}).get("children") or []), post_id, subreddit, out)


def parse_raw_json_for_live(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    post_id = path.stem
    subreddit = ""
    try:
        submission = (((payload[0] or {}).get("data") or {}).get("children") or [])[0].get("data") or {}
        post_id = str(submission.get("id") or post_id)
        subreddit = str(submission.get("subreddit") or "")
    except Exception:
        pass
    children = ((payload[1] or {}).get("data") or {}).get("children") or []
    out: list[dict] = []
    _walk_comments(children, post_id, subreddit, out)
    return out


def recent_live_comments(limit: int = 50, max_files: int = 30) -> list[dict]:
    if not RAW_JSON_DIR.exists():
        return []
    files = sorted(RAW_JSON_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    comments: list[dict] = []
    for path in files:
        rows = parse_raw_json_for_live(path)
        comments.extend(rows)
        if len(comments) >= max(limit * 3, limit):
            break
    comments.sort(key=lambda r: r.get("comment_created_at_utc") or "", reverse=True)
    return comments[:limit]


_RAW_COMMENT_COUNT_CACHE: dict[str, tuple[int, int, int]] = {}

def raw_json_comment_count() -> int:
    """Count comments visible in native raw JSON files with an mtime/size cache.

    This is a read-only live projection for monitoring; it does not replace the
    pipeline's native comments_from_raw_json.csv output.
    """
    if not RAW_JSON_DIR.exists():
        _RAW_COMMENT_COUNT_CACHE.clear()
        return 0
    active=set()
    total=0
    for path in RAW_JSON_DIR.glob("*.json"):
        key=str(path)
        active.add(key)
        try:
            st=path.stat(); sig=(st.st_mtime_ns,st.st_size)
        except Exception:
            continue
        cached=_RAW_COMMENT_COUNT_CACHE.get(key)
        if cached and cached[:2]==sig:
            count=cached[2]
        else:
            count=len(parse_raw_json_for_live(path))
            _RAW_COMMENT_COUNT_CACHE[key]=(sig[0],sig[1],count)
        total += count
    for key in list(_RAW_COMMENT_COUNT_CACHE):
        if key not in active:
            _RAW_COMMENT_COUNT_CACHE.pop(key,None)
    return total

def reddit_handoff_stats() -> dict:
    source_files = parent_source_files()
    unique = unique_parent_rows()
    master = master_parent_rows()
    eligible_rows = [r for r in master if str(r.get("eligible_for_json_collection", "")).lower() == "true"]
    raw_files = list(RAW_JSON_DIR.glob("*.json")) if RAW_JSON_DIR.exists() else []
    raw_ids = {p.stem for p in raw_files}
    pending = [r for r in eligible_rows if (r.get("post_id") or "") not in raw_ids]
    fetches = fetch_log_rows()
    status_counts: dict[str, int] = {}
    for row in fetches:
        status = (row.get("status") or "unknown").strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "parent_files": len(source_files),
        "parent_rows": sum(_count_rows(p) for p in source_files),
        "parent_unique": len(unique),
        "master_ready": MASTER_PARENT_FILE.exists(),
        "master_unique": len(master),
        "eligible": len(eligible_rows) if MASTER_PARENT_FILE.exists() else None,
        "raw_json_files": len(raw_files),
        "pending_json": len(pending) if MASTER_PARENT_FILE.exists() else None,
        "fetch_log_rows": len(fetches),
        "fetch_status": status_counts,
        "comments_live_raw_json": raw_json_comment_count(),
        "comments_final": _count_rows(COMMENTS_FILE),
        "comments_window_final": _count_rows(COMMENTS_WINDOW_FILE),
        "parent_dir": str(PARENT_DIR.resolve()),
        "audit_dir": str(AUDIT_DIR.resolve()),
    }


def reddit_live_payload(limit: int = 40) -> dict:
    limit = max(5, min(int(limit), 100))
    parents = unique_parent_rows()[:limit]
    fetches = fetch_log_rows()[:limit]
    comments = recent_live_comments(limit=limit)
    return {
        "stats": reddit_handoff_stats(),
        "parents": parents,
        "fetches": fetches,
        "comments": comments,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
