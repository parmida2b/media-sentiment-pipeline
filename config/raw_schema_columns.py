"""
raw_schema_columns.py — canonical column list for the Collector export
contract (docs/raw_schema_v03.md)

Plain, framework-free constant (no imports beyond stdlib) so Reddit's and
X's collectors can import/copy this exact list too - docs/raw_schema_v03.md
§0's whole point is that all three platforms' export CSVs share identical
column names/order. If a platform doesn't have a value for a column, the
column is still present in the row, just empty (never omit a column).

Order follows the section order of raw_schema_v03.md (§2 through §8).
"""

RAW_SCHEMA_COLUMNS: list[str] = [
    # §2 Core - identity and time (all Required)
    "platform",
    "platform_content_id",
    "content_type",
    "created_at_utc",
    "collected_at_utc",
    "text_raw",
    "author_hash",
    "project_week",
    "in_window",
    "is_partial_week",
    "query_id",
    "collection_run_id",

    # §3 Source and Provenance
    "source_id",
    "source_container",
    "source_container_id",
    "source_parent_id",
    "source_parent_title",
    "parent_id",
    "query_version",
    "discovery_route",
    "matched_query_ids",
    "collector_version",
    "permalink_hash",
    "source_total_available",
    "sampling_method",
    "sampling_applied",
    "items_kept",
    "random_seed",

    # §4 Engagement
    "engagement_score",
    "engagement_replies",
    "engagement_shares",
    "engagement_quotes",
    "engagement_views",
    "engagement_collected_at_utc",

    # §5 Author
    "author_is_verified",
    "author_follower_count",
    "author_account_age_days",
    "author_is_submitter",
    "automation_risk_score",

    # §6 Language and Status
    "language_reported",
    "language_detected",
    "language_confidence",
    "content_status",

    # §7 Geography
    "geo_method",
    "country_or_region",
    "geo_confidence",
    "geo_granularity",
    "geo_limitations",
]
