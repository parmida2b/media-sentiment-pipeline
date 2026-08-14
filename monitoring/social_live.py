from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from settings import PIPELINE_ROOT
from pipeline_metrics import topic_id, x_root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail_text_lines(path: Path, limit: int) -> list[str]:
    # Read only the last N non-empty UTF-8 lines without loading a large JSONL file.
    if not path.exists() or limit <= 0:
        return []
    try:
        with path.open('rb') as f:
            f.seek(0, 2)
            pos = f.tell()
            block = 64 * 1024
            buf = b''
            lines: list[bytes] = []
            while pos > 0 and len(lines) <= limit:
                step = min(block, pos)
                pos -= step
                f.seek(pos)
                buf = f.read(step) + buf
                lines = buf.splitlines()
            return [x.decode('utf-8', errors='replace') for x in lines[-limit:] if x.strip()]
    except Exception:
        return []


def youtube_live_payload(limit: int = 40) -> dict:
    limit = max(1, min(int(limit or 40), 200))
    path = PIPELINE_ROOT / 'data' / 'raw' / topic_id() / 'youtube_comments_v2.jsonl'
    rows = []
    for line in reversed(_tail_text_lines(path, limit)):
        try:
            r = json.loads(line)
        except Exception:
            continue
        am = r.get('author_metadata') or {}
        rows.append({
            'content_id': r.get('content_id') or '',
            'content_type': r.get('content_type') or ('reply' if r.get('is_reply') else 'comment'),
            'created_at_utc': r.get('date') or '',
            'collected_at_utc': r.get('collected_at_utc') or '',
            'video_id': r.get('post_id') or '',
            'video_title': r.get('post_title') or '',
            'query_id': r.get('query_id') or '',
            'source_container': r.get('source_container') or '',
            'project_week': r.get('project_week') or '',
            'language': r.get('language') or '',
            'like_count': am.get('like_count', 0),
            'text': r.get('text') or '',
        })
    try:
        age = max(0.0, datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) if path.exists() else None
    except Exception:
        age = None
    return {
        'generated_at_utc': _utc_now(),
        'source_file': str(path),
        'source_exists': path.exists(),
        'source_age_seconds': age,
        'rows': rows,
    }


def x_live_payload(limit: int = 40) -> dict:
    limit = max(1, min(int(limit or 40), 200))
    db = x_root() / 'twitter_data_v4.db'
    rows = []
    error = None
    if db.exists():
        conn = None
        try:
            conn = sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True, timeout=2)
            conn.row_factory = sqlite3.Row
            sql = '''
                SELECT platform_content_id, content_type, created_at_utc, collected_at_utc,
                       text_raw, query_id, project_week, source_container, tweet_url,
                       country_or_region, engagement_score, engagement_replies,
                       engagement_shares, engagement_views
                  FROM tweets_raw
              ORDER BY COALESCE(collected_at_utc, created_at_utc) DESC, platform_content_id DESC
                 LIMIT ?
            '''
            for r in conn.execute(sql, (limit,)).fetchall():
                d = dict(r)
                rows.append({
                    'content_id': d.get('platform_content_id') or '',
                    'content_type': d.get('content_type') or 'tweet',
                    'created_at_utc': d.get('created_at_utc') or '',
                    'collected_at_utc': d.get('collected_at_utc') or '',
                    'query_id': d.get('query_id') or '',
                    'project_week': d.get('project_week') or '',
                    'source_container': d.get('source_container') or '',
                    'tweet_url': d.get('tweet_url') or '',
                    'country_or_region': d.get('country_or_region') or '',
                    'engagement_score': d.get('engagement_score'),
                    'engagement_replies': d.get('engagement_replies'),
                    'engagement_shares': d.get('engagement_shares'),
                    'engagement_views': d.get('engagement_views'),
                    'text': d.get('text_raw') or '',
                })
        except Exception as e:
            error = f'{type(e).__name__}: {e}'
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    try:
        age = max(0.0, datetime.now(timezone.utc).timestamp() - db.stat().st_mtime) if db.exists() else None
    except Exception:
        age = None
    return {
        'generated_at_utc': _utc_now(),
        'source_file': str(db),
        'source_exists': db.exists(),
        'source_age_seconds': age,
        'error': error,
        'rows': rows,
    }
