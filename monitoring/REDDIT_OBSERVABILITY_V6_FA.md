# Reddit Realtime Observability — v6

این نسخه دو مشکل اصلی را اصلاح می‌کند:

1. کارت‌های Dashboard کنترل‌سنتر هر ۲ ثانیه از `/api/dashboard` به‌روزرسانی می‌شوند.
2. متریک‌های Reddit دیگر به cache حلقه‌ی background وابسته نیستند؛ سری‌های `reddit_realtime_*` در لحظه‌ی هر Prometheus scrape از خروجی‌های native Pipeline محاسبه می‌شوند.

## مسیر داده

```text
reddit_parent_post_collector.py
        ↓
*_reddit_parent_posts.csv
        ↓
reddit_raw_json_pipeline.py
        ↓
raw_reddit_json/*.json
        ↓
comments_from_raw_json.csv / comments_project_window.csv
        ↓
Read-only observability overlay
        ↓
:8003/metrics
        ↓
VictoriaMetrics :8428
        ↓
Grafana :8795
```

## متریک‌های مهم

```text
reddit_realtime_exporter_up
reddit_realtime_system_health
reddit_realtime_process_running{stage="discovery"}
reddit_realtime_process_running{stage="json_comments"}
reddit_realtime_parent_posts
reddit_realtime_json_eligible
reddit_realtime_json_pending
reddit_realtime_raw_json_files
reddit_realtime_comments_live
reddit_realtime_fetch_success
reddit_realtime_fetch_failed
reddit_realtime_output_age_seconds{output="parent_posts"}
reddit_realtime_output_age_seconds{output="raw_json"}
reddit_realtime_parent_posts_by_subreddit{subreddit="..."}
reddit_realtime_parent_posts_by_query{query_id="..."}
```

## تست سریع

Control Center را اجرا کن و این URL را باز کن:

```text
http://127.0.0.1:8003/metrics
```

باید `reddit_realtime_exporter_up 1.0` را ببینی.

سپس `START_GRAFANA.cmd` را اجرا کن. این Runner کانتینرهای قدیمی را حذف و stack جدید را recreate می‌کند، پنج ثانیه صبر می‌کند و query زیر را روی VictoriaMetrics تست می‌کند:

```text
reddit_realtime_exporter_up
```

آدرس‌ها:

```text
Metrics:                 http://127.0.0.1:8003/metrics
VictoriaMetrics targets: http://127.0.0.1:8428/targets
VictoriaMetrics:         http://127.0.0.1:8428
Grafana:                 http://127.0.0.1:8795
```

Dashboard اصلی:

```text
Group Pipeline — Reddit Realtime Health
```

## اصل Integrity

تمام تغییرات فقط در `monitoring/` هستند. فایل‌های `repo/` در این نسخه تغییر نکرده‌اند.
