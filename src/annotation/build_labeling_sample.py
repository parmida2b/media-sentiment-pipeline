"""
build_labeling_sample.py

Implements §19 of the assignment doc: samples real comments into a CSV with
the full 4-layer annotation schema (schema.GOLD_SAMPLE_COLUMNS) left blank
for a human to fill by hand. That labeled file is later scored against LLM
routes by evaluate_sentiment_accuracy.py.

Also writes a smaller "agreement subset" — the same rows, duplicated into a
second file for a SECOND annotator — per §19's requirement of "حداقل دو
Annotator برای بخشی از نمونه" (at least two annotators for part of the
sample). compute_annotator_agreement.py scores Cohen's Kappa between the two
once both are filled in.

Source: data/interim/clean.jsonl (raw comments + automation_risk_score_user +
joined video_geo, per join_and_clean.py — NOT yet deduped/normalized, so this
script does its own dedup). Falls back to data/raw/*/youtube_comments*.jsonl
if clean.jsonl doesn't exist yet.

content_id: config/schema.py's Record.content_id is not yet populated by the
YouTube collector for the data on disk (post_id is the video id, not a
per-comment id — verified 2026-08-07). Until that's fixed upstream, this
script derives a stable id as sha1(post_id + text)[:12] and labels it
"derived" so nobody mistakes it for a platform-native comment id.

Usage:
    python src/annotation/build_labeling_sample.py
    python src/annotation/build_labeling_sample.py --force   # overwrite even if already hand-labeled
"""

import argparse
import csv
import glob
import hashlib
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.annotation.schema import GOLD_SAMPLE_COLUMNS, TARGETS  # noqa: E402

# LANGUAGE_QUOTAS, not an even three-way split: per docs/source_registry_v3.md
# SR-006 (reaffirmed in docs/decision_log.md 2026-08-07 and config.yaml's
# keywords_ar/regions removal), Arabic is explicitly out of scope for this
# project's main EN+FA analysis — it should not eat an equal share of the
# annotator budget. fa/en get equal, near-full shares; ar gets a small
# non-zero share (kept in the pipeline, e.g. for later out-of-scope checks,
# but deliberately not annotator-budget-competitive with fa/en).
# Sum must equal SAMPLE_SIZE (300, per docs/pre_analysis_decision_table_v1.md
# and docs/PROJECT_EXECUTION_ORDER_v1.md مرحله ۷: "انتخاب تصادفی
# طبقه‌بندی‌شده ۳۰۰ رکورد با Seed ثابت").
LANGUAGE_QUOTAS = {"fa": 135, "en": 135, "ar": 30}
LANGUAGES = list(LANGUAGE_QUOTAS.keys())
SAMPLE_SIZE = sum(LANGUAGE_QUOTAS.values())  # 300
assert SAMPLE_SIZE == 300, "SAMPLE_SIZE must track LANGUAGE_QUOTAS (see comment above)"

RANDOM_SEED = 42
MIN_TEXT_LEN = 3

# §19: "حداقل دو annotator برای بخشی از نمونه" (at least two annotators for
# part of the sample). docs/PROJECT_EXECUTION_ORDER_v1.md مرحله ۷ pins this
# to a concrete number: "Double annotation برای ۱۲۰ رکورد" — a flat 20% of
# the new SAMPLE_SIZE=300 (=60) would undershoot that, so AGREEMENT_SUBSET_MIN
# is the new target (120) directly, not the old 90-sample-era floor of 10;
# the max(MIN, fraction) logic below is unchanged, only the target number is.
AGREEMENT_SUBSET_FRACTION = 0.20
AGREEMENT_SUBSET_MIN = 120

CLEAN_PATH = ROOT / "data" / "interim" / "clean.jsonl"
OUTPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
AGREEMENT_OUTPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels_agreement_subset.csv"

# Context-only columns the script fills in itself — never treated as
# "already hand-labeled" by has_existing_annotations(). translation_fa is
# carried over from whatever the previous version of this CSV had (a
# teammate hand-added Persian translations for 60/90 rows before this
# script's schema was extended — see docs/decision_log.md 2026-08-07); it's
# not part of schema.GOLD_SAMPLE_COLUMNS but is kept as a convenience column.
CONTEXT_COLUMNS = ["sample_id", "content_id", "language", "text", "post_title", "translation_fa"]
CSV_COLUMNS = ["sample_id", "content_id", "language", "text", "post_title", "translation_fa"] + [
    c for c in GOLD_SAMPLE_COLUMNS if c not in ("sample_id", "content_id", "language", "text")
]


def derive_content_id(post_id: str, text: str) -> str:
    digest = hashlib.sha1(f"{post_id}\x00{text}".encode("utf-8")).hexdigest()[:12]
    return f"derived:{post_id}:{digest}"


def migrate_previous_rows(path: Path) -> list[dict]:
    """Reuse the exact rows already at `path` (same texts, same order),
    filling in any columns the current schema has that the old file didn't
    (as blank) and preserving everything the old file already had —
    including hand-added convenience columns like translation_fa and any
    already-filled label columns. This is a schema migration, not a
    resample: it never silently swaps out which comments are in the sample."""
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), 1):
            migrated = {col: (row.get(col) or "") for col in CSV_COLUMNS}
            migrated["sample_id"] = row.get("sample_id") or i
            if not migrated["content_id"]:
                migrated["content_id"] = derive_content_id(row.get("post_id", ""), row.get("text", ""))
            rows.append(migrated)
    return rows


def load_records() -> list[dict]:
    if CLEAN_PATH.exists():
        source_files = [CLEAN_PATH]
    else:
        source_files = [Path(p) for p in sorted(glob.glob(str(ROOT / "data" / "raw" / "*" / "youtube_comments*.jsonl")))]

    seen = set()
    records = []
    for fp in source_files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                text = (r.get("text") or "").strip()
                if len(text) < MIN_TEXT_LEN:
                    continue
                key = (r.get("post_id"), text)
                if key in seen:
                    continue
                seen.add(key)
                records.append(r)
    return records


def stratified_sample(records: list[dict], quotas: dict[str, int]) -> list[dict]:
    """Sample per-language according to fixed `quotas` (see LANGUAGE_QUOTAS —
    deliberately NOT an even split across languages, see comment there)."""
    random.seed(RANDOM_SEED)
    by_lang = {lang: [r for r in records if r.get("language") == lang] for lang in quotas}
    for group in by_lang.values():
        random.shuffle(group)

    sample = []
    leftover = 0
    for lang, target in quotas.items():
        take = min(target, len(by_lang[lang]))
        sample.extend(by_lang[lang][:take])
        by_lang[lang] = by_lang[lang][take:]
        leftover += target - take

    # redistribute leftover slots (a language's quota exceeded what's
    # available) to languages that still have unused records
    for lang in quotas:
        if leftover <= 0:
            break
        take = min(leftover, len(by_lang[lang]))
        sample.extend(by_lang[lang][:take])
        leftover -= take

    random.shuffle(sample)
    return sample


# Explicit allowlist (not "everything outside CONTEXT_COLUMNS") — an older
# script version's own context columns (e.g. the pre-2026-08-07 CSV's
# "post_id") would otherwise be misread as hand-filled annotation values and
# block a legitimate schema migration. "human_label" is the old (pre-4-layer)
# schema's single label column, kept here so old hand-labeled files are still
# detected and protected.
KNOWN_ANNOTATION_COLUMNS = {
    c for c in GOLD_SAMPLE_COLUMNS if c not in ("sample_id", "content_id", "language", "text")
} | {"human_label"}


def has_existing_annotations(path: Path) -> bool:
    """True if `path` already exists and has any non-blank value in a column
    this project has ever used for a human-filled label (current schema's
    KNOWN_ANNOTATION_COLUMNS, or the pre-migration "human_label")."""
    if not path.exists():
        return False
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        annotation_columns = [c for c in (reader.fieldnames or []) if c in KNOWN_ANNOTATION_COLUMNS]
        return any(row.get(col, "").strip() for row in reader for col in annotation_columns)


def write_sample_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true",
        help="bypass the hand-filled-annotation safety check (needed together with --resample "
        "to draw a genuinely new random sample over an already-annotated file)",
    )
    parser.add_argument(
        "--resample", action="store_true",
        help="draw a brand-new random sample instead of reusing the existing CSV's rows "
        "(schema-migrate-in-place, which preserves every existing row/label/translation, is the default)",
    )
    args = parser.parse_args()

    if not args.force and (has_existing_annotations(OUTPUT_PATH) or has_existing_annotations(AGREEMENT_OUTPUT_PATH)):
        print(
            f"{OUTPUT_PATH} or {AGREEMENT_OUTPUT_PATH} already has hand-filled annotation "
            "values — refusing to overwrite and lose them. Re-run with --force if you "
            "really want a fresh sample."
        )
        return

    if OUTPUT_PATH.exists() and not args.resample:
        rows = migrate_previous_rows(OUTPUT_PATH)
        print(f"Reusing the {len(rows)} existing sampled rows from {OUTPUT_PATH.name} "
              "(schema migration only, no resampling — pass --resample for a fresh random sample).")
    else:
        records = load_records()
        if not records:
            print(f"No records found in {CLEAN_PATH} or data/raw/*/youtube_comments*.jsonl — "
                  "run extraction (and/or src/preprocessing/join_and_clean.py) first.")
            return

        sample = stratified_sample(records, LANGUAGE_QUOTAS)
        rows = [{
            "sample_id": i,
            "content_id": r.get("content_id") or derive_content_id(r.get("post_id", ""), r.get("text", "")),
            "language": r.get("language", ""),
            "text": r.get("text", ""),
            "post_title": r.get("post_title", ""),
            "translation_fa": "",
            "target": "",
            "annotator_id": "",
            "sentiment_label": "",
            "stance_label": "",
            "emotion_label": "",
            "content_type_label": "",
            "confidence": "",
            "notes": "",
        } for i, r in enumerate(sample, 1)]
        print(f"Drew a fresh random sample of {len(rows)} comments.")

    write_sample_csv(OUTPUT_PATH, rows)

    agreement_n = max(AGREEMENT_SUBSET_MIN, round(len(rows) * AGREEMENT_SUBSET_FRACTION))
    agreement_n = min(agreement_n, len(rows))
    random.seed(RANDOM_SEED)
    agreement_rows = random.sample(rows, agreement_n)
    write_sample_csv(AGREEMENT_OUTPUT_PATH, agreement_rows)

    from collections import Counter
    lang_counts = Counter(r["language"] for r in rows)
    print(f"Wrote {len(rows)} comments to {OUTPUT_PATH}")
    print(f"Wrote {len(agreement_rows)} comments (subset, for a SECOND annotator) to {AGREEMENT_OUTPUT_PATH}")
    print(f"By language: {dict(lang_counts)}")
    n_with_translation = sum(1 for r in rows if r.get("translation_fa"))
    if n_with_translation:
        print(f"translation_fa present for {n_with_translation}/{len(rows)} rows.")
    print("\nTarget IDs for the 'target' column (pick the one the comment most directly addresses):")
    for target_id, label_fa in TARGETS.items():
        print(f"  {target_id:28s} {label_fa}")
    print(
        "\nNext steps:\n"
        f"  1. One annotator fills every row of {OUTPUT_PATH.name}: target, annotator_id, "
        "sentiment_label, stance_label, emotion_label, content_type_label, confidence (0-1), notes.\n"
        f"     Allowed values are in src/annotation/schema.py (SENTIMENT_LABELS, STANCE_LABELS, "
        "EMOTION_LABELS, CONTENT_TYPE_LABELS).\n"
        f"  2. A SECOND annotator independently fills {AGREEMENT_OUTPUT_PATH.name} (same rows, "
        "different annotator_id) without seeing the first annotator's labels.\n"
        "  3. Run src/validation/compute_annotator_agreement.py to score Cohen's Kappa.\n"
        "  4. Run src/validation/evaluate_sentiment_accuracy.py to score the LLM routes against "
        f"{OUTPUT_PATH.name}."
    )


if __name__ == "__main__":
    main()
