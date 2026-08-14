from __future__ import annotations
import json, sys, threading, time
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from settings import *
from config_store import get_all, set_values, clear_key, set_json
from process_manager import ProcessManager, COLLECTORS
from pipeline_metrics import collect_native_metrics, update_process_metrics, integrity_ok, topic_id, x_root
from pipeline_catalog import (
    reddit_effective_sources, reddit_effective_queries, reddit_native_sources, reddit_native_queries,
    youtube_queries, x_queries, youtube_native_regions, youtube_native_explicit_video_ids,
    finance_assets,
)
import os
from ui_stats import snapshot_counts
from reddit_live import reddit_handoff_stats, reddit_live_payload
from social_live import youtube_live_payload, x_live_payload
from reddit_realtime_metrics import build_reddit_realtime_snapshot, start_reddit_realtime_metrics_server
from verify_pipeline_unchanged import verify

app = Flask(__name__)
app.secret_key = 'local-overlay-control-center-full-panel'
pm = ProcessManager(sys.executable)

NAV = [
    ('dashboard','/','داشبورد','dash'),
    ('data','/data','داده‌ها','data'),
    ('scrapers','/scrapers','تنظیمات خزشگرها','bot'),
    ('live','/live','متریک و لاگ زنده','live'),
    ('integrity','/integrity','سلامت Pipeline','admin'),
]


def base(title, sub, active, **kw):
    ok,_,_ = verify(False)
    return dict(
        title=title, sub=sub, active=active, nav_items=NAV, build_id=BUILD_ID,
        integrity=ok, topic_id=topic_id(), grafana_url='http://localhost:8795', **kw,
    )


def output_snapshot():
    st=pm.all_status(); cfg=get_all(False)
    return {
        'processes':st,'reddit_chain':pm.chain_status(),'topic_id':topic_id(),'x_root':str(x_root()),
        'pipeline_root':str(PIPELINE_ROOT),'counts':snapshot_counts(),
        'credentials':{k:bool(cfg.get(k)) for k in ['REDDIT_FIREFOX_PROFILE','YOUTUBE_API_KEY','X_ACCOUNTS_JSON','FRED_API_KEY']},
    }


def _form_values(keys):
    return {k: request.form.get(k, '') for k in keys}


def _selected_ids(form_key):
    vals = [x.strip() for x in request.form.getlist(form_key) if x.strip()]
    return ','.join(vals) if vals else '__NONE__'


def _enabled_set(raw: str, all_ids):
    raw=(raw or '').strip()
    if not raw: return set(all_ids)
    if raw == '__NONE__': return set()
    return {x.strip() for x in raw.split(',') if x.strip()}


@app.get('/')
def dashboard():
    return render_template('dashboard.html', **base(
        'داشبورد','نمای کلی زنده از pipeline گروه + Reddit observability','dashboard',
        snapshot=output_snapshot(), counts=snapshot_counts(),
        reddit_monitor=build_reddit_realtime_snapshot(pm.all_status, pm.chain_status),
    ))

@app.get('/data')
def data_page():
    return render_template('data.html', **base(
        'داده‌ها','خلاصه‌ی خروجی‌های native بدون کپی یا تغییر storage pipeline','data',
        counts=snapshot_counts(), snapshot=output_snapshot(), reddit=reddit_handoff_stats(),
    ))

@app.get('/scrapers')
def scrapers():
    return render_template('scrapers.html', **base(
        'تنظیمات خزشگرها','پنل کامل تنظیم و اجرای collectorهای اصلی؛ override فقط در حافظه runtime','scrapers',
        snapshot=output_snapshot(),
    ))

@app.get('/scrapers/reddit')
def reddit_page():
    cfg=get_all(True)
    sources=reddit_effective_sources(); queries=reddit_effective_queries()
    all_ids=[q.get('query_id') for q in queries if q.get('query_id')]
    enabled=_enabled_set(get_all(False).get('REDDIT_ACTIVE_QUERY_IDS',''), all_ids)
    query_rows=[]
    for q in queries:
        row=dict(q); row['enabled']=q.get('query_id') in enabled
        row['source_ids_text']=', '.join(q.get('source_ids') or [])
        row['search_terms_text']='\n'.join(q.get('search_terms') or [])
        query_rows.append(row)
    return render_template('reddit.html', **base(
        'Reddit','تنظیم کامل Discovery + Raw JSON؛ فایل‌های اصلی دست‌نخورده','scrapers',
        cfg=cfg, sources=[{'source_id':k,**v} for k,v in sources.items()], queries=query_rows,
        snapshot=output_snapshot(), handoff=reddit_handoff_stats(), native_source_count=len(reddit_native_sources()), native_query_count=len(reddit_native_queries()),
    ))

@app.post('/scrapers/reddit/save')
def reddit_save():
    keys=[
        'REDDIT_FIREFOX_PROFILE','REDDIT_SKIP_COMPLETED_TERMS','REDDIT_MAX_SCROLLS_PER_SEARCH_TERM',
        'REDDIT_MAX_NO_NEW_ROUNDS','REDDIT_SCROLL_PAUSE_SECONDS','REDDIT_BETWEEN_SEARCH_TERM_PAUSE_SECONDS',
        'REDDIT_BETWEEN_JOB_PAUSE_SECONDS','REDDIT_INITIAL_TIMEOUT_SECONDS','REDDIT_JSON_PAGE_PAUSE_SECONDS',
        'REDDIT_JSON_PAGE_TIMEOUT_SECONDS','REDDIT_HTTP_PROBE_TIMEOUT_SECONDS','REDDIT_PARENT_LOOKBACK_DAYS',
        'REDDIT_RESUME_EXISTING_JSON','REDDIT_MAX_POSTS',
    ]
    set_values(_form_values(keys)); flash('تنظیمات Reddit ذخیره شد؛ فقط runtime wrapper آن‌ها را اعمال می‌کند.','ok')
    return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/active-queries')
def reddit_active_queries():
    set_values({'REDDIT_ACTIVE_QUERY_IDS': _selected_ids('query_ids')})
    flash('Query selection برای اجرای بعدی ذخیره شد.','ok'); return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/source/new')
def reddit_source_new():
    sid=request.form.get('source_id','').strip(); sub=request.form.get('subreddit','').strip()
    if not sid or not sub: flash('source_id و subreddit الزامی است.','err'); return redirect(url_for('reddit_page'))
    sources=reddit_effective_sources(); sources[sid]={'subreddit':sub,'status':request.form.get('status','Active')}; set_json('REDDIT_SOURCES_JSON',sources)
    flash(f'{sid} به override بیرونی اضافه شد.','ok'); return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/source/<sid>')
def reddit_source_update(sid):
    sources=reddit_effective_sources()
    if sid in sources:
        sources[sid]={'subreddit':request.form.get('subreddit','').strip(),'status':request.form.get('status','Active')}
        set_json('REDDIT_SOURCES_JSON',sources); flash(f'{sid} برای runtime به‌روزرسانی شد.','ok')
    return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/query/new')
def reddit_query_new():
    qid=request.form.get('query_id','').strip()
    if not qid: flash('query_id الزامی است.','err'); return redirect(url_for('reddit_page'))
    queries=reddit_effective_queries(); queries=[q for q in queries if q.get('query_id')!=qid]
    q={
        'query_id':qid,'family':request.form.get('family',''),'lang':request.form.get('lang','en'),
        'logical_query':request.form.get('logical_query',''),'risk':request.form.get('risk','low'),
        'entity_anchor':request.form.get('entity_anchor',''),'discovery_route':request.form.get('discovery_route','query_search'),
        'source_ids':[x.strip() for x in request.form.get('source_ids','').split(',') if x.strip()],
        'search_terms':[x.strip() for x in request.form.get('search_terms','').splitlines() if x.strip()],
    }
    queries.append(q); set_json('REDDIT_QUERIES_JSON',queries)
    raw=get_all(False).get('REDDIT_ACTIVE_QUERY_IDS',''); all_ids=[x.get('query_id') for x in queries]
    enabled=_enabled_set(raw,all_ids); enabled.add(qid); set_values({'REDDIT_ACTIVE_QUERY_IDS':','.join(sorted(enabled))})
    flash(f'{qid} به runtime registry اضافه شد.','ok'); return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/query/<qid>')
def reddit_query_update(qid):
    queries=reddit_effective_queries(); found=False
    for q in queries:
        if q.get('query_id')==qid:
            found=True
            for key in ['family','lang','logical_query','risk','entity_anchor','discovery_route']:
                q[key]=request.form.get(key,q.get(key,''))
            q['source_ids']=[x.strip() for x in request.form.get('source_ids','').split(',') if x.strip()]
            q['search_terms']=[x.strip() for x in request.form.get('search_terms','').splitlines() if x.strip()]
    if found:
        set_json('REDDIT_QUERIES_JSON',queries)
        all_ids=[x.get('query_id') for x in queries]; enabled=_enabled_set(get_all(False).get('REDDIT_ACTIVE_QUERY_IDS',''),all_ids)
        if request.form.get('enabled')=='1': enabled.add(qid)
        else: enabled.discard(qid)
        set_values({'REDDIT_ACTIVE_QUERY_IDS':','.join(sorted(enabled)) if enabled else '__NONE__'})
        flash(f'{qid} برای runtime به‌روزرسانی شد.','ok')
    return redirect(url_for('reddit_page'))

@app.post('/scrapers/reddit/reset-overrides')
def reddit_reset_overrides():
    clear_key('REDDIT_SOURCES_JSON'); clear_key('REDDIT_QUERIES_JSON'); clear_key('REDDIT_ACTIVE_QUERY_IDS')
    flash('Source/Query registry به مقادیر اصلی pipeline برگشت.','ok'); return redirect(url_for('reddit_page'))


@app.get('/scrapers/youtube')
def youtube_page():
    cfg=get_all(True); raw=get_all(False)
    queries=youtube_queries(); all_ids=[q.get('query_id') for q in queries if q.get('query_id')]
    enabled=_enabled_set(raw.get('YOUTUBE_ACTIVE_QUERY_IDS',''),all_ids)
    regions=raw.get('YOUTUBE_REGION_CODES','').strip() or '\n'.join(','.join(map(str,r)) for r in youtube_native_regions())
    vids=raw.get('YOUTUBE_EXPLICIT_VIDEO_IDS','').strip() or ', '.join(youtube_native_explicit_video_ids())
    return render_template('youtube.html', **base(
        'YouTube','همان collector گروه با API/Quota/Query/Region controls بیرونی','scrapers',
        cfg=cfg, queries=queries, enabled_query_ids=enabled, regions_text=regions, explicit_ids_text=vids,
        snapshot=output_snapshot(), api_configured=bool(raw.get('YOUTUBE_API_KEY')),
    ))

@app.post('/scrapers/youtube/save')
def youtube_save():
    keys=['YOUTUBE_API_KEY','YOUTUBE_DAILY_QUOTA_BUDGET','YOUTUBE_REGIONS_PER_DAY','YOUTUBE_MAX_VIDEOS_PER_QUERY',
          'YOUTUBE_MAX_COMMENTS_PER_VIDEO','YOUTUBE_COMMENT_POOL_MULTIPLIER','YOUTUBE_RANDOM_SEED','AUTHOR_HASH_SALT']
    vals=_form_values(keys)
    vals['YOUTUBE_ACTIVE_QUERY_IDS']=_selected_ids('query_ids')
    vals['YOUTUBE_REGION_CODES']=request.form.get('YOUTUBE_REGION_CODES','')
    vals['YOUTUBE_EXPLICIT_VIDEO_IDS']=request.form.get('YOUTUBE_EXPLICIT_VIDEO_IDS','')
    set_values(vals); flash('تنظیمات YouTube برای اجرای بعدی ذخیره شد.','ok'); return redirect(url_for('youtube_page'))


@app.get('/scrapers/x')
def x_page():
    return render_template('x.html', **base(
        'X / Twitter','Runtime tuning کامل روی x_scraper.py بدون patch فایل','scrapers',
        cfg=get_all(True), x_queries=x_queries(), snapshot=output_snapshot(), accounts_configured=bool(get_all(False).get('X_ACCOUNTS_JSON')),
    ))

@app.post('/scrapers/x/save')
def x_save():
    keys=['X_ACCOUNTS_JSON','X_OUTPUT_ROOT','PROJECT_AUTHOR_SALT','X_MAX_WORKERS','X_MAX_SCROLLS_PER_SLICE','X_MAX_SCROLLS_MIN_DAY',
          'X_NO_NEW_SCROLL_LIMIT','X_PAGE_LOAD_TIMEOUT_SECONDS','X_READY_TIMEOUT_SECONDS','X_STARTUP_STAGGER_SECONDS',
          'X_STARTUP_MAX_ATTEMPTS','X_STARTUP_RETRY_SECONDS','X_SCROLL_MIN_DELAY_SECONDS','X_SCROLL_MAX_DELAY_SECONDS',
          'X_JOB_BACKOFF_SECONDS','X_MAX_JOB_ATTEMPTS','X_BACKFILL_MIN_DELAY_SECONDS','X_BACKFILL_MAX_DELAY_SECONDS','X_BACKFILL_READY_TIMEOUT_SECONDS']
    set_values(_form_values(keys)); flash('تنظیمات X برای runtime ذخیره شد.','ok'); return redirect(url_for('x_page'))


@app.get('/scrapers/finance')
def finance_page():
    assets=finance_assets(); sources={}
    for a in assets: sources[a.get('source')]=sources.get(a.get('source'),0)+1
    return render_template('finance.html', **base(
        'Finance','اجرای finance_market_extract.py اصلی + FRED runtime credential','scrapers',
        cfg=get_all(True), assets=assets, source_counts=sources, snapshot=output_snapshot(), fred_configured=bool(get_all(False).get('FRED_API_KEY')),
    ))

@app.post('/scrapers/finance/save')
def finance_save():
    set_values(_form_values(['FRED_API_KEY','FINANCIAL_RUN_ID'])); flash('تنظیمات Finance ذخیره شد.','ok'); return redirect(url_for('finance_page'))


@app.post('/config/clear/<key>')
def clear_config(key):
    clear_key(key); flash(f'{key} پاک شد.','ok'); return redirect(request.referrer or url_for('scrapers'))

@app.post('/process/reddit/full/start')
def reddit_full_start():
    ok,msg=pm.start_reddit_full()
    flash(msg,'ok' if ok else 'err')
    return redirect(request.referrer or url_for('reddit_page'))

@app.get('/api/data/reddit/live')
def api_data_reddit_live():
    try:
        limit=int(request.args.get('limit','40'))
    except Exception:
        limit=40
    return jsonify(reddit_live_payload(limit))

@app.get('/api/data/youtube/live')
def api_data_youtube_live():
    try:
        limit=int(request.args.get('limit','40'))
    except Exception:
        limit=40
    payload=youtube_live_payload(limit)
    payload['total_records']=snapshot_counts().get('youtube_records',0)
    return jsonify(payload)

@app.get('/api/data/x/live')
def api_data_x_live():
    try:
        limit=int(request.args.get('limit','40'))
    except Exception:
        limit=40
    payload=x_live_payload(limit)
    c=snapshot_counts()
    payload['total_records']=c.get('x_tweets',0)
    payload['total_matches']=c.get('x_matches',0)
    return jsonify(payload)

@app.post('/process/<name>/start')
def process_start(name):
    try: ok,msg=pm.start(name)
    except Exception as e: ok,msg=False,f'{type(e).__name__}: {e}'
    flash(msg,'ok' if ok else 'err'); return redirect(request.referrer or url_for('scrapers'))

@app.post('/process/<name>/stop')
def process_stop(name):
    try: ok,msg=pm.stop(name)
    except Exception as e: ok,msg=False,f'{type(e).__name__}: {e}'
    flash(msg,'ok' if ok else 'err'); return redirect(request.referrer or url_for('scrapers'))

@app.post('/process/<platform>/custom/start')
def process_custom_start(platform):
    topic = request.form.get('custom_topic', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()

    env_overrides = {}
    if topic:
        env_overrides['SCRAPER_CUSTOM_TOPIC'] = topic
    if start_date:
        env_overrides['SCRAPER_START_DATE'] = start_date
    if end_date:
        env_overrides['SCRAPER_END_DATE'] = end_date

    for key in ['max_posts', 'max_videos', 'max_comments', 'max_scrolls', 'lang', 'stage_mode']:
        val = request.form.get(key)
        if val:
            env_overrides[f'SCRAPER_{key.upper()}'] = str(val).strip()

    os.environ.update(env_overrides)

    proc_name = platform
    if platform == 'reddit':
        mode = request.form.get('stage_mode', 'full')
        if mode == 'full':
            ok, msg = pm.start_reddit_full()
            flash(f"Reddit Full Flow با موضوع سفارشی ({topic or 'پیش‌فرض'}) آغاز شد.", 'ok' if ok else 'err')
            return redirect(request.referrer or url_for('reddit_page'))
        else:
            proc_name = f'reddit_{mode}'

    try:
        ok, msg = pm.start(proc_name)
    except Exception as e:
        ok, msg = False, f'{type(e).__name__}: {e}'

    flash(msg, 'ok' if ok else 'err')
    return redirect(request.referrer or url_for('scrapers'))
@app.route('/live')
def live():
    name=request.args.get('collector','youtube'); name=name if name in COLLECTORS else 'youtube'
    return render_template('live.html', **base('متریک و لاگ زنده','stdout/stderr اصلی + وضعیت process wrapper','live',collector=name,collectors=list(COLLECTORS),snapshot=output_snapshot()))

@app.get('/integrity')
def integrity():
    ok,bad,missing=verify(False)
    return render_template('integrity.html', **base('Pipeline Integrity','Hash verification روی source/config اصلی','integrity',ok=ok,bad=bad,missing=missing))

@app.get('/api/status')
def api_status(): return jsonify(output_snapshot())

@app.get('/api/dashboard')
def api_dashboard():
    counts = snapshot_counts()
    reddit = build_reddit_realtime_snapshot(pm.all_status, pm.chain_status)
    return jsonify({
        'counts': counts,
        'reddit': reddit,
        'processes': pm.all_status(),
        'reddit_chain': pm.chain_status(),
        'generated_at_utc': reddit.get('generated_at_utc'),
    })

@app.get('/api/monitoring/reddit')
def api_monitoring_reddit():
    return jsonify(build_reddit_realtime_snapshot(pm.all_status, pm.chain_status))

@app.get('/api/logs/<name>')
def api_logs(name):
    if name not in COLLECTORS: return jsonify({'error':'unknown collector'}),404
    p=LOG_DIR/f'{name}.log'
    if not p.exists(): return jsonify({'text':'No log yet.'})
    try:
        lines=max(100,min(int(request.args.get('lines','2000')),10000))
    except Exception:
        lines=2000
    try: return jsonify({'text':'\n'.join(p.read_text(encoding='utf-8',errors='replace').splitlines()[-lines:]),'log_file':str(p),'lines':lines})
    except Exception as e: return jsonify({'text':str(e)})

@app.get('/health')
def health():
    ok,_,_=verify(False); return jsonify({'ok':True,'build':BUILD_ID,'pipeline_unchanged':ok,'topic_id':topic_id()})


def metrics_loop():
    while True:
        try:
            update_process_metrics(pm); collect_native_metrics(); ok,_,_=verify(False); integrity_ok.set(1 if ok else 0)
        except Exception as e: print('[metrics]',type(e).__name__,e)
        time.sleep(2)

def metrics_self_check():
    time.sleep(0.5)
    try:
        from urllib.request import urlopen
        body=urlopen(f'http://127.0.0.1:{METRICS_PORT}/metrics', timeout=3).read().decode('utf-8','replace')
        marker='reddit_realtime_exporter_up'
        print('[metrics] self-check OK' if marker in body else '[metrics] self-check WARNING: realtime marker missing')
    except Exception as e:
        print('[metrics] self-check FAILED:', type(e).__name__, e)



if __name__=='__main__':
    print('='*72); print('GROUP PIPELINE CONTROL CENTER — FULL EXTERNAL OVERLAY')
    print('Pipeline root:',PIPELINE_ROOT); print('Build:',BUILD_ID)
    print(f'Web UI: http://{WEB_HOST}:{WEB_PORT}'); print(f'Metrics: http://127.0.0.1:{METRICS_PORT}/metrics'); print('='*72)
    ok,_,_=verify(True)
    if not ok: raise SystemExit('Protected pipeline files changed. Refusing to start overlay.')
    start_reddit_realtime_metrics_server(METRICS_PORT, pm.all_status, pm.chain_status)
    print(f'[metrics] dynamic Reddit metrics server listening on 0.0.0.0:{METRICS_PORT}')
    print('[metrics] scrape-time metrics prefix: reddit_realtime_*')
    threading.Thread(target=metrics_loop,daemon=True).start()
    threading.Thread(target=metrics_self_check,daemon=True).start()
    app.run(host=WEB_HOST,port=WEB_PORT,debug=False,use_reloader=False)
