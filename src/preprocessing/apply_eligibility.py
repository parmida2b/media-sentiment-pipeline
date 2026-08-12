"""
apply_eligibility.py — implements docs/eligibility_rules_v03.md §2-§4
(Parmida, Day 5+)

Reads the harmonized layer (docs/raw_schema_v05.md's `raw_harmonized`
output, one parquet per platform under data/raw_harmonized/{platform}/) and
runs the record-level Eligibility pipeline in the exact order fixed by
eligibility_rules_v03.md §2:

    Raw validation
    -> Exact-ID deduplication
    -> Date rule
    -> Text availability
    -> Provenance rule
    -> Topic relevance
    -> Analysis-role rule
    -> Analytical datasets

Every record ends up in exactly one of six buckets (§3/§3.2/§4 + §12's
`dataset_target` enum, minus `neither` — see below):

    opinion_main       full-quality opinion record (§3 general entry
                       condition, complete provenance, valid timestamp)
    opinion_limited    opinion record, `provenance_quality = partial`
                       (§3: "تحلیل با و بدون این رکوردها تکرار می‌شود")
    opinion_untimed    opinion record, no usable timestamp (§3: kept out of
                       weekly/event/financial-window analysis)
    context_only       not an independent opinion unit but keeps Parent
                       context (§3.2, §4: YouTube video, textless Reddit
                       submission)
    audit_only         kept only for Collection documentation (§3.2, §4:
                       repost without text, deleted/removed content)
    quarantine         everything else that fails a hard gate (§3.1:
                       "رکوردهای مشکوک در quarantine نگهداری می‌شوند و حذف
                       فیزیکی نمی‌شوند" — nothing is ever physically
                       dropped, including exact duplicates and genuinely
                       out-of-window/out-of-scope/invalid records)

§12's `dataset_target` enum also lists a 7th value, `neither` — this script
never emits it: every record that isn't Opinion/context/audit is routed to
`quarantine` instead, which is the concrete embodiment of "قرنطینه، نه حذف"
for those same cases and keeps every excluded row physically retrievable.

Row-count reconciliation (verifies nothing was silently dropped) follows
the second equation in legacy_data_intake_and_harmonization_plan_v1.md §9
("آشتی تعداد رکوردها"), applied to this script's `harmonized_rows` input:

    harmonized_rows
    = opinion_main + opinion_limited + opinion_untimed
    + context_only + audit_only
    + excluded + duplicate_exact

`excluded` and `duplicate_exact` are both physically stored inside the one
`quarantine` output (see above); the equation splits them back out via
`primary_exclusion_reason == 'duplicate_exact_id'` purely for the printed
check. The full per-record decision (§12's Audit table) is written
separately to data/audits/eligibility_audit.{parquet,csv}.

Scope note on Topic relevance (execution-order step 6): this change targets
§2-§4 precisely. §5's full in-scope/out-of-scope keyword domain and §7's
two-stage Relevance audit (rule-based screening + human-reviewed sample)
are a separate, larger task. The `assess_topic_relevance` stage below does
only the structural, deterministic part that has to run inline for the
pipeline order to hold together (synthetic/placeholder text,
bare-URL-with-no-query-linkage spam) and passes everything else through —
every surviving record already came from a topic-scoped query per
query_registry_v5.md, so "assumed in scope unless structurally obviously
not" is the correct conservative default here, not a full classifier.

Input:
  data/raw_harmonized/{platform}/*.parquet   (platform in x/reddit/youtube)

Output (under data/interim/, one parquet per dataset_target, always written
even when empty so downstream scripts can rely on the file existing):
  data/interim/opinion_main.parquet
  data/interim/opinion_limited.parquet
  data/interim/opinion_untimed.parquet
  data/interim/context_only.parquet
  data/interim/audit_only.parquet
  data/interim/quarantine.parquet

Audit trail (§12's Audit table, one row per input record):
  data/audits/eligibility_audit.parquet
  data/audits/eligibility_audit.csv

Usage:
    python src/preprocessing/apply_eligibility.py
    python src/preprocessing/apply_eligibility.py --input-dir data/raw_harmonized --output-dir data/interim
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")  # notes/prints below carry Persian §-references

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "ingestion"))

from config.raw_schema_columns_v05 import RAW_SCHEMA_V05_COLUMNS  # noqa: E402

import project_calendar  # noqa: E402 - single source of truth for project_week/in_window (raw_schema_v05.md §10)

RULE_VERSION = "eligibility_rules_v03"
DECIDED_AT = datetime.now(timezone.utc).isoformat()

VALID_PLATFORMS = {"x", "reddit", "youtube"}

# raw_schema_v05.md §8
CONTENT_TYPES_KNOWN = {
    "original_post", "comment", "reply", "quote", "repost",
    "video_context", "deleted_or_unavailable", "unknown",
}

DATASET_TARGETS = [
    "opinion_main", "opinion_limited", "opinion_untimed",
    "context_only", "audit_only", "quarantine",
]

_EMPTY_TEXT_MARKERS = {"", "[deleted]", "[removed]", "nan", "none", "null"}
_SYNTHETIC_MARKERS = ("lorem ipsum", "test data", "sample text", "synthetic data", "placeholder text")
_URL_ONLY_RE = re.compile(r"^(https?://\S+\s*)+$", re.IGNORECASE)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _norm_str(x):
    """lower/strip a string value, leave non-strings (incl. NaN) untouched"""
    return x.strip().lower() if isinstance(x, str) else x


def _present(x) -> bool:
    """True if x is a non-null, non-blank value.

    Must handle pd.NA the same as None/NaN/NaT: _load_harmonized() fills any
    column a platform's harmonized parquet doesn't have with pd.NA (raw_schema_v05
    columns are unioned across platforms), so every downstream caller of
    _present() sees pd.NA for those columns on every row of that platform.
    A bare `pd.isna(x)` is used for the scalar case, but pd.isna() on a
    list/tuple/set/dict returns an elementwise array (or, for dict, doesn't
    apply cleanly at all) rather than a single bool, which raises ValueError
    if truthed directly — so collections are special-cased on length first.
    """
    if isinstance(x, (list, tuple, set, dict)):
        return len(x) > 0
    if isinstance(x, str):
        return x.strip() != ""
    try:
        is_na = pd.isna(x)
    except (TypeError, ValueError):
        return True
    if isinstance(is_na, bool):
        return not is_na
    # some exotic scalar made pd.isna return a non-bool (e.g. an array-like)
    # instead of erroring outright -- treat as present rather than crash.
    return True


def _is_empty_text(x) -> bool:
    if not _present(x):
        return True
    return str(x).strip().lower() in _EMPTY_TEXT_MARKERS


def _looks_synthetic(text) -> bool:
    if not _present(text):
        return False
    t = str(text).lower()
    return any(marker in t for marker in _SYNTHETIC_MARKERS)


def _looks_spam(text) -> bool:
    t = str(text).strip() if _present(text) else ""
    if not t:
        return False
    return bool(_URL_ONLY_RE.match(t))


def _to_id_set(value) -> set[str]:
    if not _present(value):
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).strip() for v in value if str(v).strip()}
    parts = re.split(r"[;,]\s*", str(value).strip())
    return {p for p in (p.strip() for p in parts) if p}


def _join_ids(ids: set[str]) -> str | None:
    return ";".join(sorted(ids)) if ids else None


def _finalize(df: pd.DataFrame, dataset_target: str, primary_reason: str | None,
              secondary: str = "", notes: str = "", eligible: bool | None = None) -> pd.DataFrame:
    """Stamp a slice of records with the final §12 audit-decision columns."""
    out = df.copy()
    if eligible is None:
        eligible = dataset_target in ("opinion_main", "opinion_limited", "opinion_untimed")
    out["eligible"] = eligible
    out["dataset_target"] = dataset_target
    out["primary_exclusion_reason"] = primary_reason
    out["secondary_exclusion_reasons"] = secondary if secondary else None
    out["notes"] = notes
    out["rule_version"] = RULE_VERSION
    out["decided_at_utc"] = DECIDED_AT
    out["review_status"] = "automatic"
    return out


def _empty_like(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[0:0]


# --------------------------------------------------------------------------
# stage 1 — Raw validation (§2 step 1; §3 conditions 1 and 3)
# --------------------------------------------------------------------------

def stage_raw_validation(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["platform"] = df["platform"].map(_norm_str)

    platform_valid = df["platform"].isin(VALID_PLATFORMS)
    has_id = df["platform_content_id"].map(_present) | df["record_uid"].map(_present)

    bad_platform = df[~platform_valid]
    missing_id = df[platform_valid & ~has_id]
    survivors = df[platform_valid & has_id].copy()

    decided_parts = []
    if len(bad_platform):
        decided_parts.append(_finalize(
            bad_platform, "quarantine", "other_documented",
            notes="platform مقدار نامعتبر یا خالی دارد؛ باید یکی از x/reddit/youtube باشد",
        ))
    if len(missing_id):
        decided_parts.append(_finalize(
            missing_id, "quarantine", "missing_content_id",
            notes="نه platform_content_id و نه record_uid موجود است",
        ))
    decided = pd.concat(decided_parts, ignore_index=True, sort=False) if decided_parts else _empty_like(df)

    survivors["_surrogate_id_only"] = (
        ~survivors["platform_content_id"].map(_present) & survivors["record_uid"].map(_present)
    )
    return survivors, decided


# --------------------------------------------------------------------------
# stage 2 — Exact-ID deduplication (§2 step 2; §8 dedup key)
# --------------------------------------------------------------------------

def stage_dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    has_platform_id = df["platform_content_id"].map(_present)
    df["_dedup_key"] = df["platform"].astype(str) + "::" + (
        df["platform_content_id"].where(has_platform_id, "uid::" + df["record_uid"].astype(str)).astype(str)
    )
    df["_collected_sort"] = pd.to_datetime(df["collected_at_utc"], errors="coerce", utc=True)

    df = df.sort_values(
        ["_dedup_key", "_collected_sort", "original_row_number"],
        na_position="last", kind="stable",
    )
    is_dup = df.duplicated(subset="_dedup_key", keep="first")
    canonical = df[~is_dup].copy()
    dupes = df[is_dup].copy()

    if len(dupes):
        dup_id_map: dict[str, set[str]] = {}
        for key, val in zip(dupes["_dedup_key"], dupes["matched_query_ids"]):
            dup_id_map.setdefault(key, set()).update(_to_id_set(val))

        def _apply_merge(row):
            extra = dup_id_map.get(row["_dedup_key"])
            if not extra:
                return row["matched_query_ids"]
            return _join_ids(_to_id_set(row["matched_query_ids"]) | extra)

        canonical["matched_query_ids"] = canonical.apply(_apply_merge, axis=1)

    decided = _finalize(
        dupes, "quarantine", "duplicate_exact_id",
        notes="کلید platform+platform_content_id (یا record_uid) تکراری بود؛ "
              "قدیمی‌ترین رکورد (بر اساس collected_at_utc) نگه داشته شد و "
              "matched_query_ids آن با رکوردهای حذف‌شده ادغام شد (§۸)",
    ) if len(dupes) else _empty_like(df)

    survivors = canonical.drop(columns=["_dedup_key", "_collected_sort"], errors="ignore")
    return survivors, decided


# --------------------------------------------------------------------------
# stage 3 — Date rule (§2 step 3; §3 condition 2; §6 week definition)
# --------------------------------------------------------------------------

def stage_date_rule(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    # created_at_utc is already parsed to a tz-aware datetime64[ns, UTC] column
    # (with NaT for unparseable values) by _load_harmonized() — parsing once,
    # up front, for every row (not just survivors reaching this stage) keeps
    # the column a single consistent dtype across every dataset_target output,
    # including rows that exit earlier (raw_validation/dedup -> quarantine).
    ts = df["created_at_utc"]

    origin_unknown = df.get("timestamp_origin", pd.Series(index=df.index, dtype=object)).map(_norm_str).eq("unknown")
    missing_timestamp = ts.isna() | origin_unknown.fillna(False)
    df["_missing_timestamp"] = missing_timestamp

    weeks = ts.map(lambda t: project_calendar.project_week(t.to_pydatetime()) if pd.notna(t) else ("OUT", False, False))
    df["project_week"] = [w[0] for w in weeks]
    df["in_window"] = [w[1] for w in weeks]
    df["is_partial_week"] = [w[2] for w in weeks]

    out_of_window = ~missing_timestamp & ~df["in_window"]
    decided = _finalize(
        df[out_of_window], "quarantine", "out_of_window",
        notes="created_at_utc خارج از بازه پروژه (2026-02-28T00:00:00Z .. 2026-07-22T23:59:59Z)",
    ) if out_of_window.any() else _empty_like(df)

    survivors = df[~out_of_window].copy()
    return survivors, decided


# --------------------------------------------------------------------------
# stage 4 — Text availability (§2 step 4; §3 condition 4; §4 content-type table)
# --------------------------------------------------------------------------

# raw_schema_v05.md §4 / §8 content-type table: platform+content_type combos
# that are legitimately textless by design. Single source of truth for both
# stage_text_availability (via _needs_independent_text, below) and
# stage_analysis_role (via _textless_role, in stage 7) -- previously each
# stage re-encoded this fact independently.
#
# Keyed by (platform, content_type); "*" wildcards platform. Each entry is
# the Analysis-role disposition (dataset_target, primary_exclusion_reason)
# the combo resolves to, plus `requires_empty_text`:
#   False -> always textless by design, regardless of whether text happens
#            to be present (video_context, repost)
#   True  -> only textless-by-design when the text actually turns out empty
#            (a reddit original_post can still carry a selftext body)
TEXTLESS_BY_DESIGN: dict[tuple[str, str], dict] = {
    ("*", "video_context"): {"target": "context_only", "reason": None, "requires_empty_text": False},
    ("*", "repost"): {"target": "audit_only", "reason": "repost_only", "requires_empty_text": False},
    ("reddit", "original_post"): {"target": "context_only", "reason": None, "requires_empty_text": True},
}


def _textless_rule(platform, content_type) -> dict | None:
    return TEXTLESS_BY_DESIGN.get((platform, content_type)) or TEXTLESS_BY_DESIGN.get(("*", content_type))


def _needs_independent_text(platform, content_type) -> bool:
    """content_type/platform combos that are legitimately textless by design
    (§4) skip the empty-text gate here and get resolved to context_only/
    audit_only in the Analysis-role stage instead."""
    return _textless_rule(platform, content_type) is None


def _textless_role(platform, content_type, text_raw) -> tuple[str, str | None] | None:
    """Analysis-role disposition (§4) for a platform/content_type combo that's
    legitimately textless by design, or None if this row doesn't qualify
    (either the combo requires text, or it's an empty-text-gated combo whose
    text isn't actually empty on this row)."""
    rule = _textless_rule(platform, content_type)
    if rule is None:
        return None
    if rule["requires_empty_text"] and not _is_empty_text(text_raw):
        return None
    return rule["target"], rule["reason"]


def stage_text_availability(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["content_type"] = df["content_type"].map(_norm_str)
    status = df.get("content_status", pd.Series(index=df.index, dtype=object)).map(_norm_str)

    deleted_mask = df["content_type"].eq("deleted_or_unavailable") | status.isin(["deleted", "removed"])
    decided_deleted = _finalize(
        df[deleted_mask], "audit_only", "deleted_or_removed",
        notes="content_type=deleted_or_unavailable یا content_status حذف/removed (§۴)",
    ) if deleted_mask.any() else _empty_like(df)

    remaining = df[~deleted_mask].copy()
    unknown_type = ~remaining["content_type"].isin(CONTENT_TYPES_KNOWN)
    decided_unknown = _finalize(
        remaining[unknown_type], "quarantine", "invalid_content_type",
        notes="content_type خارج از مقادیر مجاز raw_schema_v05.md §۸",
    ) if unknown_type.any() else _empty_like(remaining)
    remaining = remaining[~unknown_type].copy()

    if len(remaining):
        needs_text = remaining.apply(
            lambda r: _needs_independent_text(r["platform"], r["content_type"]), axis=1,
        )
    else:
        needs_text = pd.Series(dtype=bool)
    empty_text = remaining["text_raw"].map(_is_empty_text)
    fail_text = needs_text & empty_text

    decided_empty = _finalize(
        remaining[fail_text], "quarantine", "empty_text",
        notes="متن خام موجود یا قابل خواندن نیست",
    ) if fail_text.any() else _empty_like(remaining)

    survivors = remaining[~fail_text].copy()
    decided = pd.concat(
        [c for c in (decided_deleted, decided_unknown, decided_empty) if len(c)],
        ignore_index=True, sort=False,
    ) if any(len(c) for c in (decided_deleted, decided_unknown, decided_empty)) else _empty_like(df)
    return survivors, decided


# --------------------------------------------------------------------------
# stage 5 — Provenance rule (§2 step 5; §3 paragraph on provenance_quality)
# --------------------------------------------------------------------------

def _assess_provenance(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Prefer the harmonization layer's own provenance_quality (raw_schema_v05
    §4.1, set by the Provenance-reconstruction evidence chain in
    legacy_data_intake_and_harmonization_plan_v1.md §6-§7) when present.
    Only fall back to a local has-run/has-file heuristic when it wasn't
    populated upstream.

    Vectorized over the whole frame (np.select instead of a per-row
    .apply()); the condition order below is the exact if/elif priority of
    the original scalar version -- np.select keeps the first matching
    condition per row, so a later condition being incidentally true for an
    already-matched row (e.g. a `complete`-upstream row that also happens
    to lack collection_run_id) never overrides the earlier match."""
    raw_upstream = df.get("provenance_quality", pd.Series(pd.NA, index=df.index))
    # guard with _present() first: comparing a bare pd.NA/NaT (what a platform
    # missing this column gets from _load_harmonized()) with `==` yields pd.NA,
    # not True/False -- so absent/blank upstream values are normalized to ""
    # (a sentinel that can't match a real provenance_quality value) instead
    # of being compared directly.
    upstream_present = raw_upstream.map(_present)
    upstream = raw_upstream.map(_norm_str).where(upstream_present, "")

    has_run = df.get("collection_run_id", pd.Series(pd.NA, index=df.index)).map(_present)
    has_file = (
        df.get("original_file_name", pd.Series(pd.NA, index=df.index)).map(_present)
        | df.get("original_file_sha256", pd.Series(pd.NA, index=df.index)).map(_present)
    )
    has_query = df.get("query_id", pd.Series(pd.NA, index=df.index)).map(_present)
    has_source = df.get("source_id", pd.Series(pd.NA, index=df.index)).map(_present)

    not_auditable = ~has_run & ~has_file  # not auditable at all -> invalid_provenance
    complete_links = has_run & has_query & has_source

    conditions = [
        upstream.eq("complete"),
        upstream.isin(["partial", "reconstructed"]),
        not_auditable,
        complete_links,
    ]
    quality = pd.Series(
        np.select(conditions, ["complete", "partial", "unknown", "complete"], default="partial"),
        index=df.index,
    )
    invalid = pd.Series(
        np.select(conditions, [False, False, True, False], default=False),
        index=df.index,
    ).astype(bool)
    return quality, invalid


def stage_provenance(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    if len(df):
        df["provenance_quality"], df["_provenance_invalid"] = _assess_provenance(df)
    else:
        df["_provenance_invalid"] = pd.Series(dtype=bool)

    invalid = df["_provenance_invalid"].fillna(False).astype(bool)
    decided = _finalize(
        df[invalid], "quarantine", "invalid_provenance",
        notes="نه collection_run_id و نه original_file_name/original_file_sha256 موجود است؛ "
              "منشأ فایل و Platform قابل ممیزی نیست (§۳ شرط ۵)",
    ) if invalid.any() else _empty_like(df)

    survivors = df[~invalid].drop(columns=["_provenance_invalid"], errors="ignore")
    return survivors, decided


# --------------------------------------------------------------------------
# stage 6 — Topic relevance (§2 step 6) — structural screening only; see the
# "Scope note on Topic relevance" in the module docstring.
# --------------------------------------------------------------------------

def stage_topic_relevance(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    synthetic_mask = df["text_raw"].map(_looks_synthetic)
    decided_synth = _finalize(
        df[synthetic_mask], "quarantine", "synthetic_or_test",
        notes="متن حاوی نشانگر داده آزمایشی/Placeholder است (§۵)",
    ) if synthetic_mask.any() else _empty_like(df)

    remaining = df[~synthetic_mask].copy()
    no_query_link = ~remaining["query_id"].map(_present) & ~remaining["matched_query_ids"].map(_present)
    spam_like = remaining["text_raw"].map(_looks_spam)
    out_of_scope_mask = no_query_link & spam_like

    decided_oos = _finalize(
        remaining[out_of_scope_mask], "quarantine", "out_of_scope",
        notes="بدون اتصال به Query پروژه و متن فقط شامل URL/الگوی Spam (§۵)",
    ) if out_of_scope_mask.any() else _empty_like(remaining)

    survivors = remaining[~out_of_scope_mask].copy()
    parts = [c for c in (decided_synth, decided_oos) if len(c)]
    decided = pd.concat(parts, ignore_index=True, sort=False) if parts else _empty_like(df)
    return survivors, decided


# --------------------------------------------------------------------------
# stage 7 — Analysis-role rule (§2 step 7; §3.2 role table; §4 content-type table)
# --------------------------------------------------------------------------

def _assess_analysis_role(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized equivalent of the row-wise Analysis-role assignment (§3.2/
    §4): np.select mirrors the original if/elif priority exactly (textless-
    by-design combos first, then the defensive invalid-content-type gate,
    then the opinion-role flags), so a later condition being incidentally
    true for an already-matched row never overrides the earlier match.

    TEXTLESS_BY_DESIGN currently has no (platform, content_type) combos that
    overlap in content_type, so the three textless masks below are already
    mutually exclusive per row; np.select's left-to-right priority is kept
    anyway so this stays correct if that ever changes."""
    ct, platform, text_raw = df["content_type"], df["platform"], df["text_raw"]

    is_video_context = ct.eq("video_context")
    is_repost = ct.eq("repost")
    is_reddit_op_empty = platform.eq("reddit") & ct.eq("original_post") & text_raw.map(_is_empty_text)
    is_textless = is_video_context | is_repost | is_reddit_op_empty
    is_invalid_type = ~is_textless & ~ct.isin(CONTENT_TYPES_KNOWN)  # defensive; should already be filtered in stage 4
    is_opinion_role = ~is_textless & ~is_invalid_type

    surrogate_flag = df.get("_surrogate_id_only", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    partial_prov_flag = df.get("provenance_quality", pd.Series(pd.NA, index=df.index)).eq("partial")
    missing_ts_flag = df.get("_missing_timestamp", pd.Series(False, index=df.index)).fillna(False).astype(bool)

    conditions = [is_video_context, is_repost, is_reddit_op_empty, is_invalid_type, missing_ts_flag, partial_prov_flag]
    target = pd.Series(
        np.select(
            conditions,
            ["context_only", "audit_only", "context_only", "quarantine", "opinion_untimed", "opinion_limited"],
            default="opinion_main",
        ),
        index=df.index,
    )
    reason = pd.Series(
        np.select([is_repost, is_invalid_type], ["repost_only", "invalid_content_type"], default=None),
        index=df.index,
    )

    # flags/secondary (§3.2) only apply to rows that reach the opinion-role
    # branch -- textless/invalid rows carry secondary="" (matching the
    # scalar version's hardcoded "" for those early returns), joined in the
    # same surrogate/provenance/timestamp order as the original.
    secondary = pd.Series("", index=df.index, dtype=object)
    for flag, name in (
        (surrogate_flag, "surrogate_id_only"),
        (partial_prov_flag, "limited_provenance"),
        (missing_ts_flag, "missing_timestamp"),
    ):
        appended = np.where(secondary.eq(""), name, secondary.astype(str) + ";" + name)
        secondary = pd.Series(np.where(flag, appended, secondary), index=df.index, dtype=object)
    secondary = pd.Series(np.where(is_opinion_role, secondary, ""), index=df.index, dtype=object)

    return pd.DataFrame({"_target": target, "_reason": reason, "_secondary": secondary}, index=df.index)


def stage_analysis_role(df: pd.DataFrame) -> pd.DataFrame:
    if not len(df):
        return _finalize(df, "quarantine", None)

    roles = _assess_analysis_role(df)

    chunks = []
    for target in roles["_target"].unique():
        mask = roles["_target"] == target
        chunk = _finalize(
            df[mask], target,
            primary_reason=None,  # set per-row below (constant for repost/invalid; None for opinion/context_only)
            notes="",
        )
        chunk["primary_exclusion_reason"] = roles.loc[mask, "_reason"].values
        chunk["secondary_exclusion_reasons"] = roles.loc[mask, "_secondary"].replace("", None).values
        chunks.append(chunk)

    return pd.concat(chunks, ignore_index=True, sort=False)


# --------------------------------------------------------------------------
# loading + orchestration
# --------------------------------------------------------------------------

def _load_harmonized(input_dir: Path) -> pd.DataFrame:
    files = sorted(input_dir.glob("*/*.parquet"))
    if not files:
        raise SystemExit(
            f"no *.parquet files found under {input_dir}/{{platform}}/ — "
            "run the raw_harmonized harmonization step first (docs/raw_schema_v05.md)"
        )

    frames = []
    for f in files:
        try:
            part = pd.read_parquet(f)
        except Exception as exc:  # noqa: BLE001 - one bad file shouldn't abort the whole run
            print(f"WARNING: skipping unreadable file {f}: {exc}")
            continue
        for col in RAW_SCHEMA_V05_COLUMNS:
            if col not in part.columns:
                part[col] = pd.NA
        part["source_file"] = str(f.relative_to(input_dir))
        frames.append(part)

    if not frames:
        raise SystemExit(f"found {len(files)} file(s) under {input_dir} but none were readable")

    out = pd.concat(frames, ignore_index=True, sort=False)
    # Parse once, for every row, right after load — keeps created_at_utc a
    # single consistent datetime64[ns, UTC] dtype (NaT where unparseable)
    # across every later dataset_target output, including rows that exit
    # before stage_date_rule ever runs on them (e.g. raw_validation/dedup
    # exits into quarantine).
    out["created_at_utc"] = pd.to_datetime(out["created_at_utc"], errors="coerce", utc=True)
    return out


def _write_outputs(all_decided: pd.DataFrame, output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    internal_prefixes = ("_",)
    for target in DATASET_TARGETS:
        sub = all_decided[all_decided["dataset_target"] == target]
        counts[target] = len(sub)
        keep_cols = [c for c in sub.columns if not c.startswith(internal_prefixes)]
        out_path = output_dir / f"{target}.parquet"
        sub[keep_cols].to_parquet(out_path, index=False)
        print(f"  {target:16s} {len(sub):8d} rows -> {out_path}")
    return counts


def _write_audit(all_decided: pd.DataFrame, audits_dir: Path) -> None:
    audits_dir.mkdir(parents=True, exist_ok=True)
    audit_cols = [
        "platform", "platform_content_id", "record_uid", "content_type",
        "project_week", "is_partial_week", "provenance_quality",
        "eligible", "dataset_target", "primary_exclusion_reason",
        "secondary_exclusion_reasons", "rule_version", "decided_at_utc",
        "review_status", "notes", "source_file",
    ]
    audit_cols = [c for c in audit_cols if c in all_decided.columns]
    audit_df = all_decided[audit_cols]
    audit_df.to_parquet(audits_dir / "eligibility_audit.parquet", index=False)
    audit_df.to_csv(audits_dir / "eligibility_audit.csv", index=False, encoding="utf-8-sig")
    print(f"  audit trail ({len(audit_df)} rows) -> {audits_dir / 'eligibility_audit.parquet'}")
    print(f"  audit trail ({len(audit_df)} rows) -> {audits_dir / 'eligibility_audit.csv'}")


def _print_reconciliation(harmonized_rows: int, all_decided: pd.DataFrame) -> bool:
    """legacy_data_intake_and_harmonization_plan_v1.md §9, second equation."""
    counts = all_decided["dataset_target"].value_counts().to_dict()
    opinion_main = counts.get("opinion_main", 0)
    opinion_limited = counts.get("opinion_limited", 0)
    opinion_untimed = counts.get("opinion_untimed", 0)
    context_only = counts.get("context_only", 0)
    audit_only = counts.get("audit_only", 0)

    quarantine_df = all_decided[all_decided["dataset_target"] == "quarantine"]
    duplicate_exact = int((quarantine_df["primary_exclusion_reason"] == "duplicate_exact_id").sum())
    excluded = len(quarantine_df) - duplicate_exact

    computed_sum = (
        opinion_main + opinion_limited + opinion_untimed
        + context_only + audit_only + excluded + duplicate_exact
    )
    ok = computed_sum == harmonized_rows and len(all_decided) == harmonized_rows

    print()
    print("=" * 72)
    print("Record-count reconciliation (legacy_data_intake_and_harmonization_plan_v1.md §9)")
    print("=" * 72)
    print(f"harmonized_rows      = {harmonized_rows}")
    print("=")
    print(f"  opinion_main       {opinion_main:>8}")
    print(f"+ opinion_limited    {opinion_limited:>8}")
    print(f"+ opinion_untimed    {opinion_untimed:>8}")
    print(f"+ context_only       {context_only:>8}")
    print(f"+ audit_only         {audit_only:>8}")
    print(f"+ excluded           {excluded:>8}   (quarantine, non-duplicate reasons)")
    print(f"+ duplicate_exact    {duplicate_exact:>8}   (quarantine, primary_exclusion_reason=duplicate_exact_id)")
    print("-" * 44)
    print(f"  sum                {computed_sum:>8}")
    print()
    print(f"Equation holds: {ok}  [{'PASS - nothing lost' if ok else 'FAIL - counts do not reconcile'}]")
    print("=" * 72)

    print()
    print("Per-platform breakdown:")
    pivot = all_decided.pivot_table(index="platform", columns="dataset_target", aggfunc="size", fill_value=0)
    for target in DATASET_TARGETS:
        if target not in pivot.columns:
            pivot[target] = 0
    pivot = pivot[DATASET_TARGETS]
    pivot["total"] = pivot.sum(axis=1)
    print(pivot.to_string())
    print()

    return ok


def run(input_dir: Path | str | None = None, output_dir: Path | str | None = None,
        audits_dir: Path | str | None = None) -> bool:
    input_dir = Path(input_dir) if input_dir else ROOT / "data" / "raw_harmonized"
    output_dir = Path(output_dir) if output_dir else ROOT / "data" / "interim"
    audits_dir = Path(audits_dir) if audits_dir else ROOT / "data" / "audits"

    df = _load_harmonized(input_dir)
    harmonized_rows = len(df)
    print(f"loaded {harmonized_rows} rows from {input_dir}")

    active = df
    decided_chunks: list[pd.DataFrame] = []
    for stage_fn, label in [
        (stage_raw_validation, "raw_validation"),
        (stage_dedup, "exact_id_dedup"),
        (stage_date_rule, "date_rule"),
        (stage_text_availability, "text_availability"),
        (stage_provenance, "provenance_rule"),
        (stage_topic_relevance, "topic_relevance"),
    ]:
        active, decided = stage_fn(active)
        if len(decided):
            decided_chunks.append(decided)
        print(f"  stage {label:20s} exited={len(decided):6d}  remaining={len(active):6d}")

    final_decided = stage_analysis_role(active)
    decided_chunks.append(final_decided)

    all_decided = pd.concat(decided_chunks, ignore_index=True, sort=False)
    if len(all_decided) != harmonized_rows:
        raise SystemExit(
            f"internal error: {len(all_decided)} decided rows != {harmonized_rows} input rows "
            "(a stage dropped or duplicated records instead of routing them)"
        )

    print()
    print("Writing dataset outputs:")
    _write_outputs(all_decided, output_dir)
    print()
    print("Writing audit trail:")
    _write_audit(all_decided, audits_dir)

    return _print_reconciliation(harmonized_rows, all_decided)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=None, help="default: data/raw_harmonized")
    parser.add_argument("--output-dir", default=None, help="default: data/interim")
    parser.add_argument("--audits-dir", default=None, help="default: data/audits")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    ok = run(input_dir=args.input_dir, output_dir=args.output_dir, audits_dir=args.audits_dir)
    sys.exit(0 if ok else 1)
