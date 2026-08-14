# Reddit Realtime Integration — v5

این نسخه بدون تغییر فایل‌های `repo/`، handoff دو مرحله‌ی Reddit را در Overlay صریح و قابل مانیتور کرده است.

## Flow

```text
reddit_parent_post_collector.py
        ↓ native *_reddit_parent_posts.csv
runtime handoff diagnostics
        ↓
reddit_raw_json_pipeline.py
        ↓ .json URL
raw_reddit_json/<post_id>.json
        ↓
comments_from_raw_json.csv / comments_project_window.csv
```

## تغییرات Overlay

- اجرای subprocessها با `python -u` و `PYTHONUNBUFFERED=1` برای Live Log واقعی.
- جلوگیری از اجرای هم‌زمان Discovery و Raw JSON، چون هر دو می‌توانند یک Firefox Profile مشترک داشته باشند.
- دکمه‌ی `Start Full Reddit Flow` برای اجرای خودکار `Discovery → Raw JSON/Comments`.
- Stage-2 preflight که قبل از Firefox موارد زیر را لاگ می‌کند:
  - تعداد parent CSVها
  - تعداد unique parent postها
  - تعداد eligible postها
  - تعداد raw JSON موجود
  - تعداد JSON URLهای pending
  - تمام JSON URLهای صف Stage 2
- لاگ ریزدانه:
  - `POST_SAVED`
  - `JSON_FETCH START/RESULT`
  - `RAW_JSON SAVED_AND_PARSED`
  - `COMMENT PARSED`
  - `COMMENTS_CSV SAVED`
- Data tab با refresh دو ثانیه‌ای برای:
  - Parent posts
  - JSON fetch events
  - Comments خوانده‌شده مستقیم از Raw JSONهای ذخیره‌شده
- Metrics جدید برای Grafana:
  - `reddit_parent_posts_unique`
  - `reddit_parent_posts_eligible_for_json`
  - `reddit_json_pending_fetch`
  - `reddit_json_fetch_events_total`
  - `reddit_json_fetch_status_total{status=...}`
  - `reddit_raw_json_files_total`
  - `reddit_comments_live_from_raw_json`
  - `reddit_comments_native_total`
  - `reddit_comments_project_window_total`
- VictoriaMetrics scrape interval: `2s`
- Grafana Reddit dashboard: refresh `5s`

## نکته مهم eligibility

Pipeline اصلی فقط parent postهای واجد شرایط project window + lookback را برای JSON collection انتخاب می‌کند. اگر `Eligible for JSON = 0` باشد، باز نشدن JSON URL خطای Overlay نیست؛ پنل این وضعیت را صریح نشان می‌دهد.

## Resume

`Resume existing JSON` به‌صورت پیش‌فرض فعال است. اگر همه‌ی JSONهای واجد شرایط از قبل وجود داشته باشند، `Pending JSON Fetch = 0` خواهد بود و fetch جدید انجام نمی‌شود.

فایل‌های اصلی Pipeline گروه در `repo/` تغییر نکرده‌اند.
