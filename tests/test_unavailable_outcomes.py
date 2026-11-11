"""Tests for the not-available and empty-data guards in Pipeline B."""

import math

import pandas as pd

from src.temporal_analysis.build_social_weekly_outcomes import build_social_weekly_outcomes
from tests.test_temporal_analysis_common import _minimal_contract_df


def _annotated_rows(n: int, **overrides) -> pd.DataFrame:
    df = _minimal_contract_df().iloc[:1].copy()
    df = pd.concat([df] * n, ignore_index=True)
    df["platform"] = "x"
    df["project_week"] = "W01"
    df["annotation_status"] = "ok"
    df["stance_label"] = "support"
    df["sentiment_label"] = "negative"
    df["emotion_label"] = "anger"
    df["is_flagged_bot_suspect"] = None
    for column, value in overrides.items():
        df[column] = value
    return df


def _row(table: pd.DataFrame, platform: str, week: str, outcome_id: str) -> pd.Series:
    match = table[
        (table["platform"] == platform)
        & (table["project_week"] == week)
        & (table["outcome_id"] == outcome_id)
    ]
    assert len(match) == 1
    return match.iloc[0]


def test_all_null_bot_flag_is_not_available_not_zero():
    table = build_social_weekly_outcomes(_annotated_rows(40), source_file="t.parquet")

    risk = _row(table, "x", "W01", "automation_risk_share")
    assert math.isnan(risk["outcome_value"])
    assert math.isnan(risk["ci_low"]) and math.isnan(risk["ci_high"])
    assert risk["status"] == "not_available"
    assert risk["n_records"] == 40


def test_available_columns_stay_ok_next_to_unavailable_one():
    table = build_social_weekly_outcomes(_annotated_rows(40), source_file="t.parquet")

    support = _row(table, "x", "W01", "support_share")
    assert support["outcome_value"] == 1.0
    assert support["status"] == "ok"


def test_populated_bot_flag_is_computed():
    df = _annotated_rows(40, is_flagged_bot_suspect=False)
    df.loc[:9, "is_flagged_bot_suspect"] = True

    risk = _row(build_social_weekly_outcomes(df, source_file="t.parquet"), "x", "W01", "automation_risk_share")

    assert risk["outcome_value"] == 0.25
    assert risk["status"] == "ok"


def test_week_without_eligible_rows_is_data_gap():
    table = build_social_weekly_outcomes(_annotated_rows(40), source_file="t.parquet")

    gap = _row(table, "reddit", "W02", "support_share")
    assert math.isnan(gap["outcome_value"])
    assert gap["n_records"] == 0
    assert gap["status"] == "data_gap"
