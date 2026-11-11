# T06: بازه‌ی زمانی قابل تنظیم از یک منبع
- موج 2 | مهم (هدف کاربر) | یافته: C-12 | مدل: Opus / high | وابستگی: T02، T03 | نیاز به کاربر: خیر

## مسئله
پنجره در چند جا ثابت است و `config.yaml` عمداً در تحلیل خوانده نمی‌شود:
`src/ingestion/project_calendar.py:19-20` (`START`, `END`)، `src/temporal_analysis/common.py:42-43` (`WEEKS` = W01..W21، `PARTIAL_WEEK`)،
`src/ingestion/reddit_raw_json_pipeline.py:110` و `reddit_parent_post_collector.py:84` (`PROJECT_START`)، `src/ingestion/x_scraper.py:3119` (چک `'2026-02-28'`)،
`src/temporal_analysis/build_financial_outputs.py:346` (چک «دقیقاً ۲۱ هفته»)، `src/event_analysis/event_registry.py`.

## تغییر
1. `config.yaml`: `date_range: {start: "2026-02-28", end: "2026-07-22" | "today"}`. پیش‌فرض همان بازه‌ی فعلی تا نتایج قبلی بازتولیدپذیر بمانند.
2. `project_calendar`: START/END و تابع `weeks()` از config؛ `"today"` در شروع اجرا یک بار حل و در manifest اجرا ثبت شود. هفته‌ی آخر کوتاه‌تر از ۷ روز = partial.
3. `common.WEEKS` و `PARTIAL_WEEK` از `project_calendar` مشتق شوند. collectorها و چک‌های بالا از همین منبع بخوانند.
4. `run_pipeline.py`: `--start` و `--end` (override روی config). چک مالی «۲۱ هفته» = «تعداد هفته‌ی محاسبه‌شده».
5. `event_registry`: فقط رویدادهای داخل بازه فعال باشند.

## تست
پیش‌فرض: ۲۱ هفته، W21 = ۵ روز partial. `end=2026-11-10`: ۳۷ هفته، W37 = ۴ روز partial. تاریخ قبل از start = `OUT`.

## معیار پذیرش
grep تاریخ‌های ثابت در `src/` فقط در config و تست‌ها؛ pipeline پیش‌فرض روی کپی همان اعداد قبلی را بدهد.
