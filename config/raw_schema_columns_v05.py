"""
raw_schema_columns_v05.py — canonical column list for the raw_harmonized
export contract (docs/raw_schema_v05.md)

Sibling of raw_schema_columns.py (the v03 list still used by data/raw/...
CSV export) - kept as its own plain, framework-free constant for the same
reason raw_schema_columns.py gives: docs/raw_schema_v05.md §1 requires X,
Reddit and YouTube's raw_harmonized output to share identical column
names/order, so every platform's harmonization step can import this exact
list rather than each re-typing it. If a platform doesn't have a value for
a column, the column is still present (as null), never omitted -
raw_schema_v05.md §1.1 point 5.

Deliberately excludes columns raw_schema_v05.md itself excludes from the
raw layer vs. v03's raw_schema_columns.py - see
docs/schema_migration_v03_to_v05_diff.md §3.2:
  - automation_risk_score: v05 §11 lists it as a *derived* field, built in
    the processed layer, not raw.
  - author_follower_count, author_is_submitter, geo_granularity,
    geo_limitations: not present in any raw_schema_v05.md table (diff
    doc flags this as possibly an editorial omission, unconfirmed with the
    document's author - not re-added here since this file mirrors the
    document as written).
  - source_total_available, sampling_method, sampling_applied, items_kept,
    random_seed: moved to the Collection Manifest (v05 §12), no longer
    per-record.

Order follows the section order of raw_schema_v05.md (§3 through §7, plus
§4.1's historical-data audit block in its documented position).
"""

RAW_SCHEMA_V05_COLUMNS: list[str] = [
    # §3 Core - identity and time
    "platform",
    "platform_content_id",
    "content_type",
    "created_at_utc",
    "collected_at_utc",
    "text_raw",
    "collection_run_id",
    "collector_version",
    "schema_version",
    "project_week",
    "in_window",
    "is_partial_week",

    # §4 Provenance and parent structure
    "query_id",
    "matched_query_ids",
    "query_version",
    "source_id",
    "source_registry_version",
    "discovery_route",
    "source_container",
    "source_container_id",
    "source_parent_id",
    "source_parent_title",
    "parent_id",
    "permalink_hash",

    # §4.1 Historical-data audit fields
    "original_file_name",
    "original_file_sha256",
    "original_row_number",
    "source_schema_version",
    "source_query_registry_version",
    "record_uid",
    "id_origin",
    "timestamp_origin",
    "provenance_quality",
    "field_origin",
    "missing_reason",

    # §5 Author and privacy
    "author_hash",
    "author_id_status",
    "author_type",
    "author_is_verified",
    "author_account_age_days",

    # §6 Engagement snapshot
    "engagement_score",
    "engagement_replies",
    "engagement_shares",
    "engagement_quotes",
    "engagement_views",
    "engagement_collected_at_utc",

    # §7 Language, status and location
    "language_reported",
    "language_detected",
    "language_confidence",
    "content_status",
    "geo_method",
    "country_or_region",
    "geo_confidence",
]
