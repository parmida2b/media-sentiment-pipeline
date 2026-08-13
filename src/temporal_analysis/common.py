"""
common.py — shared constants/helpers for src/temporal_analysis/ (Parmida)

Both descriptive_stats.py (docs/checklist.md فاز نهم/§21) and weekly_trend.py
(فاز دهم/§22) read the exact same one file Pipeline B is allowed to touch
(docs/pipeline_b_input_contract.md) and need the exact same platform/week
vocabulary and the same Wilson CI formula — kept here once so the two
scripts can't drift apart on either.

No scipy/statsmodels dependency: neither is in requirements.txt and the
project prefers to stay light (see this task's own instructions) — the
Wilson score interval below is the textbook closed-form, not a library call.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_INPUT_PATH = ROOT / "data" / "processed" / "annotated_dataset.sample.parquet"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "tables"

PLATFORMS = ["x", "reddit", "youtube"]
WEEKS = [f"W{w:02d}" for w in range(1, 22)]
PARTIAL_WEEK = "W21"  # docs/checklist.md §7/§22: only W21 is a real partial (5-day) week
LOW_SAMPLE_THRESHOLD = 30  # docs/checklist.md §22: "هفته با n<30 فقط توصیفی"

# The 4 §22 structured-annotation label axes this project tracks. Shared here
# so descriptive_stats.py's category shares and weekly_trend.py's per-axis
# trend tables enumerate the exact same axis->column mapping.
LABEL_AXES = {
    "sentiment": "sentiment_label",
    "stance": "stance_label",
    "emotion": "emotion_label",
    "content_type": "content_type_label",
}

# Columns pipeline_b_input_contract.md documents as nullable. Used by
# descriptive_stats.py's missing-rate table. (`target` is also nullable but
# is conditionally so — "null only if stance_label=unrelated" — so it is
# reported by the annotation-coverage logic instead of the generic
# missing-rate table; see descriptive_stats.py.)
NULLABLE_COLUMNS = [
    "parent_id",
    "post_id",
    "source_id",
    "source_container",
    "query_id",
    "query_version",
    "language_confidence",
    "country_or_region",
    "geo_confidence",
    "author_hash",
    "automation_risk_score_user",
    "near_duplicate_cluster_id",
]

NON_OK_ANNOTATION_STATUSES = ["low_confidence", "json_parse_failure", "api_failure"]


def load_annotated_dataset(path: Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    """Read the one file Pipeline B is allowed to depend on
    (docs/pipeline_b_input_contract.md) and do the minimal structural sanity
    check that every contract column is present — fails loudly instead of
    letting a silently-missing column turn into a silently-wrong stat
    somewhere downstream."""
    df = pd.read_parquet(path)

    required_columns = {
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
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"{path} is missing contract columns (docs/pipeline_b_input_contract.md): "
            f"{sorted(missing)}"
        )
    return df


def wilson_confidence_interval(class_count: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion class_count/n.

    docs/checklist.md §22 asks for "95% Wilson CI" specifically (not a naive
    normal-approximation CI) because it stays well-behaved for the
    low-n/near-0/near-1 proportions this project's weekly label shares
    routinely hit — a normal-approximation CI can produce bounds outside
    [0, 1] in exactly those cases.

    Returns (nan, nan) when n == 0 (nothing to estimate — the caller is
    expected to treat that as a data-gap week, not a 0% proportion).
    """
    if n <= 0:
        return float("nan"), float("nan")
    if not 0 <= class_count <= n:
        raise ValueError(f"class_count={class_count} must be within [0, n={n}]")

    z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}[confidence]
    p_hat = class_count / n
    denom = 1 + z**2 / n
    center = p_hat + z**2 / (2 * n)
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    low = (center - margin) / denom
    high = (center + margin) / denom
    return max(0.0, low), min(1.0, high)


def median_iqr(series: pd.Series) -> tuple[float, float, float, float]:
    """(median, q1, q3, iqr) for a numeric series, skipping NaN.
    docs/checklist.md §21: "برای متغیرهای چوله مانند Engagement، Median و
    IQR مهم‌تر از Mean هستند" — used for both text length and engagement."""
    clean = series.dropna()
    if clean.empty:
        return (float("nan"),) * 4
    q1, median, q3 = clean.quantile([0.25, 0.5, 0.75])
    return float(median), float(q1), float(q3), float(q3 - q1)
