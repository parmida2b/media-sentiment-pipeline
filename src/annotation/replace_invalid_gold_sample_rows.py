"""
replace_invalid_gold_sample_rows.py -- docs/checklist.md item 17, targeted
fix (2026-08-14, see docs/decision_log.md).

Problem: data/annotated/sample_sentiment_labels.csv (the 300-row Gold
Sample two annotators have already hand-labeled, Kappa already computed on
it) was drawn from data/interim/clean.jsonl -- BEFORE apply_eligibility.py
had ever run on real, complete data. Cross-checking today against
data/audits/eligibility_audit.parquet (built after the real run) found 62
of those 300 content_ids are not actually eligible content: 49 are entirely
absent from eligibility_audit.parquet, 13 landed in quarantine/audit_only.

This is a TARGETED replacement, not a resample (docs/decision_log.md
2026-08-14, explicit user decision): the 238 healthy rows -- and every
label two annotators already filled in on them -- are left byte-for-byte
untouched. Only the 62 invalid rows are swapped for new ones drawn from the
real eligible pool (opinion_main/opinion_limited/opinion_untimed), matched
to the SAME (platform, language) cell as the row being replaced (keeps the
existing 100/100/100 platform x 45/45/10 language quotas intact), with the
same fixed seed (1405) build_labeling_sample.py already uses. New rows get
every label column blank -- they still need real human annotation.

The same old_content_id -> new_content_id swap is applied to
sample_sentiment_labels_agreement_subset.csv wherever a swapped id was part
of the double-annotation subset, so a row that was being double-annotated
stays double-annotated (just with new content), instead of silently losing
subset coverage.

KNOWN, SEPARATE issue surfaced by this script but NOT fixed here (out of
scope for the 62-row swap): 47 of the agreement subset's 120 content_ids do
not match ANY row in the main 300-row file at all (pre-existing, likely
related to the 2026-08-13 Excel-scientific-notation content_id repair that
was applied to the main file but not the subset copy -- see decision_log).
Reported in this script's output; needs a separate team decision.

Usage:
    python src/annotation/replace_invalid_gold_sample_rows.py            # dry-run, report only
    python src/annotation/replace_invalid_gold_sample_rows.py --apply    # write the changes
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.annotation.build_labeling_sample import (  # noqa: E402
    CSV_COLUMNS, RANDOM_SEED, _eligibility_paths, _load_from_eligibility_outputs,
)

SAMPLE_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
AGREEMENT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels_agreement_subset.csv"
AUDIT_PATH = ROOT / "data" / "audits" / "eligibility_audit.parquet"
DELTA_PATH = ROOT / "data" / "annotated" / "gold_sample_replacement_delta_2026-08-14.csv"

INVALID_DATASET_TARGETS = {"quarantine", "audit_only"}
BLANK_ANNOTATION_COLUMNS = [
    "target", "annotator_id", "sentiment_label", "stance_label",
    "emotion_label", "content_type_label", "confidence", "notes",
]


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def find_invalid_ids(sample_ids: set[str]) -> tuple[set[str], dict[str, str]]:
    """Returns (invalid_ids, reason_by_id). A content_id is invalid if it's
    absent from eligibility_audit.parquet entirely, or present with
    dataset_target in {quarantine, audit_only}."""
    audit = pd.read_parquet(AUDIT_PATH, columns=["platform_content_id", "dataset_target"])
    audit_map = dict(zip(audit["platform_content_id"].astype(str).str.strip(), audit["dataset_target"]))

    invalid, reasons = set(), {}
    for cid in sample_ids:
        target = audit_map.get(cid)
        if target is None:
            invalid.add(cid)
            reasons[cid] = "missing_from_eligibility_audit"
        elif target in INVALID_DATASET_TARGETS:
            invalid.add(cid)
            reasons[cid] = f"dataset_target={target}"
    return invalid, reasons


def build_replacement_pool(exclude_ids: set[str]) -> dict[tuple[str, str], list[dict]]:
    """(platform, language) -> shuffled list of eligible candidate records,
    excluding any content_id already in the sample (either the 238 kept
    rows or an id already picked as a replacement in this same run)."""
    paths = _eligibility_paths()
    if not all(p.exists() for p in paths):
        raise SystemExit(f"Eligibility outputs not found ({paths}) -- run apply_eligibility.py first.")
    records = _load_from_eligibility_outputs(paths)

    random.seed(RANDOM_SEED)
    pool: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        cid = r.get("content_id") or ""
        if not cid or cid in exclude_ids:
            continue
        text = (r.get("text") or "").strip()
        if len(text) < 3:
            continue
        key = (r.get("platform") or "", r.get("language") or "")
        pool.setdefault(key, []).append(r)
    for group in pool.values():
        random.shuffle(group)
    return pool


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write the changes (default: dry-run report only).")
    args = parser.parse_args()

    main_rows = read_csv_rows(SAMPLE_PATH)
    agreement_rows = read_csv_rows(AGREEMENT_PATH)
    main_ids = {r["content_id"].strip() for r in main_rows}
    agreement_ids = {r["content_id"].strip() for r in agreement_rows}

    invalid_ids, reasons = find_invalid_ids(main_ids)
    print(f"Main sample: {len(main_rows)} rows, {len(invalid_ids)} invalid (need replacement).")
    orphan_agreement_ids = agreement_ids - main_ids
    if orphan_agreement_ids:
        print(
            f"NOTE (separate, pre-existing issue, NOT fixed by this script): "
            f"{len(orphan_agreement_ids)}/{len(agreement_rows)} agreement-subset content_ids "
            "don't match ANY row in the main sample at all -- see module docstring."
        )

    pool = build_replacement_pool(exclude_ids=main_ids)

    def _take_from_cell(key: tuple[str, str]):
        candidates = pool.get(key, [])
        return candidates.pop() if candidates else None

    def _take_same_platform_any_language(platform: str):
        """Fallback pass 1 (docs/checklist.md §17 spirit, same pattern
        build_labeling_sample.py's stratified_sample() already uses):
        same platform, any language, picked from whichever non-empty pool
        is largest so one thin language isn't drained first."""
        options = [(k, v) for k, v in pool.items() if k[0] == platform and v]
        if not options:
            return None
        key = max(options, key=lambda kv: len(kv[1]))[0]
        return pool[key].pop()

    replacement_map: dict[str, dict] = {}  # old_content_id -> new row dict (CSV_COLUMNS shape)
    unfilled = []
    fallback_used = []
    for row in main_rows:
        cid = row["content_id"].strip()
        if cid not in invalid_ids:
            continue
        key = (row["platform"], row["language"])
        new_rec = _take_from_cell(key)
        if new_rec is None:
            new_rec = _take_same_platform_any_language(row["platform"])
            if new_rec is not None:
                fallback_used.append((cid, key, (new_rec.get("platform"), new_rec.get("language"))))
        if new_rec is None:
            unfilled.append(cid)
            continue
        new_row = {col: "" for col in CSV_COLUMNS}
        new_row.update({
            "sample_id": row["sample_id"],
            "content_id": new_rec.get("content_id") or "",
            "platform": new_rec.get("platform") or "",
            "language": new_rec.get("language") or "",
            "text": new_rec.get("text") or "",
            "post_title": new_rec.get("post_title") or "",
        })
        replacement_map[cid] = new_row

    if fallback_used:
        print(f"WARNING: {len(fallback_used)} replacement(s) fell back to same-platform/different-language "
              f"because the original (platform, language) cell had no unused eligible candidates left:")
        for old_cid, wanted, got in fallback_used:
            print(f"  {old_cid}: wanted {wanted}, used {got}")
    if unfilled:
        print(f"WARNING: {len(unfilled)} invalid id(s) could not be replaced at all -- no unused eligible "
              f"candidates anywhere on that platform: {unfilled}")

    print(f"\nReplacements found: {len(replacement_map)}/{len(invalid_ids)}")
    by_platform: dict[str, int] = {}
    for old_cid, new_row in replacement_map.items():
        by_platform[new_row["platform"]] = by_platform.get(new_row["platform"], 0) + 1
    print(f"New rows by platform: {by_platform}")

    new_main_rows = [replacement_map.get(r["content_id"].strip(), r) for r in main_rows]
    n_agreement_swapped = 0
    new_agreement_rows = []
    for r in agreement_rows:
        cid = r["content_id"].strip()
        if cid in replacement_map:
            new_agreement_rows.append(replacement_map[cid])
            n_agreement_swapped += 1
        else:
            new_agreement_rows.append(r)
    print(f"Agreement subset rows swapped: {n_agreement_swapped}")

    assert len(new_main_rows) == len(main_rows) == 300, "row count of main sample must stay 300"
    assert len(new_agreement_rows) == len(agreement_rows), "row count of agreement subset must not change"
    kept_unchanged = sum(
        1 for old, new in zip(main_rows, new_main_rows) if old["content_id"].strip() not in replacement_map
    )
    print(f"Rows left byte-for-byte unchanged: {kept_unchanged}/300 (expected {300 - len(replacement_map)})")

    if args.apply:
        write_csv_rows(SAMPLE_PATH, new_main_rows)
        write_csv_rows(AGREEMENT_PATH, new_agreement_rows)
        delta_rows = list(replacement_map.values())
        write_csv_rows(DELTA_PATH, delta_rows)
        print(f"\nWrote {SAMPLE_PATH}")
        print(f"Wrote {AGREEMENT_PATH}")
        print(f"Wrote {DELTA_PATH} ({len(delta_rows)} new rows, for handing to annotators)")
        print("\nReasons for each replaced id:")
        for old_cid, reason in reasons.items():
            if old_cid in replacement_map:
                print(f"  {old_cid}: {reason} -> replaced with {replacement_map[old_cid]['content_id']}")
    else:
        print("\n--dry-run: nothing written. Pass --apply to write the changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
