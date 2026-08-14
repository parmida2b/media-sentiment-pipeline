"""
handoff_csv_to_record.py — converts a teammate-delivered raw file that is
ALREADY shaped like config/raw_schema_columns.py's RAW_SCHEMA_COLUMNS
(same 47 column names, e.g. a "Raw_Tweets" export sheet or a
reddit_raw_schema.csv handoff) into this project's shared Record JSONL —
the same two artifacts every other collector bridge produces:

    data/raw/{platform}/{platform}_comments_v1.jsonl
    data/raw/{platform}/{platform}_raw_export.csv

Why this script exists instead of reusing x_to_record.py / reddit_to_record.py
directly
---------------------------------------------------------------------------
Those two scripts each bridge one specific collector's NATIVE raw export
format (x_scraper.py's SQLite-backed x_raw.csv, or
reddit_raw_json_pipeline.py's two audit CSVs) into Record — their row-
parsing assumes that specific upstream shape.

Here the input file is already in the shared RAW_SCHEMA_COLUMNS shape (a
teammate mapped it before handing it over — verified column-by-column
against config/raw_schema_columns.py before this script was written; see
docs/decision_log.md 2026-08-13 entry for this script). So the actual
row -> Record mapping needed is IDENTICAL to what x_to_record.py's
build_record()/record_to_raw_schema_row() already implement and the team
already reviewed (PII stripping — author_username/author_display_name/
tweet_url are never read into the output; author_hash is only carried
through when author_hash_method says a real handle was resolved, otherwise
author_id_status="unavailable" — see x_to_record.py's module docstring).
That logic is reused as-is (import, not copy) rather than re-derived a
second time, to avoid two bridges silently disagreeing on the same PII
rule. build_record() is already platform-agnostic (it reads `platform`
straight from the row), so this works unchanged for both X and Reddit.

Input can be .csv or .xlsx (pass --sheet for a specific worksheet, default
"Raw_Tweets" — only used for .xlsx).

Usage:
    python src/ingestion/handoff_csv_to_record.py --input data/raw/iran_us_war/X_Scraper_v4_7_Target20K_Current.xlsx --sheet Raw_Tweets --platform x
    python src/ingestion/handoff_csv_to_record.py --input data/raw/iran_us_war/reddit_raw_schema.csv --platform reddit
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.raw_schema_columns import RAW_SCHEMA_COLUMNS  # noqa: E402
from src.ingestion.x_to_record import build_record, record_to_raw_schema_row  # noqa: E402
import automation_risk  # noqa: E402 - sibling module in src/ingestion/
import geo_tagger  # noqa: E402 - reuse the exact same lightweight script-detection heuristic reddit_to_record.py already uses (_detect_text_language), so a record that goes through THIS bridge gets the same language value it would have gotten going through that one

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def compute_automation_risk_scores_for_raw_schema_rows(rows: list[dict[str, str]]) -> dict[str, float]:
    """docs/checklist.md item 15 (2026-08-14): both real-data platforms that
    go through THIS bridge (X and Reddit -- see decision_log.md, this was
    found to be the actual path the real production data took, not
    x_to_record.py's/reddit_to_record.py's own main()) had
    automation_risk_score=None for every single record, because neither of
    those scripts' own batching logic was ever invoked here.

    Batches by source_parent_id when it's populated (Reddit: one batch per
    submission, the same "per parent container" scope
    reddit_to_record.py's own compute_automation_risk_scores() and
    youtube_extract.py use) -- falls back to one single whole-file batch for
    rows where it's empty (X: every tweet is a standalone top-level item,
    per x_to_record.py's module docstring, so there is no parent to group
    by). automation_risk.score_batch() itself is platform-agnostic (just
    wants content_id/text/date/author_channel_id per item)."""
    by_group: dict[str, list[dict]] = {}
    for row in rows:
        content_id = row.get("platform_content_id") or ""
        if not content_id:
            continue
        group_key = row.get("source_parent_id") or "__no_parent__"
        by_group.setdefault(group_key, []).append({
            "content_id": content_id,
            "text": row.get("text_raw", ""),
            "date": row.get("created_at_utc", ""),
            "author_channel_id": row.get("author_hash", ""),
        })

    scores: dict[str, float] = {}
    for group_rows in by_group.values():
        scores.update(automation_risk.score_batch(group_rows))
    return scores


def load_rows(path: Path, sheet: str | None) -> list[dict[str, str]]:
    """Reads the handoff file and returns rows shaped like csv.DictReader
    output (every value a plain string, missing/NaN -> ""), matching what
    build_record()/record_to_raw_schema_row() (written against
    csv.DictReader rows) expect. Preserves large integer ids (e.g.
    platform_content_id) exactly — pandas keeps a NaN-free integer column
    as int64, so str(value) never goes through float/scientific notation."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet or "Raw_Tweets")
    else:
        df = pd.read_csv(path, dtype=str, keep_default_na=True)

    rows: list[dict[str, str]] = []
    for record in df.to_dict(orient="records"):
        row: dict[str, str] = {}
        for key, value in record.items():
            row[key] = "" if pd.isna(value) else str(value)
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True, help="Path to the handoff .csv or .xlsx file.")
    parser.add_argument("--sheet", type=str, default="Raw_Tweets", help="Worksheet name, only used for .xlsx input.")
    parser.add_argument("--platform", type=str, required=True, choices=["x", "reddit"], help="Output directory / filename prefix.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows (smoke-testing).")
    parser.add_argument("--skip-automation-risk", action="store_true", help="Skip automation_risk.score_batch (faster iteration).")
    args = parser.parse_args()

    rows = load_rows(args.input, args.sheet)
    if args.limit:
        rows = rows[: args.limit]
    print(f"Loaded {len(rows)} row(s) from {args.input}.")

    # Informational only: build_record()/record_to_raw_schema_row() use
    # dict.get() with defaults for every column, and some columns (e.g.
    # sampling_method, author_is_submitter) are never read from `row` at
    # all (they're hardcoded/derived) — so a missing column here is not
    # fatal, just worth flagging in case it was an accidental mapping gap.
    missing_cols = sorted(set(RAW_SCHEMA_COLUMNS) - set(rows[0].keys())) if rows else []
    if missing_cols:
        print(f"Note: input has no column for {missing_cols} (will be treated as empty).")

    # build_record()'s author_hash_and_status() (x_to_record.py) decides
    # whether to carry an author_hash through by reading an
    # `author_hash_method` column ('handle_fallback_v1' vs
    # 'content_id_fallback_v1') — a disambiguator X's collector needs
    # because x_raw.csv's author_hash is NEVER empty (it hashes a synthetic
    # 'unknown:{content_id}' placeholder when no handle was resolved, see
    # that module's docstring). Reddit's handoff has no such placeholder-
    # hash problem: reddit_to_record.py's own author_hash_and_status()
    # (hashing the stable author_fullname) already leaves author_hash
    # genuinely empty for deleted/unavailable authors — so a present,
    # non-empty author_hash here always means a real author was resolved.
    # Without this shim, every reddit row would fall through to
    # 'content_id_fallback_v1' (no author_username column either) and lose
    # every real author_hash. Synthesizing the method column lets
    # build_record()'s existing, already-reviewed logic reach the correct
    # answer unmodified.
    if args.platform == "reddit":
        for row in rows:
            row["author_hash_method"] = "handle_fallback_v1" if row.get("author_hash") else ""

    # Some handoffs (this Reddit file, verified 2026-08-13) never ran a
    # language-detection pass upstream — language_reported/language_detected
    # are empty for every row. build_labeling_sample.py's Platform×Language
    # quotas (docs/checklist.md §17) need a real fa/en/ar value per record or
    # that platform's whole quota silently goes unfilled. Fill it in here
    # with the same heuristic reddit_to_record.py already uses for this
    # exact purpose (geo_tagger._detect_text_language) — only when both
    # upstream language columns are empty, so a platform that already did
    # its own (better) language detection is left untouched.
    filled_language = 0
    for row in rows:
        if not (row.get("language_reported") or "").strip() and not (row.get("language_detected") or "").strip():
            text = row.get("text_raw") or ""
            row["language_detected"] = geo_tagger._detect_text_language(text)
            filled_language += 1
    if filled_language:
        print(f"Filled missing language_detected for {filled_language}/{len(rows)} row(s) via script-detection heuristic.")

    output_dir = PROJECT_ROOT / "data" / "raw" / args.platform
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_output = output_dir / f"{args.platform}_comments_v1.jsonl"
    csv_output = output_dir / f"{args.platform}_raw_export.csv"

    if args.skip_automation_risk:
        risk_scores: dict[str, float] = {}
    else:
        risk_scores = compute_automation_risk_scores_for_raw_schema_rows(rows)
        print(f"automation_risk_score computed for {len(risk_scores)} row(s).")

    records = [build_record(row, risk_scores) for row in rows]

    with jsonl_output.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(record.to_json_line() + "\n")

    with csv_output.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()
        for row, record in zip(rows, records):
            writer.writerow(record_to_raw_schema_row(record, row))

    hashed = sum(1 for r in records if r.author_metadata.author_hash)
    not_active = sum(1 for r in records if r.content_status != "active")
    high_risk = sum(1 for r in records if (r.automation_risk_score or 0.0) >= 0.7)
    print(f"Wrote {len(records)} record(s) -> {jsonl_output}")
    print(f"Wrote {len(records)} record(s) -> {csv_output}")
    print(f"  author_hash present: {hashed}/{len(records)}")
    print(f"  content_status != active: {not_active}/{len(records)}")
    print(f"  automation_risk_score >= 0.7 (high risk, flagged not removed): {high_risk}/{len(records)}")


if __name__ == "__main__":
    main()
