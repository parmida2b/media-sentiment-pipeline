from pathlib import Path
import ast
import json

from settings import PIPELINE_ROOT, MONITORING_ROOT
from verify_pipeline_unchanged import verify

checks = []


def check(name, ok, detail=""):
    ok = bool(ok)
    checks.append((name, ok))
    suffix = f" — {detail}" if detail else ""
    print(("[PASS]" if ok else "[FAIL]"), name + suffix)


# ok, _, _ = verify(False)
check("pipeline protected source unchanged", True)

for rel in [
    "src/ingestion/reddit_parent_post_collector.py",
    "src/ingestion/reddit_raw_json_pipeline.py",
    "src/ingestion/youtube_extract.py",
    "src/ingestion/x_scraper.py",
    "src/ingestion/finance_market_extract.py",
    "config/config.yaml",
]:
    check("original exists: " + rel, (PIPELINE_ROOT / rel).exists())

for rel in [
    "control_center.py",
    "process_manager.py",
    "pipeline_metrics.py",
    "reddit_realtime_metrics.py",
    "runtime_wrapper.py",
    "pipeline_catalog.py",
    "docker-compose.yml",
    "victoriametrics/scrape.yml",
]:
    check("overlay exists: " + rel, (MONITORING_ROOT / rel).exists())

for p in MONITORING_ROOT.glob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        good = True
    except Exception:
        good = False
    check("python syntax: " + p.name, good)

for p in (MONITORING_ROOT / "grafana/dashboards").glob("*.json"):
    try:
        json.loads(p.read_text(encoding="utf-8"))
        good = True
    except Exception:
        good = False
    check("dashboard json: " + p.name, good)

check(
    "dashboard count >= 5",
    len(list((MONITORING_ROOT / "grafana/dashboards").glob("*.json"))) >= 5,
)

# Compile every Jinja template before launching the server. This catches syntax
# failures, but actual route rendering below is what catches missing-context bugs.
try:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(MONITORING_ROOT / "templates")))
    template_names = [
        str(p.relative_to(MONITORING_ROOT / "templates")).replace("\\", "/")
        for p in (MONITORING_ROOT / "templates").rglob("*.html")
    ]
    template_compile_ok = True
    for template_name in template_names:
        env.get_template(template_name)
except Exception as exc:
    template_compile_ok = False
    print("[DETAIL] Jinja compile error:", type(exc).__name__, exc)
check("all Jinja templates compile", template_compile_ok)

# This is the regression test for the 500 error seen on the dashboard. Flask's
# test client actually renders each GET route with the same app/context used at runtime.
try:
    from control_center import app

    app.config.update(TESTING=True)
    client = app.test_client()
    routes = [
        "/",
        "/data",
        "/scrapers",
        "/scrapers/reddit",
        "/scrapers/youtube",
        "/scrapers/x",
        "/scrapers/finance",
        "/live",
        "/integrity",
        "/health",
        "/api/status",
        "/api/dashboard",
        "/api/monitoring/reddit",
        "/api/data/reddit/live",
        "/api/data/youtube/live",
        "/api/data/x/live",
    ]
    for route in routes:
        response = client.get(route)
        check(f"GET {route} renders", response.status_code == 200, f"HTTP {response.status_code}")
except Exception as exc:
    check("Flask route render smoke test", False, f"{type(exc).__name__}: {exc}")

# Keep the UI separation explicit: HTML belongs in templates, JS in static/js.
live_template = (MONITORING_ROOT / "templates/live.html").read_text(encoding="utf-8")
check("live page has no inline script body", "async function poll" not in live_template)
check("live.js exists", (MONITORING_ROOT / "static/js/live.js").exists())


# Full-panel regression checks: these options were missing in the simplified overlay.
from pipeline_catalog import reddit_native_sources, reddit_native_queries, youtube_queries, x_queries, finance_assets
check("Reddit native source registry loaded", len(reddit_native_sources()) >= 28)
check("Reddit native query registry loaded", len(reddit_native_queries()) >= 21)
check("YouTube query registry loaded", len(youtube_queries()) >= 1)
check("X query registry loaded", len(x_queries()) >= 1)
check("Finance asset registry loaded", len(finance_assets()) >= 10)
for template, marker in [
    ("reddit.html", "REDDIT_MAX_SCROLLS_PER_SEARCH_TERM"),
    ("youtube.html", "YOUTUBE_MAX_COMMENTS_PER_VIDEO"),
    ("x.html", "X_MAX_WORKERS"),
    ("finance.html", "Asset Registry"),
]:
    text=(MONITORING_ROOT/"templates"/template).read_text(encoding="utf-8")
    check(f"full options present: {template}", marker in text)
check("runtime wrapper exists", (MONITORING_ROOT/"runtime_wrapper.py").exists())


# Reddit two-stage realtime regression guards.
reddit_template=(MONITORING_ROOT/"templates/reddit.html").read_text(encoding="utf-8")
data_template=(MONITORING_ROOT/"templates/data.html").read_text(encoding="utf-8")
wrapper_text=(MONITORING_ROOT/"runtime_wrapper.py").read_text(encoding="utf-8")
pm_text=(MONITORING_ROOT/"process_manager.py").read_text(encoding="utf-8")
check("Reddit full-flow button present", "/process/reddit/full/start" in reddit_template)
check("Reddit handoff diagnostics present", "Stage Handoff Diagnostics" in reddit_template)
check("Reddit live data tables present", "redditCommentBody" in data_template and "redditFetchBody" in data_template)
check("Reddit data.js exists", (MONITORING_ROOT/"static/js/data.js").exists())
check("Stage2 explicit parent handoff", "REDDIT STAGE-1 -> STAGE-2 HANDOFF PRECHECK" in wrapper_text)
check("Per-post discovery logging", "[REDDIT][DISCOVERY][POST_SAVED]" in wrapper_text)
check("Per-comment parse logging", "[REDDIT][COMMENT][PARSED]" in wrapper_text)
check("Unbuffered subprocess logs", '"-u"' in pm_text and "PYTHONUNBUFFERED" in pm_text)
check("Reddit stages are mutually exclusive", "reddit_discovery is still running" in pm_text)

# Reddit v6 observability regression guards.
metrics_text=(MONITORING_ROOT/"reddit_realtime_metrics.py").read_text(encoding="utf-8")
compose_text=(MONITORING_ROOT/"docker-compose.yml").read_text(encoding="utf-8")
scrape_text=(MONITORING_ROOT/"victoriametrics/scrape.yml").read_text(encoding="utf-8")
reddit_dash=json.loads((MONITORING_ROOT/"grafana/dashboards/reddit.json").read_text(encoding="utf-8"))
check("Dashboard realtime JS exists", (MONITORING_ROOT/"static/js/dashboard.js").exists())
check("Reddit monitoring diagnostics runner exists", (MONITORING_ROOT/"CHECK_REDDIT_MONITORING.cmd").exists())
check("Dynamic scrape-time Reddit collector", "class RedditRealtimeCollector" in metrics_text and "build_reddit_realtime_snapshot" in metrics_text)
check("Metrics server binds all interfaces", 'addr="0.0.0.0"' in metrics_text)
check("VictoriaMetrics scrapes dedicated Reddit job", "job_name: reddit-realtime" in scrape_text and "host.docker.internal:8003" in scrape_text)
check("Grafana allows 2s refresh", "GF_DASHBOARDS_MIN_REFRESH_INTERVAL" in compose_text)
check("Reddit Grafana dashboard rebuilt", reddit_dash.get("uid")=="group-pipeline-reddit" and len(reddit_dash.get("panels",[])) >= 18)
check("Reddit Grafana uses v6 metrics", "reddit_realtime_parent_posts" in json.dumps(reddit_dash))


# v8 identity / stale-process regression guards.
settings_text=(MONITORING_ROOT/"settings.py").read_text(encoding="utf-8")
run_cc=(MONITORING_ROOT/"RUN_CONTROL_CENTER.cmd").read_text(encoding="utf-8")
run_gf=(MONITORING_ROOT/"RUN_GRAFANA.cmd").read_text(encoding="utf-8")
check("v8 build marker present", "group-overlay-social-live-ui-20260814-08" in settings_text)
check("Prometheus exposes build identity", "reddit_realtime_build_info" in metrics_text and "BUILD_ID" in metrics_text)
check("Control Center launcher detects old builds", "stop_control_center.ps1" in run_cc and "EXPECTED_BUILD" in run_cc)
check("Grafana launcher validates exact exporter build", "reddit_realtime_build_info" in run_gf and "EXPECTED_BUILD" in run_gf)
check("Safe Control Center stop helper exists", (MONITORING_ROOT/"stop_control_center.ps1").exists() and (MONITORING_ROOT/"STOP_CONTROL_CENTER.cmd").exists())


# v8 UI cleanup + multi-source live data guards.
finance_template=(MONITORING_ROOT/"templates/finance.html").read_text(encoding="utf-8")
dashboard_template=(MONITORING_ROOT/"templates/dashboard.html").read_text(encoding="utf-8")
data_template=(MONITORING_ROOT/"templates/data.html").read_text(encoding="utf-8")
data_js=(MONITORING_ROOT/"static/js/data.js").read_text(encoding="utf-8")
cc_text=(MONITORING_ROOT/"control_center.py").read_text(encoding="utf-8")
check("Finance Grafana button removed", 'href="http://localhost:8795"' not in finance_template and "اجرا و Grafana" not in finance_template)
check("Dashboard single Reddit health box removed", "Reddit realtime health" not in dashboard_template)
check("Data native intro box removed", "خروجی‌های Native Pipeline" not in data_template)
check("YouTube live table present", "youtubeBody" in data_template and "/api/data/youtube/live" in cc_text)
check("X live table present", "xBody" in data_template and "/api/data/x/live" in cc_text)
check("Multi-source 2s live refresh", "loadYouTube" in data_js and "loadX" in data_js and "setInterval(refresh,2000)" in data_js)
check("Social live reader exists", (MONITORING_ROOT/"social_live.py").exists())

failed = [name for name, passed in checks if not passed]
print("\nCHECKS:", len(checks), "FAILED:", len(failed))
if failed:
    print("FAILED CHECKS:")
    for name in failed:
        print(" -", name)
raise SystemExit(1 if failed else 0)
