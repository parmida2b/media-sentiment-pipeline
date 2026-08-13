"""
descriptive_stats.py — docs/checklist.md فاز نهم (§21): آمار توصیفی

Reads the one file Pipeline B is allowed to depend on
(docs/pipeline_b_input_contract.md -> data/processed/annotated_dataset.parquet,
or the synthetic stand-in data/processed/annotated_dataset.sample.parquet from
scripts/make_synthetic_annotated_dataset.py while Pipeline A is still running)
and computes §21's descriptive statistics for the whole dataset, each
platform, and each project week — every count/rate/share §21 lists, minus
raw_n/harmonized_n (those live upstream of the one file Pipeline B can touch;
see collection_coverage.csv from docs/checklist.md §7 for those numbers —
every row in *this* file is already eligible content, so "eligible" here
just means len(df)).

§24's Label-exclusion rule is applied precisely where it applies: rows with
annotation_status != "ok" are dropped only from the four §22 label-axis
shares (sentiment/stance/emotion/content_type), never from row counts,
language/source/automation-risk shares, or text-length/engagement stats —
those describe the CONTENT, not the annotation outcome, and dropping them
would silently understate how much data actually exists. The exclusion rate
itself is reported explicitly (outputs/tables/descriptive_stats_annotation_coverage.csv),
per §24: "چند درصد از کل بودن".

Outputs (outputs/tables/, one CSV per grouping level / concern):
  descriptive_stats_overall.csv                    - 1 row, whole dataset
  descriptive_stats_by_platform.csv                - 1 row per platform
  descriptive_stats_by_week_pooled_all_platforms.csv - 1 row per project week,
      pooled across platforms. Supplementary only — this project's own
      closing principle (docs/checklist.md, end) is that X/Reddit/YouTube
      are analyzed SEPARATELY; use descriptive_stats_by_platform_week.csv
      for the real per-platform weekly breakdown.
  descriptive_stats_by_platform_week.csv           - 1 row per (platform,
      week) cell, including week="UNTIMED" (the opinion_untimed rows,
      which have no project_week) and every W01-W21 cell even when it has
      zero rows (is_data_gap=True) — never silently missing.
  descriptive_stats_category_shares.csv            - long format: n/share
      per (group, dimension, category) for language, source_container,
      automation_risk_bucket, and the 4 label axes (label axes computed on
      annotation_status=="ok" rows only, per §24 above).
  descriptive_stats_missing_rates.csv              - long format: missing
      rate per (group, column) for every nullable contract column.
  descriptive_stats_annotation_coverage.csv        - n_ok / n_low_confidence
      / n_json_parse_failure / n_api_failure / pct_non_ok per group.

Usage:
    python -m src.temporal_analysis.descriptive_stats
    python -m src.temporal_analysis.descriptive_stats --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.temporal_analysis.common import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    LABEL_AXES,
    NON_OK_ANNOTATION_STATUSES,
    NULLABLE_COLUMNS,
    PLATFORMS,
    WEEKS,
    load_annotated_dataset,
    median_iqr,
)

UNTIMED_BUCKET = "UNTIMED"  # stand-in "week" label for dataset_target=opinion_untimed rows


def bucket_automation_risk(score: float | None) -> str:
    """Coarse automation_risk_score_user bucket for the category-shares
    table. `None`/NaN (score not available — see common.NULLABLE_COLUMNS)
    is its own explicit "unknown" bucket, never silently folded into "low"."""
    if pd.isna(score):
        return "unknown"
    if score < 0.3:
        return "low"
    if score < 0.6:
        return "medium"
    return "high"


def summarize_group(g: pd.DataFrame) -> dict:
    """§21's scalar metrics for one slice of the dataset (whole dataset /
    one platform / one week / one platform-week cell)."""
    n_total = len(g)
    n_ok = int((g["annotation_status"] == "ok").sum())
    n_non_ok = n_total - n_ok

    text_med, text_q1, text_q3, text_iqr = median_iqr(g["text_raw"].str.len())
    eng_med, eng_q1, eng_q3, eng_iqr = median_iqr(g["engagement_score"])

    return {
        "n_total": n_total,
        "n_annotation_ok": n_ok,
        "n_annotation_non_ok": n_non_ok,
        "pct_annotation_non_ok": round(100 * n_non_ok / n_total, 2) if n_total else float("nan"),
        "n_opinion_untimed": int((g["dataset_target"] == "opinion_untimed").sum()),
        "n_unique_content_id": int(g["content_id"].nunique()),
        "n_unique_text_raw": int(g["text_raw"].nunique()),
        "n_unique_parent_id": int(g["parent_id"].nunique(dropna=True)),
        "n_unique_post_id": int(g["post_id"].nunique(dropna=True)),
        "n_unique_author_hash": int(g["author_hash"].nunique(dropna=True)),
        "n_unique_source_id": int(g["source_id"].nunique(dropna=True)),
        "n_unique_query_id": int(g["query_id"].nunique(dropna=True)),
        "duplicate_rate_exact": round(float(g["is_exact_duplicate"].mean()), 4) if n_total else float("nan"),
        "duplicate_rate_near": round(float(g["is_near_duplicate"].mean()), 4) if n_total else float("nan"),
        "text_length_median": text_med,
        "text_length_q1": text_q1,
        "text_length_q3": text_q3,
        "text_length_iqr": text_iqr,
        "engagement_score_median": eng_med,
        "engagement_score_q1": eng_q1,
        "engagement_score_q3": eng_q3,
        "engagement_score_iqr": eng_iqr,
    }


def category_share_rows(g: pd.DataFrame, group_keys: dict) -> list[dict]:
    """Long-format n/proportion rows for one slice, covering every §21
    "share of ..." bullet this contract's columns support: language, source,
    content type (== content_type_label; see this task's closing note on why
    the checklist's two separate "نوع محتوا" / "Opinion/News/Quotation/Spam"
    bullets collapse into the one column the contract actually provides),
    automation risk, and the 4 §22 label axes."""
    rows: list[dict] = []

    def add(dimension: str, series: pd.Series) -> None:
        total = len(series)
        if total == 0:
            return
        counts = series.value_counts(dropna=True)
        for category, n in counts.items():
            rows.append({**group_keys, "dimension": dimension, "category": str(category),
                         "n": int(n), "proportion": round(n / total, 4)})
        n_missing = int(series.isna().sum())
        if n_missing:
            rows.append({**group_keys, "dimension": dimension, "category": "(missing)",
                         "n": n_missing, "proportion": round(n_missing / total, 4)})

    add("language_detected", g["language_detected"])
    add("source_container", g["source_container"])
    add("automation_risk_bucket", g["automation_risk_score_user"].apply(bucket_automation_risk))

    ok_rows = g[g["annotation_status"] == "ok"]
    for axis_name, column in LABEL_AXES.items():
        add(f"label:{axis_name}", ok_rows[column])

    return rows


def missing_rate_rows(g: pd.DataFrame, group_keys: dict) -> list[dict]:
    total = len(g)
    if total == 0:
        return []
    rows = []
    for column in NULLABLE_COLUMNS:
        n_missing = int(g[column].isna().sum())
        rows.append({**group_keys, "column": column, "n_missing": n_missing,
                     "missing_rate": round(n_missing / total, 4)})
    return rows


def annotation_coverage_rows(g: pd.DataFrame, group_keys: dict) -> dict:
    total = len(g)
    counts = g["annotation_status"].value_counts()
    n_ok = int(counts.get("ok", 0))
    non_ok_counts = {status: int(counts.get(status, 0)) for status in NON_OK_ANNOTATION_STATUSES}
    n_non_ok = sum(non_ok_counts.values())
    return {
        **group_keys,
        "n_total": total,
        "n_ok": n_ok,
        **{f"n_{status}": n for status, n in non_ok_counts.items()},
        "n_non_ok": n_non_ok,
        "pct_non_ok": round(100 * n_non_ok / total, 2) if total else float("nan"),
    }


def build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    week_bucket = df["project_week"].fillna(UNTIMED_BUCKET)
    df = df.assign(_week_bucket=week_bucket)

    tables: dict[str, list[dict]] = {
        "overall": [], "by_platform": [], "by_week_pooled": [], "by_platform_week": [],
    }
    category_shares: list[dict] = []
    missing_rates: list[dict] = []
    coverage: list[dict] = []

    # --- overall -------------------------------------------------------
    tables["overall"].append({"group": "overall", **summarize_group(df)})
    category_shares += category_share_rows(df, {"group_level": "overall", "platform": None, "week": None})
    missing_rates += missing_rate_rows(df, {"group_level": "overall", "platform": None, "week": None})
    coverage.append(annotation_coverage_rows(df, {"group_level": "overall", "platform": None, "week": None}))

    # --- by platform -----------------------------------------------------
    for platform in PLATFORMS:
        g = df[df["platform"] == platform]
        tables["by_platform"].append({"platform": platform, **summarize_group(g)})
        keys = {"group_level": "platform", "platform": platform, "week": None}
        category_shares += category_share_rows(g, keys)
        missing_rates += missing_rate_rows(g, keys)
        coverage.append(annotation_coverage_rows(g, keys))

    # --- by week, pooled across platforms (supplementary) -----------------
    for week in WEEKS + [UNTIMED_BUCKET]:
        g = df[df["_week_bucket"] == week]
        row = {"project_week": week, "is_data_gap": week != UNTIMED_BUCKET and len(g) == 0, **summarize_group(g)}
        tables["by_week_pooled"].append(row)
        keys = {"group_level": "week_pooled", "platform": None, "week": week}
        category_shares += category_share_rows(g, keys)
        missing_rates += missing_rate_rows(g, keys)
        coverage.append(annotation_coverage_rows(g, keys))

    # --- by (platform, week) — the primary breakdown ----------------------
    for platform in PLATFORMS:
        for week in WEEKS + [UNTIMED_BUCKET]:
            g = df[(df["platform"] == platform) & (df["_week_bucket"] == week)]
            row = {
                "platform": platform, "project_week": week,
                "is_data_gap": week != UNTIMED_BUCKET and len(g) == 0,
                **summarize_group(g),
            }
            tables["by_platform_week"].append(row)
            keys = {"group_level": "platform_week", "platform": platform, "week": week}
            category_shares += category_share_rows(g, keys)
            missing_rates += missing_rate_rows(g, keys)
            coverage.append(annotation_coverage_rows(g, keys))

    return {
        "descriptive_stats_overall": pd.DataFrame(tables["overall"]),
        "descriptive_stats_by_platform": pd.DataFrame(tables["by_platform"]),
        "descriptive_stats_by_week_pooled_all_platforms": pd.DataFrame(tables["by_week_pooled"]),
        "descriptive_stats_by_platform_week": pd.DataFrame(tables["by_platform_week"]),
        "descriptive_stats_category_shares": pd.DataFrame(category_shares),
        "descriptive_stats_missing_rates": pd.DataFrame(missing_rates),
        "descriptive_stats_annotation_coverage": pd.DataFrame(coverage),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    df = load_annotated_dataset(args.input)
    tables = build_tables(df)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        out_path = args.output_dir / f"{name}.csv"
        table.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(table)} rows to {out_path}")


if __name__ == "__main__":
    main()
