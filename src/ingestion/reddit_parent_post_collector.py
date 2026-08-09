"""
Reddit Master Parent-Post URL Collector — Query Registry v3
===========================================================

Purpose
-------
Run the full Reddit URL-discovery plan automatically from one script.

Workflow
--------
1) Iterate through every Reddit Query Registry v3 item.
2) For source-scoped queries, run every configured simple search term
   inside every registered subreddit in that query's source scope.
3) For discovery queries (RQ-A01/RQ-A02/RQ-A03), search across all Reddit.
4) Save RAW parent-post discovery files with checkpoints.
5) Do NOT perform global deduplication yet.
6) Later: merge all raw files -> global dedup -> comments/replies extraction.

Important
---------
- Uses Reddit visible search only.
- sort=new is mandatory.
- No MAX_URLS_PER_SOURCE cap.
- Stops each search term on no-growth or MAX_SCROLLS_PER_SEARCH_TERM.
- Parent post timestamps are retained for provenance.
- Final temporal filtering is primarily based on COMMENT timestamps.
- Restricted sources are collected but clearly marked.
- A post discovered by several terms inside the same query/source job is stored
  once in that job and matched_search_terms preserves all matching terms.
"""

#%%
from __future__ import annotations

import csv
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


# ============================================================
# 1. PROJECT SETTINGS
# ============================================================

# Optional local Firefox profile.
# Keep the real machine-specific path outside Git.
FIREFOX_PROFILE_PATH = os.environ.get(
    "REDDIT_FIREFOX_PROFILE",
    "",
)

# Repository-local raw output directory.
# data/raw should remain gitignored.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "reddit"
    / "parent_posts"
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROJECT_START = datetime(
    2026, 2, 28,
    0, 0, 0,
    tzinfo=timezone.utc,
)

PROJECT_END = datetime(
    2026, 7, 22,
    23, 59, 59,
    tzinfo=timezone.utc,
)

QUERY_VERSION = "v3.0"

# None = run every Reddit query in this registry.
#
# If you want to run in smaller batches, use for example:
# ACTIVE_QUERY_IDS = {"RQ-001", "RQ-002", "RQ-003"}
ACTIVE_QUERY_IDS: set[str] | None = None

# Resume behavior:
# Read ALL previous *_runs.csv files in DATA_DIR and skip only search-term
# jobs that were conclusively completed.
SKIP_COMPLETED_TERMS = True

TERMINAL_SUCCESS_STATUSES = {
    "completed_no_growth",
    "reached_before_project_start",
}

# Main collection settings.
# There is deliberately NO MAX_URLS cap.
MAX_SCROLLS_PER_SEARCH_TERM = 60
MAX_NO_NEW_ROUNDS = 6

SCROLL_PAUSE_SECONDS = 3.0
BETWEEN_SEARCH_TERM_PAUSE_SECONDS = 8.0
BETWEEN_JOB_PAUSE_SECONDS = 10.0
INITIAL_TIMEOUT_SECONDS = 25

POST_SELECTOR = 'a[data-testid="post-title"]'

MASTER_RUN_ID = (
    "reddit_master_"
    + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    + "_"
    + uuid.uuid4().hex[:8]
)

RUN_LOG_FILE = DATA_DIR / (
    f"{MASTER_RUN_ID}_runs.csv"
)


# ============================================================
# 2. SOURCE REGISTRY v3 — REDDIT
# ============================================================

SOURCE_REGISTRY = {
    "RD-001": {
        "subreddit": "worldnews",
        "status": "Active",
    },
    "RD-002": {
        "subreddit": "geopolitics",
        "status": "Active",
    },
    "RD-003": {
        "subreddit": "InternationalNews",
        "status": "Active",
    },
    "RD-004": {
        "subreddit": "news",
        "status": "Active",
    },
    "RD-005": {
        "subreddit": "politics",
        "status": "Active",
    },
    "RD-006": {
        "subreddit": "PoliticalDiscussion",
        "status": "Active",
    },
    "RD-007": {
        "subreddit": "NeutralPolitics",
        "status": "Active",
    },
    "RD-008": {
        "subreddit": "AskAnAmerican",
        "status": "Active",
    },
    "RD-009": {
        "subreddit": "iran",
        "status": "Active",
    },
    "RD-010": {
        "subreddit": "NewIran",
        "status": "Active",
    },
    "RD-011": {
        "subreddit": "ProIran",
        "status": "Restricted",
    },
    "RD-012": {
        "subreddit": "iranian",
        "status": "Active",
    },
    "RD-013": {
        "subreddit": "MiddleEast",
        "status": "Active",
    },
    "RD-014": {
        "subreddit": "AskMiddleEast",
        "status": "Active",
    },
    "RD-015": {
        "subreddit": "Arabs",
        "status": "Active",
    },
    "RD-016": {
        "subreddit": "Israel",
        "status": "Active",
    },
    "RD-017": {
        "subreddit": "CredibleDefense",
        "status": "Active",
    },
    "RD-018": {
        "subreddit": "LessCredibleDefence",
        "status": "Active",
    },
    "RD-019": {
        "subreddit": "WarCollege",
        "status": "Active",
    },
    "RD-020": {
        "subreddit": "CombatFootage",
        "status": "Active",
    },
    "RD-021": {
        "subreddit": "military",
        "status": "Active",
    },
    "RD-022": {
        "subreddit": "IRstudies",
        "status": "Active",
    },
    "RD-023": {
        "subreddit": "energy",
        "status": "Active",
    },
    "RD-024": {
        "subreddit": "oil",
        "status": "Active",
    },
    "RD-025": {
        "subreddit": "Economics",
        "status": "Active",
    },
    "RD-026": {
        "subreddit": "investing",
        "status": "Active",
    },
    "RD-027": {
        "subreddit": "stocks",
        "status": "Active",
    },
    "RD-028": {
        "subreddit": "ww3",
        "status": "Restricted",
    },
}


# ============================================================
# 3. QUERY REGISTRY v3 — REDDIT
# ============================================================
#
# logical_query = approved Registry expression.
# search_terms  = practical simple Reddit searches used for retrieval.
#
# Search terms intentionally avoid a full Cartesian expansion.
# They are concise, entity-anchored expressions intended to keep precision
# reasonably high while preserving the major branches of each logical query.

QUERY_REGISTRY = [
    {
        "query_id": "RQ-001",
        "family": "Core conflict",
        "lang": "en",
        "logical_query": (
            '"Iran-US war" OR "US-Iran tensions" OR "Iran war"'
        ),
        "risk": "low",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-001",
            "RD-003",
            "RD-004",
        ],
        "search_terms": [
            "Iran-US war",
            "US-Iran tensions",
            "Iran war",
        ],
    },
    {
        "query_id": "RQ-002",
        "family": "Geopolitical",
        "lang": "en",
        "logical_query": (
            '("Iran" AND "United States") '
            'AND ("tensions" OR "war")'
        ),
        "risk": "low",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-002",
            "RD-006",
            "RD-007",
        ],
        "search_terms": [
            "Iran United States tensions",
            "Iran United States war",
        ],
    },
    {
        "query_id": "RQ-003",
        "family": "Iran perspectives",
        "lang": "en",
        "logical_query": (
            '("United States" OR America) AND '
            '("Iran-US war" OR sanctions OR airstrike)'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "United States Iran-US war",
            "America Iran-US war",
            "United States Iran sanctions",
            "United States Iran airstrike",
        ],
    },
    {
        "query_id": "RQ-004",
        "family": "Regional",
        "lang": "en",
        "logical_query": (
            '("Iran" AND "United States") OR '
            '("Strait of Hormuz" AND Iran)'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-013",
            "RD-014",
            "RD-015",
            "RD-016",
        ],
        "search_terms": [
            "Iran United States",
            "Iran Strait of Hormuz",
            "Iran Hormuz",
        ],
    },
    {
        "query_id": "RQ-005",
        "family": "Military",
        "lang": "en",
        "logical_query": (
            '("Iran" OR IRGC) AND '
            '(airstrike OR "missile strike" OR "drone attack")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-017",
            "RD-018",
            "RD-019",
            "RD-020",
            "RD-021",
        ],
        "search_terms": [
            "Iran airstrike",
            "Iran missile strike",
            "Iran drone attack",
            "IRGC missile strike",
        ],
    },
    {
        "query_id": "RQ-006",
        "family": "Diplomacy",
        "lang": "en",
        "logical_query": (
            '("Iran" OR "United States") AND '
            '(ceasefire OR negotiations)'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-022",
            "RD-002",
            "RD-006",
        ],
        "search_terms": [
            "Iran ceasefire",
            "Iran United States negotiations",
            "US Iran ceasefire",
        ],
    },
    {
        "query_id": "RQ-007",
        "family": "Economic",
        "lang": "en",
        "logical_query": (
            '("Iran" OR "Iran-US war") AND '
            '("oil price" OR "gold price" OR "market volatility")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-023",
            "RD-024",
            "RD-025",
            "RD-026",
            "RD-027",
        ],
        "search_terms": [
            "Iran oil price",
            "Iran gold price",
            "Iran market volatility",
            "Iran-US war oil price",
        ],
    },
    {
        "query_id": "RQ-008",
        "family": "Escalation",
        "lang": "en",
        "logical_query": (
            '("Iran" AND "United States") AND '
            '("Iran-US war" OR "missile strike")'
        ),
        "risk": "high",
        "entity_anchor": "Iran + United States",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-028",
        ],
        "search_terms": [
            "Iran United States Iran-US war",
            "Iran United States missile strike",
        ],
    },
    {
        "query_id": "RQ-017",
        "family": "Operation-specific",
        "lang": "en",
        "logical_query": (
            '"Epic Fury" OR "Operation Epic Fury" OR "Roaring Lion"'
        ),
        "risk": "low",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-001",
            "RD-002",
            "RD-017",
            "RD-018",
        ],
        "search_terms": [
            "Epic Fury",
            "Operation Epic Fury",
            "Roaring Lion",
        ],
    },
    {
        "query_id": "RQ-018",
        "family": "Hormuz blockade",
        "lang": "en",
        "logical_query": (
            '(Hormuz OR "Strait of Hormuz") AND '
            '(blockade OR closed OR shipping)'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-001",
            "RD-023",
            "RD-024",
        ],
        "search_terms": [
            "Hormuz blockade",
            "Strait of Hormuz closed",
            "Strait of Hormuz shipping",
        ],
    },

    # Persian Reddit queries
    {
        "query_id": "RQ-009",
        "family": "Core conflict",
        "lang": "fa",
        "logical_query": (
            '"جنگ ایران و آمریکا" OR "تنش ایران و آمریکا"'
        ),
        "risk": "low",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "جنگ ایران و آمریکا",
            "تنش ایران و آمریکا",
        ],
    },
    {
        "query_id": "RQ-010",
        "family": "Military",
        "lang": "fa",
        "logical_query": (
            '"ایران" AND '
            '("حمله هوایی" OR "حمله موشکی" OR "حمله پهپادی")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران حمله هوایی",
            "ایران حمله موشکی",
            "ایران حمله پهپادی",
        ],
    },
    {
        "query_id": "RQ-011",
        "family": "Diplomacy",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "آمریکا") AND '
            '("آتش‌بس" OR "مذاکرات")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران آمریکا آتش‌بس",
            "ایران آمریکا مذاکرات",
        ],
    },
    {
        "query_id": "RQ-012",
        "family": "Humanitarian",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "جنگ ایران و آمریکا") AND '
            '("تلفات غیرنظامیان" OR "بحران انسانی")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران تلفات غیرنظامیان",
            "جنگ ایران و آمریکا بحران انسانی",
        ],
    },
    {
        "query_id": "RQ-013",
        "family": "Economic",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "جنگ ایران و آمریکا") AND '
            '("قیمت نفت" OR "نرخ ارز" OR "قیمت طلا")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران قیمت نفت",
            "ایران نرخ ارز",
            "ایران قیمت طلا",
        ],
    },
    {
        "query_id": "RQ-014",
        "family": "Information",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "جنگ ایران و آمریکا") AND '
            '("اطلاعات نادرست" OR "تبلیغات سیاسی")'
        ),
        "risk": "high",
        "entity_anchor": "ایران",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران اطلاعات نادرست",
            "ایران تبلیغات سیاسی",
            "جنگ ایران و آمریکا اطلاعات نادرست",
        ],
    },
    {
        "query_id": "RQ-015",
        "family": "Hormuz",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "جنگ ایران و آمریکا") AND '
            '("تنگه هرمز" OR "قیمت نفت")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران تنگه هرمز",
            "جنگ ایران و آمریکا قیمت نفت",
        ],
    },
    {
        "query_id": "RQ-016",
        "family": "Sanctions/nuclear",
        "lang": "fa",
        "logical_query": (
            '("ایران" OR "آمریکا") AND '
            '("تحریم‌ها" OR "برنامه هسته‌ای")'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "source_scope",
        "source_ids": [
            "RD-009",
            "RD-010",
            "RD-011",
            "RD-012",
        ],
        "search_terms": [
            "ایران آمریکا تحریم‌ها",
            "ایران برنامه هسته‌ای",
        ],
    },

    # Discovery on r/all / all Reddit
    {
        "query_id": "RQ-A01",
        "family": "Discovery — core",
        "lang": "en",
        "logical_query": (
            '"Iran war" OR "Iran-US war"'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "query_search",
        "source_ids": [],
        "search_terms": [
            "Iran war",
            "Iran-US war",
        ],
    },
    {
        "query_id": "RQ-A02",
        "family": "Discovery — bilateral",
        "lang": "en",
        "logical_query": (
            '"Iran" AND "United States"'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "query_search",
        "source_ids": [],
        "search_terms": [
            "Iran United States",
        ],
    },
    {
        "query_id": "RQ-A03",
        "family": "Discovery — operation",
        "lang": "en",
        "logical_query": (
            '"Epic Fury" OR "Strait of Hormuz" OR Hormuz'
        ),
        "risk": "medium",
        "entity_anchor": "",
        "discovery_route": "query_search",
        "source_ids": [],
        "search_terms": [
            "Epic Fury",
            "Strait of Hormuz",
            "Hormuz",
        ],
    },
]


# ============================================================
# 4. OUTPUT SCHEMAS
# ============================================================

FIELDNAMES = [
    "platform",
    "platform_content_id",
    "query_id",
    "query_version",
    "collection_run_id",
    "family",
    "lang",
    "risk",
    "entity_anchor",
    "discovery_route",
    "source_id",
    "source_status",
    "sort_mode",
    "logical_query",
    "matched_search_terms",
    "post_id",
    "subreddit",
    "title",
    "url",
    "created_at_utc",
    "post_inside_project_window",
    "collected_at_utc",
]

RUN_LOG_FIELDS = [
    "master_run_id",
    "query_id",
    "source_id",
    "subreddit",
    "source_status",
    "search_term",
    "sort_mode",
    "started_at_utc",
    "finished_at_utc",
    "status",
    "unique_posts_after_job",
    "oldest_observed_utc",
    "newest_observed_utc",
    "output_file",
]


# ============================================================
# 5. REGISTRY VALIDATION
# ============================================================

def validate_registry() -> None:
    seen_query_ids: set[str] = set()

    for query in QUERY_REGISTRY:
        query_id = query["query_id"]

        if query_id in seen_query_ids:
            raise ValueError(
                f"Duplicate query_id: {query_id}"
            )

        seen_query_ids.add(query_id)

        if query["discovery_route"] not in {
            "source_scope",
            "query_search",
        }:
            raise ValueError(
                f"{query_id}: invalid discovery_route"
            )

        if query["risk"] == "high":
            if not query["entity_anchor"]:
                raise ValueError(
                    f"{query_id}: high-risk query "
                    "requires entity_anchor"
                )

        if (
            query["discovery_route"]
            == "source_scope"
        ):
            if not query["source_ids"]:
                raise ValueError(
                    f"{query_id}: source_scope "
                    "requires source_ids"
                )

            for source_id in query["source_ids"]:
                if source_id not in SOURCE_REGISTRY:
                    raise KeyError(
                        f"{query_id}: unknown source "
                        f"{source_id}"
                    )

        if (
            query["discovery_route"]
            == "query_search"
            and query["source_ids"]
        ):
            raise ValueError(
                f"{query_id}: query_search "
                "must not specify source_ids"
            )

        if not query["search_terms"]:
            raise ValueError(
                f"{query_id}: no search_terms"
            )


# ============================================================
# 5.1 RESUME HELPERS
# ============================================================

def make_term_job_key(
    query_id: str,
    source_id: str,
    subreddit: str,
    search_term: str,
) -> tuple[str, str, str, str]:
    """
    Stable identity of one collection unit.

    A unit is:
        Query × Source × Search Term

    For r/all discovery jobs, source_id and subreddit are blank.
    """
    return (
        (query_id or "").strip(),
        (source_id or "").strip(),
        (subreddit or "").strip().lower(),
        (search_term or "").strip(),
    )


def load_completed_term_jobs(
    data_dir: Path,
) -> set[tuple[str, str, str, str]]:
    """
    Scan ALL previous master run logs in DATA_DIR.

    Only conclusively successful terminal statuses are considered complete.
    Interrupted / blocked / scroll-error / max-scroll jobs are NOT skipped.
    """
    completed: set[
        tuple[str, str, str, str]
    ] = set()

    log_files = sorted(
        data_dir.glob(
            "reddit_master_*_runs.csv"
        )
    )

    for log_file in log_files:

        try:
            with log_file.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                reader = csv.DictReader(
                    file
                )

                for row in reader:

                    status = (
                        row.get("status")
                        or ""
                    ).strip()

                    if (
                        status
                        not in TERMINAL_SUCCESS_STATUSES
                    ):
                        continue

                    key = make_term_job_key(
                        query_id=(
                            row.get("query_id")
                            or ""
                        ),
                        source_id=(
                            row.get("source_id")
                            or ""
                        ),
                        subreddit=(
                            row.get("subreddit")
                            or ""
                        ),
                        search_term=(
                            row.get("search_term")
                            or ""
                        ),
                    )

                    completed.add(
                        key
                    )

        except (
            OSError,
            csv.Error,
        ) as error:

            print(
                "Warning: could not read "
                f"resume log {log_file.name}: "
                f"{error}"
            )

    return completed


# ============================================================
# 6. DATE HELPERS
# ============================================================

def parse_reddit_datetime(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = (
                value[:-1]
                + "+00:00"
            )

        parsed = datetime.fromisoformat(
            value
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except ValueError:
        return None


def normalize_datetime_string(
    value: str | None,
) -> str:

    parsed = parse_reddit_datetime(
        value
    )

    if parsed is None:
        return ""

    return parsed.isoformat()


def is_inside_project_window(
    created_time: str,
) -> bool:

    parsed = parse_reddit_datetime(
        created_time
    )

    if parsed is None:
        return False

    return (
        PROJECT_START
        <= parsed
        <= PROJECT_END
    )


# ============================================================
# 7. URL HELPERS
# ============================================================

def normalize_reddit_post_url(
    url: str | None,
) -> str | None:

    if not url:
        return None

    parts = urlsplit(
        url
    )

    if parts.netloc.lower() not in {
        "reddit.com",
        "www.reddit.com",
        "old.reddit.com",
    }:
        return None

    clean_url = urlunsplit(
        (
            "https",
            "www.reddit.com",
            parts.path,
            "",
            "",
        )
    )

    return (
        clean_url.rstrip("/")
        + "/"
    )


def parse_post_url(
    url: str | None,
) -> tuple[str | None, str | None]:

    if not url:
        return None, None

    path_parts = (
        urlsplit(url)
        .path
        .strip("/")
        .split("/")
    )

    try:
        comments_index = (
            path_parts.index(
                "comments"
            )
        )

        post_id = path_parts[
            comments_index + 1
        ]

    except (
        ValueError,
        IndexError,
    ):
        return None, None

    subreddit = None

    if (
        len(path_parts) >= 2
        and path_parts[0].lower()
        == "r"
    ):
        subreddit = path_parts[1]

    return post_id, subreddit


def build_search_url(
    search_term: str,
    subreddit: str = "",
) -> str:

    params = {
        "q": search_term,
        "type": "posts",
        "sort": "new",
    }

    if subreddit:
        params[
            "restrict_sr"
        ] = "1"

        return (
            "https://www.reddit.com/"
            f"r/{subreddit}/search/?"
            + urlencode(params)
        )

    return (
        "https://www.reddit.com/search/?"
        + urlencode(params)
    )


# ============================================================
# 8. CSV HELPERS
# ============================================================

def load_existing_records(
    output_file: Path,
) -> dict[str, dict[str, str]]:

    if not output_file.exists():
        return {}

    records_by_post_id: dict[
        str,
        dict[str, str],
    ] = {}

    try:
        with output_file.open(
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:
                post_id = (
                    row.get("post_id")
                    or ""
                ).strip()

                if not post_id:
                    continue

                records_by_post_id[
                    post_id
                ] = {
                    field: row.get(
                        field,
                        "",
                    )
                    for field
                    in FIELDNAMES
                }

    except (
        OSError,
        csv.Error,
    ) as error:

        print(
            "Warning: could not read "
            f"previous CSV: {error}"
        )

    return records_by_post_id


def save_checkpoint(
    output_file: Path,
    records_by_post_id: dict[
        str,
        dict[str, str],
    ],
) -> None:

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        output_file.with_suffix(
            output_file.suffix
            + ".tmp"
        )
    )

    with temporary_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(
            records_by_post_id.values()
        )

    os.replace(
        temporary_file,
        output_file,
    )


def append_run_log(
    row: dict[str, str],
) -> None:

    write_header = (
        not RUN_LOG_FILE.exists()
    )

    with RUN_LOG_FILE.open(
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=RUN_LOG_FIELDS,
            extrasaction="ignore",
        )

        if write_header:
            writer.writeheader()

        writer.writerow(row)


def add_search_term_to_record(
    record: dict[str, str],
    search_term: str,
) -> bool:

    current_terms = {
        term.strip()
        for term in (
            record.get(
                "matched_search_terms"
            )
            or ""
        ).split(" | ")
        if term.strip()
    }

    before = set(
        current_terms
    )

    current_terms.add(
        search_term
    )

    record[
        "matched_search_terms"
    ] = " | ".join(
        sorted(current_terms)
    )

    return (
        current_terms
        != before
    )


# ============================================================
# 9. VISIBLE BLOCK CHECK
# ============================================================

def get_visible_body_text(
    driver: webdriver.Firefox,
) -> str:

    try:
        return (
            driver.find_element(
                By.TAG_NAME,
                "body",
            )
            .text
            .lower()
        )

    except Exception:
        return ""


def visible_page_looks_blocked(
    driver: webdriver.Firefox,
) -> bool:

    body_text = (
        get_visible_body_text(
            driver
        )
    )

    strong_block_phrases = (
        "you've been blocked",
        "you have been blocked",
        "too many requests",
        "access denied",
        "whoa there, pardner",
        "complete the captcha",
        "verify you are human",
    )

    return any(
        phrase in body_text
        for phrase
        in strong_block_phrases
    )


# ============================================================
# 10. POST METADATA
# ============================================================

def extract_created_time(
    post_element,
) -> str:
    """
    Use the timestamp strategy already validated on Reddit search results:
    find the nearest ancestor containing a descendant <time datetime="...">.
    """

    try:
        result_container = (
            post_element.find_element(
                By.XPATH,
                "./ancestor::*[.//time[@datetime]][1]",
            )
        )

        time_element = (
            result_container.find_element(
                By.XPATH,
                ".//time[@datetime][1]",
            )
        )

        raw_datetime = (
            time_element.get_attribute(
                "datetime"
            )
            or ""
        )

        return normalize_datetime_string(
            raw_datetime
        )

    except Exception:
        return ""


# ============================================================
# 11. BUILD COLLECTION JOBS
# ============================================================

def build_jobs() -> list[dict]:

    jobs: list[dict] = []

    for query in QUERY_REGISTRY:

        if (
            ACTIVE_QUERY_IDS
            is not None
            and query["query_id"]
            not in ACTIVE_QUERY_IDS
        ):
            continue

        if (
            query["discovery_route"]
            == "query_search"
        ):
            jobs.append(
                {
                    "query": query,
                    "source_id": "",
                    "subreddit": "",
                    "source_status": "",
                }
            )
            continue

        for source_id in query[
            "source_ids"
        ]:

            source = (
                SOURCE_REGISTRY[
                    source_id
                ]
            )

            jobs.append(
                {
                    "query": query,
                    "source_id": source_id,
                    "subreddit": source[
                        "subreddit"
                    ],
                    "source_status": source[
                        "status"
                    ],
                }
            )

    return jobs


# ============================================================
# 12. COLLECT ONE SEARCH TERM INSIDE ONE JOB
# ============================================================

def collect_one_search_term(
    driver: webdriver.Firefox,
    query: dict,
    output_file: Path,
    source_id: str,
    subreddit: str,
    source_status: str,
    search_term: str,
) -> tuple[
    dict[str, dict[str, str]],
    datetime | None,
    datetime | None,
    str,
]:

    records_by_post_id = (
        load_existing_records(
            output_file
        )
    )

    try:
        WebDriverWait(
            driver,
            INITIAL_TIMEOUT_SECONDS,
        ).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    POST_SELECTOR,
                )
            )
        )

    except TimeoutException:

        if visible_page_looks_blocked(
            driver
        ):
            status = "blocked_or_captcha"
        else:
            status = "no_visible_results"

        return (
            records_by_post_id,
            None,
            None,
            status,
        )

    no_new_rounds = 0
    oldest_for_term: datetime | None = None
    newest_for_term: datetime | None = None
    status = "completed"

    for scroll_number in range(
        1,
        MAX_SCROLLS_PER_SEARCH_TERM
        + 1,
    ):

        if visible_page_looks_blocked(
            driver
        ):
            status = (
                "blocked_or_captcha"
            )
            break

        post_elements = (
            driver.find_elements(
                By.CSS_SELECTOR,
                POST_SELECTOR,
            )
        )

        new_this_round = 0
        existing_matches_updated = 0

        for post_element in post_elements:

            try:
                raw_url = (
                    post_element.get_attribute(
                        "href"
                    )
                )

                title = (
                    post_element.get_attribute(
                        "aria-label"
                    )
                    or post_element.text
                    or ""
                ).strip()

            except StaleElementReferenceException:
                continue

            clean_url = (
                normalize_reddit_post_url(
                    raw_url
                )
            )

            post_id, found_subreddit = (
                parse_post_url(
                    clean_url
                )
            )

            if not clean_url or not post_id:
                continue

            # For source-scoped jobs, enforce exact subreddit.
            if (
                subreddit
                and found_subreddit
                and found_subreddit.lower()
                != subreddit.lower()
            ):
                continue

            if post_id in records_by_post_id:

                if add_search_term_to_record(
                    records_by_post_id[
                        post_id
                    ],
                    search_term,
                ):
                    existing_matches_updated += 1

                continue

            created_time = (
                extract_created_time(
                    post_element
                )
            )

            parsed_time = (
                parse_reddit_datetime(
                    created_time
                )
            )

            if parsed_time is not None:

                if (
                    oldest_for_term is None
                    or parsed_time
                    < oldest_for_term
                ):
                    oldest_for_term = (
                        parsed_time
                    )

                if (
                    newest_for_term is None
                    or parsed_time
                    > newest_for_term
                ):
                    newest_for_term = (
                        parsed_time
                    )

            # Discovery route has no curated source_id.
            actual_source_id = (
                source_id
            )

            actual_source_status = (
                source_status
            )

            records_by_post_id[
                post_id
            ] = {
                "platform": "reddit",
                "platform_content_id": post_id,
                "query_id": query[
                    "query_id"
                ],
                "query_version": QUERY_VERSION,
                "collection_run_id": MASTER_RUN_ID,
                "family": query[
                    "family"
                ],
                "lang": query[
                    "lang"
                ],
                "risk": query[
                    "risk"
                ],
                "entity_anchor": query[
                    "entity_anchor"
                ],
                "discovery_route": query[
                    "discovery_route"
                ],
                "source_id": actual_source_id,
                "source_status": actual_source_status,
                "sort_mode": "new",
                "logical_query": query[
                    "logical_query"
                ],
                "matched_search_terms": search_term,
                "post_id": post_id,
                "subreddit": (
                    found_subreddit
                    or subreddit
                ),
                "title": title,
                "url": clean_url,
                "created_at_utc": created_time,
                "post_inside_project_window": str(
                    is_inside_project_window(
                        created_time
                    )
                ),
                "collected_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            new_this_round += 1

        save_checkpoint(
            output_file,
            records_by_post_id,
        )

        oldest_text = (
            oldest_for_term.isoformat()
            if oldest_for_term
            is not None
            else "N/A"
        )

        print(
            f"Round {scroll_number}/"
            f"{MAX_SCROLLS_PER_SEARCH_TERM} | "
            f"Visible: {len(post_elements)} | "
            f"New unique: {new_this_round} | "
            f"Matches updated: "
            f"{existing_matches_updated} | "
            f"Job total: "
            f"{len(records_by_post_id)} | "
            f"Oldest: {oldest_text}"
        )

        # NEW STOP CONDITION
        if (
            oldest_for_term is not None
            and oldest_for_term < PROJECT_START
        ):
            status = "reached_before_project_start"

            print(
                "Reached posts older than PROJECT_START. "
                "Stopping this search term."
            )

            break

        if new_this_round == 0:
            no_new_rounds += 1
        else:
            no_new_rounds = 0

        if (
            no_new_rounds
            >= MAX_NO_NEW_ROUNDS
        ):
            status = (
                "completed_no_growth"
            )

            print(
                "Stopping this search term: "
                f"{MAX_NO_NEW_ROUNDS} "
                "consecutive no-growth rounds."
            )
            break

        try:
            driver.execute_script(
                "window.scrollBy(0, 900);"
            )

        except WebDriverException:
            status = (
                "scroll_error"
            )
            break

        time.sleep(
            SCROLL_PAUSE_SECONDS
        )

    save_checkpoint(
        output_file,
        records_by_post_id,
    )

    return (
        records_by_post_id,
        oldest_for_term,
        newest_for_term,
        status,
    )


# ============================================================
# 13. MAIN
# ============================================================

def main() -> None:

    validate_registry()

    jobs = build_jobs()

    completed_term_jobs = (
        load_completed_term_jobs(
            DATA_DIR
        )
        if SKIP_COMPLETED_TERMS
        else set()
    )

    print(
        "\n"
        + "=" * 80
    )
    print(
        "REDDIT MASTER PARENT-POST URL COLLECTION"
    )
    print(
        "=" * 80
    )
    print(
        f"Master run ID: "
        f"{MASTER_RUN_ID}"
    )
    print(
        f"Queries selected: "
        f"{len({job['query']['query_id'] for job in jobs})}"
    )
    print(
        f"Query/source jobs: "
        f"{len(jobs)}"
    )
    print(
        f"Output directory: "
        f"{DATA_DIR.resolve()}"
    )
    print(
        f"Previously completed term-jobs found: "
        f"{len(completed_term_jobs)}"
    )
    print(
        "Resume mode: "
        + (
            "ON"
            if SKIP_COMPLETED_TERMS
            else "OFF"
        )
    )

    options = (
        webdriver.FirefoxOptions()
    )

    # Reuse a local Firefox profile only when configured explicitly.
    if FIREFOX_PROFILE_PATH:
        options.add_argument(
            "-profile"
        )

        options.add_argument(
            FIREFOX_PROFILE_PATH
        )

    driver = webdriver.Firefox(
        service=Service(
            GeckoDriverManager().install()
        ),
        options=options,
    )

    try:

        for job_number, job in enumerate(
            jobs,
            start=1,
        ):

            query = job["query"]
            source_id = job["source_id"]
            subreddit = job["subreddit"]
            source_status = job[
                "source_status"
            ]

            if source_id:
                output_file = DATA_DIR / (
                    f"{query['query_id']}_"
                    f"{source_id}_"
                    "reddit_parent_posts.csv"
                )

                scope_label = (
                    f"{source_id} -> "
                    f"r/{subreddit}"
                )

            else:
                output_file = DATA_DIR / (
                    f"{query['query_id']}_"
                    "r_all_"
                    "reddit_parent_posts.csv"
                )

                scope_label = "r/all"

            print(
                "\n"
                + "=" * 80
            )
            print(
                f"JOB {job_number}/"
                f"{len(jobs)}"
            )
            print(
                f"Query: "
                f"{query['query_id']} | "
                f"{query['family']} | "
                f"{query['lang']}"
            )
            print(
                f"Scope: {scope_label}"
            )

            if source_status:
                print(
                    f"Source status: "
                    f"{source_status}"
                )

            print(
                f"Output: "
                f"{output_file}"
            )
            print(
                "=" * 80
            )

            for term_number, search_term in enumerate(
                query[
                    "search_terms"
                ],
                start=1,
            ):

                term_job_key = make_term_job_key(
                    query_id=query[
                        "query_id"
                    ],
                    source_id=source_id,
                    subreddit=subreddit,
                    search_term=search_term,
                )

                if (
                    SKIP_COMPLETED_TERMS
                    and term_job_key
                    in completed_term_jobs
                ):
                    print(
                        "\n"
                        + "-" * 70
                    )
                    print(
                        f"SKIP COMPLETED | "
                        f"{query['query_id']} | "
                        f"{source_id or 'r/all'} | "
                        f"{search_term}"
                    )
                    print(
                        "This Query × Source × Search Term "
                        "was conclusively completed in a previous run."
                    )
                    print(
                        "-" * 70
                    )
                    continue

                search_url = (
                    build_search_url(
                        search_term=search_term,
                        subreddit=subreddit,
                    )
                )

                print(
                    "\n"
                    + "-" * 70
                )
                print(
                    f"Term {term_number}/"
                    f"{len(query['search_terms'])}: "
                    f"{search_term}"
                )
                print(
                    f"URL: {search_url}"
                )
                print(
                    "-" * 70
                )

                started_at = datetime.now(
                    timezone.utc
                )

                driver.get(
                    search_url
                )

                (
                    records_by_post_id,
                    oldest,
                    newest,
                    status,
                ) = collect_one_search_term(
                    driver=driver,
                    query=query,
                    output_file=output_file,
                    source_id=source_id,
                    subreddit=subreddit,
                    source_status=source_status,
                    search_term=search_term,
                )

                finished_at = datetime.now(
                    timezone.utc
                )

                append_run_log(
                    {
                        "master_run_id": MASTER_RUN_ID,
                        "query_id": query[
                            "query_id"
                        ],
                        "source_id": source_id,
                        "subreddit": subreddit,
                        "source_status": source_status,
                        "search_term": search_term,
                        "sort_mode": "new",
                        "started_at_utc": (
                            started_at.isoformat()
                        ),
                        "finished_at_utc": (
                            finished_at.isoformat()
                        ),
                        "status": status,
                        "unique_posts_after_job": str(
                            len(
                                records_by_post_id
                            )
                        ),
                        "oldest_observed_utc": (
                            oldest.isoformat()
                            if oldest
                            is not None
                            else ""
                        ),
                        "newest_observed_utc": (
                            newest.isoformat()
                            if newest
                            is not None
                            else ""
                        ),
                        "output_file": str(
                            output_file
                        ),
                    }
                )

                if (
                    status
                    in TERMINAL_SUCCESS_STATUSES
                ):
                    completed_term_jobs.add(
                        term_job_key
                    )

                if (
                    term_number
                    < len(
                        query[
                            "search_terms"
                        ]
                    )
                ):
                    print(
                        f"Pausing "
                        f"{BETWEEN_SEARCH_TERM_PAUSE_SECONDS:.0f}s "
                        "before next term..."
                    )

                    time.sleep(
                        BETWEEN_SEARCH_TERM_PAUSE_SECONDS
                    )

            if (
                job_number
                < len(jobs)
            ):
                print(
                    f"\nPausing "
                    f"{BETWEEN_JOB_PAUSE_SECONDS:.0f}s "
                    "before next job..."
                )

                time.sleep(
                    BETWEEN_JOB_PAUSE_SECONDS
                )

        print(
            "\n"
            + "=" * 80
        )
        print(
            "MASTER URL COLLECTION COMPLETED"
        )
        print(
            "=" * 80
        )
        print(
            f"Run log: "
            f"{RUN_LOG_FILE}"
        )
        print(
            "Completed term-jobs are now resumable across future runs."
        )
        print(
            "Next phase: merge all raw parent-post CSVs, "
            "global deduplication by post_id, preserve "
            "matched_query_ids, then collect comments/replies."
        )

    finally:

        print(
            "\nClosing Firefox."
        )

        driver.quit()


if __name__ == "__main__":
    main()

# %%
