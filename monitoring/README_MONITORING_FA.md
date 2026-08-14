# لایه Monitoring بیرونی برای Pipeline گروه

## اصل طراحی
پوشه `../repo` همان pipeline گروه است و برای اضافه‌کردن Control Center هیچ فایل source آن patch نشده است. تمام integration در این پوشه (`monitoring`) قرار دارد.

## اجرا
1. `START_CONTROL_CENTER.cmd` در ریشه bundle را اجرا کنید.
2. برای Grafana، Docker Desktop را روشن کنید و `START_GRAFANA.cmd` را اجرا کنید.
3. Control Center: `http://127.0.0.1:8020`
4. Metrics: `http://127.0.0.1:8003/metrics`
5. Grafana: `http://127.0.0.1:8795` (admin/admin)

## Collectorهای اصلی که بدون تغییر اجرا می‌شوند
- Reddit discovery: `repo/src/ingestion/reddit_parent_post_collector.py`
- Reddit comments/audit: `repo/src/ingestion/reddit_raw_json_pipeline.py`
- YouTube: `repo/src/ingestion/youtube_extract.py`
- X: `repo/src/ingestion/x_scraper.py`
- Finance: `python -m src.ingestion.finance_market_extract`

## Credentialها
Credentialها در `monitoring/state/control_plane.db` نگهداری می‌شوند و هنگام Start فقط به environment process مربوطه تزریق می‌شوند. `.env` در repo نوشته یا اصلاح نمی‌شود.

## Storage
Overlay storage اصلی pipeline را تغییر نمی‌دهد:
- Reddit: CSV/Raw JSONهای native pipeline
- YouTube: JSONL/CSV/manifest/checkpoint native pipeline
- X: SQLite خود `x_scraper.py`
- Finance: run directories و CSVهای خود `finance_market_extract.py`

## Integrity
`monitoring/PIPELINE_SOURCE.sha256` hash فایل‌های source/config محافظت‌شده در زمان تحویل است. Control Center قبل از بالا آمدن `verify_pipeline_unchanged.py` را اجرا می‌کند. پوشه‌های runtime مثل `data/raw`, `data/interim`, `outputs` عمداً از این check خارج‌اند.

## نکته ویندوز: مسیر virtual environment
برای جلوگیری از محدودیت طول مسیر ویندوز، runner محیط مجازی را داخل پوشه پروژه نمی‌سازد. مسیر پیش‌فرض آن این است:

`%LOCALAPPDATA%\group-pipeline-monitoring-overlay\.venv312`

این تغییر فقط مربوط به لایه monitoring است و هیچ فایل داخل `repo/` را تغییر نمی‌دهد.

## Regression guard رابط کاربری
قبل از اجرای Control Center، فایل `smoke_test_overlay.py` تمام routeهای GET اصلی را با Flask test client رندر می‌کند. بنابراین خطاهای Jinja/context مانند `UndefinedError` قبل از start شدن سرور شناسایی می‌شوند. JavaScript رابط کاربری نیز در `static/js/` نگه‌داری می‌شود و فایل‌های pipeline اصلی همچنان در `repo/` بدون patch باقی می‌مانند.
