from __future__ import annotations
import csv, json, sqlite3
from pathlib import Path
from settings import PIPELINE_ROOT
from pipeline_metrics import topic_id, x_root
from reddit_live import reddit_handoff_stats


def _rows(path: Path):
    if not path.exists(): return 0
    try:
        with path.open('r', encoding='utf-8-sig', errors='replace', newline='') as f:
            return max(0, sum(1 for _ in f)-1)
    except Exception: return 0


def _lines(path: Path):
    if not path.exists(): return 0
    try:
        with path.open('r', encoding='utf-8', errors='replace') as f: return sum(1 for _ in f)
    except Exception: return 0


def snapshot_counts():
    # Reddit
    pp = PIPELINE_ROOT/'data/raw/reddit/parent_posts'
    reddit_stats = reddit_handoff_stats()
    parent = reddit_stats['parent_unique']
    ra = PIPELINE_ROOT/'data/interim/reddit/raw_json_audit'
    reddit_comments = _rows(ra/'comments_from_raw_json.csv')
    reddit_window = _rows(ra/'comments_project_window.csv')
    reddit_live = int(reddit_stats.get('comments_live_raw_json') or 0)
    reddit_visible = max(reddit_window, reddit_live)
    # YouTube
    yd = PIPELINE_ROOT/'data/raw'/topic_id()
    youtube = _lines(yd/'youtube_comments_v2.jsonl')
    youtube_manifest = _rows(yd/'youtube_runs.csv')
    # X
    x_tweets=x_matches=0
    db = x_root()/'twitter_data_v4.db'
    if db.exists():
        try:
            conn=sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True, timeout=2)
            for table,key in [('tweets_raw','tweets'),('tweet_matches','matches')]:
                try:
                    n=conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    if key=='tweets': x_tweets=n
                    else: x_matches=n
                except Exception: pass
            conn.close()
        except Exception: pass
    # Finance
    fin_raw=fin_weekly=0; latest_run='—'
    fr=PIPELINE_ROOT/'data/raw'/topic_id()/'financial/runs'
    if fr.exists():
        runs=[p for p in fr.iterdir() if p.is_dir()]
        if runs:
            latest=max(runs,key=lambda p:p.stat().st_mtime); latest_run=latest.name
            prepared=latest/'prepared'
            fin_raw=_rows(prepared/'financial_raw.csv')
            fin_weekly=_rows(prepared/'financial_weekly.csv')
    return {
        'reddit_parent_posts':parent,'reddit_comments':reddit_comments,'reddit_window_comments':reddit_window,
        'reddit_live_comments':reddit_live,'reddit_visible_comments':reddit_visible,
        'reddit_raw_json_files':int(reddit_stats.get('raw_json_files') or 0),
        'reddit_eligible':int(reddit_stats.get('eligible') or 0),
        'reddit_pending_json':int(reddit_stats.get('pending_json') or 0),
        'youtube_records':youtube,'youtube_manifest':youtube_manifest,
        'x_tweets':x_tweets,'x_matches':x_matches,
        'finance_raw':fin_raw,'finance_weekly':fin_weekly,'finance_latest_run':latest_run,
        'total_social':reddit_visible+youtube+x_tweets,
    }
