# علت No Data در Grafana و اصلاح v7

## علت اصلی

VictoriaMetrics target روی `host.docker.internal:8003` حالت `UP` داشت، اما query متریک
`reddit_realtime_exporter_up` هیچ series برنمی‌گرداند. این یعنی اتصال شبکه سالم بود ولی
سرویسی که روی 8003 پاسخ می‌داد exporter مورد انتظار v6 نبود.

در اسکرین‌شات Control Center نیز `Pipeline root` هنوز به فولدر `v5-reddit-realtime`
اشاره می‌کرد. بنابراین Control Center قدیمی v5 روی پورت‌های 8020/8003 باز مانده بود و
Grafana/VictoriaMetrics جدید همان exporter قدیمی را scrape می‌کردند.

## چرا RUN_GRAFANA قبلی متوجه نشد؟

Runner قبلی فقط بررسی می‌کرد که `http://127.0.0.1:8003/metrics` پاسخ HTTP بدهد. بنابراین
هر exporter قدیمی هم به اشتباه `[OK]` محسوب می‌شد.

## اصلاح v7

- متریک جدید `reddit_realtime_build_info{build_id="..."} 1` اضافه شد.
- `/health` و `/metrics` هر دو Build ID یکسان را اعلام می‌کنند.
- `START_CONTROL_CENTER.cmd` قبل از اجرا نسخه قدیمی را شناسایی می‌کند.
- فقط Python processی که `control_center.py` است روی پورت‌های 8020/8003 به صورت safe cleanup بسته می‌شود.
- اگر پورت متعلق به برنامه دیگری باشد، launcher آن را kill نمی‌کند و با خطای روشن متوقف می‌شود.
- `START_GRAFANA.cmd` دیگر صرفاً reachability را کافی نمی‌داند؛ دقیقاً Build ID و
  `reddit_realtime_exporter_up` را بررسی می‌کند.
- بعد از بالا آمدن Docker، runner تا زمانی که VictoriaMetrics واقعاً همان metric را ingest نکند موفق اعلام نمی‌شود.

## تست درست

پس از اجرای v7:

```text
http://127.0.0.1:8020/health
```

باید Build زیر را نشان دهد:

```text
group-overlay-reddit-observability-20260814-07
```

و در:

```text
http://127.0.0.1:8003/metrics
```

باید حداقل این دو series وجود داشته باشند:

```text
reddit_realtime_exporter_up 1.0
reddit_realtime_build_info{build_id="group-overlay-reddit-observability-20260814-07"} 1.0
```

سپس VictoriaMetrics query برای `reddit_realtime_exporter_up` باید یک result غیرخالی برگرداند.
