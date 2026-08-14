"""
build_annotated_dataset.py -- the Pipeline A -> Pipeline B bridge script that
docs/pipeline_b_input_contract.md names but that did not exist before
2026-08-14: joins apply_eligibility.py's eligible-content output with
run_full_annotation.py's annotation output (by content_id) and writes
data/processed/annotated_dataset.parquet in the exact schema the contract
locks.

Left join, eligibility as the base population (every eligible record appears
at least once, even if not annotated yet -- annotation_status=
"pending_annotation" for those): this lets Pipeline B see the TRUE current
annotation coverage (checklist.md's own requirement that Coverage be
reported honestly), instead of only showing the subset that happens to be
annotated so far.

Two DELIBERATE, DOCUMENTED deviations from docs/pipeline_b_input_contract.md
as written -- flagged here for Pipeline B/team sign-off, not silently
decided:

1. `content_id` is NOT unique in the output. run_full_annotation.py scores
   stance against up to 3 primary Targets (T01/T02/T03) per record (see its
   --targets flag), i.e. up to 3 annotation rows per content_id -- but the
   contract's schema implies one row per content_id with a single `target`.
   Collapsing to one row per content_id would silently discard 2/3 of the
   real per-Target stance judgments that src/event_analysis/event_study.py
   and checklist.md item 25 (per-Target Stance share around events) need.
   Keeping one row per (content_id, target) preserves all of it; every
   other column (sentiment/emotion/content_type/eligibility/provenance/...)
   is simply repeated across a content_id's target-rows. A consumer that
   truly wants one row per content_id can dedupe on content_id keeping any
   one target-row (sentiment/emotion/content_type do not vary by target).

2. `automation_risk_score_user` / `is_flagged_bot_suspect` are always null
   here. They exist only in data/interim/clean.jsonl's Tier-B (per-author,
   joined by raw author_channel_id) -- a different identifier space than
   this file's author_hash (raw_schema_v05 hashed id), and clean.jsonl
   predates the eligibility/harmonization rebuild (docs/decision_log.md
   2026-08-14), so it is not a safe join key here without real work to
   reconcile the two. Left as an explicit, documented gap rather than a
   fragile best-effort join under time pressure -- see docs/decision_log.md.

Usage:
    python src/annotation/build_annotated_dataset.py
    python src/annotation/build_annotated_dataset.py --annotation-glob "outputs/full_annotation/shard_*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
ELIGIBLE_PARQUETS = [
    ROOT / "data" / "interim" / "opinion_main.parquet",
    ROOT / "data" / "interim" / "opinion_limited.parquet",
    ROOT / "data" / "interim" / "opinion_untimed.parquet",
]
DEFAULT_ANNOTATION_GLOB = str(ROOT / "outputs" / "full_annotation" / "shard_*.jsonl")
OUTPUT_PATH = ROOT / "data" / "processed" / "annotated_dataset.parquet"

# docs/pipeline_b_input_contract.md's exact column order.
CONTRACT_COLUMNS = [
    "content_id", "platform", "parent_id", "post_id", "dataset_target", "provenance_quality",
    "created_at_utc", "project_week", "in_window", "is_partial_week",
    "text_raw",
    "source_id", "source_container", "query_id", "query_version",
    "language_detected", "language_confidence", "country_or_region", "geo_confidence",
    "engagement_score", "engagement_replies", "engagement_shares", "engagement_views",
    "author_hash", "automation_risk_score_user", "is_flagged_bot_suspect",
    "is_exact_duplicate", "is_near_duplicate", "near_duplicate_cluster_id",
    "target", "sentiment_label", "stance_label", "emotion_label", "content_type_label",
    "confidence", "reason_code", "annotation_status", "model_version", "prompt_version",
    "annotated_at_utc",
]

ELIGIBILITY_SOURCE_COLUMNS = [
    "platform_content_id", "platform", "parent_id", "source_parent_id", "dataset_target",
    "provenance_quality", "created_at_utc", "project_week", "in_window", "is_partial_week",
    "text_raw", "source_id", "source_container", "query_id", "query_version",
    "language_detected", "language_confidence", "country_or_region", "geo_confidence",
    "engagement_score", "engagement_replies", "engagement_shares", "engagement_views",
    "author_hash", "duplicate_text_diff_id", "duplicate_text_group_id", "near_duplicate_cluster_id",
]


def load_eligible() -> pd.DataFrame:
    frames = []
    for path in ELIGIBLE_PARQUETS:
        if not path.exists():
            raise FileNotFoundError(f"{path} not found -- run src/preprocessing/apply_eligibility.py first.")
        df = pd.read_parquet(path)
        cols = [c for c in ELIGIBILITY_SOURCE_COLUMNS if c in df.columns]
        missing = set(ELIGIBILITY_SOURCE_COLUMNS) - set(cols)
        if missing:
            print(f"NOTE: {path.name} is missing columns {sorted(missing)} "
                  "(run src/preprocessing/duplicate_analysis.py if duplicate_text_diff_id/"
                  "near_duplicate_cluster_id are missing) -- filled with null.")
            for m in missing:
                df[m] = None
        frames.append(df[ELIGIBILITY_SOURCE_COLUMNS])
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(columns={"platform_content_id": "content_id", "source_parent_id": "post_id"})
    dupes = combined["content_id"].duplicated().sum()
    if dupes:
        raise SystemExit(
            f"internal error: {dupes} duplicate content_id(s) across opinion_main/opinion_limited/"
            "opinion_untimed -- apply_eligibility.py's buckets should be mutually exclusive."
        )
    return combined


def load_annotations(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"WARNING: no annotation files matched {pattern} -- output will have 0 annotated rows "
              "(every eligible record gets annotation_status=pending_annotation).")
        return pd.DataFrame(columns=[
            "content_id", "target_id", "sentiment", "stance", "emotion", "content_type",
            "confidence", "reason_code", "annotation_status", "model_version", "prompt_version",
            "annotated_at_utc",
        ])

    frames = [pd.read_json(f, lines=True) for f in files]
    raw = pd.concat(frames, ignore_index=True)
    print(f"Read {len(raw):,} annotation row(s) from {len(files)} file(s): {[Path(f).name for f in files]}")

    # Keep only the best (ok wins; latest wins among same status) attempt
    # per (content_id, target_id) -- a shard file is append-only across
    # resumed runs, so the same pair can appear more than once.
    raw["_ok_rank"] = (raw["annotation_status"] == "ok").astype(int)
    raw = raw.sort_values(["_ok_rank"]).drop_duplicates(subset=["content_id", "target_id"], keep="last")
    raw = raw.drop(columns=["_ok_rank"])

    # run_full_annotation.py's shard rows also carry their own `platform`
    # column (copied at write time from the eligibility row that was being
    # annotated) -- dropped here, not merged in. Merging two frames that
    # both have a `platform` column silently produces `platform_x`/
    # `platform_y` (pandas' default suffixing for unmatched-but-same-named
    # non-key columns), so the bare `platform` column build() expects never
    # exists and gets filled with None for every row -- found 2026-08-14 on
    # the very first real run (100% null platform in the output). The
    # eligibility side's `platform` is authoritative anyway (it is read
    # straight from apply_eligibility.py's harmonized+validated output, not
    # copied through an extra hop), so the annotation side's copy is
    # redundant even when it IS correct.
    if "platform" in raw.columns:
        raw = raw.drop(columns=["platform"])
    return raw


def build(annotation_glob: str) -> pd.DataFrame:
    eligible = load_eligible()
    annotations = load_annotations(annotation_glob)

    merged = eligible.merge(
        annotations.rename(columns={"target_id": "target"}),
        on="content_id", how="left",
    )
    merged["annotation_status"] = merged["annotation_status"].fillna("pending_annotation")

    merged["is_exact_duplicate"] = False  # exact-ID duplicates never reach this population -- routed to quarantine upstream
    merged["is_near_duplicate"] = (
        merged["near_duplicate_cluster_id"].notna() | merged["duplicate_text_diff_id"].fillna(False)
    )
    merged["near_duplicate_cluster_id"] = merged["near_duplicate_cluster_id"].where(
        merged["near_duplicate_cluster_id"].notna(), merged["duplicate_text_group_id"]
    )
    merged["sentiment_label"] = merged.pop("sentiment") if "sentiment" in merged.columns else None
    merged["stance_label"] = merged.pop("stance") if "stance" in merged.columns else None
    merged["emotion_label"] = merged.pop("emotion") if "emotion" in merged.columns else None
    merged["content_type_label"] = merged.pop("content_type") if "content_type" in merged.columns else None
    merged["automation_risk_score_user"] = None  # documented gap -- see module docstring
    merged["is_flagged_bot_suspect"] = None       # documented gap -- see module docstring

    for col in CONTRACT_COLUMNS:
        if col not in merged.columns:
            merged[col] = None
    return merged[CONTRACT_COLUMNS]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotation-glob", default=DEFAULT_ANNOTATION_GLOB)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out = build(args.annotation_glob)

    n_content_ids = out["content_id"].nunique()
    status_counts = out["annotation_status"].value_counts()
    print(f"\nOutput: {len(out):,} row(s) covering {n_content_ids:,} unique eligible content_id(s).")
    print("annotation_status breakdown:")
    for status, n in status_counts.items():
        print(f"  {status:20s} {n:8,d}  ({100 * n / len(out):.1f}%)")

    n_ok = int((out["annotation_status"] == "ok").sum())
    n_ok_content_ids = out.loc[out["annotation_status"] == "ok", "content_id"].nunique()
    print(f"\nReal ('ok') annotations: {n_ok:,} row(s) covering {n_ok_content_ids:,} unique content_id(s) "
          f"({100 * n_ok_content_ids / n_content_ids:.2f}% of eligible content).")
    print(
        "\nThis is a PARTIAL real dataset -- Full Annotation is still in progress "
        "(docs/decision_log.md 2026-08-14: Groq daily quota exhausted, OpenRouter account "
        "at $0 credit). Every eligible record IS present (so Coverage reporting stays honest); "
        "most currently have annotation_status=pending_annotation, not ok."
    )

    if not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUTPUT_PATH, index=False)
        print(f"\nWrote {OUTPUT_PATH}")
    else:
        print("\n--dry-run: nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
