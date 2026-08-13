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

Source: preferentially data/interim/{opinion_main,opinion_limited,opinion_untimed}.parquet
— the eligible-record outputs of src/preprocessing/apply_eligibility.py (§2-§4
of docs/eligibility_rules_v03.md: deduped, date/provenance/topic-screened).
If those haven't been generated yet, falls back to data/interim/clean.jsonl
(raw comments + automation_risk_score_user + joined video_geo, per
join_and_clean.py — NOT yet deduped/normalized, so this script does its own
dedup), and then to data/raw/*/youtube_comments*.jsonl if clean.jsonl doesn't
exist yet either. See docs/decision_log.md 2026-08-13 (eligibility hookup).

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

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.annotation.schema import GOLD_SAMPLE_COLUMNS, TARGETS  # noqa: E402

# Two-dimensional quotas: docs/checklist.md §17 requires BOTH Platform and
# Language as main strata ("طبقات اصلی: Platform و Language", "۱۰۰ رکورد برای
# هر پلتفرم") — so each of the 3 platforms gets a flat 100-record quota.
# Within each platform's 100, the language split is NOT even three-way: per
# docs/source_registry_v3.md SR-006 (reaffirmed in docs/decision_log.md
# 2026-08-07 and config.yaml's keywords_ar/regions removal), Arabic is
# explicitly out of scope for this project's main EN+FA analysis, so it
# should not eat an equal share of the annotator budget. fa/en get equal,
# near-full shares (45 each); ar gets a small non-zero share (10 — kept in
# the pipeline, e.g. for later out-of-scope checks, but deliberately not
# annotator-budget-competitive with fa/en). 45+45+10=100 per platform, so the
# *language* marginal across all 3 platforms still sums to fa=135/en=135/
# ar=30 — the exact split docs/decision_log.md 2026-08-13 already justified —
# this only adds the missing Platform dimension on top of it.
# Grand total must equal 300, per docs/pre_analysis_decision_table_v1.md and
# docs/PROJECT_EXECUTION_ORDER_v1.md مرحله ۷: "انتخاب تصادفی طبقه‌بندی‌شده
# ۳۰۰ رکورد با Seed ثابت". main() prints the summed total when building the
# sample as a safety check against that number.
PLATFORMS = ["x", "reddit", "youtube"]
LANGUAGES = ["fa", "en", "ar"]
PLATFORM_LANGUAGE_QUOTAS = {
    platform: {"fa": 45, "en": 45, "ar": 10} for platform in PLATFORMS
}

RANDOM_SEED = 1405  # docs/checklist.md §17: "Seed ثابت: 1405"
MIN_TEXT_LEN = 3

# §19: "حداقل دو annotator برای بخشی از نمونه" (at least two annotators for
# part of the sample). docs/PROJECT_EXECUTION_ORDER_v1.md مرحله ۷ pins this
# to a concrete number: "Double annotation برای ۱۲۰ رکورد" — a flat 20% of
# the new sample size of 300 (=60) would undershoot that, so AGREEMENT_SUBSET_MIN
# is the new target (120) directly, not the old 90-sample-era floor of 10;
# the max(MIN, fraction) logic below is unchanged, only the target number is.
AGREEMENT_SUBSET_FRACTION = 0.20
AGREEMENT_SUBSET_MIN = 120

CLEAN_PATH = ROOT / "data" / "interim" / "clean.jsonl"
OUTPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
AGREEMENT_OUTPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels_agreement_subset.csv"

# apply_eligibility.py's _write_outputs() always writes these three (plus
# context_only/audit_only/quarantine) under data/interim/, one parquet per
# dataset_target, even when a target has 0 rows — so "do all three files
# exist" is a reliable "has the eligibility pipeline been run at least once"
# check. These three are the eligible-for-analysis buckets (§3/§3.2 of
# docs/eligibility_rules_v03.md); context_only/audit_only/quarantine are not
# opinion records and are intentionally excluded from the labeling sample.
ELIGIBILITY_TARGETS = ("opinion_main", "opinion_limited", "opinion_untimed")
ELIGIBILITY_DIR = ROOT / "data" / "interim"

# Context-only columns the script fills in itself — never treated as
# "already hand-labeled" by has_existing_annotations(). translation_fa is
# carried over from whatever the previous version of this CSV had (a
# teammate hand-added Persian translations for 60/90 rows before this
# script's schema was extended — see docs/decision_log.md 2026-08-07); it's
# not part of schema.GOLD_SAMPLE_COLUMNS but is kept as a convenience column.
CONTEXT_COLUMNS = ["sample_id", "content_id", "platform", "language", "text", "post_title", "translation_fa"]
CSV_COLUMNS = ["sample_id", "content_id", "platform", "language", "text", "post_title", "translation_fa"] + [
    c for c in GOLD_SAMPLE_COLUMNS if c not in ("sample_id", "content_id", "platform", "language", "text")
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


def _eligibility_paths() -> list[Path]:
    return [ELIGIBILITY_DIR / f"{target}.parquet" for target in ELIGIBILITY_TARGETS]


def _val(row: dict, *cols: str):
    """First non-blank value among `cols` in a pandas-row-as-dict, treating
    NaN/NaT/pd.NA the same as missing (raw_schema_v05 columns are unioned
    across platforms in apply_eligibility.py's _load_harmonized(), so a
    platform missing a column sees pd.NA for it on every row)."""
    for col in cols:
        if col not in row:
            continue
        v = row[col]
        if isinstance(v, str):
            if v.strip():
                return v.strip()
            continue
        if v is None:
            continue
        try:
            if pd.isna(v):
                continue
        except (TypeError, ValueError):
            pass
        return v
    return None


def _load_from_eligibility_outputs(paths: list[Path]) -> list[dict]:
    """Read apply_eligibility.py's opinion_main/opinion_limited/opinion_untimed
    parquet outputs and reshape each row into this script's plain-dict record
    shape (post_id/text/language/post_title/content_id) so downstream sampling
    code doesn't need to know about raw_schema_v05 column names.

    Field mapping (docs/raw_schema_v05.md §3/§6/§8):
      post_id      <- source_parent_id (video/submission/conversation id —
                       same concept as clean.jsonl's post_id), falling back
                       to platform_content_id for records that ARE the parent
                       (e.g. a Reddit self-post with no separate parent).
      content_id   <- platform_content_id (the platform's own id for this
                       exact piece of content; schema.py's Record.content_id).
      platform     <- platform (required top-level field on every Record;
                       one of PLATFORMS — needed for the Platform stratum
                       docs/checklist.md §17 requires alongside Language).
      text         <- text_raw
      language     <- language_detected, falling back to language_reported
                       (language_reported is rarely populated upstream and,
                       when it is, isn't guaranteed to use the fa/en/ar codes
                       PLATFORM_LANGUAGE_QUOTAS expects).
      post_title   <- source_parent_title
    """
    frames = [df for df in (pd.read_parquet(p) for p in paths) if len(df)]
    if not frames:
        return []
    combined = pd.concat(frames, ignore_index=True, sort=False)

    records = []
    for row in combined.to_dict(orient="records"):
        records.append({
            "post_id": _val(row, "source_parent_id", "platform_content_id") or "",
            "content_id": _val(row, "platform_content_id") or "",
            "platform": _val(row, "platform") or "",
            "text": _val(row, "text_raw") or "",
            "language": _val(row, "language_detected", "language_reported") or "",
            "post_title": _val(row, "source_parent_title") or "",
        })
    return records


def _load_raw_records() -> list[dict]:
    """Returns the raw (pre-filter/dedup) record dicts, preferring the
    eligibility pipeline's outputs (see module docstring) and falling back to
    clean.jsonl / raw youtube_comments*.jsonl when those haven't been
    generated yet."""
    eligibility_paths = _eligibility_paths()
    if all(p.exists() for p in eligibility_paths):
        print(f"Sampling from eligibility pipeline outputs: {', '.join(p.name for p in eligibility_paths)}")
        return _load_from_eligibility_outputs(eligibility_paths)

    print(
        "WARNING: eligibility pipeline outputs not found "
        f"({', '.join(p.name for p in eligibility_paths)} under {ELIGIBILITY_DIR}) — "
        "این سمپل بدون فیلتر eligibility (دوپلیکیت/بازه‌زمانی/provenance) ساخته شده — "
        "قبل از استفاده‌ی نهایی src/preprocessing/apply_eligibility.py را اجرا کن."
    )
    if CLEAN_PATH.exists():
        source_files = [CLEAN_PATH]
    else:
        source_files = [Path(p) for p in sorted(glob.glob(str(ROOT / "data" / "raw" / "*" / "youtube_comments*.jsonl")))]

    raw = []
    for fp in source_files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                raw.append(json.loads(line))
    return raw


def load_records() -> list[dict]:
    seen = set()
    records = []
    for r in _load_raw_records():
        text = (r.get("text") or "").strip()
        if len(text) < MIN_TEXT_LEN:
            continue
        key = (r.get("post_id"), text)
        if key in seen:
            continue
        seen.add(key)
        records.append(r)
    return records


def stratified_sample(records: list[dict], quotas: dict[str, dict[str, int]]) -> list[dict]:
    """Sample per (platform, language) cell according to fixed `quotas` (see
    PLATFORM_LANGUAGE_QUOTAS). Both dimensions are required strata per
    docs/checklist.md §17 ("طبقات اصلی: Platform و Language") — sampling by
    language alone (the previous behaviour) could let one platform crowd out
    the others entirely.

    Leftover slots (a cell's quota exceeds what's actually available) are
    redistributed in two passes: first to other languages within the SAME
    platform (keeps each platform's 100-record total intact), then, only if
    a whole platform's pool is thinner than its quota, across platforms
    (keeps the grand total at 300 at the cost of an uneven platform split —
    printed as a warning by the caller so it's never silent)."""
    random.seed(RANDOM_SEED)
    by_cell = {
        (platform, lang): [r for r in records if r.get("platform") == platform and r.get("language") == lang]
        for platform, langs in quotas.items() for lang in langs
    }
    for group in by_cell.values():
        random.shuffle(group)

    sample = []
    leftover_by_platform = {platform: 0 for platform in quotas}
    for platform, langs in quotas.items():
        for lang, target in langs.items():
            pool = by_cell[(platform, lang)]
            take = min(target, len(pool))
            sample.extend(pool[:take])
            by_cell[(platform, lang)] = pool[take:]
            leftover_by_platform[platform] += target - take

    # pass 1: redistribute within the same platform's other languages
    for platform, langs in quotas.items():
        leftover = leftover_by_platform[platform]
        for lang in langs:
            if leftover <= 0:
                break
            pool = by_cell[(platform, lang)]
            take = min(leftover, len(pool))
            sample.extend(pool[:take])
            by_cell[(platform, lang)] = pool[take:]
            leftover -= take
        leftover_by_platform[platform] = leftover

    # pass 2: last resort, redistribute across platforms if one platform's
    # own pool couldn't cover its quota even after pass 1
    total_leftover = sum(leftover_by_platform.values())
    if total_leftover > 0:
        remaining_pool = [r for pool in by_cell.values() for r in pool]
        random.shuffle(remaining_pool)
        backfilled = remaining_pool[:total_leftover]
        sample.extend(backfilled)
        shortfall_note = (
            f" Only {len(backfilled)}/{total_leftover} could actually be backfilled — "
            "records overall are too few to hit 300."
            if len(backfilled) < total_leftover else ""
        )
        print(
            f"WARNING: {total_leftover} slot(s) could not be filled within their own "
            f"(platform, language) cell (pool exhausted) and were backfilled from other "
            f"platforms — per-platform shortfall was {leftover_by_platform}.{shortfall_note}"
        )

    random.shuffle(sample)
    return sample


# Explicit allowlist (not "everything outside CONTEXT_COLUMNS") — an older
# script version's own context columns (e.g. the pre-2026-08-07 CSV's
# "post_id") would otherwise be misread as hand-filled annotation values and
# block a legitimate schema migration. "human_label" is the old (pre-4-layer)
# schema's single label column, kept here so old hand-labeled files are still
# detected and protected.
KNOWN_ANNOTATION_COLUMNS = {
    c for c in GOLD_SAMPLE_COLUMNS if c not in ("sample_id", "content_id", "platform", "language", "text")
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

        quota_total = sum(n for langs in PLATFORM_LANGUAGE_QUOTAS.values() for n in langs.values())
        print(f"PLATFORM_LANGUAGE_QUOTAS sum to {quota_total} (expected 300).")
        sample = stratified_sample(records, PLATFORM_LANGUAGE_QUOTAS)
        rows = [{
            "sample_id": i,
            "content_id": r.get("content_id") or derive_content_id(r.get("post_id", ""), r.get("text", "")),
            "platform": r.get("platform", ""),
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
    if rows and agreement_n > 0.5 * len(rows):
        print(
            f"WARNING: the agreement subset ({agreement_n} rows) is more than 50% of the "
            f"current sample ({len(rows)} rows), because AGREEMENT_SUBSET_MIN={AGREEMENT_SUBSET_MIN} "
            f"is bigger than {AGREEMENT_SUBSET_FRACTION:.0%} of {len(rows)} rows would be. This "
            "usually means the sample file is smaller than the full 300-row run (e.g. "
            "reused an old/partial CSV without --resample) — the 'subset' the second annotator "
            "gets is effectively the ENTIRE file, not a partial double-check. Continuing anyway."
        )
    random.seed(RANDOM_SEED)
    agreement_rows = random.sample(rows, agreement_n)
    write_sample_csv(AGREEMENT_OUTPUT_PATH, agreement_rows)

    from collections import Counter
    lang_counts = Counter(r["language"] for r in rows)
    platform_counts = Counter(r["platform"] for r in rows)
    print(f"Wrote {len(rows)} comments to {OUTPUT_PATH}")
    print(f"Wrote {len(agreement_rows)} comments (subset, for a SECOND annotator) to {AGREEMENT_OUTPUT_PATH}")
    print(f"By platform: {dict(platform_counts)}")
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
