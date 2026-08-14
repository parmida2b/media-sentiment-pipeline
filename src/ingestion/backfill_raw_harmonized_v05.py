"""
backfill_raw_harmonized_v05.py — one-time harmonization backfill for all
three platforms (YouTube, Reddit, X).

Context (see docs/decision_log.md 2026-08-14):
  - YouTube: export_to_raw_harmonized() exists in youtube_extract.py and
    is called for each incremental run going forward, but was NEVER run on
    the already-collected youtube_comments_v2.jsonl (~82,550 records).
  - Reddit/X: record_to_raw_harmonized_row() and export_to_raw_harmonized()
    were added to reddit_to_record.py and x_to_record.py in the same
    commit as this script (docs/checklist.md item 10).

What it does per platform:
  1. Reads the platform's JSONL from data/raw/{platform}/{file}.
  2. Reconstructs Record objects from the stored JSON (field-filtered to
     handle schema evolution between JSONL-write time and now).
  3. Passes each Record through the platform's record_to_raw_harmonized_row()
     (the "function from step 2" referenced in the task prompt).
  4. Writes Parquet to data/raw_harmonized/{platform}/:
       YouTube: one file per collection_run_id (mirrors live-collector
                convention); records with no run_id → 'backfill_youtube_orphan'
       Reddit:  single file 'backfill_reddit_v1'
       X:       single file 'backfill_x_v1'
  5. Prints the reconciliation equation required by docs/checklist.md §10:
       input_rows == harmonized_rows + parse_quarantine_rows

Idempotent: re-running overwrites the same Parquet files with identical
content (given the same JSONL input).

Usage:
    python src/ingestion/backfill_raw_harmonized_v05.py
    python src/ingestion/backfill_raw_harmonized_v05.py --platform reddit
    python src/ingestion/backfill_raw_harmonized_v05.py --platform youtube reddit x
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import fields as dc_fields
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # src/ingestion/ for sibling imports

from config.schema import AuthorMetadata, Record  # noqa: E402
from config import config_loader  # noqa: E402

load_dotenv()

CONFIG = config_loader.load_config()

# ---------------------------------------------------------------------------
# JSONL paths
# ---------------------------------------------------------------------------

_YOUTUBE_RAW_DIR = ROOT / "data" / "raw" / CONFIG.topic_id
_REDDIT_JSONL = ROOT / "data" / "raw" / "reddit" / "reddit_comments_v1.jsonl"
_X_JSONL = ROOT / "data" / "raw" / "x" / "x_comments_v1.jsonl"

# YouTube: glob every youtube_comments_*.jsonl (same convention
# join_and_clean.py's _load_all_comments() already uses — see its
# docstring), not just youtube_comments_v2.jsonl. Fixed 2026-08-14 (see
# docs/decision_log.md): the first backfill pass only pointed at v2.jsonl
# (~82,550 records) and silently missed youtube_comments_1404-12-09_to_
# ongoing.jsonl (~74,924 records, roughly half of all YouTube data) — no
# error, just fewer harmonized rows than clean.jsonl's YouTube count, which
# would have gone unnoticed until apply_eligibility.py's output was already
# short by that much.
_PLATFORM_JSONL: dict[str, list[Path]] = {
    "youtube": sorted(_YOUTUBE_RAW_DIR.glob("youtube_comments_*.jsonl")),
    "reddit": [_REDDIT_JSONL],
    "x": [_X_JSONL],
}

# ---------------------------------------------------------------------------
# Record reconstruction from JSONL
# ---------------------------------------------------------------------------

_AM_FIELDS = {f.name for f in dc_fields(AuthorMetadata)}
_RECORD_FIELDS = {f.name for f in dc_fields(Record)}


def _record_from_json(data: dict) -> Record:
    """Reconstruct a Record from the dict produced by Record.to_json_line()
    (i.e. asdict(record)). Filters to only known fields so that JSONL written
    by an older schema version (with extra or missing keys) doesn't crash."""
    am_raw = data.get("author_metadata") or {}
    am = AuthorMetadata(**{k: v for k, v in am_raw.items() if k in _AM_FIELDS})
    record_kwargs = {k: v for k, v in data.items() if k in _RECORD_FIELDS and k != "author_metadata"}
    return Record(author_metadata=am, **record_kwargs)


def _load_jsonl(path: Path) -> tuple[list[Record], int]:
    """Reads a JSONL file, returning (valid_records, parse_quarantine_count).
    Lines that fail JSON parsing or Record reconstruction are counted as
    parse_quarantine (they can't produce a harmonized row) but are not
    physically dropped — this script only reads, never modifies the JSONL."""
    if not path.exists():
        print(f"  [warn] {path} does not exist — skipping.")
        return [], 0

    records: list[Record] = []
    quarantined = 0
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(_record_from_json(data))
            except Exception as exc:  # noqa: BLE001
                quarantined += 1
                print(f"  [parse_quarantine] line {lineno}: {exc!r}")
    return records, quarantined


# ---------------------------------------------------------------------------
# Reconciliation printer
# ---------------------------------------------------------------------------

def _print_reconciliation(platform: str, input_rows: int,
                           harmonized_rows: int, quarantine_rows: int) -> bool:
    """Prints the docs/checklist.md §10 equation and returns True if it holds."""
    ok = input_rows == harmonized_rows + quarantine_rows
    print()
    print("=" * 60)
    print(f"Reconciliation [{platform}]  (checklist.md §10)")
    print("=" * 60)
    print(f"  input_rows          = {input_rows}")
    print(f"  harmonized_rows     = {harmonized_rows}")
    print(f"  parse_quarantine    = {quarantine_rows}")
    print(f"  sum                 = {harmonized_rows + quarantine_rows}")
    print()
    print(f"  Equation holds: {ok}  [{'PASS' if ok else 'FAIL'}]")
    print("=" * 60)
    return ok


# ---------------------------------------------------------------------------
# per-platform backfill logic
# ---------------------------------------------------------------------------

def _backfill_youtube(records: list[Record]) -> int:
    """Groups YouTube records by collection_run_id and calls
    youtube_extract.export_to_raw_harmonized() for each group.
    Returns total harmonized rows written."""
    # Import here to avoid heavy YouTube API deps at module level (same
    # reason backfill_author_hash_v05.py uses a sys.path insert rather than
    # a top-level import of the full collector module).
    try:
        from youtube_extract import (  # noqa: PLC0415
            record_to_raw_harmonized_row,
            _V05_BOOL_COLUMNS, _V05_INT_COLUMNS,
            _V05_FLOAT_COLUMNS, _V05_DATETIME_COLUMNS,
            RAW_HARMONIZED_DIR as YT_HARMONIZED_DIR,
        )
        from config.raw_schema_columns_v05 import RAW_SCHEMA_V05_COLUMNS  # noqa: PLC0415
    except ImportError as exc:
        print(f"  [error] Cannot import youtube_extract: {exc}")
        print("          Ensure Google API client and all YouTube deps are installed.")
        return 0

    by_run: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        key = r.collection_run_id or "backfill_youtube_orphan"
        by_run[key].append(r)

    total_written = 0
    for run_id, run_records in sorted(by_run.items()):
        rows = [record_to_raw_harmonized_row(r) for r in run_records]
        df = pd.DataFrame(rows, columns=RAW_SCHEMA_V05_COLUMNS)
        for col in _V05_BOOL_COLUMNS:
            df[col] = df[col].astype("boolean")
        for col in _V05_INT_COLUMNS:
            df[col] = df[col].astype("Int64")
        for col in _V05_FLOAT_COLUMNS:
            df[col] = df[col].astype("float64")
        for col in _V05_DATETIME_COLUMNS:
            df[col] = pd.to_datetime(df[col], utc=True)

        out = YT_HARMONIZED_DIR / f"{run_id}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
        print(f"  raw_harmonized: wrote {len(df)} row(s) to {out}")
        total_written += len(df)

    return total_written


def _backfill_reddit(records: list[Record]) -> int:
    """Calls reddit_to_record.export_to_raw_harmonized() with all records."""
    from reddit_to_record import export_to_raw_harmonized  # noqa: PLC0415
    df = export_to_raw_harmonized(records, run_id="backfill_reddit_v1")
    return len(df)


def _backfill_x(records: list[Record]) -> int:
    """Calls x_to_record.export_to_raw_harmonized() with all records."""
    from x_to_record import export_to_raw_harmonized  # noqa: PLC0415
    df = export_to_raw_harmonized(records, run_id="backfill_x_v1")
    return len(df)


_BACKFILL_FN = {
    "youtube": _backfill_youtube,
    "reddit": _backfill_reddit,
    "x": _backfill_x,
}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run(platforms: list[str]) -> bool:
    all_ok = True
    for platform in platforms:
        jsonl_paths = _PLATFORM_JSONL[platform]
        print(f"\n{'=' * 60}")
        print(f"Platform: {platform.upper()}  ({', '.join(p.name for p in jsonl_paths) or 'NO FILES FOUND'})")
        print("=" * 60)

        records: list[Record] = []
        quarantined = 0
        for jsonl_path in jsonl_paths:
            file_records, file_quarantined = _load_jsonl(jsonl_path)
            print(f"  {jsonl_path.name}: {len(file_records)} record(s), {file_quarantined} parse_quarantine")
            records.extend(file_records)
            quarantined += file_quarantined
        input_rows = len(records) + quarantined
        print(f"  Loaded total: {len(records)} record(s), {quarantined} parse_quarantine")

        if not records:
            print("  Nothing to harmonize.")
            _print_reconciliation(platform, input_rows, 0, quarantined)
            all_ok = False
            continue

        harmonized = _BACKFILL_FN[platform](records)
        ok = _print_reconciliation(platform, input_rows, harmonized, quarantined)
        all_ok = all_ok and ok

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--platform", nargs="+", default=["youtube", "reddit", "x"],
        choices=["youtube", "reddit", "x"],
        help="Platform(s) to backfill (default: all three).",
    )
    args = parser.parse_args()

    ok = run(args.platform)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
