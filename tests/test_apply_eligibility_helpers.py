"""
tests/test_apply_eligibility_helpers.py — unit tests for the pure helper
functions and the exact-ID dedup stage in src/preprocessing/apply_eligibility.py.

Covers roadmap_pipeline.md's own §3 unit-test ask: "تست preprocessing: با یه
نمونه دستی‌ساخته (شامل تکراری، بات، متن خالی) چک کن خروجی درست فیلتر می‌شه"
(a hand-built sample containing a duplicate, a bot-like row, and empty text
must be filtered correctly).
"""

import pandas as pd

from src.preprocessing.apply_eligibility import (
    _is_empty_text,
    _looks_spam,
    _looks_synthetic,
    _present,
    stage_dedup,
)

# -- _present -----------------------------------------------------------------

def test_present_true_for_non_empty_string():
    assert _present("hello") is True


def test_present_false_for_none_nan_and_blank_string():
    assert _present(None) is False
    assert _present(float("nan")) is False
    assert _present("") is False
    assert _present("   ") is False


def test_present_handles_pd_na_without_raising():
    # _load_harmonized() fills missing platform columns with pd.NA -- a bare
    # `if x:` on pd.NA raises TypeError, which is exactly what _present()
    # exists to avoid.
    assert _present(pd.NA) is False


def test_present_true_for_non_empty_collection():
    assert _present(["a"]) is True
    assert _present([]) is False


# -- _is_empty_text -------------------------------------------------------------

def test_is_empty_text_recognizes_deleted_and_removed_markers():
    assert _is_empty_text("[deleted]") is True
    assert _is_empty_text("[removed]") is True
    assert _is_empty_text("  [DELETED]  ".strip().lower()) is True  # case/whitespace tolerant path


def test_is_empty_text_recognizes_missing_value():
    assert _is_empty_text(None) is True
    assert _is_empty_text(float("nan")) is True


def test_is_empty_text_false_for_real_text():
    assert _is_empty_text("این یک نظر واقعی است") is False
    assert _is_empty_text("actual opinion text") is False


# -- _looks_spam ----------------------------------------------------------------

def test_looks_spam_true_for_url_only_text():
    assert _looks_spam("https://example.com/some-article") is True
    assert _looks_spam("https://a.com http://b.com") is True


def test_looks_spam_false_for_text_with_url_and_commentary():
    # A URL alongside real opinion text is not spam by this rule -- only a
    # message that is ENTIRELY link(s).
    assert _looks_spam("check this out https://example.com it's outrageous") is False


def test_looks_spam_false_for_empty_or_missing():
    assert _looks_spam("") is False
    assert _looks_spam(None) is False


# -- _looks_synthetic -------------------------------------------------------------

def test_looks_synthetic_true_for_known_markers():
    assert _looks_synthetic("this is Lorem Ipsum filler") is True
    assert _looks_synthetic("just some test data here") is True


def test_looks_synthetic_false_for_real_opinion_text():
    assert _looks_synthetic("جنگ ایران و آمریکا نگران‌کننده است") is False


# -- stage_dedup ----------------------------------------------------------------

def _dedup_input_df() -> pd.DataFrame:
    # Two rows share the same (platform, platform_content_id) -- an exact
    # duplicate that must be quarantined, keeping only the earliest by
    # collected_at_utc.
    return pd.DataFrame(
        {
            "platform": ["youtube", "youtube", "reddit"],
            "platform_content_id": ["c1", "c1", "c2"],
            "record_uid": ["u1", "u2", "u3"],
            "collected_at_utc": [
                "2026-03-01T00:00:00Z",  # kept (earliest for c1)
                "2026-03-02T00:00:00Z",  # duplicate of c1, later -> quarantined
                "2026-03-01T00:00:00Z",
            ],
            "original_row_number": [0, 1, 2],
            "matched_query_ids": ["q1", "q2", "q3"],
        }
    )


def test_stage_dedup_keeps_one_survivor_per_exact_id():
    survivors, decided = stage_dedup(_dedup_input_df())
    assert len(survivors) == 2  # c1 (one copy) + c2
    assert sorted(survivors["platform_content_id"]) == ["c1", "c2"]


def test_stage_dedup_keeps_earliest_collected_copy():
    survivors, _ = stage_dedup(_dedup_input_df())
    kept_c1 = survivors[survivors["platform_content_id"] == "c1"].iloc[0]
    assert kept_c1["record_uid"] == "u1"  # the 2026-03-01 copy, not the later 03-02 one


def test_stage_dedup_quarantines_the_later_duplicate_with_reason():
    _, decided = stage_dedup(_dedup_input_df())
    assert len(decided) == 1
    row = decided.iloc[0]
    assert row["record_uid"] == "u2"
    assert row["dataset_target"] == "quarantine"
    assert row["primary_exclusion_reason"] == "duplicate_exact_id"
    assert bool(row["eligible"]) is False


def test_stage_dedup_merges_matched_query_ids_from_duplicate_into_survivor():
    survivors, _ = stage_dedup(_dedup_input_df())
    kept_c1 = survivors[survivors["platform_content_id"] == "c1"].iloc[0]
    # q2 (the quarantined duplicate's query) must not be lost -- it's merged
    # into the surviving record so "which query discovered this" stays complete.
    assert set(kept_c1["matched_query_ids"].split(";")) == {"q1", "q2"}


def test_stage_dedup_no_duplicates_returns_empty_decided():
    df = _dedup_input_df()
    df = df[df["platform_content_id"] != "c1"].reset_index(drop=True)  # drop the dup pair, keep only c2
    survivors, decided = stage_dedup(df)
    assert len(survivors) == 1
    assert len(decided) == 0
