"""Content key shared by eligibility, duplicate analysis and annotation.

A record is keyed by its platform_content_id. Legacy rows without one fall
back to "uid::<record_uid>" so they stay unique and reach every later step.
"""

import pandas as pd

UID_PREFIX = "uid::"


def _blank(values: pd.Series) -> pd.Series:
    return values.isna() | values.astype(str).str.strip().eq("")


def content_id(df: pd.DataFrame) -> pd.Series:
    """Return platform_content_id, else "uid::<record_uid>", else NA when both are blank."""
    platform_id = df["platform_content_id"]
    record_uid = df["record_uid"]
    fallback = (UID_PREFIX + record_uid.astype(str)).where(~_blank(record_uid))
    return platform_id.where(~_blank(platform_id), fallback)
