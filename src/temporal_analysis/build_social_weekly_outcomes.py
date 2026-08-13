"""
build_social_weekly_outcomes.py — builds the one file
docs/financial/02_financial_social_alignment.ipynb (notebook 02) is blocked
on: data/processed/social_media/social_weekly_outcomes_v1.csv
(outputs/audits/financial/financial_social_alignment_status_v1.csv,
component=weekly_social_financial_alignment, required_input).

Like descriptive_stats.py / weekly_trend.py, this reads the one file
Pipeline B is allowed to depend on (docs/pipeline_b_input_contract.md) via
src.temporal_analysis.common.load_annotated_dataset, and defaults to the
synthetic fixture (DEFAULT_INPUT_PATH = data/processed/annotated_dataset.
sample.parquet) so the financial-alignment notebook can be wired and tested
end-to-end *now*, before real annotation exists. Once Pipeline A produces
data/processed/annotated_dataset.parquet, re-run with
    python -m src.temporal_analysis.build_social_weekly_outcomes --input data/processed/annotated_dataset.parquet
and the output overwrites in place with the exact same schema — nothing else
downstream (notebook 02) needs to change.

Output schema matches outputs/audits/financial/financial_social_input_template_v1.csv
exactly:
    platform, project_week, outcome_id, target_id, outcome_value, n_records,
    ci_low, ci_high, source_file, source_version

Six outcome_id values, each a share in [0, 1] aggregated across every Target
(target_id left blank — this is a whole-platform weekly signal, not a
per-Target one, matching what the financial-alignment notebook actually
consumes: "Outcome اجتماعی هفته t"), one row per (platform, project_week,
outcome_id):
    support_share            share of stance_label == "support"
    oppose_share              share of stance_label == "oppose"
    unclear_share             share of stance_label == "unclear"
    negative_sentiment_share  share of sentiment_label == "negative"
    anger_share               share of emotion_label == "anger"
    automation_risk_share     share of is_flagged_bot_suspect == True

This mirrors the outcome set already used in the (gitignored, non-Pipeline-B)
data/processed/weekly_summary.SYNTHETIC_FOR_POWERBI.csv, reusing a naming
convention the team already settled on rather than inventing a new one
(docs/decision_log.md, 2026-08-13).

Same denominator rule as weekly_trend.py (§24): only annotation_status ==
"ok" rows count toward n_records and every share. Same data-gap handling: a
(platform, week) with zero eligible rows still gets all six outcome rows
emitted, with outcome_value/ci_low/ci_high = NaN — a gap is a visible row,
never a missing one.

Usage:
    python -m src.temporal_analysis.build_social_weekly_outcomes
    python -m src.temporal_analysis.build_social_weekly_outcomes --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.temporal_analysis.common import (
    DEFAULT_INPUT_PATH,
    PLATFORMS,
    ROOT,
    WEEKS,
    load_annotated_dataset,
    wilson_confidence_interval,
)

DEFAULT_OUTPUT_PATH = ROOT / "data" / "processed" / "social_media" / "social_weekly_outcomes_v1.csv"
SOURCE_VERSION = "social_weekly_outcomes_build_v1"

# Each outcome_id -> (column it's derived from, the value counted as a "hit").
# is_flagged_bot_suspect is bool, not a label column, but is checked against
# True the same way for a uniform share() helper below.
OUTCOME_DEFINITIONS: dict[str, tuple[str, object]] = {
    "support_share": ("stance_label", "support"),
    "oppose_share": ("stance_label", "oppose"),
    "unclear_share": ("stance_label", "unclear"),
    "negative_sentiment_share": ("sentiment_label", "negative"),
    "anger_share": ("emotion_label", "anger"),
    "automation_risk_share": ("is_flagged_bot_suspect", True),
}


def build_social_weekly_outcomes(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    # §24: only successfully-annotated rows count. Rows with no project_week
    # (dataset_target == "opinion_untimed") never match any WEEKS entry, so
    # they're excluded by construction, same as weekly_trend.py.
    eligible = df[df["annotation_status"] == "ok"]

    rows: list[dict] = []
    for platform in PLATFORMS:
        platform_df = eligible[eligible["platform"] == platform]
        for week in WEEKS:
            week_df = platform_df[platform_df["project_week"] == week]
            n = len(week_df)
            is_data_gap = n == 0

            for outcome_id, (column, hit_value) in OUTCOME_DEFINITIONS.items():
                if is_data_gap:
                    outcome_value = float("nan")
                    ci_low, ci_high = float("nan"), float("nan")
                else:
                    hit_count = int((week_df[column] == hit_value).sum())
                    outcome_value = round(hit_count / n, 4)
                    ci_low, ci_high = wilson_confidence_interval(hit_count, n)
                    ci_low, ci_high = round(ci_low, 4), round(ci_high, 4)
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "outcome_id": outcome_id,
                    "target_id": None,
                    "outcome_value": outcome_value,
                    "n_records": n,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "source_file": source_file,
                    "source_version": SOURCE_VERSION,
                })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    df = load_annotated_dataset(args.input)
    try:
        source_file = str(args.input.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        source_file = str(args.input)

    table = build_social_weekly_outcomes(df, source_file=source_file)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False, encoding="utf-8-sig")

    n_gap_rows = int(table["n_records"].eq(0).sum())
    print(f"Wrote {len(table)} rows to {args.output} ({n_gap_rows} data-gap (platform, week, outcome) rows)")
    print(f"source_file={source_file}")


if __name__ == "__main__":
    main()
