"""
project_calendar.py — fixed project-window / project-week math (Parmida)

Pure, no I/O, no API calls. START/END and the project_week() function are
copied verbatim from docs/raw_schema_v03.md §10 — the whole point of this
module is that every collector (and later, preprocessing/analysis) computes
project_week/in_window/is_partial_week the SAME way, off the record's own
created_at_utc, independent of whatever config.yaml's date_range.end happens
to be set to at collection time (that field only controls how far collection
itself reaches "auto"/open-ended; it is deliberately NOT wired into this
module - see raw_schema_v03.md §10-1 "Window Lock").

Records collected with created_at_utc after END are not discarded - they are
kept with project_week="OUT", in_window=False (raw_schema_v03 §12 rule 4).
"""

from datetime import datetime, timezone

START = datetime(2026, 2, 28, tzinfo=timezone.utc)
END = datetime(2026, 7, 22, 23, 59, 59, tzinfo=timezone.utc)


def project_week(ts: datetime) -> tuple[str, bool, bool]:
    """returns (project_week, in_window, is_partial_week)"""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if not (START <= ts <= END):
        return "OUT", False, False
    w = (ts - START).days // 7 + 1
    return f"W{w:02d}", True, (w == 21)


def project_week_from_iso(iso_str: str) -> tuple[str, bool, bool]:
    """Convenience wrapper for the RFC3339 "%Y-%m-%dT%H:%M:%SZ" strings the
    YouTube API (and this project's Record.date/created_at_utc) use."""
    ts = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return project_week(ts)
