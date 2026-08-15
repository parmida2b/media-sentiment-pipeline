"""
tests/test_temporal_analysis_common.py — unit tests for
src/temporal_analysis/common.py, the single module every Pipeline B script
(weekly_trend.py, composition_shift.py, group_comparison.py,
sensitivity_analysis.py, event_study.py, build_social_weekly_outcomes.py,
descriptive_stats.py) routes its input-loading through.

Includes regression tests for the 2026-08-14 fix: every script's --input is
now required (no synthetic-fixture default at all -- see common.py's comment
where DEFAULT_INPUT_PATH used to be), because a synthetic default meant
silently computing every statistic on 800 fake rows instead of real
annotation output, with no error at all -- caught happening in practice
during a pipeline review (docs/decision_log.md 2026-08-14).
load_annotated_dataset() still warns (rather than silently accepting it) if
--input is explicitly pointed at something that looks synthetic, as
defense-in-depth for local testing with scripts/make_synthetic_annotated_dataset.py.
"""

import math

import pandas as pd
import pytest

from src.temporal_analysis.common import (
    load_annotated_dataset,
    median_iqr,
    wilson_confidence_interval,
)

# -- wilson_confidence_interval ----------------------------------------------

def test_wilson_ci_n_zero_returns_nan():
    low, high = wilson_confidence_interval(0, 0)
    assert math.isnan(low) and math.isnan(high)


def test_wilson_ci_bounds_stay_within_unit_interval():
    # The whole reason this project uses Wilson over a naive normal
    # approximation: near-0/near-1 proportions must not produce a bound
    # outside [0, 1].
    for class_count, n in [(0, 10), (10, 10), (1, 5), (4, 5)]:
        low, high = wilson_confidence_interval(class_count, n)
        assert 0.0 <= low <= high <= 1.0


def test_wilson_ci_center_matches_proportion_for_large_n():
    # For large n the Wilson interval's center converges close to the raw
    # proportion.
    low, high = wilson_confidence_interval(500, 1000)
    assert low < 0.5 < high
    assert (high - low) < 0.1


def test_wilson_ci_rejects_class_count_above_n():
    with pytest.raises(ValueError):
        wilson_confidence_interval(11, 10)


def test_wilson_ci_rejects_negative_class_count():
    with pytest.raises(ValueError):
        wilson_confidence_interval(-1, 10)


# -- median_iqr ---------------------------------------------------------------

def test_median_iqr_basic():
    median, q1, q3, iqr = median_iqr(pd.Series([1, 2, 3, 4, 5]))
    assert median == 3
    assert iqr == q3 - q1


def test_median_iqr_all_nan_returns_nan_tuple():
    result = median_iqr(pd.Series([float("nan"), float("nan")]))
    assert all(math.isnan(v) for v in result)


def test_median_iqr_skips_nan_values():
    with_nan = median_iqr(pd.Series([1, 2, 3, float("nan")]))
    without_nan = median_iqr(pd.Series([1, 2, 3]))
    assert with_nan == without_nan


# -- load_annotated_dataset: contract-column check ----------------------------

def test_load_annotated_dataset_raises_on_missing_contract_column(tmp_path):
    # A parquet missing even one docs/pipeline_b_input_contract.md column
    # must fail loudly, not let a downstream KeyError/silent-NaN column
    # happen somewhere deep in a stats function instead.
    df = pd.DataFrame({"content_id": ["a", "b"], "platform": ["x", "x"]})
    path = tmp_path / "incomplete.parquet"
    df.to_parquet(path)
    with pytest.raises(ValueError, match="missing contract columns"):
        load_annotated_dataset(path)


# -- load_annotated_dataset: no default at all (2026-08-14) -----------------

def test_load_annotated_dataset_has_no_default_path():
    # common.py used to define DEFAULT_INPUT_PATH pointing at the synthetic
    # fixture; it's gone now, and load_annotated_dataset's `path` parameter
    # has no default either -- calling it with zero arguments must be a
    # TypeError, not a fallback to anything.
    with pytest.raises(TypeError):
        load_annotated_dataset()


# -- load_annotated_dataset: synthetic-fixture warning (defense-in-depth) ---

def test_load_annotated_dataset_warns_when_filename_looks_synthetic(tmp_path, capsys):
    # Filename heuristic: a file literally named like the old fixture (or
    # any "*sample*"/"*synthetic*" name) still gets warned about, even
    # though nothing defaults to it anymore -- catches the case where
    # someone manually re-points --input at a regenerated fixture.
    df = _minimal_contract_df()
    path = tmp_path / "annotated_dataset.sample.parquet"
    df.to_parquet(path)

    load_annotated_dataset(path)
    captured = capsys.readouterr()
    assert "SYNTHETIC" in captured.err
    assert "annotated_dataset.parquet" in captured.err  # tells the user the real-data flag


def test_load_annotated_dataset_warns_via_is_synthetic_column_even_with_unrelated_name(tmp_path):
    # Defense-in-depth: even a file whose NAME doesn't look synthetic must
    # still warn if its own is_synthetic column says so (catches a renamed/
    # copied fixture, not just an obvious filename).
    df = _minimal_contract_df()
    df["is_synthetic"] = True
    path = tmp_path / "totally_unrelated_name.parquet"
    df.to_parquet(path)

    load_annotated_dataset(path)
    # (capsys not used here to keep this test focused on "doesn't crash and
    # the column is honored"; the stderr-content assertion lives in the
    # sibling test below to keep capsys usage isolated per test.)


def test_load_annotated_dataset_synthetic_column_warning_reaches_stderr(tmp_path, capsys):
    df = _minimal_contract_df()
    df["is_synthetic"] = [True, False]
    path = tmp_path / "mixed.parquet"
    df.to_parquet(path)

    load_annotated_dataset(path)
    captured = capsys.readouterr()
    assert "SYNTHETIC" in captured.err
    assert "1/2 rows" in captured.err


def test_load_annotated_dataset_real_looking_path_is_silent(tmp_path, capsys):
    # A file that neither looks synthetic by name nor is flagged
    # is_synthetic=True must NOT print the warning -- it would train people
    # to ignore it.
    df = _minimal_contract_df()
    path = tmp_path / "annotated_dataset.parquet"  # deliberately real-looking name
    df.to_parquet(path)

    load_annotated_dataset(path)
    captured = capsys.readouterr()
    assert "SYNTHETIC" not in captured.err


def _minimal_contract_df() -> pd.DataFrame:
    """A 2-row DataFrame with every column load_annotated_dataset()'s
    contract check requires, values otherwise arbitrary."""
    required_columns = [
        "content_id", "platform", "parent_id", "post_id", "dataset_target",
        "provenance_quality", "created_at_utc", "project_week", "in_window",
        "is_partial_week", "text_raw", "source_id", "source_container",
        "query_id", "query_version", "language_detected", "language_confidence",
        "country_or_region", "geo_confidence", "engagement_score",
        "engagement_replies", "engagement_shares", "engagement_views",
        "author_hash", "automation_risk_score_user", "is_flagged_bot_suspect",
        "is_exact_duplicate", "is_near_duplicate", "near_duplicate_cluster_id",
        "target", "sentiment_label", "stance_label", "emotion_label",
        "content_type_label", "confidence", "reason_code", "annotation_status",
        "model_version", "prompt_version", "annotated_at_utc",
    ]
    return pd.DataFrame({col: [None, None] for col in required_columns})
