"""
fix_gold_sample_content_id_corruption.py -- docs/checklist.md item 17,
follow-up fix (2026-08-14, see docs/decision_log.md).

Problem: data/annotated/sample_sentiment_labels.csv and its
_agreement_subset.csv counterpart both had their X-platform content_id
values mangled by Excel into scientific notation (e.g. "2.04352E+18"
instead of the real 19-digit tweet id) -- the exact same corruption class
already fixed once on 2026-08-13 (see decision_log.md), reintroduced by
opening/saving these CSVs in Excel again while annotators were filling in
the 62 replacement rows (docs/decision_log.md, replace_invalid_gold_sample_
rows.py entry). Confirmed: 100/100 X rows corrupted in the main file (7
resulting duplicate content_id values) and 47/47 X rows corrupted in the
agreement subset (present even in this morning's pre-replacement backup,
i.e. a separate, earlier instance of the same corruption).

Fix strategy -- content_id repaired by POSITION (sample_id), never by
re-deriving or guessing a value:
  1. Build a sample_id -> correct_content_id map from two known-clean
     sources: the pre-62-replacement backup (238 unchanged rows) and
     gold_sample_replacement_delta_2026-08-14.csv (the 62 replaced rows --
     written directly by this repo's own code, never touched by Excel).
  2. Apply that map to BOTH the main file and the agreement_subset file by
     sample_id -- every other column (all hand-filled labels) is left
     untouched. sample_id is a safe join key: verified every
     agreement_subset sample_id exists in the main file and both files
     have zero duplicate sample_id.

This is expected to also resolve the "47 orphan agreement-subset rows
don't match the main file" issue flagged earlier as separate -- that
mismatch was largely a symptom of the two files being corrupted
independently/differently, not a distinct identity problem.

Usage:
    python src/annotation/fix_gold_sample_content_id_corruption.py            # dry-run, report only
    python src/annotation/fix_gold_sample_content_id_corruption.py --apply    # write the fix
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
AGREEMENT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels_agreement_subset.csv"
BACKUP_PATH = ROOT / "data" / "annotated" / "_backup_before_content_id_fix_2026-08-13" / "sample_sentiment_labels_pre_62_replacement_2026-08-14.csv"
DELTA_PATH = ROOT / "data" / "annotated" / "gold_sample_replacement_delta_2026-08-14.csv"


def read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in fieldnames})


def build_correct_id_map() -> dict[str, str]:
    _, backup_rows = read_csv_rows(BACKUP_PATH)
    _, delta_rows = read_csv_rows(DELTA_PATH)

    correct: dict[str, str] = {r["sample_id"]: r["content_id"] for r in backup_rows}
    correct.update({r["sample_id"]: r["content_id"] for r in delta_rows})  # authoritative for the 62 replaced rows
    return correct


def apply_fix(path: Path, correct_id_by_sample_id: dict[str, str]) -> tuple[list[str], list[dict], int]:
    fieldnames, rows = read_csv_rows(path)
    n_fixed = 0
    for row in rows:
        sid = row["sample_id"]
        correct = correct_id_by_sample_id.get(sid)
        if correct is None:
            continue  # no known-clean source for this sample_id -- left as-is, not guessed
        if row["content_id"] != correct:
            row["content_id"] = correct
            n_fixed += 1
    return fieldnames, rows, n_fixed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    correct_id_by_sample_id = build_correct_id_map()
    print(f"Built correct-id map from {len(correct_id_by_sample_id)} sample_id(s) "
          f"(backup + delta, both known-clean, never touched by Excel).")

    main_fields, main_rows, n_main_fixed = apply_fix(MAIN_PATH, correct_id_by_sample_id)
    agr_fields, agr_rows, n_agr_fixed = apply_fix(AGREEMENT_PATH, correct_id_by_sample_id)

    main_ids = [r["content_id"] for r in main_rows]
    n_dup = len(main_ids) - len(set(main_ids))
    print(f"Main sample: {n_main_fixed}/{len(main_rows)} content_id value(s) corrected. "
          f"Duplicate content_id after fix: {n_dup} (expect 0).")

    agr_matched = sum(1 for r in agr_rows if r["content_id"] in set(main_ids))
    print(f"Agreement subset: {n_agr_fixed}/{len(agr_rows)} content_id value(s) corrected. "
          f"Rows now matching main file by content_id: {agr_matched}/{len(agr_rows)} (was 73/120 before this fix).")

    if args.apply:
        write_csv_rows(MAIN_PATH, main_fields, main_rows)
        write_csv_rows(AGREEMENT_PATH, agr_fields, agr_rows)
        print(f"\nWrote {MAIN_PATH}")
        print(f"Wrote {AGREEMENT_PATH}")
    else:
        print("\n--dry-run: nothing written. Pass --apply to write the fix.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
