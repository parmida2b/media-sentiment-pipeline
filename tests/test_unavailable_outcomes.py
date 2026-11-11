"""Tests for the not-available and empty-data guards in Pipeline B."""

import math

import pandas as pd

from src.temporal_analysis import group_comparison
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


def _run_group_comparison(tmp_path, df: pd.DataFrame) -> pd.DataFrame:
    path = tmp_path / "annotated_dataset.parquet"
    df.to_parquet(path)
    return group_comparison.run(path, tmp_path / "out")


def _not_annotated_dataset() -> pd.DataFrame:
    df = _annotated_rows(6, annotation_status="not_annotated")
    df["platform"] = ["x", "x", "reddit", "reddit", "youtube", "youtube"]
    df["language_detected"] = "fa"
    df["text_raw"] = "abc"
    df["stance_label"] = None
    df["sentiment_label"] = None
    df["engagement_score"] = None
    return df


def test_group_comparison_without_ok_rows_reports_not_computable(tmp_path):
    out = _run_group_comparison(tmp_path, _not_annotated_dataset())

    by_test = out.groupby("test")
    for test in ("chi_square", "fisher_exact"):
        rows = by_test.get_group(test)
        assert rows["assumptions"].str.startswith("not_computable").all()
        assert rows["p_value"].isna().all()
    assert len(by_test.get_group("chi_square")) == 2
    assert len(by_test.get_group("fisher_exact")) == 3
    assert out["p_value"].isna().all()


def test_welch_with_single_row_group_is_not_computable(tmp_path):
    df = _not_annotated_dataset().iloc[[0, 2, 3, 4, 5]].reset_index(drop=True)

    out = _run_group_comparison(tmp_path, df)

    welch = out[out["comparison_id"] == "welch_text_length_x_vs_reddit"].iloc[0]
    assert welch["assumptions"].startswith("not_computable")
    assert pd.isna(welch["p_value"])


def test_mann_whitney_with_empty_group_is_not_computable():
    row = group_comparison.mann_whitney_test(
        pd.Series([1.0, 2.0, 3.0]), pd.Series([], dtype=float), "id", "q", "g"
    )

    assert row["assumptions"].startswith("not_computable")
    assert row["p_value"] is None
