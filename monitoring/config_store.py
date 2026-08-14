import json
import sqlite3
from settings import CONTROL_DB

DEFAULTS = {
    # Generic / secrets
    "REDDIT_FIREFOX_PROFILE": "",
    "YOUTUBE_API_KEY": "",
    "AUTHOR_HASH_SALT": "",
    "X_ACCOUNTS_JSON": "",
    "X_OUTPUT_ROOT": "",
    "PROJECT_AUTHOR_SALT": "",
    "FRED_API_KEY": "",
    "FINANCIAL_RUN_ID": "",

    # Reddit discovery (runtime in-memory overrides; source file remains untouched)
    "REDDIT_SKIP_COMPLETED_TERMS": "1",
    "REDDIT_MAX_SCROLLS_PER_SEARCH_TERM": "60",
    "REDDIT_MAX_NO_NEW_ROUNDS": "6",
    "REDDIT_SCROLL_PAUSE_SECONDS": "3.0",
    "REDDIT_BETWEEN_SEARCH_TERM_PAUSE_SECONDS": "8.0",
    "REDDIT_BETWEEN_JOB_PAUSE_SECONDS": "10.0",
    "REDDIT_INITIAL_TIMEOUT_SECONDS": "25",
    "REDDIT_ACTIVE_QUERY_IDS": "",
    "REDDIT_SOURCES_JSON": "",
    "REDDIT_QUERIES_JSON": "",
    # Reddit raw JSON stage
    "REDDIT_JSON_PAGE_PAUSE_SECONDS": "4.0",
    "REDDIT_JSON_PAGE_TIMEOUT_SECONDS": "25",
    "REDDIT_HTTP_PROBE_TIMEOUT_SECONDS": "10",
    "REDDIT_PARENT_LOOKBACK_DAYS": "14",
    "REDDIT_RESUME_EXISTING_JSON": "1",
    "REDDIT_MAX_POSTS": "",

    # YouTube
    "YOUTUBE_DAILY_QUOTA_BUDGET": "8000",
    "YOUTUBE_REGIONS_PER_DAY": "2",
    "YOUTUBE_MAX_VIDEOS_PER_QUERY": "25",
    "YOUTUBE_MAX_COMMENTS_PER_VIDEO": "300",
    "YOUTUBE_COMMENT_POOL_MULTIPLIER": "5",
    "YOUTUBE_RANDOM_SEED": "42",
    "YOUTUBE_ACTIVE_QUERY_IDS": "",
    "YOUTUBE_REGION_CODES": "",
    "YOUTUBE_EXPLICIT_VIDEO_IDS": "",

    # X / Twitter
    "X_MAX_WORKERS": "3",
    "X_MAX_SCROLLS_PER_SLICE": "4",
    "X_MAX_SCROLLS_MIN_DAY": "9",
    "X_NO_NEW_SCROLL_LIMIT": "2",
    "X_PAGE_LOAD_TIMEOUT_SECONDS": "45",
    "X_READY_TIMEOUT_SECONDS": "28",
    "X_STARTUP_STAGGER_SECONDS": "8",
    "X_STARTUP_MAX_ATTEMPTS": "3",
    "X_STARTUP_RETRY_SECONDS": "12",
    "X_SCROLL_MIN_DELAY_SECONDS": "1.8",
    "X_SCROLL_MAX_DELAY_SECONDS": "3.8",
    "X_JOB_BACKOFF_SECONDS": "30",
    "X_MAX_JOB_ATTEMPTS": "3",
    "X_BACKFILL_MIN_DELAY_SECONDS": "3.0",
    "X_BACKFILL_MAX_DELAY_SECONDS": "6.0",
    "X_BACKFILL_READY_TIMEOUT_SECONDS": "20",
}

SECRET_KEYS = {
    "YOUTUBE_API_KEY", "AUTHOR_HASH_SALT", "X_ACCOUNTS_JSON",
    "PROJECT_AUTHOR_SALT", "FRED_API_KEY",
}


def connect():
    conn = sqlite3.connect(CONTROL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runtime_config ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '', "
        "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    for key, value in DEFAULTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO runtime_config(key,value) VALUES(?,?)",
            (key, value),
        )
    conn.commit()
    return conn


def get_all(mask_secrets=False):
    with connect() as conn:
        values = {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM runtime_config")}
    for k, v in DEFAULTS.items():
        values.setdefault(k, v)
    if mask_secrets:
        return {k: ("••••••••" if k in SECRET_KEYS and v else v) for k, v in values.items()}
    return values


def get_value(key, default=""):
    return get_all(False).get(key, default)


def set_values(values):
    with connect() as conn:
        for key, value in values.items():
            if key not in DEFAULTS:
                continue
            value = "" if value is None else str(value)
            # Blank secret field means keep current secret; explicit clear uses clear_key.
            if key in SECRET_KEYS and value == "":
                continue
            conn.execute(
                "INSERT INTO runtime_config(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (key, value),
            )
        conn.commit()


def clear_key(key):
    if key not in DEFAULTS:
        return
    with connect() as conn:
        conn.execute(
            "UPDATE runtime_config SET value='', updated_at=CURRENT_TIMESTAMP WHERE key=?",
            (key,),
        )
        conn.commit()


def get_json(key, default):
    raw = get_value(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def set_json(key, value):
    if key not in DEFAULTS:
        raise KeyError(key)
    set_values({key: json.dumps(value, ensure_ascii=False)})
