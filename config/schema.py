"""
schema.py — unified data format definition for the whole team
---------------------------------------------------------------
This file is the single source of truth for the data format.
Idea by Yasaman; implemented and maintained by Parmida — everyone else just imports from it.
If a field needs to change, coordinate with the team first.

Version: v3 - Day 4 (see docs/decision_log.md for the v2/v3 additive changes)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class AuthorMetadata:
    author_display_name: Optional[str] = None
    author_channel_id: Optional[str] = None   # or user_id, depending on the platform
    like_count: int = 0
    follower_count: Optional[int] = None      # if the platform provides it (e.g. Reddit/Telegram)
    account_age_days: Optional[int] = None    # for bot filtering later (Ali/Reyhaneh)

    # v2 (Day 3+, Parmida) - see docs/decision_log.md. Salted hash of a stable
    # author identifier, for collectors that must not store raw usernames
    # (project brief section 10/43: no unnecessary PII). Prefer this over
    # author_display_name in new collectors; the latter stays for backward
    # compatibility with data already collected under v1.
    author_hash: Optional[str] = None

    # v4 (Day 5, Parmida) - docs/raw_schema_v05.md §5 defines this alongside
    # author_hash but it was never added to Record when the v2 author_hash
    # field went in. One of: available/deleted/unavailable/not_provided.
    # Lets a collector record *why* author_hash is None (e.g. Reddit's
    # "[deleted]"/"[removed]" authors have no stable id to hash) instead of
    # that case being indistinguishable from "collector forgot to hash it".
    author_id_status: Optional[str] = None


@dataclass
class Record:
    """A standard record - the output of every extraction module must match this shape."""
    text: str
    date: str                      # ISO 8601, e.g. "2026-03-05T12:00:00Z"
    source: str                    # "youtube" | "reddit" | "twitter" | ...
    platform: str                  # usually the same as source, kept separate for flexibility
    author_metadata: AuthorMetadata

    # Optional fields shared across sources
    language: Optional[str] = None         # "fa" | "en" | "ar" | ...
    post_id: Optional[str] = None          # video_id / submission_id / message_id
    post_title: Optional[str] = None
    reply_count: int = 0
    is_reply: bool = False

    # v2 (Day 3+, Parmida) - additive fields to close gaps against the project
    # brief's raw-data contract (section 10), Collection Manifest (11),
    # automation risk (16), and geo (17). All optional with defaults so
    # existing v1 producers/consumers of Record are unaffected. See
    # docs/decision_log.md for why these were added and coordinate with
    # the team before renaming/removing anything above this line.
    content_id: Optional[str] = None       # platform's own id for this exact piece of content (e.g. comment id) - required for dedup/uniqueness checks
    parent_id: Optional[str] = None        # content_id of the parent, when is_reply is True
    collected_at_utc: Optional[str] = None # when THIS pipeline fetched the record, distinct from `date` (when it was posted)
    collection_run_id: Optional[str] = None
    query_id: Optional[str] = None         # which query/channel/region combo discovered this record

    # Per-commenter geo tag from author_geo.py, using the project brief's
    # controlled vocabulary: geo_method is one of
    # geotag/profile/timezone/text_place/source_community/language_weak,
    # geo_confidence is categorical (high/medium/low, not a score), and
    # geo_granularity is one of country/region/city/unknown.
    geo_method: Optional[str] = None
    geo_confidence: Optional[str] = None
    geo_granularity: Optional[str] = None
    country_or_region: Optional[str] = None
    geo_limitations: Optional[str] = None

    # Heuristic risk score in [0, 1], not a bot verdict - see automation_risk.py.
    automation_risk_score: Optional[float] = None

    # v3 (Day 4+, Parmida) - additive fields to match docs/raw_schema_v03.md
    # (the team's raw-data export contract) and docs/source_registry_v3.md
    # (the allowed-sources list). See docs/decision_log.md for the full
    # rationale. All optional with defaults so existing producers/consumers
    # of Record are unaffected. Coordinate with the team before renaming/
    # removing anything above this line, same as the v2 block.
    content_type: Optional[str] = None        # "comment" | "reply" | ... - raw_schema_v03 §8
    matched_query_ids: Optional[str] = None    # ";"-joined query_ids that discovered this content's video (raw_schema_v03 §3)
    query_version: Optional[str] = None        # query_registry.yaml's registry_version at collection time
    discovery_route: Optional[str] = None      # "query_search" | "source_scope" | "hashtag"
    source_id: Optional[str] = None            # Source Registry ID (e.g. "YT-001"); empty if source isn't in the registry
    source_container: Optional[str] = None     # human-readable container, e.g. channel title
    source_container_id: Optional[str] = None  # platform ID of the container, e.g. channel_id
    permalink_hash: Optional[str] = None       # sha256 of the content's permalink - never store the raw URL
    source_total_available: Optional[int] = None  # platform-reported total items available before any cap, if given
    sampling_method: Optional[str] = None      # "none" | "random" | ... - raw_schema_v03 §3/§12.8
    sampling_applied: Optional[bool] = None
    items_kept: Optional[int] = None
    random_seed: Optional[str] = None          # only set when sampling_method == "random"
    language_confidence: Optional[float] = None
    project_week: Optional[str] = None         # "W01".."W21" or "OUT" - raw_schema_v03 §10
    in_window: Optional[bool] = None
    is_partial_week: Optional[bool] = None

    # v4 (Day 5, Parmida) - raw_schema_columns.py already lists content_status
    # (§6) as part of the shared export contract; Record never had a matching
    # field. One of: active/deleted/removed/unknown. "[deleted]"/"[removed]"
    # text is not valid opinion content (docs/legacy_data_intake_and_
    # harmonization_plan_v1.md §8, Reddit rules) - this lets downstream steps
    # filter on it explicitly instead of string-matching text_raw themselves.
    content_status: Optional[str] = None

    def to_json_line(self) -> str:
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)


def validate_record(d: Dict[str, Any]) -> bool:
    """Quick check before saving - prevents incomplete data from entering the pipeline."""
    required = ["text", "date", "source", "platform"]
    return all(k in d and d[k] not in (None, "") for k in required)


if __name__ == "__main__":
    # usage example
    r = Record(
        text="sample comment text",
        date="2026-03-05T12:00:00Z",
        source="youtube",
        platform="youtube",
        author_metadata=AuthorMetadata(author_display_name="test_user", like_count=3),
        language="fa",
        post_id="abc123",
    )
    print(r.to_json_line())
