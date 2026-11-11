"""Tests for the shared content key and the loaders that build the annotation population."""

import pandas as pd
import pytest

from src.preprocessing.duplicate_analysis import _row_key


def content_id(df):
    from src.common.ids import content_id as shared_content_id

    return shared_content_id(df)


def _mixed_ids() -> pd.DataFrame:
    return pd.DataFrame({
        "platform_content_id": ["yt_1", None, float("nan"), "", pd.NA, "t3_x"],
        "record_uid": ["u1", "abc", "def", "ghi", "jkl", "u6"],
    })


def test_content_id_uses_platform_id_or_uid_fallback():
    assert content_id(_mixed_ids()).tolist() == [
        "yt_1", "uid::abc", "uid::def", "uid::ghi", "uid::jkl", "t3_x",
    ]


def test_content_id_matches_duplicate_analysis_row_key():
    df = _mixed_ids()
    assert content_id(df).tolist() == _row_key(df).tolist()


def test_content_id_treats_whitespace_platform_id_as_missing():
    df = pd.DataFrame({"platform_content_id": ["  "], "record_uid": ["abc"]})
    assert content_id(df).tolist() == ["uid::abc"]


def test_content_id_is_missing_when_both_ids_are_missing():
    df = pd.DataFrame({"platform_content_id": [None], "record_uid": [None]})
    assert content_id(df).isna().all()


def _eligible_frame(dataset_target: str) -> pd.DataFrame:
    return pd.DataFrame({
        "platform_content_id": [None, "yt_real"],
        "record_uid": ["abc", "u2"],
        "source_parent_id": ["vid1", "vid1"],
        "source_parent_title": ["title", "title"],
        "text_raw": ["a legacy comment with text", "a new comment with text"],
        "platform": ["youtube", "youtube"],
        "language_detected": ["en", "en"],
        "dataset_target": [dataset_target, dataset_target],
        "project_week": ["W03", "W03"],
    })


@pytest.fixture
def eligible_parquets(tmp_path):
    paths = []
    for target in ["opinion_main", "opinion_limited", "opinion_untimed"]:
        path = tmp_path / f"{target}.parquet"
        frame = _eligible_frame(target) if target == "opinion_main" else _eligible_frame(target).iloc[0:0]
        frame.to_parquet(path)
        paths.append(path)
    return paths


def test_load_eligible_records_keeps_rows_without_platform_id(monkeypatch, eligible_parquets):
    from src.annotation import run_full_annotation

    monkeypatch.setattr(run_full_annotation, "ELIGIBLE_PARQUETS", eligible_parquets)
    records = run_full_annotation.load_eligible_records()
    assert sorted(records["content_id"]) == ["uid::abc", "yt_real"]


def test_labeling_sample_gives_rows_without_platform_id_a_content_id(eligible_parquets):
    from src.annotation.build_labeling_sample import _load_from_eligibility_outputs

    records = _load_from_eligibility_outputs(eligible_parquets)
    assert sorted(r["content_id"] for r in records) == ["uid::abc", "yt_real"]
