from __future__ import annotations
import csv, json, os, sqlite3, time
from pathlib import Path
import yaml
from prometheus_client import Gauge, Counter
from settings import PIPELINE_ROOT
from config_store import get_all
from reddit_live import reddit_handoff_stats

running = Gauge('pipeline_collector_running','Collector process running',['collector'])
last_exit = Gauge('pipeline_collector_last_exit_code','Last collector exit code',['collector'])
last_run_ts = Gauge('pipeline_collector_last_run_timestamp_seconds','Last collector start Unix time',['collector'])
last_success_ts = Gauge('pipeline_collector_last_success_timestamp_seconds','Last successful collector finish Unix time',['collector'])
last_duration = Gauge('pipeline_collector_run_duration_seconds','Last collector run duration',['collector'])
output_records = Gauge('pipeline_output_records','Rows/records observed in native pipeline outputs',['collector','kind'])
output_files = Gauge('pipeline_output_files','Files observed in native pipeline outputs',['collector','kind'])
output_age = Gauge('pipeline_output_age_seconds','Age of native output in seconds',['collector','kind'])
integrity_ok = Gauge('pipeline_integrity_ok','1 when protected pipeline files match original manifest')
credentials = Gauge('pipeline_runtime_configured','Runtime credential/config presence',['key'])
youtube_quota_used = Gauge('youtube_quota_used','Quota units used today')
youtube_quota_budget = Gauge('youtube_quota_budget','Configured YouTube daily quota budget')
youtube_known_videos = Gauge('youtube_known_videos','Known YouTube videos in incremental checkpoint')
reddit_terms = Gauge('reddit_term_runs','Reddit discovery term-run statuses',['status'])
x_jobs = Gauge('x_jobs','X scraper jobs by status',['status'])
x_workers = Gauge('x_workers','X scraper workers by state',['state'])
finance_latest_files = Gauge('finance_latest_run_files','Files in latest finance run')
reddit_parent_unique = Gauge('reddit_parent_posts_unique','Unique Reddit parent post IDs discovered across native parent CSV files')
reddit_parent_eligible = Gauge('reddit_parent_posts_eligible_for_json','Parent posts eligible for native JSON collection')
reddit_json_pending = Gauge('reddit_json_pending_fetch','Eligible Reddit JSON URLs still pending fetch')
reddit_fetch_events = Gauge('reddit_json_fetch_events_total','Rows in native Reddit raw_json_fetch_log.csv')
reddit_fetch_status = Gauge('reddit_json_fetch_status_total','Native Reddit JSON fetch events by status',['status'])
reddit_raw_json_files = Gauge('reddit_raw_json_files_total','Native Reddit raw JSON files currently saved')
reddit_live_comments = Gauge('reddit_comments_live_from_raw_json','Comments currently visible by read-only parsing of saved native raw JSON files')
reddit_final_comments = Gauge('reddit_comments_native_total','Rows in native comments_from_raw_json.csv')
reddit_window_comments = Gauge('reddit_comments_project_window_total','Rows in native comments_project_window.csv')
_reddit_status_seen = set()


def _rows(path: Path):
    if not path.exists(): return 0
    try:
        with path.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
            return max(0, sum(1 for _ in f)-1)
    except Exception: return 0

def _lines(path: Path):
    if not path.exists(): return 0
    try:
        with path.open('r',encoding='utf-8',errors='replace') as f: return sum(1 for _ in f)
    except Exception: return 0

def _age(path: Path):
    try: return max(0.0,time.time()-path.stat().st_mtime)
    except Exception: return 0.0

def topic_id():
    try:
        cfg=yaml.safe_load((PIPELINE_ROOT/'config/config.yaml').read_text(encoding='utf-8'))
        return cfg.get('topic_id','iran_us_war')
    except Exception: return 'iran_us_war'

def x_root():
    cfg=get_all(False); value=(cfg.get('X_OUTPUT_ROOT') or '').strip()
    if not value:
        return PIPELINE_ROOT/'Twitter_Scraper_Data_v4'
    p=Path(value).expanduser()
    return p if p.is_absolute() else PIPELINE_ROOT/p

def update_process_metrics(pm):
    for name,s in pm.all_status().items():
        running.labels(name).set(1 if s['running'] else 0)
        if s.get('exit_code') is not None: last_exit.labels(name).set(s['exit_code'])
        if s.get('started_at'): last_run_ts.labels(name).set(s['started_at'])
        if s.get('duration') is not None: last_duration.labels(name).set(s['duration'])
        if s.get('last_status')=='success' and s.get('finished_at'): last_success_ts.labels(name).set(s['finished_at'])


def collect_native_metrics():
    cfg=get_all(False)
    for key in ['REDDIT_FIREFOX_PROFILE','YOUTUBE_API_KEY','X_ACCOUNTS_JSON','FRED_API_KEY']:
        credentials.labels(key).set(1 if cfg.get(key) else 0)
    try: youtube_quota_budget.set(int(cfg.get('YOUTUBE_DAILY_QUOTA_BUDGET') or 8000))
    except Exception: youtube_quota_budget.set(8000)

    # Reddit native outputs + explicit stage handoff metrics
    pp=PIPELINE_ROOT/'data/raw/reddit/parent_posts'
    parent_files=list(pp.glob('*_reddit_parent_posts.csv')) if pp.exists() else []
    handoff=reddit_handoff_stats()
    output_files.labels('reddit_discovery','parent_csv').set(len(parent_files))
    output_records.labels('reddit_discovery','parent_posts').set(handoff['parent_unique'])
    reddit_parent_unique.set(handoff['parent_unique'])
    reddit_parent_eligible.set(handoff['eligible'] or 0)
    reddit_json_pending.set(handoff['pending_json'] or 0)
    reddit_fetch_events.set(handoff['fetch_log_rows'])
    reddit_raw_json_files.set(handoff['raw_json_files'])
    reddit_live_comments.set(handoff['comments_live_raw_json'])
    reddit_final_comments.set(handoff['comments_final'])
    reddit_window_comments.set(handoff['comments_window_final'])

    current_status=set(handoff.get('fetch_status',{}))
    global _reddit_status_seen
    for st in _reddit_status_seen | current_status:
        reddit_fetch_status.labels(st).set(handoff.get('fetch_status',{}).get(st,0))
    _reddit_status_seen |= current_status

    run_files=list(pp.glob('reddit_master_*_runs.csv')) if pp.exists() else []
    statuses={}
    for p in run_files:
        try:
            with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
                for r in csv.DictReader(f): statuses[r.get('status') or 'unknown']=statuses.get(r.get('status') or 'unknown',0)+1
        except Exception: pass
    for st,n in statuses.items(): reddit_terms.labels(st).set(n)
    if parent_files: output_age.labels('reddit_discovery','parent_csv').set(min(_age(p) for p in parent_files))

    ra=PIPELINE_ROOT/'data/interim/reddit/raw_json_audit'
    rawj=ra/'raw_reddit_json'
    output_files.labels('reddit_comments','raw_json').set(handoff['raw_json_files'])
    for kind,fn in [('comments','comments_from_raw_json.csv'),('window_comments','comments_project_window.csv'),('coverage','weekly_coverage_W01_W21.csv'),('fetch_log','raw_json_fetch_log.csv')]:
        p=ra/fn; output_records.labels('reddit_comments',kind).set(_rows(p)); output_age.labels('reddit_comments',kind).set(_age(p))

    # YouTube native outputs/checkpoint
    yd=PIPELINE_ROOT/'data/raw'/topic_id()
    yjson=yd/'youtube_comments_v2.jsonl'; ycsv=yd/'youtube_raw_export.csv'; yruns=yd/'youtube_runs.csv'; yskip=yd/'youtube_skipped_videos.csv'
    output_records.labels('youtube','jsonl').set(_lines(yjson))
    output_records.labels('youtube','raw_csv').set(_rows(ycsv))
    output_records.labels('youtube','manifest_rows').set(_rows(yruns))
    output_records.labels('youtube','skipped_videos').set(_rows(yskip))
    output_age.labels('youtube','jsonl').set(_age(yjson))
    cp=yd/'checkpoint.json'
    if cp.exists():
        try:
            state=json.loads(cp.read_text(encoding='utf-8'))
            youtube_quota_used.set(float(state.get('quota_used_today',0)))
            youtube_known_videos.set(len(state.get('v2_incremental',{}).get('known_video_ids',[])))
        except Exception: pass

    # X native SQLite output
    xr=x_root(); db=xr/'twitter_data_v4.db'
    output_files.labels('x','sqlite').set(1 if db.exists() else 0)
    output_age.labels('x','sqlite').set(_age(db))
    if db.exists():
        try:
            conn=sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True, timeout=2)
            for kind,table in [('tweets','tweets_raw'),('matches','tweet_matches'),('subruns','x_subruns')]:
                try: output_records.labels('x',kind).set(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
                except Exception: pass
            try:
                for st,n in conn.execute('SELECT status,COUNT(*) FROM x_jobs GROUP BY status'): x_jobs.labels(st or 'unknown').set(n)
            except Exception: pass
            try:
                for st,n in conn.execute('SELECT state,COUNT(*) FROM worker_heartbeat GROUP BY state'): x_workers.labels(st or 'unknown').set(n)
            except Exception: pass
            conn.close()
        except Exception: pass

    # Finance native run directories
    fr=PIPELINE_ROOT/'data/raw'/topic_id()/'financial/runs'
    runs=[p for p in fr.iterdir() if p.is_dir()] if fr.exists() else []
    if runs:
        latest=max(runs,key=lambda p:p.stat().st_mtime)
        files=[p for p in latest.rglob('*') if p.is_file()]
        finance_latest_files.set(len(files)); output_files.labels('finance','latest_run').set(len(files)); output_age.labels('finance','latest_run').set(_age(latest))
        prepared=latest/'prepared'
        for fn,kind in [('financial_raw.csv','raw'),('financial_analytical_source.csv','analytical'),('financial_weekly.csv','weekly'),('asset_registry.csv','assets')]:
            output_records.labels('finance',kind).set(_rows(prepared/fn))
    else:
        finance_latest_files.set(0); output_files.labels('finance','latest_run').set(0)
