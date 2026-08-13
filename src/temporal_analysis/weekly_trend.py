"""
weekly_trend.py — docs/checklist.md فاز دهم (§22): روند هفتگی

Builds one CSV per §22 label axis (sentiment / stance / emotion /
content_type), each with every platform's weekly class distribution and its
95% Wilson CI, computed independently per platform — per this project's own
closing principle (docs/checklist.md, end of file): "مهم‌ترین اصل آماری این
پروژه آن است که تحلیل اصلی X، Reddit و YouTube جدا باشد."

Columns: platform, project_week, class_label, n, class_count,
class_proportion, wilson_ci_low, wilson_ci_high, is_low_sample,
is_partial_week, is_data_gap.

§22's mandatory rules, each implemented as an explicit column rather than a
silent filter:
  - n < 30            -> is_low_sample=True. The week is NOT dropped — it's
                          kept, fully computed (Wilson CI is well-behaved at
                          low n by construction), just flagged as
                          descriptive-only.
  - W21 (is_partial_week) -> is_partial_week=True on every W21 row. Its raw
                          volume must not be compared to a full week's — left
                          to the analyst reading the flag, not silently
                          normalized away here.
  - n == 0 (a genuine gap, e.g. this project's synthetic reddit/W05) ->
                          is_data_gap=True, class_count/class_proportion/CI
                          all NaN. The week row is still emitted (once per
                          canonical class label) so a gap is a visible row,
                          never a missing one.
  - dataset_target == "opinion_untimed" -> excluded entirely by construction:
                          these rows have no project_week (see
                          scripts/make_synthetic_annotated_dataset.py /
                          pipeline_b_input_contract.md), so they can never
                          match any of the W01-W21 groups this script builds.
                          They remain visible only in descriptive_stats.py's
                          overall/platform tables, per §21.
  - annotation_status != "ok" -> excluded from n and every class_count
                          (§24), same rule descriptive_stats.py applies to
                          its label-axis shares.

Class labels are the FULL canonical enum from src/annotation/schema.py, not
just whatever happened to appear in the data — a class with zero occurrences
in a given week still gets its own class_count=0 row, so downstream charting
never has to guess whether a missing (week, class) combo means "zero" or
"not computed yet."

Usage:
    python -m src.temporal_analysis.weekly_trend
    python -m src.temporal_analysis.weekly_trend --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.annotation.schema import (
    CONTENT_TYPE_LABELS,
    EMOTION_LABELS,
    SENTIMENT_LABELS,
    STANCE_LABELS,
)
from src.temporal_analysis.common import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    LOW_SAMPLE_THRESHOLD,
    PARTIAL_WEEK,
    PLATFORMS,
    WEEKS,
    load_annotated_dataset,
    wilson_confidence_interval,
)

LABEL_AXES: dict[str, tuple[str, list[str]]] = {
    "sentiment": ("sentiment_label", SENTIMENT_LABELS),
    "stance": ("stance_label", STANCE_LABELS),
    "emotion": ("emotion_label", EMOTION_LABELS),
    "content_type": ("content_type_label", CONTENT_TYPE_LABELS),
}


def build_axis_trend(df: pd.DataFrame, column: str, class_labels: list[str]) -> pd.DataFrame:
    """One long-format weekly-trend table (all platforms, all weeks, all
    canonical classes of one label axis) for the given annotation column."""
    # §22 + §24: only weeks that have an actual project_week, and only rows
    # whose annotation succeeded, count toward n/class_count.
    eligible = df[df["annotation_status"] == "ok"]

    rows: list[dict] = []
    for platform in PLATFORMS:
        platform_df = eligible[eligible["platform"] == platform]
        for week in WEEKS:
            week_df = platform_df[platform_df["project_week"] == week]
            n = len(week_df)
            is_data_gap = n == 0
            is_low_sample = 0 < n < LOW_SAMPLE_THRESHOLD
            is_partial = week == PARTIAL_WEEK

            value_counts = week_df[column].value_counts() if n else {}
            for class_label in class_labels:
                class_count = int(value_counts.get(class_label, 0))
                if is_data_gap:
                    class_proportion = float("nan")
                    ci_low, ci_high = float("nan"), float("nan")
                else:
                    class_proportion = round(class_count / n, 4)
                    ci_low, ci_high = wilson_confidence_interval(class_count, n)
                    ci_low, ci_high = round(ci_low, 4), round(ci_high, 4)
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "class_label": class_label,
                    "n": n,
                    "class_count": class_count,
                    "class_proportion": class_proportion,
                    "wilson_ci_low": ci_low,
                    "wilson_ci_high": ci_high,
                    "is_low_sample": is_low_sample,
                    "is_partial_week": is_partial,
                    "is_data_gap": is_data_gap,
                })
    return pd.DataFrame(rows)


def build_all_trends(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        f"weekly_trend_{axis_name}_by_platform": build_axis_trend(df, column, class_labels)
        for axis_name, (column, class_labels) in LABEL_AXES.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    df = load_annotated_dataset(args.input)
    tables = build_all_trends(df)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        out_path = args.output_dir / f"{name}.csv"
        table.to_csv(out_path, index=False, encoding="utf-8-sig")
        weeks = table[["platform", "project_week", "is_data_gap"]].drop_duplicates()
        n_gap_weeks = int(weeks["is_data_gap"].sum())
        print(f"Wrote {len(table)} rows to {out_path} ({n_gap_weeks} (platform, week) data-gap cells)")


if __name__ == "__main__":
    main()
