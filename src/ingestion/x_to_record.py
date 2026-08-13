"""
x_to_record.py — converts already-collected X (Twitter) raw data into the
project's shared Record schema (config/schema.py), the same path YouTube's
and Reddit's collectors write into (see src/ingestion/reddit_to_record.py,
the pattern this script mirrors). (Parmida, Day 5)

Why this exists
----------------
src/ingestion/x_scraper.py (Hossein) already collects X posts end-to-end
(Selenium-driven, resumable, SQLite-backed) and its export_raw_csv() already
writes every collected row to {X_OUTPUT_ROOT or the local default}/exports/
x_raw.csv. That CSV is already very close to raw_schema_v03 shape - most of
parse_article()'s dict keys (platform, platform_content_id, content_type,
created_at_utc, engagement_score, geo_method, ...) already match
config/raw_schema_columns.py's RAW_SCHEMA_COLUMNS names 1:1, and both of its
timestamp fields are already emitted in the exact "...Z" format
config/schema.py's Record.date expects (x_scraper.py's iso_z()/utc_now()) -
so unlike Reddit's bridge (which had to fix a real "+00:00" vs "Z" format
mismatch), this script does no timestamp reformatting at all.

What never touched config/schema.py's Record before this script is a
config/raw_schema_columns.py-shaped export and the shared JSONL Record
format. This is that missing bridge: it reads x_raw.csv and produces the
same two artifacts YouTube's and Reddit's collectors produce:
    data/raw/x/x_comments_v1.jsonl   (Record.to_json_line() per row)
    data/raw/x/x_raw_export.csv      (config/raw_schema_columns.py shape)
so join_and_clean.py can pick X up the same way it already picks up
YouTube/Reddit (see the matching edit there). This resolves the warning box
at the top of docs/cross_platform_alignment_guide_fa.md ("X هنوز export
مطابق schema استاندارد نداره").

It does NOT re-collect anything, does NOT import Selenium, and does NOT
touch src/ingestion/x_scraper.py - purely a read-existing-CSV -> write-
Record step, safe to re-run. (It also does not import x_scraper.py itself:
that module pulls in selenium/webdriver_manager/IPython/colorama, connects
to a SQLite DB, and creates a persistent salt file, all at module import
time - none of which a pure CSV->Record conversion step needs. Its output-
root resolution logic (X_OUTPUT_ROOT env var -> config.yaml's
x.runtime.default_local_output_root, x_scraper.py lines ~145-167) is
replicated below instead of imported, same reasoning reddit_to_record.py
gives for not importing reddit_parent_post_collector.py.)

Deliberately NOT done in this pass (see docs/decision_log.md, dated entry
for this change):
  - automation_risk.score_batch() is NOT called here. x_raw.csv's
    automation_risk_score column is already always empty (parse_article()
    in x_scraper.py never computes it) and this script leaves it exactly
    that way - wiring Tier A scoring for X is a separate, team-reviewed
    decision, not something to add unilaterally in a schema-bridging pass.
  - geo_tagger's LLM relevance/perspective tagging ("Tier 0") is NOT called
    here either, for the same reason - x_raw.csv's geo_method/
    country_or_region/geo_confidence/geo_granularity/geo_limitations
    columns are already always empty (x_scraper.py's Tier-0 pass for X was
    never wired in) and are carried through empty, not fabricated.
  - config/config.yaml's `x:` collector-settings block (collector_version,
    query_version, runtime.output_root_env_var, etc.) is currently nested
    one level too deep, under `youtube:` (config.yaml lines ~110-153)
    instead of being its own top-level `x:` key - `platforms: [...]`
    already lists "x" as a sibling of "youtube", but the settings block
    wasn't hoisted to match, so config_loader.load_config().x resolves to
    {} today. This means x_scraper.py's own `if not X_CONFIG: raise
    ValueError(...)` check would currently fire too - a pre-existing
    config.yaml authoring bug, unrelated to this task and not something to
    silently fix here (config.yaml is shared, not owned by this change).
    _x_runtime_config() below falls back to the nested location so this
    script still resolves the real configured output root either way; see
    that function's docstring.

Judgment calls worth flagging (not fabrication, but inference from what
x_raw.csv actually contains - see decision_log.md):
  - Record.post_id is set to platform_content_id (the tweet's own id), not
    left None. x_raw.csv's source_parent_id/source_parent_title/parent_id
    columns are always empty - x_scraper.py has no parent/reply-chain
    resolution, every collected tweet is its own top-level item. Leaving
    post_id None instead would silently zero out user_features.py's
    "posts_participated" feature for every X user (it only counts records
    where post_id is truthy) rather than reflecting that each tweet really
    is a distinct item that author posted.
  - AuthorMetadata.author_id_status is NOT simply "available whenever
    author_hash is non-empty": x_raw.csv's author_hash column is NEVER
    empty (tweets_raw.author_hash is NOT NULL) because parse_article()
    hashes a synthetic 'unknown:{content_id}' fallback when no handle could
    be resolved from the rendered card, so every row's raw author_hash is
    populated even when nothing about the author was actually identified.
    This script instead reads x_raw.csv's author_hash_method column
    ('handle_fallback_v1' vs 'content_id_fallback_v1', parse_article's own
    record of which branch it took) to decide, and only carries the hash
    into Record when a handle was actually resolved - see
    author_hash_and_status() below.
  - "collector_version" in the exported CSV is taken directly from
    x_raw.csv's own collector_version column (x_scraper.py's
    PROJECT_CONFIG['collector_version'], e.g. "x-selenium-v4.5") rather
    than a version string for *this* bridge script. reddit_to_record.py did
    the opposite (its own COLLECTOR_VERSION constant) only because Reddit's
    underlying Selenium pipeline never tracked a collector_version per row
    at all; x_scraper.py already does, and that's the more faithful
    provenance value for raw_schema_v03's "which collector produced this
    row" intent.

No raw PII is carried into the Record or the CSV export (project brief
§10/43, same rule Reddit's bridge follows): x_raw.csv's author_username,
author_display_name, and tweet_url columns are never read into anything
that gets written out - author_username is read transiently, in-memory
only, to help decide author_id_status (see above), never stored;
permalink_hash (already a sha256 digest in x_raw.csv, not a raw URL) is the
only permalink-derived value carried through.

Usage:
    python src/ingestion/x_to_record.py
    python src/ingestion/x_to_record.py --limit 200   # smoke-test on a subset
    python src/ingestion/x_to_record.py --input-csv path/to/x_raw.csv   # test without running the real collector
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.schema import AuthorMetadata, Record  # noqa: E402
from config.raw_schema_columns import RAW_SCHEMA_COLUMNS  # noqa: E402
from config import config_loader  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "x"
JSONL_OUTPUT = OUTPUT_DIR / "x_comments_v1.jsonl"
CSV_OUTPUT = OUTPUT_DIR / "x_raw_export.csv"

CONFIG = config_loader.load_config()


# ---------------------------------------------------------------------------
# output-root resolution - mirrors x_scraper.py's own logic (its lines
# ~145-167) without importing that module (see module docstring)
# ---------------------------------------------------------------------------

def _x_runtime_config() -> dict:
    """CONFIG.x (config_loader's top-level "x:" key) is currently {} - see
    module docstring's "Deliberately NOT done" section on config.yaml's
    nesting bug. Falls back to the nested config.yaml location
    (youtube.x.runtime, where the block currently actually lives) so this
    still resolves real configured values instead of hardcoding X_scraper's
    defaults; works unchanged if config.yaml's nesting is fixed later."""
    return CONFIG.x or CONFIG.youtube.get("x", {})


def resolve_output_root() -> Path:
    """Same env-var-with-default resolution as x_scraper.py's DRIVE_DIR
    (lines ~145-166): the OUTPUT_ROOT_ENV_VAR (X_OUTPUT_ROOT) env var if
    set and non-empty, else config.yaml's default_local_output_root (or the
    Colab default when actually running in Colab). Deliberately does NOT
    call google.colab.drive.mount() itself the way x_scraper.py does -
    mounting Drive is a real side effect that belongs to the collector
    starting a session, not to a script that only reads an already-exported
    CSV; a find_spec() check is enough to pick the right *default path*."""
    runtime = _x_runtime_config().get("runtime", {})
    env_var = runtime.get("output_root_env_var", "X_OUTPUT_ROOT")

    in_colab = importlib.util.find_spec("google.colab") is not None
    if in_colab:
        default_root = runtime.get(
            "default_colab_output_root", "/content/drive/MyDrive/Twitter_Scraper_Data_v4"
        )
    else:
        default_root = runtime.get("default_local_output_root", "./Twitter_Scraper_Data_v4")

    configured = os.environ.get(env_var, default_root).strip() or default_root
    return Path(configured).expanduser()


DEFAULT_INPUT_CSV = resolve_output_root() / "exports" / "x_raw.csv"


# ---------------------------------------------------------------------------
# small helpers - x_raw.csv values are all strings (csv.DictReader), and
# pandas.read_sql_query()/to_csv() (x_scraper.py's export_raw_csv()) upcasts
# an INTEGER column to float64 - hence "12.0" not "12" - the moment ANY row
# in the whole table has a NULL in that column, which is true for most
# numeric columns here since x_scraper.py currently leaves most engagement/
# author-numeric fields empty. int(float(v)) below tolerates that shape
# either way instead of failing on it.
# ---------------------------------------------------------------------------

def parse_int(value: str | None) -> int | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_bool01(value: str | None) -> bool:
    return (value or "").strip() in ("1", "1.0", "True", "true")


def s_or_none(value: str | None) -> str | None:
    v = (value or "").strip()
    return v or None


def int_str(value: str | None) -> str:
    parsed = parse_int(value)
    return "" if parsed is None else str(parsed)


def author_hash_and_status(row: dict[str, str]) -> tuple[str | None, str]:
    """Returns (author_hash, author_id_status). See module docstring's
    "Judgment calls" section for why this can't just check "is author_hash
    present" (it always is, NOT NULL in x_scraper.py's DB) - it reads
    author_hash_method instead, with a fallback (checking author_username
    presence, read-only, never persisted) for exports that predate that
    column."""
    method = (row.get("author_hash_method") or "").strip()
    if not method:
        method = "handle_fallback_v1" if (row.get("author_username") or "").strip() else "content_id_fallback_v1"
    if method == "handle_fallback_v1":
        return row.get("author_hash") or None, "available"
    # Handle could not be resolved from the rendered card - x_raw.csv's
    # author_hash for this row is a content_id-keyed fallback, not a real
    # per-author pseudonym (see module docstring); don't carry it into
    # Record as if it identified anyone.
    return None, "unavailable"


# ---------------------------------------------------------------------------
# load already-collected x_raw.csv
# ---------------------------------------------------------------------------

def load_rows(path: Path, limit: int | None) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run x_scraper.py's export_raw_csv() (or the "
            "full collection notebook) first, or pass --input-csv to point "
            "at a CSV already in x_scraper.py's RAW_COLUMNS shape."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows[:limit] if limit else rows


# ---------------------------------------------------------------------------
# build one Record
# ---------------------------------------------------------------------------

def build_record(row: dict[str, str]) -> Record:
    platform = row.get("platform") or "x"
    content_type = s_or_none(row.get("content_type"))
    content_id = s_or_none(row.get("platform_content_id"))
    a_hash, a_status = author_hash_and_status(row)

    author_metadata = AuthorMetadata(
        author_channel_id=None,  # no stable numeric X user id captured; author_username/display_name are raw PII this bridge must not carry (see module docstring)
        author_hash=a_hash,
        author_id_status=a_status,
        follower_count=parse_int(row.get("author_follower_count")),
        account_age_days=parse_int(row.get("author_account_age_days")),
    )

    return Record(
        text=row.get("text_raw", "") or "",
        date=row.get("created_at_utc") or "",
        source=platform,
        platform=platform,
        author_metadata=author_metadata,
        language=s_or_none(row.get("language_detected")),
        post_id=content_id,  # each tweet is its own top-level item - see module docstring
        post_title=None,     # X has no separate post-title concept
        is_reply=(content_type == "reply"),
        content_id=content_id,
        parent_id=s_or_none(row.get("parent_id")),
        collected_at_utc=s_or_none(row.get("collected_at_utc")),
        collection_run_id=s_or_none(row.get("collection_run_id")),
        query_id=s_or_none(row.get("query_id")),
        automation_risk_score=parse_float(row.get("automation_risk_score")),
        content_type=content_type,
        matched_query_ids=s_or_none(row.get("matched_query_ids")),
        query_version=s_or_none(row.get("query_version")),
        discovery_route=s_or_none(row.get("discovery_route")),
        source_id=s_or_none(row.get("source_id")),
        source_container=s_or_none(row.get("source_container")),
        source_container_id=s_or_none(row.get("source_container_id")),
        permalink_hash=s_or_none(row.get("permalink_hash")),
        source_total_available=parse_int(row.get("source_total_available")),
        sampling_method="none",  # x_scraper.py's collector does not sample - RAW_COLUMNS has sampling_applied but no sampling_method, same decision Reddit's bridge made
        sampling_applied=parse_bool01(row.get("sampling_applied")),
        items_kept=parse_int(row.get("items_kept")),
        random_seed=s_or_none(row.get("random_seed")),
        language_confidence=parse_float(row.get("language_confidence")),
        project_week=s_or_none(row.get("project_week")),
        in_window=parse_bool01(row.get("in_window")),
        is_partial_week=parse_bool01(row.get("is_partial_week")),
        content_status=s_or_none(row.get("content_status")),
        geo_method=s_or_none(row.get("geo_method")),
        geo_confidence=s_or_none(row.get("geo_confidence")),
        geo_granularity=s_or_none(row.get("geo_granularity")),
        country_or_region=s_or_none(row.get("country_or_region")),
        geo_limitations=s_or_none(row.get("geo_limitations")),
    )


# ---------------------------------------------------------------------------
# Record -> raw_schema_columns.py CSV row
# ---------------------------------------------------------------------------

def record_to_raw_schema_row(record: Record, row: dict[str, str]) -> dict[str, str]:
    """Every RAW_SCHEMA_COLUMNS entry explicitly, "" for genuinely
    unavailable data rather than omitted (config/raw_schema_columns.py's own
    docstring requires every column present even when empty) - same rule
    Reddit's bridge follows.

    engagement_*/author_is_verified/language_reported/collector_version
    pull straight from `row` rather than `record`: config/schema.py's
    Record has no engagement_* fields at all (see module docstring) and
    those particular columns aren't on AuthorMetadata/Record either -
    Reddit's bridge has the same split (its `raw_score` parameter)."""
    am = record.author_metadata
    return {
        "platform": record.platform or "",
        "platform_content_id": record.content_id or "",
        "content_type": record.content_type or "",
        "created_at_utc": record.date or "",
        "collected_at_utc": record.collected_at_utc or "",
        "text_raw": record.text,
        "author_hash": am.author_hash or "",
        "project_week": record.project_week or "",
        "in_window": str(bool(record.in_window)),
        "is_partial_week": str(bool(record.is_partial_week)),
        "query_id": record.query_id or "",
        "collection_run_id": record.collection_run_id or "",
        "source_id": record.source_id or "",
        "source_container": record.source_container or "",
        "source_container_id": record.source_container_id or "",
        "source_parent_id": "",    # X tweets are standalone - x_scraper.py never populates this (see module docstring)
        "source_parent_title": "",
        "parent_id": record.parent_id or "",
        "query_version": record.query_version or "",
        "discovery_route": record.discovery_route or "",
        "matched_query_ids": record.matched_query_ids or "",
        "collector_version": row.get("collector_version") or "",
        "permalink_hash": record.permalink_hash or "",
        "source_total_available": "" if record.source_total_available is None else str(record.source_total_available),
        "sampling_method": record.sampling_method or "",
        "sampling_applied": str(bool(record.sampling_applied)),
        "items_kept": "" if record.items_kept is None else str(record.items_kept),
        "random_seed": record.random_seed or "",
        "engagement_score": int_str(row.get("engagement_score")),
        "engagement_replies": int_str(row.get("engagement_replies")),
        "engagement_shares": int_str(row.get("engagement_shares")),
        "engagement_quotes": int_str(row.get("engagement_quotes")),
        "engagement_views": int_str(row.get("engagement_views")),
        "engagement_collected_at_utc": row.get("engagement_collected_at_utc") or "",
        "author_is_verified": int_str(row.get("author_is_verified")),
        "author_follower_count": "" if am.follower_count is None else str(am.follower_count),
        "author_account_age_days": "" if am.account_age_days is None else str(am.account_age_days),
        "author_is_submitter": "",  # not applicable to X (see module docstring / task decision)
        "automation_risk_score": "" if record.automation_risk_score is None else str(record.automation_risk_score),
        "language_reported": row.get("language_reported") or "",
        "language_detected": record.language or "",
        "language_confidence": "" if record.language_confidence is None else str(record.language_confidence),
        "content_status": record.content_status or "",
        "geo_method": record.geo_method or "",
        "country_or_region": record.country_or_region or "",
        "geo_confidence": record.geo_confidence or "",
        "geo_granularity": record.geo_granularity or "",
        "geo_limitations": record.geo_limitations or "",
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows (smoke-testing).")
    parser.add_argument(
        "--input-csv", type=Path, default=None,
        help=f"Override the x_raw.csv path (default: resolved the same way x_scraper.py resolves "
             f"X_OUTPUT_ROOT - currently {DEFAULT_INPUT_CSV}).",
    )
    args = parser.parse_args()

    input_csv = args.input_csv or DEFAULT_INPUT_CSV
    rows = load_rows(input_csv, args.limit)
    print(f"Loaded {len(rows)} row(s) from {input_csv}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = [build_record(row) for row in rows]

    with JSONL_OUTPUT.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(record.to_json_line() + "\n")

    with CSV_OUTPUT.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()
        for row, record in zip(rows, records):
            writer.writerow(record_to_raw_schema_row(record, row))

    hashed = sum(1 for r in records if r.author_metadata.author_hash)
    not_active = sum(1 for r in records if r.content_status != "active")

    print(f"\nWrote {len(records)} record(s):")
    print(f"  JSONL: {JSONL_OUTPUT}")
    print(f"  CSV:   {CSV_OUTPUT}")
    print(f"  author_hash populated (handle resolved): {hashed}/{len(records)}")
    print(f"  content_status != active: {not_active}/{len(records)}")


if __name__ == "__main__":
    main()
