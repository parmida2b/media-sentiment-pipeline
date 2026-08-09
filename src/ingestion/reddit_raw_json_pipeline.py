"""
Reddit Raw Structured JSON Collector + Offline Coverage Audit
=============================================================

Purpose
-------
Build a reproducible raw-first Reddit pipeline from the parent-post URLs
already collected by the Master URL Collector.

Pipeline
--------
1) Read all *_reddit_parent_posts.csv files.
2) Merge + globally deduplicate by post_id.
3) Skip parent posts created AFTER PROJECT_END.
   - Posts before PROJECT_START are intentionally kept because they may have
     comments created inside the project window.
4) Convert each Reddit post URL to its public `.json` representation.
5) Open each public `.json` URL directly in the existing Firefox browser.
6) Save the RAW Reddit JSON unchanged, one file per post.
7) Resume automatically: existing raw JSON files are skipped.
8) Parse saved JSON files OFFLINE.
9) Filter comments to:
       2026-02-28 <= comment_created_at_utc <= 2026-07-22
10) Assign W01 ... W21.
11) Produce weekly coverage.

Important access behavior
-------------------------
- No Selenium-cookie transfer to requests; Firefox opens the JSON URL directly.
- No account/IP rotation.
- No retry tricks for bypassing access controls.
- Visible block/CAPTCHA/access-denied pages stop the collection.
- Fixed inter-request pauses are used.
- Raw JSON is never modified after saving.
- Machine-specific paths and browser profile settings are kept outside Git.

Note
----
Reddit's public `.json` representation may not expose every possible comment
when a thread is very large or contains "more" placeholders. This script
preserves exactly what the endpoint returns and records unresolved `more`
nodes in the raw files. It does not attempt to bypass or expand them through
undocumented/private methods.
"""

#%%
from __future__ import annotations

import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


# ============================================================
# 1. SETTINGS
# ============================================================

# Repository-local data directories.
# Raw/interim data should remain local and gitignored.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_DIR = (
    PROJECT_ROOT
    / "data"
)

PARENT_DIR = (
    BASE_DIR
    / "raw"
    / "reddit"
    / "parent_posts"
)

OUTPUT_DIR = (
    BASE_DIR
    / "interim"
    / "reddit"
    / "raw_json_audit"
)

RAW_JSON_DIR = (
    OUTPUT_DIR
    / "raw_reddit_json"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RAW_JSON_DIR.mkdir(
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

# Optional local Firefox profile.
# Keep the real machine-specific path outside Git.
FIREFOX_PROFILE_PATH = os.environ.get(
    "REDDIT_FIREFOX_PROFILE",
    "",
)

# Parent-post temporal window for the interim comment audit.
#
# We prioritize posts created inside the project window and keep a small
# look-back buffer before PROJECT_START because a slightly older parent post
# may still receive comments after PROJECT_START.
#
# Set to 0 if you want parent posts strictly inside the project window.
PARENT_LOOKBACK_DAYS = 14

# Fixed pause between successful JSON page loads.
JSON_PAGE_PAUSE_SECONDS = 4.0

JSON_PAGE_TIMEOUT_SECONDS = 25

# Existing JSON = already collected successfully -> skip.
RESUME_EXISTING_JSON = True

# Set to an integer for a small test, e.g. 20.
# None = process every eligible parent URL.
MAX_POSTS: int | None = None

MASTER_PARENT_FILE = (
    OUTPUT_DIR
    / "master_parent_posts_dedup.csv"
)

FETCH_LOG_FILE = (
    OUTPUT_DIR
    / "raw_json_fetch_log.csv"
)

COMMENTS_FILE = (
    OUTPUT_DIR
    / "comments_from_raw_json.csv"
)

COMMENTS_WINDOW_FILE = (
    OUTPUT_DIR
    / "comments_project_window.csv"
)

COVERAGE_FILE = (
    OUTPUT_DIR
    / "weekly_coverage_W01_W21.csv"
)


# ============================================================
# 2. DATE HELPERS
# ============================================================

def parse_datetime(
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


def unix_to_iso(
    value: Any,
) -> str:

    try:
        return datetime.fromtimestamp(
            float(value),
            tz=timezone.utc,
        ).isoformat()

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return ""


def week_label(
    created_at_utc: str,
) -> str:

    parsed = parse_datetime(
        created_at_utc
    )

    if parsed is None:
        return ""

    if not (
        PROJECT_START
        <= parsed
        <= PROJECT_END
    ):
        return ""

    day_index = (
        parsed.date()
        - PROJECT_START.date()
    ).days

    week_number = (
        day_index // 7
    ) + 1

    if not (
        1
        <= week_number
        <= 21
    ):
        return ""

    return f"W{week_number:02d}"


# ============================================================
# 3. STRING / PROVENANCE HELPERS
# ============================================================

def split_pipe_values(
    value: str | None,
) -> list[str]:

    if not value:
        return []

    return [
        item.strip()
        for item in value.split("|")
        if item.strip()
    ]


def join_sorted(
    values: set[str],
) -> str:

    return " | ".join(
        sorted(
            value
            for value in values
            if value
        )
    )


# ============================================================
# 4. MERGE + GLOBAL DEDUP PARENT POSTS
# ============================================================

PARENT_FIELDS = [
    "post_id",
    "subreddit",
    "title",
    "url",
    "created_at_utc",
    "matched_query_ids",
    "matched_source_ids",
    "matched_search_terms",
    "source_statuses",
    "discovery_routes",
    "languages",
    "risks",
    "eligible_for_json_collection",
]


def find_parent_files() -> list[Path]:

    return sorted(
        PARENT_DIR.glob(
            "*_reddit_parent_posts.csv"
        )
    )


def merge_parent_posts() -> list[
    dict[str, str]
]:

    files = find_parent_files()

    if not files:
        raise FileNotFoundError(
            "No parent-post CSV files found in "
            f"{PARENT_DIR}"
        )

    merged: dict[
        str,
        dict[str, Any],
    ] = {}

    for input_file in files:

        print(
            f"Reading: "
            f"{input_file.name}"
        )

        with input_file.open(
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
                    or row.get(
                        "platform_content_id"
                    )
                    or ""
                ).strip()

                if not post_id:
                    continue

                if post_id not in merged:

                    merged[
                        post_id
                    ] = {
                        "post_id": post_id,
                        "subreddit": (
                            row.get(
                                "subreddit"
                            )
                            or ""
                        ),
                        "title": (
                            row.get(
                                "title"
                            )
                            or ""
                        ),
                        "url": (
                            row.get(
                                "url"
                            )
                            or ""
                        ),
                        "created_at_utc": (
                            row.get(
                                "created_at_utc"
                            )
                            or ""
                        ),
                        "_query_ids": set(),
                        "_source_ids": set(),
                        "_search_terms": set(),
                        "_source_statuses": set(),
                        "_routes": set(),
                        "_languages": set(),
                        "_risks": set(),
                    }

                record = merged[
                    post_id
                ]

                simple_sets = [
                    (
                        "query_id",
                        "_query_ids",
                    ),
                    (
                        "source_id",
                        "_source_ids",
                    ),
                    (
                        "source_status",
                        "_source_statuses",
                    ),
                    (
                        "discovery_route",
                        "_routes",
                    ),
                    (
                        "lang",
                        "_languages",
                    ),
                    (
                        "risk",
                        "_risks",
                    ),
                ]

                for source_field, set_field in simple_sets:

                    value = (
                        row.get(
                            source_field
                        )
                        or ""
                    ).strip()

                    if value:
                        record[
                            set_field
                        ].add(
                            value
                        )

                for term in split_pipe_values(
                    row.get(
                        "matched_search_terms"
                    )
                ):
                    record[
                        "_search_terms"
                    ].add(
                        term
                    )

                for field in (
                    "subreddit",
                    "title",
                    "url",
                    "created_at_utc",
                ):

                    if (
                        not record[
                            field
                        ]
                        and row.get(
                            field
                        )
                    ):
                        record[
                            field
                        ] = row[
                            field
                        ]

    output = []

    for record in merged.values():

        post_time = parse_datetime(
            record[
                "created_at_utc"
            ]
        )

        parent_window_start = (
            PROJECT_START
            - timedelta(
                days=PARENT_LOOKBACK_DAYS
            )
        )

        # Interim audit optimization:
        #   - posts after PROJECT_END cannot contain project-window comments;
        #   - very old parent posts are excluded from this interim audit;
        #   - a small pre-project buffer is retained.
        eligible = (
            post_time is None
            or (
                parent_window_start
                <= post_time
                <= PROJECT_END
            )
        )

        output.append(
            {
                "post_id": (
                    record[
                        "post_id"
                    ]
                ),
                "subreddit": (
                    record[
                        "subreddit"
                    ]
                ),
                "title": (
                    record[
                        "title"
                    ]
                ),
                "url": (
                    record[
                        "url"
                    ]
                ),
                "created_at_utc": (
                    record[
                        "created_at_utc"
                    ]
                ),
                "matched_query_ids": (
                    join_sorted(
                        record[
                            "_query_ids"
                        ]
                    )
                ),
                "matched_source_ids": (
                    join_sorted(
                        record[
                            "_source_ids"
                        ]
                    )
                ),
                "matched_search_terms": (
                    join_sorted(
                        record[
                            "_search_terms"
                        ]
                    )
                ),
                "source_statuses": (
                    join_sorted(
                        record[
                            "_source_statuses"
                        ]
                    )
                ),
                "discovery_routes": (
                    join_sorted(
                        record[
                            "_routes"
                        ]
                    )
                ),
                "languages": (
                    join_sorted(
                        record[
                            "_languages"
                        ]
                    )
                ),
                "risks": (
                    join_sorted(
                        record[
                            "_risks"
                        ]
                    )
                ),
                "eligible_for_json_collection": (
                    str(
                        eligible
                    )
                ),
            }
        )

    def parent_sort_key(
        row: dict[str, str],
    ):
        dt = parse_datetime(
            row["created_at_utc"]
        )

        if dt is None:
            return (
                2,
                0.0,
                row["post_id"],
            )

        # First: posts inside PROJECT_START..PROJECT_END
        if (
            PROJECT_START
            <= dt
            <= PROJECT_END
        ):
            group = 0
        else:
            # Second: pre-project buffer posts
            group = 1

        # Newer first inside each group.
        return (
            group,
            -dt.timestamp(),
            row["post_id"],
        )

    output.sort(
        key=parent_sort_key
    )

    with MASTER_PARENT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=PARENT_FIELDS,
        )

        writer.writeheader()
        writer.writerows(
            output
        )

    eligible_count = sum(
        1
        for row in output
        if row[
            "eligible_for_json_collection"
        ] == "True"
    )

    skipped_count = (
        len(output)
        - eligible_count
    )

    unknown_dates = sum(
        1
        for row in output
        if not parse_datetime(
            row[
                "created_at_utc"
            ]
        )
    )

    print(
        "\nParent merge summary"
    )
    print(
        f"Unique parent posts: "
        f"{len(output)}"
    )
    print(
        f"Eligible for JSON collection: "
        f"{eligible_count}"
    )
    print(
        "Skipped because parent post is outside "
        f"{PARENT_LOOKBACK_DAYS}-day lookback + project window: "
        f"{skipped_count}"
    )
    print(
        "Unknown post dates kept "
        f"for safety: {unknown_dates}"
    )

    return output


# ============================================================
# 5. REDDIT JSON URL
# ============================================================

def build_reddit_json_url(
    post_url: str,
) -> str:

    parts = urlsplit(
        post_url
    )

    path = parts.path.rstrip(
        "/"
    )

    # Avoid double-appending.
    if not path.endswith(
        ".json"
    ):
        path = (
            path
            + ".json"
        )

    return urlunsplit(
        (
            "https",
            "www.reddit.com",
            path,
            "",
            "",
        )
    )


def raw_json_path(
    post_id: str,
) -> Path:

    return (
        RAW_JSON_DIR
        / f"{post_id}.json"
    )


# ============================================================
# 6. FETCH LOG
# ============================================================

FETCH_LOG_FIELDS = [
    "post_id",
    "subreddit",
    "post_created_at_utc",
    "post_url",
    "json_url",
    "status",
    "http_status",
    "started_at_utc",
    "finished_at_utc",
    "raw_json_file",
    "message",
]


def append_fetch_log(
    row: dict[str, Any],
) -> None:

    write_header = (
        not FETCH_LOG_FILE.exists()
    )

    with FETCH_LOG_FILE.open(
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FETCH_LOG_FIELDS,
            extrasaction="ignore",
        )

        if write_header:
            writer.writeheader()

        writer.writerow(
            row
        )


# ============================================================
# 7. RAW JSON FETCH THROUGH FIREFOX
# ============================================================

def visible_json_page_blocked(
    driver: webdriver.Firefox,
) -> bool:

    try:
        body_text = (
            driver.find_element(
                By.TAG_NAME,
                "body",
            )
            .text
            .lower()
        )
    except Exception:
        return False

    phrases = (
        "you've been blocked",
        "you have been blocked",
        "too many requests",
        "access denied",
        "complete the captcha",
        "verify you are human",
    )

    return any(
        phrase in body_text
        for phrase in phrases
    )


def read_json_text_from_firefox(
    driver: webdriver.Firefox,
) -> str:

    def page_has_json(d):
        try:
            text = (
                d.find_element(
                    By.TAG_NAME,
                    "body",
                )
                .text
                .strip()
            )

            return (
                text.startswith("[")
                or text.startswith("{")
            )
        except Exception:
            return False

    WebDriverWait(
        driver,
        JSON_PAGE_TIMEOUT_SECONDS,
    ).until(
        page_has_json
    )

    return (
        driver.find_element(
            By.TAG_NAME,
            "body",
        )
        .text
        .strip()
    )


def fetch_and_save_raw_json(
    driver: webdriver.Firefox,
    parent: dict[str, str],
) -> tuple[str, bool]:

    """
    Open the public Reddit .json URL directly in Firefox.

    No cookie transfer to requests is used. If the browser itself can open the
    JSON page, the returned structured JSON is saved locally.

    Returns:
        (status, should_continue_collection)
    """

    post_id = parent["post_id"]
    output_file = raw_json_path(
        post_id
    )

    if (
        RESUME_EXISTING_JSON
        and output_file.exists()
    ):
        return (
            "skip_existing_json",
            True,
        )

    json_url = build_reddit_json_url(
        parent["url"]
    )

    started_at = datetime.now(
        timezone.utc
    )

    try:

        driver.get(
            json_url
        )

        if visible_json_page_blocked(
            driver
        ):
            status = (
                "browser_block_or_captcha"
            )

            append_fetch_log(
                {
                    "post_id": post_id,
                    "subreddit": parent["subreddit"],
                    "post_created_at_utc": parent["created_at_utc"],
                    "post_url": parent["url"],
                    "json_url": json_url,
                    "status": status,
                    "http_status": "",
                    "started_at_utc": started_at.isoformat(),
                    "finished_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "raw_json_file": "",
                    "message": (
                        "Visible block/CAPTCHA/access-denied "
                        "message detected in Firefox."
                    ),
                }
            )

            return (
                status,
                False,
            )

        raw_text = read_json_text_from_firefox(
            driver
        )

        try:
            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError as error:
            status = "invalid_json"

            append_fetch_log(
                {
                    "post_id": post_id,
                    "subreddit": parent["subreddit"],
                    "post_created_at_utc": parent["created_at_utc"],
                    "post_url": parent["url"],
                    "json_url": json_url,
                    "status": status,
                    "http_status": "",
                    "started_at_utc": started_at.isoformat(),
                    "finished_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "raw_json_file": "",
                    "message": (
                        f"Firefox page was not parseable JSON: {error}"
                    ),
                }
            )

            return (
                status,
                True,
            )

        # Save structured Reddit JSON. Formatting may differ from the browser,
        # but the returned JSON structure/content is preserved.
        temporary_file = (
            output_file.with_suffix(
                ".json.tmp"
            )
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temporary_file,
            output_file,
        )

        status = "saved_raw_json"

        append_fetch_log(
            {
                "post_id": post_id,
                "subreddit": parent["subreddit"],
                "post_created_at_utc": parent["created_at_utc"],
                "post_url": parent["url"],
                "json_url": json_url,
                "status": status,
                "http_status": "",
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "raw_json_file": str(
                    output_file
                ),
                "message": "",
            }
        )

        return (
            status,
            True,
        )

    except TimeoutException as error:

        status = "json_page_timeout"

        append_fetch_log(
            {
                "post_id": post_id,
                "subreddit": parent["subreddit"],
                "post_created_at_utc": parent["created_at_utc"],
                "post_url": parent["url"],
                "json_url": json_url,
                "status": status,
                "http_status": "",
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "raw_json_file": "",
                "message": str(
                    error
                ),
            }
        )

        return (
            status,
            True,
        )

    except WebDriverException as error:

        status = "webdriver_error"

        append_fetch_log(
            {
                "post_id": post_id,
                "subreddit": parent["subreddit"],
                "post_created_at_utc": parent["created_at_utc"],
                "post_url": parent["url"],
                "json_url": json_url,
                "status": status,
                "http_status": "",
                "started_at_utc": started_at.isoformat(),
                "finished_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "raw_json_file": "",
                "message": str(
                    error
                ),
            }
        )

        return (
            status,
            True,
        )


def collect_raw_json(
    parents: list[
        dict[str, str]
    ],
) -> None:

    eligible_parents = [
        parent
        for parent in parents
        if parent[
            "eligible_for_json_collection"
        ] == "True"
    ]

    if MAX_POSTS is not None:
        eligible_parents = (
            eligible_parents[
                :MAX_POSTS
            ]
        )

    print(
        "\n"
        + "=" * 88
    )
    print(
        "RAW REDDIT JSON COLLECTION VIA FIREFOX"
    )
    print(
        "=" * 88
    )
    print(
        f"Eligible posts: "
        f"{len(eligible_parents)}"
    )
    print(
        f"Pause between JSON pages: "
        f"{JSON_PAGE_PAUSE_SECONDS}s"
    )
    print(
        "Priority: project-window parent posts first, "
        "then pre-project buffer posts."
    )

    options = webdriver.FirefoxOptions()

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

        for index, parent in enumerate(
            eligible_parents,
            start=1,
        ):

            post_id = parent[
                "post_id"
            ]

            if (
                RESUME_EXISTING_JSON
                and raw_json_path(
                    post_id
                ).exists()
            ):

                print(
                    f"[{index}/"
                    f"{len(eligible_parents)}] "
                    f"SKIP existing JSON | "
                    f"{post_id}"
                )

                continue

            print(
                f"\n[{index}/"
                f"{len(eligible_parents)}] "
                f"{post_id} | "
                f"r/{parent['subreddit']}"
            )

            print(
                f"Post date: "
                f"{parent['created_at_utc']}"
            )

            print(
                f"JSON URL: "
                f"{build_reddit_json_url(parent['url'])}"
            )

            status, should_continue = (
                fetch_and_save_raw_json(
                    driver,
                    parent,
                )
            )

            print(
                f"Status: {status}"
            )

            if not should_continue:

                print(
                    "\nStopping this run because the browser "
                    "shows an access restriction."
                )

                break

            if status == "saved_raw_json":

                time.sleep(
                    JSON_PAGE_PAUSE_SECONDS
                )

    finally:

        print(
            "\nClosing Firefox."
        )

        driver.quit()


# ============================================================
# 8. OFFLINE RAW JSON PARSER
# ============================================================

COMMENT_FIELDS = [
    "comment_id",
    "post_id",
    "subreddit",
    "author",
    "comment",
    "comment_created_at_utc",
    "score",
    "depth",
    "parent_id",
    "is_top_level",
    "matched_query_ids",
    "matched_source_ids",
    "matched_search_terms",
    "raw_json_file",
]


def parent_lookup(
    parents: list[
        dict[str, str]
    ],
) -> dict[
    str,
    dict[str, str],
]:

    return {
        parent[
            "post_id"
        ]: parent
        for parent in parents
    }


def walk_comment_children(
    children: list[dict[str, Any]],
    parent: dict[str, str],
    raw_file: Path,
    output: list[
        dict[str, Any]
    ],
) -> None:

    for child in children:

        if not isinstance(
            child,
            dict,
        ):
            continue

        kind = child.get(
            "kind"
        )

        data = (
            child.get(
                "data"
            )
            or {}
        )

        # t1 = comment.
        if kind == "t1":

            comment_id = (
                data.get(
                    "id"
                )
                or ""
            )

            depth = (
                data.get(
                    "depth"
                )
            )

            try:
                depth_int = int(
                    depth
                )
            except (
                TypeError,
                ValueError,
            ):
                depth_int = 0

            output.append(
                {
                    "comment_id": comment_id,
                    "post_id": parent[
                        "post_id"
                    ],
                    "subreddit": (
                        data.get(
                            "subreddit"
                        )
                        or parent[
                            "subreddit"
                        ]
                    ),
                    "author": (
                        data.get(
                            "author"
                        )
                        or ""
                    ),
                    "comment": (
                        data.get(
                            "body"
                        )
                        or ""
                    ),
                    "comment_created_at_utc": (
                        unix_to_iso(
                            data.get(
                                "created_utc"
                            )
                        )
                    ),
                    "score": (
                        data.get(
                            "score"
                        )
                    ),
                    "depth": (
                        depth_int
                    ),
                    "parent_id": (
                        data.get(
                            "parent_id"
                        )
                        or ""
                    ),
                    "is_top_level": (
                        depth_int == 0
                    ),
                    "matched_query_ids": (
                        parent[
                            "matched_query_ids"
                        ]
                    ),
                    "matched_source_ids": (
                        parent[
                            "matched_source_ids"
                        ]
                    ),
                    "matched_search_terms": (
                        parent[
                            "matched_search_terms"
                        ]
                    ),
                    "raw_json_file": str(
                        raw_file
                    ),
                }
            )

            replies = data.get(
                "replies"
            )

            if isinstance(
                replies,
                dict,
            ):

                reply_children = (
                    replies
                    .get(
                        "data",
                        {}
                    )
                    .get(
                        "children",
                        []
                    )
                )

                walk_comment_children(
                    reply_children,
                    parent,
                    raw_file,
                    output,
                )

        # kind == "more" is preserved in raw JSON but not expanded here.


def parse_one_raw_json(
    raw_file: Path,
    parent: dict[str, str],
) -> list[
    dict[str, Any]
]:

    try:

        data = json.loads(
            raw_file.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:

        print(
            f"Could not parse "
            f"{raw_file.name}: "
            f"{error}"
        )

        return []

    if not (
        isinstance(
            data,
            list,
        )
        and len(
            data
        ) >= 2
    ):
        return []

    try:

        comment_children = (
            data[1]
            ["data"]
            ["children"]
        )

    except (
        KeyError,
        TypeError,
        IndexError,
    ):
        return []

    comments: list[
        dict[str, Any]
    ] = []

    walk_comment_children(
        comment_children,
        parent,
        raw_file,
        comments,
    )

    return comments


def parse_all_raw_json(
    parents: list[
        dict[str, str]
    ],
) -> list[
    dict[str, Any]
]:

    lookup = parent_lookup(
        parents
    )

    comments: list[
        dict[str, Any]
    ] = []

    for raw_file in sorted(
        RAW_JSON_DIR.glob(
            "*.json"
        )
    ):

        post_id = (
            raw_file.stem
        )

        parent = lookup.get(
            post_id
        )

        if parent is None:
            continue

        comments.extend(
            parse_one_raw_json(
                raw_file,
                parent,
            )
        )

    # Defensive dedup by Reddit comment id.
    deduped: dict[
        str,
        dict[str, Any],
    ] = {}

    fallback_counter = 0

    for comment in comments:

        comment_id = (
            comment.get(
                "comment_id"
            )
            or ""
        )

        if comment_id:
            key = comment_id

        else:
            fallback_counter += 1
            key = (
                f"missing_id_"
                f"{fallback_counter}"
            )

        deduped[
            key
        ] = comment

    return list(
        deduped.values()
    )


def write_comments_csv(
    comments: list[
        dict[str, Any]
    ],
    output_file: Path,
    include_week: bool = False,
) -> None:

    fieldnames = list(
        COMMENT_FIELDS
    )

    if include_week:
        fieldnames.append(
            "week"
        )

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(
            comments
        )


# ============================================================
# 9. PROJECT WINDOW + COVERAGE
# ============================================================

COVERAGE_FIELDS = [
    "Week",
    "Start UTC",
    "End UTC",
    "Comments",
    "Unique Posts",
    "Unique Users",
    "Unique Subreddits",
    "Top-level Comments",
    "Replies",
    "Status",
]


def filter_comments_to_window(
    comments: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:

    output = []

    for comment in comments:

        week = week_label(
            comment[
                "comment_created_at_utc"
            ]
        )

        if not week:
            continue

        row = dict(
            comment
        )

        row[
            "week"
        ] = week

        output.append(
            row
        )

    return output


def build_coverage(
    comments: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:

    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(
        list
    )

    for comment in comments:

        grouped[
            comment[
                "week"
            ]
        ].append(
            comment
        )

    nonzero = sorted(
        len(
            grouped[
                f"W{i:02d}"
            ]
        )
        for i in range(
            1,
            22,
        )
        if len(
            grouped[
                f"W{i:02d}"
            ]
        ) > 0
    )

    if nonzero:

        n = len(
            nonzero
        )

        if n % 2:
            median_count = (
                nonzero[
                    n // 2
                ]
            )
        else:
            median_count = (
                nonzero[
                    n // 2 - 1
                ]
                + nonzero[
                    n // 2
                ]
            ) / 2

    else:
        median_count = 0

    low_threshold = (
        median_count
        * 0.25
    )

    rows = []

    for i in range(
        1,
        22,
    ):

        week = f"W{i:02d}"

        rows_week = (
            grouped[
                week
            ]
        )

        start = (
            PROJECT_START
            + timedelta(
                days=(
                    i - 1
                ) * 7
            )
        )

        end = min(
            start
            + timedelta(
                days=7
            )
            - timedelta(
                microseconds=1
            ),
            PROJECT_END,
        )

        comment_count = len(
            rows_week
        )

        unique_posts = {
            row[
                "post_id"
            ]
            for row in rows_week
            if row.get(
                "post_id"
            )
        }

        unique_users = {
            row[
                "author"
            ]
            for row in rows_week
            if row.get(
                "author"
            )
            and row[
                "author"
            ] not in {
                "[deleted]",
                "deleted",
            }
        }

        unique_subreddits = {
            row[
                "subreddit"
            ]
            for row in rows_week
            if row.get(
                "subreddit"
            )
        }

        top_level = sum(
            1
            for row in rows_week
            if row[
                "is_top_level"
            ]
        )

        replies = (
            comment_count
            - top_level
        )

        if comment_count == 0:
            status = "EMPTY"

        elif (
            median_count > 0
            and comment_count
            < low_threshold
        ):
            status = "LOW"

        else:
            status = "OK"

        rows.append(
            {
                "Week": week,
                "Start UTC": (
                    start.isoformat()
                ),
                "End UTC": (
                    end.isoformat()
                ),
                "Comments": (
                    comment_count
                ),
                "Unique Posts": (
                    len(
                        unique_posts
                    )
                ),
                "Unique Users": (
                    len(
                        unique_users
                    )
                ),
                "Unique Subreddits": (
                    len(
                        unique_subreddits
                    )
                ),
                "Top-level Comments": (
                    top_level
                ),
                "Replies": (
                    replies
                ),
                "Status": status,
            }
        )

    return rows


def write_coverage(
    rows: list[
        dict[str, Any]
    ],
) -> None:

    with COVERAGE_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=COVERAGE_FIELDS,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def print_coverage(
    rows: list[
        dict[str, Any]
    ],
) -> None:

    print(
        "\n"
        + "=" * 95
    )

    print(
        "WEEKLY COVERAGE FROM SAVED RAW JSON"
    )

    print(
        "=" * 95
    )

    print(
        f"{'Week':<6}"
        f"{'Comments':>10}"
        f"{'Posts':>10}"
        f"{'Users':>10}"
        f"{'Subs':>10}"
        f"{'Top':>10}"
        f"{'Replies':>10}"
        f"{'Status':>12}"
    )

    print(
        "-" * 95
    )

    for row in rows:

        print(
            f"{row['Week']:<6}"
            f"{row['Comments']:>10}"
            f"{row['Unique Posts']:>10}"
            f"{row['Unique Users']:>10}"
            f"{row['Unique Subreddits']:>10}"
            f"{row['Top-level Comments']:>10}"
            f"{row['Replies']:>10}"
            f"{row['Status']:>12}"
        )


# ============================================================
# 10. OFFLINE AUDIT
# ============================================================

def rebuild_offline_outputs(
    parents: list[
        dict[str, str]
    ],
) -> None:

    comments = (
        parse_all_raw_json(
            parents
        )
    )

    write_comments_csv(
        comments,
        COMMENTS_FILE,
        include_week=False,
    )

    window_comments = (
        filter_comments_to_window(
            comments
        )
    )

    write_comments_csv(
        window_comments,
        COMMENTS_WINDOW_FILE,
        include_week=True,
    )

    coverage = (
        build_coverage(
            window_comments
        )
    )

    write_coverage(
        coverage
    )

    print_coverage(
        coverage
    )

    print(
        "\n"
        + "=" * 88
    )

    print(
        "OFFLINE OUTPUT SUMMARY"
    )

    print(
        "=" * 88
    )

    print(
        f"Raw JSON files: "
        f"{len(list(RAW_JSON_DIR.glob('*.json')))}"
    )

    print(
        f"Parsed comments: "
        f"{len(comments)}"
    )

    print(
        "Comments inside project window: "
        f"{len(window_comments)}"
    )

    print(
        f"Comments CSV: "
        f"{COMMENTS_FILE}"
    )

    print(
        f"Window comments CSV: "
        f"{COMMENTS_WINDOW_FILE}"
    )

    print(
        f"Coverage CSV: "
        f"{COVERAGE_FILE}"
    )


# ============================================================
# 11. MAIN
# ============================================================

def main() -> None:

    print(
        "\n"
        + "=" * 88
    )

    print(
        "REDDIT RAW JSON + OFFLINE COVERAGE PIPELINE"
    )

    print(
        "=" * 88
    )

    parents = (
        merge_parent_posts()
    )

    collect_raw_json(
        parents
    )

    print(
        "\nParsing whatever raw JSON "
        "has been saved so far..."
    )

    rebuild_offline_outputs(
        parents
    )


if __name__ == "__main__":
    main()

# %%
