"""External runtime adapter for the untouched group pipeline.

This file intentionally lives outside repo/. It imports the original collector,
applies Control Center values to that module's in-memory globals, then calls the
original functions. No source/config file in repo/ is written or patched.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

MONITORING_ROOT = Path(__file__).resolve().parent
PIPELINE_ROOT = MONITORING_ROOT.parent
INGESTION_ROOT = PIPELINE_ROOT / "src" / "ingestion"
for p in (str(INGESTION_ROOT), str(PIPELINE_ROOT), str(MONITORING_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from config_store import get_all, get_json


def _int(cfg, key, default):
    try: return int(str(cfg.get(key, default)).strip())
    except Exception: return int(default)


def _float(cfg, key, default):
    try: return float(str(cfg.get(key, default)).strip())
    except Exception: return float(default)


def _bool(cfg, key, default=True):
    v = str(cfg.get(key, "1" if default else "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _csv(cfg, key):
    raw = str(cfg.get(key, "") or "")
    return [x.strip() for x in raw.replace("\n", ",").split(",") if x.strip()]


def _log(*parts):
    print(*parts, flush=True)


def _log_effective(name, values):
    _log("\n" + "=" * 72)
    _log(f"CONTROL CENTER RUNTIME ADAPTER — {name}")
    _log("Original pipeline files: UNCHANGED")
    for k, v in values.items():
        if any(s in k.upper() for s in ("KEY", "SALT", "ACCOUNTS")):
            v = "configured" if v else "not configured"
        _log(f"{k}: {v}")
    _log("=" * 72 + "\n")


def run_reddit_discovery(cfg):
    import os
    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")

    if custom_topic:
        print(f"[REDDIT][OVERRIDE] Custom Topic Detected: '{custom_topic}'")
        custom_query_obj = [{
                "query_id": "RQ-CUSTOM-001",
                "family": "Custom Run",
                "lang": os.getenv("SCRAPER_LANG", "en"),
                "logical_query": custom_topic,
                "risk": "low",
                "entity_anchor": "",
                "discovery_route": "query_search",
                "source_ids": ["RD-001"],
                "search_terms": [custom_topic],
                "enabled": True
            }]

        import src.ingestion.reddit_parent_post_collector as r_collector
        if hasattr(r_collector, 'QUERIES'):
            r_collector.QUERIES = custom_query_obj
        if hasattr(r_collector, 'ACTIVE_QUERIES'):
            r_collector.ACTIVE_QUERIES = custom_query_obj
        if hasattr(r_collector, 'SELECTED_QUERIES'):
            r_collector.SELECTED_QUERIES = custom_query_obj
    import src.ingestion.reddit_parent_post_collector as m
    m.SKIP_COMPLETED_TERMS = _bool(cfg, "REDDIT_SKIP_COMPLETED_TERMS", True)
    m.MAX_SCROLLS_PER_SEARCH_TERM = _int(cfg, "REDDIT_MAX_SCROLLS_PER_SEARCH_TERM", 60)
    m.MAX_NO_NEW_ROUNDS = _int(cfg, "REDDIT_MAX_NO_NEW_ROUNDS", 6)
    m.SCROLL_PAUSE_SECONDS = _float(cfg, "REDDIT_SCROLL_PAUSE_SECONDS", 3.0)
    m.BETWEEN_SEARCH_TERM_PAUSE_SECONDS = _float(cfg, "REDDIT_BETWEEN_SEARCH_TERM_PAUSE_SECONDS", 8.0)
    m.BETWEEN_JOB_PAUSE_SECONDS = _float(cfg, "REDDIT_BETWEEN_JOB_PAUSE_SECONDS", 10.0)
    m.INITIAL_TIMEOUT_SECONDS = _int(cfg, "REDDIT_INITIAL_TIMEOUT_SECONDS", 25)
    ids = _csv(cfg, "REDDIT_ACTIVE_QUERY_IDS")
    m.ACTIVE_QUERY_IDS = set(ids) if ids else None
    sources = get_json("REDDIT_SOURCES_JSON", None)
    queries = get_json("REDDIT_QUERIES_JSON", None)
    if isinstance(sources, dict): m.SOURCE_REGISTRY = sources
    if isinstance(queries, list): m.QUERY_REGISTRY = queries

    # Detailed, real-time audit of every newly checkpointed parent post.
    seen_by_file: dict[str, set[str]] = {}
    original_load = m.load_existing_records
    original_save = m.save_checkpoint

    def load_existing_records_logged(output_file):
        records = original_load(output_file)
        seen_by_file[str(output_file)] = set(records)
        _log(f"[REDDIT][DISCOVERY][CHECKPOINT_LOAD] file={output_file} existing_posts={len(records)}")
        return records

    def save_checkpoint_logged(output_file, records_by_post_id):
        key = str(output_file)
        before = seen_by_file.setdefault(key, set())
        original_save(output_file, records_by_post_id)
        new_ids = [pid for pid in records_by_post_id if pid not in before]
        for pid in new_ids:
            row = records_by_post_id[pid]
            _log(
                "[REDDIT][DISCOVERY][POST_SAVED] "
                f"post_id={pid} subreddit={row.get('subreddit','')} "
                f"query_id={row.get('query_id','')} source_id={row.get('source_id','')} "
                f"created_at={row.get('created_at_utc','')} url={row.get('url','')} "
                f"file={output_file.name}"
            )
        if new_ids:
            _log(f"[REDDIT][DISCOVERY][CHECKPOINT_SAVED] file={output_file} new_posts={len(new_ids)} total_posts={len(records_by_post_id)}")
        before.update(records_by_post_id)

    m.load_existing_records = load_existing_records_logged
    m.save_checkpoint = save_checkpoint_logged

    _log_effective("reddit_discovery", {
        "ACTIVE_QUERY_IDS": ids or "ALL", "SOURCES": len(m.SOURCE_REGISTRY),
        "QUERIES": len(m.QUERY_REGISTRY), "MAX_SCROLLS_PER_SEARCH_TERM": m.MAX_SCROLLS_PER_SEARCH_TERM,
        "MAX_NO_NEW_ROUNDS": m.MAX_NO_NEW_ROUNDS, "SCROLL_PAUSE_SECONDS": m.SCROLL_PAUSE_SECONDS,
        "BETWEEN_SEARCH_TERM_PAUSE_SECONDS": m.BETWEEN_SEARCH_TERM_PAUSE_SECONDS,
        "BETWEEN_JOB_PAUSE_SECONDS": m.BETWEEN_JOB_PAUSE_SECONDS,
        "INITIAL_TIMEOUT_SECONDS": m.INITIAL_TIMEOUT_SECONDS,
    })
    _log("[REDDIT][DISCOVERY][START] Parent-post collector is running. Every new checkpointed post will be logged below.")
    m.main()
    _log("[REDDIT][DISCOVERY][DONE] Parent-post discovery completed. Stage-2 can now read *_reddit_parent_posts.csv files.")


def run_reddit_comments(cfg):
    import src.ingestion.reddit_raw_json_pipeline as m
    m.JSON_PAGE_PAUSE_SECONDS = _float(cfg, "REDDIT_JSON_PAGE_PAUSE_SECONDS", 4.0)
    m.JSON_PAGE_TIMEOUT_SECONDS = _int(cfg, "REDDIT_JSON_PAGE_TIMEOUT_SECONDS", 25)
    m.HTTP_PROBE_TIMEOUT_SECONDS = _int(cfg, "REDDIT_HTTP_PROBE_TIMEOUT_SECONDS", 10)
    m.PARENT_LOOKBACK_DAYS = _int(cfg, "REDDIT_PARENT_LOOKBACK_DAYS", 14)
    m.RESUME_EXISTING_JSON = _bool(cfg, "REDDIT_RESUME_EXISTING_JSON", True)
    raw_max = str(cfg.get("REDDIT_MAX_POSTS", "") or "").strip()
    m.MAX_POSTS = int(raw_max) if raw_max else None

    _log_effective("reddit_comments", {
        "JSON_PAGE_PAUSE_SECONDS": m.JSON_PAGE_PAUSE_SECONDS,
        "JSON_PAGE_TIMEOUT_SECONDS": m.JSON_PAGE_TIMEOUT_SECONDS,
        "HTTP_PROBE_TIMEOUT_SECONDS": m.HTTP_PROBE_TIMEOUT_SECONDS,
        "PARENT_LOOKBACK_DAYS": m.PARENT_LOOKBACK_DAYS,
        "RESUME_EXISTING_JSON": m.RESUME_EXISTING_JSON,
        "MAX_POSTS": m.MAX_POSTS if m.MAX_POSTS is not None else "ALL",
    })

    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")
    if custom_topic:
        parent_files = list(m.PARENT_DIR.glob("RQ-CUSTOM-*.csv"))
    else:
        parent_files = m.find_parent_files()
    _log("\n" + "=" * 88)
    _log("REDDIT STAGE-1 -> STAGE-2 HANDOFF PRECHECK")
    _log("=" * 88)
    _log(f"[REDDIT][HANDOFF] parent_dir={m.PARENT_DIR}")
    _log(f"[REDDIT][HANDOFF] parent_files_found={len(parent_files)}")
    for p in parent_files:
        _log(f"[REDDIT][HANDOFF][INPUT_FILE] {p}")
    if not parent_files:
        _log("[REDDIT][HANDOFF][ERROR] No *_reddit_parent_posts.csv files exist. Run Parent Post Discovery first.")
        raise FileNotFoundError(f"No parent-post CSV files found in {m.PARENT_DIR}")

    # Use the original pipeline merge function exactly once, then continue with
    # its original collect + rebuild functions. This makes the handoff explicit
    # without changing the native pipeline source.
    parents = m.merge_parent_posts()
    eligible = [p for p in parents if p.get("eligible_for_json_collection") == "True"]
    limited = eligible[:m.MAX_POSTS] if m.MAX_POSTS is not None else eligible
    existing_ids = {p.stem for p in m.RAW_JSON_DIR.glob("*.json")}
    pending = [p for p in limited if (not m.RESUME_EXISTING_JSON) or p.get("post_id") not in existing_ids]

    _log(f"[REDDIT][HANDOFF] unique_parent_posts={len(parents)}")
    _log(f"[REDDIT][HANDOFF] eligible_for_json={len(eligible)}")
    _log(f"[REDDIT][HANDOFF] selected_after_MAX_POSTS={len(limited)}")
    _log(f"[REDDIT][HANDOFF] existing_raw_json={len(existing_ids)}")
    _log(f"[REDDIT][HANDOFF] pending_json_fetch={len(pending)}")
    if len(eligible) == 0:
        _log("[REDDIT][HANDOFF][WARNING] Eligible JSON queue is ZERO. The native pipeline only fetches parent posts inside the project window (plus lookback). Check post dates in master_parent_posts_dedup.csv.")
    elif len(pending) == 0 and m.RESUME_EXISTING_JSON:
        _log("[REDDIT][HANDOFF][INFO] No new JSON fetch is pending because every selected eligible post already has a raw JSON file. Disable 'Resume existing JSON' only if you intentionally want to re-fetch them.")

    for i, parent in enumerate(limited, start=1):
        pid = parent.get("post_id", "")
        state = "EXISTING_SKIP" if (m.RESUME_EXISTING_JSON and pid in existing_ids) else "PENDING"
        _log(
            f"[REDDIT][JSON_QUEUE][{i}/{len(limited)}] state={state} post_id={pid} "
            f"created_at={parent.get('created_at_utc','')} json_url={m.build_reddit_json_url(parent.get('url',''))}"
        )

    original_fetch = m.fetch_and_save_raw_json
    original_write_comments = m.write_comments_csv
    original_write_submissions = m.write_submissions_csv

    def fetch_and_save_logged(driver, parent):
        pid = parent.get("post_id", "")
        json_url = m.build_reddit_json_url(parent.get("url", ""))
        _log(f"[REDDIT][JSON_FETCH][START] post_id={pid} json_url={json_url}")
        status, should_continue = original_fetch(driver, parent)
        raw_path = m.raw_json_path(pid)
        _log(
            f"[REDDIT][JSON_FETCH][RESULT] post_id={pid} status={status} "
            f"continue={should_continue} raw_json_file={raw_path if raw_path.exists() else ''}"
        )
        if status == "saved_raw_json" and raw_path.exists():
            try:
                comments, more_stats, submission = m.parse_one_raw_json(raw_path, parent)
                _log(
                    f"[REDDIT][RAW_JSON][SAVED_AND_PARSED] post_id={pid} bytes={raw_path.stat().st_size} "
                    f"comments={len(comments)} more_nodes={more_stats.get('count',0)} submission={'yes' if submission else 'no'}"
                )
                if submission:
                    preview = str(submission.get("selftext") or submission.get("title") or "").replace("\r", " ").replace("\n", " ")[:160]
                    _log(f"[REDDIT][POST][PARSED] post_id={pid} subreddit={submission.get('subreddit','')} title={json.dumps(preview,ensure_ascii=False)}")
                for c in comments:
                    preview = str(c.get("comment") or "").replace("\r", " ").replace("\n", " ")[:180]
                    _log(
                        "[REDDIT][COMMENT][PARSED] "
                        f"comment_id={c.get('comment_id','')} post_id={pid} parent_id={c.get('parent_id','')} "
                        f"depth={c.get('depth','')} created_at={c.get('comment_created_at_utc','')} "
                        f"text={json.dumps(preview,ensure_ascii=False)}"
                    )
            except Exception as e:
                _log(f"[REDDIT][RAW_JSON][PARSE_PREVIEW_ERROR] post_id={pid} error={type(e).__name__}: {e}")
        return status, should_continue

    def write_comments_logged(comments, output_file, include_week=False):
        _log(f"[REDDIT][COMMENTS_CSV][WRITE_START] rows={len(comments)} include_week={include_week} file={output_file}")
        result = original_write_comments(comments, output_file, include_week=include_week)
        try: size = output_file.stat().st_size
        except Exception: size = 0
        _log(f"[REDDIT][COMMENTS_CSV][SAVED] rows={len(comments)} bytes={size} file={output_file}")
        return result

    def write_submissions_logged(rows, output_file):
        _log(f"[REDDIT][SUBMISSIONS_CSV][WRITE_START] rows={len(rows)} file={output_file}")
        result = original_write_submissions(rows, output_file)
        _log(f"[REDDIT][SUBMISSIONS_CSV][SAVED] rows={len(rows)} file={output_file}")
        return result

    m.fetch_and_save_raw_json = fetch_and_save_logged
    m.write_comments_csv = write_comments_logged
    m.write_submissions_csv = write_submissions_logged

    _log("[REDDIT][STAGE2][START] Opening native Raw JSON collector.")
    m.collect_raw_json(parents)
    _log("[REDDIT][STAGE2][RAW_FETCH_DONE] Parsing all raw JSON files into native comment/submission outputs.")
    m.rebuild_offline_outputs(parents)
    _log("[REDDIT][STAGE2][DONE] Raw JSON collection + native offline outputs completed.")


def run_youtube(cfg):
    import src.ingestion.youtube_extract as m
    from types import SimpleNamespace

    m.REGIONS_PER_DAY = _int(cfg, "YOUTUBE_REGIONS_PER_DAY", 2)
    m.MAX_VIDEOS_PER_QUERY = _int(cfg, "YOUTUBE_MAX_VIDEOS_PER_QUERY", 25)
    m.MAX_COMMENTS_PER_VIDEO = _int(cfg, "YOUTUBE_MAX_COMMENTS_PER_VIDEO", 300)
    m.COMMENT_POOL_MULTIPLIER = _int(cfg, "YOUTUBE_COMMENT_POOL_MULTIPLIER", 5)
    m.RANDOM_SEED = _int(cfg, "YOUTUBE_RANDOM_SEED", 42)
    m.COMMENT_POOL_CAP = m.MAX_COMMENTS_PER_VIDEO * m.COMMENT_POOL_MULTIPLIER
    m.COMMENT_FETCH_QUOTA_RESERVE = -(-m.COMMENT_POOL_CAP // 100) * m.checkpoint.QUOTA_COSTS["comment_threads"]
    m.checkpoint.MAX_DAILY_QUOTA = _int(cfg, "YOUTUBE_DAILY_QUOTA_BUDGET", 8000)

    region_lines = str(cfg.get("YOUTUBE_REGION_CODES", "") or "").strip()
    if region_lines:
        parsed = []
        for item in region_lines.replace(";", "\n").splitlines():
            parts = [p.strip() for p in item.split(",") if p.strip()]
            if len(parts) >= 2:
                parsed.append((parts[0], parts[1]))
        if parsed:
            m.REGION_CODES = parsed

    vids = _csv(cfg, "YOUTUBE_EXPLICIT_VIDEO_IDS")
    if vids:
        m.EXPLICIT_VIDEO_IDS = vids


    def _to_rfc3339(date_str, end_of_day=False):
        date_str = str(date_str).strip()
        if "T" in date_str:
            return date_str if date_str.endswith("Z") else date_str + "Z"
        return f"{date_str}T23:59:59Z" if end_of_day else f"{date_str}T00:00:00Z"

    custom_topic = (
        os.getenv("SCRAPER_CUSTOM_TOPIC")
        or str(cfg.get("SCRAPER_CUSTOM_TOPIC", "") or "").strip()
    )

    if custom_topic:
        _log(f"[YOUTUBE][OVERRIDE] Custom Topic Detected: '{custom_topic}'")

        custom_q = SimpleNamespace(
            query_id="YQ-CUSTOM-001",
            query_text=custom_topic,
            language=os.getenv("SCRAPER_LANG", "en"),
        )
        m.query_registry_loader.load_active_queries = lambda *a, **kw: [custom_q]
        m.CHANNEL_REGISTRY = {}
        m.EXPLICIT_VIDEO_IDS = []
        start_date = (
            os.getenv("SCRAPER_START_DATE")
            or str(cfg.get("SCRAPER_START_DATE", "") or "").strip()
        )
        end_date = (
            os.getenv("SCRAPER_END_DATE")
            or str(cfg.get("SCRAPER_END_DATE", "") or "").strip()
        )
        if start_date:
            m.PUBLISHED_AFTER_RFC3339 = _to_rfc3339(start_date, end_of_day=False)
            m.DEFAULT_WATERMARK_ISO   = m.PUBLISHED_AFTER_RFC3339
        if end_date:
            m.PUBLISHED_BEFORE_RFC3339 = _to_rfc3339(end_date, end_of_day=True)

        custom_topic_id = (m.CONFIG.topic_id or "topic") + "__custom"
        m.DATA_DIR               = m.PROJECT_ROOT / "data" / "raw" / custom_topic_id
        m.RESOLVED_CHANNELS_PATH = m.DATA_DIR / "resolved_channels.json"
        m.OUTPUT_JSONL_PATH      = m.DATA_DIR / "youtube_comments_v2.jsonl"
        m.OUTPUT_CSV_PATH        = m.DATA_DIR / "youtube_raw_export.csv"
        m.MANIFEST_PATH          = m.DATA_DIR / "youtube_runs.csv"
        m.SKIPPED_VIDEOS_PATH    = m.DATA_DIR / "youtube_skipped_videos.csv"

        _log(f"[YOUTUBE][OVERRIDE] Isolated DATA_DIR: {m.DATA_DIR}")
        _log(f"[YOUTUBE][OVERRIDE] Window: {m.PUBLISHED_AFTER_RFC3339} -> {m.PUBLISHED_BEFORE_RFC3339}")

    else:
        selected = set(_csv(cfg, "YOUTUBE_ACTIVE_QUERY_IDS"))
        if selected:
            original_loader = m.query_registry_loader.load_active_queries
            m.query_registry_loader.load_active_queries = (
                lambda *a, **kw: [
                    q for q in original_loader(*a, **kw) if q.query_id in selected
                ]
            )

    _log_effective("youtube", {
        "YOUTUBE_API_KEY": bool(m.API_KEY),
        "DAILY_QUOTA": m.checkpoint.MAX_DAILY_QUOTA,
        "REGIONS_PER_DAY": m.REGIONS_PER_DAY,
        "REGION_CODES": m.REGION_CODES,
        "MAX_VIDEOS_PER_QUERY": m.MAX_VIDEOS_PER_QUERY,
        "MAX_COMMENTS_PER_VIDEO": m.MAX_COMMENTS_PER_VIDEO,
        "COMMENT_POOL_MULTIPLIER": m.COMMENT_POOL_MULTIPLIER,
        "CUSTOM_TOPIC": custom_topic or "-",
        "WINDOW": f"{m.PUBLISHED_AFTER_RFC3339} -> {m.PUBLISHED_BEFORE_RFC3339}",
        "EXPLICIT_VIDEO_IDS": m.EXPLICIT_VIDEO_IDS,
    })
    m.main()
def _import_x_scraper_with_config_fallback():
    """Import the untouched X scraper while tolerating the current YAML nesting bug.

    The group pipeline currently stores the X block as ``youtube.x`` in
    config.yaml, while config_loader.PipelineConfig expects a top-level ``x``
    key.  We do not modify repo/config/config.yaml.  Instead, only for the
    duration of the original module import, we wrap config_loader.load_config
    and copy the nested dict into the in-memory PipelineConfig.x field when the
    native top-level field is empty.  Once the group config is corrected, the
    native top-level value wins and this fallback becomes a no-op.
    """
    from config import config_loader

    original_load_config = config_loader.load_config

    def load_config_with_x_fallback(*args, **kwargs):
        pipeline_cfg = original_load_config(*args, **kwargs)
        if pipeline_cfg.x:
            _log("[X][CONFIG] Using native top-level config.yaml -> x block.")
            return pipeline_cfg

        youtube_cfg = pipeline_cfg.youtube if isinstance(pipeline_cfg.youtube, dict) else {}
        nested_x = youtube_cfg.get("x") if isinstance(youtube_cfg, dict) else None
        if isinstance(nested_x, dict) and nested_x:
            pipeline_cfg.x = dict(nested_x)
            _log(
                "[X][CONFIG][OVERLAY_FALLBACK] Native top-level x config is empty; "
                "using existing config.yaml youtube.x block in memory only. "
                "repo/config/config.yaml remains unchanged."
            )
        return pipeline_cfg

    config_loader.load_config = load_config_with_x_fallback
    try:
        import src.ingestion.x_scraper as x_module
    finally:
        config_loader.load_config = original_load_config
    return x_module


def run_x(cfg):
    m = _import_x_scraper_with_config_fallback()
    mapping = {
        "MAX_WORKERS": ("X_MAX_WORKERS", _int, 3),
        "MAX_SCROLLS_PER_SLICE": ("X_MAX_SCROLLS_PER_SLICE", _int, 4),
        "MAX_SCROLLS_MIN_DAY": ("X_MAX_SCROLLS_MIN_DAY", _int, 9),
        "NO_NEW_SCROLL_LIMIT": ("X_NO_NEW_SCROLL_LIMIT", _int, 2),
        "PAGE_LOAD_TIMEOUT": ("X_PAGE_LOAD_TIMEOUT_SECONDS", _int, 45),
        "SAFE_GET_READY_TIMEOUT": ("X_READY_TIMEOUT_SECONDS", _int, 28),
        "STARTUP_STAGGER_SECONDS": ("X_STARTUP_STAGGER_SECONDS", _int, 8),
        "STARTUP_MAX_ATTEMPTS": ("X_STARTUP_MAX_ATTEMPTS", _int, 3),
        "STARTUP_RETRY_SECONDS": ("X_STARTUP_RETRY_SECONDS", _int, 12),
        "SCROLL_MIN_DELAY": ("X_SCROLL_MIN_DELAY_SECONDS", _float, 1.8),
        "SCROLL_MAX_DELAY": ("X_SCROLL_MAX_DELAY_SECONDS", _float, 3.8),
        "JOB_BACKOFF_SECONDS": ("X_JOB_BACKOFF_SECONDS", _int, 30),
        "MAX_JOB_ATTEMPTS": ("X_MAX_JOB_ATTEMPTS", _int, 3),
        "BACKFILL_MIN_DELAY": ("X_BACKFILL_MIN_DELAY_SECONDS", _float, 3.0),
        "BACKFILL_MAX_DELAY": ("X_BACKFILL_MAX_DELAY_SECONDS", _float, 6.0),
        "BACKFILL_READY_TIMEOUT": ("X_BACKFILL_READY_TIMEOUT_SECONDS", _int, 20),
    }
    effective = {}
    for attr, (key, caster, default) in mapping.items():
        val = caster(cfg, key, default)
        setattr(m, attr, val); effective[attr] = val
    effective.update({"X_ACCOUNTS_JSON": bool(cfg.get("X_ACCOUNTS_JSON")), "X_OUTPUT_ROOT": cfg.get("X_OUTPUT_ROOT") or "native default"})
    _log_effective("x", effective)
    m.main()


def run_finance(cfg):
    import src.ingestion.finance_market_extract as m
    _log_effective("finance", {
        "FRED_API_KEY": bool(m.FRED_API_KEY), "FINANCIAL_RUN_ID": m.RUN_ID,
        "REGISTERED_ASSETS": len(m.ASSETS), "VERIFY_SERIES": len(m.VERIFY),
        "PROJECT_START": m.START, "PROJECT_END": m.END,
    })
    m.main()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: runtime_wrapper.py <reddit_discovery|reddit_comments|youtube|x|finance>")
    name = sys.argv[1]
    cfg = get_all(False)
    funcs = {
        "reddit_discovery": run_reddit_discovery,
        "reddit_comments": run_reddit_comments,
        "youtube": run_youtube,
        "x": run_x,
        "finance": run_finance,
    }
    if name not in funcs:
        raise SystemExit(f"unknown collector: {name}")
    funcs[name](cfg)

if __name__ == "__main__":
    main()
