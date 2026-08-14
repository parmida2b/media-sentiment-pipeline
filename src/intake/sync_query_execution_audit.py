"""
sync_query_execution_audit.py — docs/checklist.md item 4 (Collector/Run Log audit).

Converts a platform's real, structured Run Log into
docs/query_execution_audit_template.csv's row shape and appends any rows not
already present in docs/query_execution_audit.csv (matched by
(collection_run_id, query_id) — never re-appends, never rewrites existing
rows, never guesses a missing value).

Currently wired for YouTube only: data/raw/iran_us_war/youtube_runs.csv is a
real, structured Run Log (youtube_extract.py's write_manifest(), see its
MANIFEST_COLUMNS). Reddit (reddit_raw_json_pipeline.py /
reddit_parent_post_collector.py) and X (x_scraper.py) do not write an
equivalent structured per-query run log as of 2026-08-14 — their rows in
docs/query_execution_audit.csv were reconstructed from Jobs/Subruns sheets
inside the delivered handoff file (X) or are simply absent (Reddit); that gap
is documented in docs/reference_file_determination.md, not silently filled
here.

Field mapping (youtube_runs.csv -> query_execution_audit_template.csv):
  collection_run_id          -> collection_run_id
  platform                   -> platform
  query_version               -> assigned_query_registry_version
  query_id                   -> query_id
  query_text                 -> assigned_query AND executed_query (YouTube's
                                 search.list takes one plain query string --
                                 unlike X's live search operators, there is no
                                 separately-logged "as typed" vs "as executed"
                                 variant, so both columns get the same value;
                                 noted in `notes`)
  project_week                -> requested_start_utc/requested_end_utc, via
                                 project_calendar.START + the week's 7-day
                                 span (the run log itself only stores the
                                 week label, not the literal date-window
                                 bounds that were requested)
  sort_mode                  -> sort_mode
  sampling_cap                -> cap
  records_sampled_out         -> pagination_status ("capped" if >0 else
                                 "not_capped"; youtube_runs.csv has no
                                 separate page-token/scroll-count field)
  error_count                 -> execution_status ("error" if >0 else "done")
  (everything else)           -> notes (discovery_route, source_id,
                                 returned_count, stored_count,
                                 records_in_window, oldest/newest_record_utc,
                                 quota_consumed, error_count,
                                 prefiltered_sources_count/log_ref)

Usage:
    python src/intake/sync_query_execution_audit.py --platform youtube
    python src/intake/sync_query_execution_audit.py --platform youtube --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "ingestion"))
import project_calendar  # noqa: E402

RUN_LOG_PATHS = {
    "youtube": REPO_ROOT / "data" / "raw" / "iran_us_war" / "youtube_runs.csv",
}
AUDIT_PATH = REPO_ROOT / "docs" / "query_execution_audit.csv"
AUDIT_COLUMNS = [
    "collection_run_id", "platform", "assigned_query_registry_version", "query_id",
    "assigned_query", "executed_query", "requested_start_utc", "requested_end_utc",
    "sort_mode", "cap", "pagination_status", "execution_status", "evidence_source",
    "evidence_path", "notes",
]


def week_bounds(week_label: str) -> tuple[str, str]:
    """project_week (e.g. 'W03') -> (requested_start_utc, requested_end_utc)
    date strings, using the same 7-day span project_calendar.py defines.
    'OUT' or unrecognized labels return ('unknown', 'unknown') -- not guessed."""
    if not week_label or not week_label.startswith("W") or not week_label[1:].isdigit():
        return "unknown", "unknown"
    w = int(week_label[1:])
    start = project_calendar.START + timedelta(days=(w - 1) * 7)
    end = min(start + timedelta(days=6), project_calendar.END)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def row_hash(r: dict) -> str:
    """Stable hash of a run-log row's own full content (all fields, in the
    run log's own column order) -- NOT just (collection_run_id, query_id):
    youtube_runs.csv logs one row per (query x source/channel x region)
    execution, so many legitimate distinct rows share the same
    collection_run_id+query_id (e.g. 22 rows for one run_id with a blank
    query_id -- curated-channel discovery, no search query). Keying on the
    full row means only an exact repeated line collapses, never two
    genuinely different executions."""
    payload = "\x1f".join(f"{k}={r.get(k, '')}" for k in sorted(r))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def convert_row(r: dict) -> dict:
    req_start, req_end = week_bounds(r.get("project_week", ""))
    records_sampled_out = (r.get("records_sampled_out") or "0").strip() or "0"
    error_count = (r.get("error_count") or "0").strip() or "0"
    try:
        capped = int(records_sampled_out) > 0
    except ValueError:
        capped = False
    try:
        has_error = int(error_count) > 0
    except ValueError:
        has_error = False

    notes_bits = [
        f"project_week={r.get('project_week', 'unknown')}",
        f"discovery_route={r.get('discovery_route', 'unknown')}",
        f"source_id={r.get('source_id', 'unknown')}",
        f"returned_count={r.get('returned_count', 'unknown')}",
        f"stored_count={r.get('stored_count', 'unknown')}",
        f"records_in_window={r.get('records_in_window', 'unknown')}",
        f"records_sampled_out={records_sampled_out}",
        f"oldest_record_utc={r.get('oldest_record_utc', 'unknown')}",
        f"newest_record_utc={r.get('newest_record_utc', 'unknown')}",
        f"quota_consumed={r.get('quota_consumed', 'unknown')}",
        f"error_count={error_count}",
        f"prefiltered_sources_count={r.get('prefiltered_sources_count', 'unknown')}",
        f"prefiltered_sources_log_ref={r.get('prefiltered_sources_log_ref', 'unknown')}",
        f"started_at_utc={r.get('started_at_utc', 'unknown')}",
        f"finished_at_utc={r.get('finished_at_utc', 'unknown')}",
        "assigned_query==executed_query: youtube_runs.csv logs one query_text field, "
        "no separate as-typed vs as-executed variant (search.list takes a single string)",
    ]
    if r.get("notes"):
        notes_bits.append(f"run_log_notes={r['notes']}")
    notes_bits.append(f"source_row_hash={row_hash(r)}")

    return {
        "collection_run_id": r.get("collection_run_id", ""),
        "platform": r.get("platform", ""),
        "assigned_query_registry_version": r.get("query_version", "unknown"),
        "query_id": r.get("query_id", ""),
        "assigned_query": r.get("query_text", ""),
        "executed_query": r.get("query_text", ""),
        "requested_start_utc": req_start,
        "requested_end_utc": req_end,
        "sort_mode": r.get("sort_mode", "unknown"),
        "cap": r.get("sampling_cap", "unknown"),
        "pagination_status": "capped" if capped else "not_capped",
        "execution_status": "error" if has_error else "done",
        "evidence_source": "youtube_runs.csv",
        "evidence_path": "data/raw/iran_us_war/youtube_runs.csv",
        "notes": "; ".join(notes_bits),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True, choices=sorted(RUN_LOG_PATHS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_log_path = RUN_LOG_PATHS[args.platform]
    if not run_log_path.exists():
        print(f"No run log found at {run_log_path} for platform={args.platform} — nothing to sync.")
        return 1

    with run_log_path.open("r", encoding="utf-8-sig", newline="") as f:
        run_rows = list(csv.DictReader(f))
    print(f"Read {len(run_rows)} row(s) from {run_log_path}")

    with AUDIT_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or AUDIT_COLUMNS
        existing_rows = list(reader)
    # Idempotency key: a source_row_hash=... marker embedded in `notes` by a
    # previous run of THIS script (see row_hash()) -- not (collection_run_id,
    # query_id), which is not unique per real execution for this run log.
    existing_hashes = {
        bit.split("=", 1)[1]
        for r in existing_rows
        for bit in (r.get("notes") or "").split("; ")
        if bit.startswith("source_row_hash=")
    }

    new_rows = []
    seen_this_run: set[str] = set()
    for r in run_rows:
        h = row_hash(r)
        if h in existing_hashes or h in seen_this_run:
            continue
        new_rows.append(convert_row(r))
        seen_this_run.add(h)

    print(f"{len(new_rows)} new row(s) {'would be ' if args.dry_run else ''}appended "
          f"(platform={args.platform}); {len(run_rows) - len(new_rows)} already present.")

    if new_rows and not args.dry_run:
        with AUDIT_PATH.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            for row in new_rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        print(f"Appended to {AUDIT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
