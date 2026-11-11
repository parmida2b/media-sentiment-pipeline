# T02: شمارش در سطح محتوا و Target صریح در Pipeline B
- موج 1 | بحرانی | یافته: C-09 | مدل: Opus / high | وابستگی: T04 | نیاز به کاربر: خیر
- فایل‌ها: `src/temporal_analysis/common.py`، `weekly_trend.py`، `descriptive_stats.py`، `composition_shift.py`، `group_comparison.py`،
  `sensitivity_analysis.py`، `build_social_weekly_outcomes.py`، `tests/test_content_level.py` (جدید)

## مسئله
پل برای هر (content_id, target) یک ردیف می‌سازد و sentiment/emotion/content_type را تکرار می‌کند. هیچ ماژول Pipeline B (جز `event_study`)
روی `content_id` یکتا نمی‌کند و روی target فیلتر نمی‌کند. بازتولید: محتوای A با ۳ Target (positive) و B با ۱ Target (unclear)
در `weekly_trend.build_axis_trend` نتیجه‌ی `n=4`، positive=0.75 می‌دهد؛ درست: `n=2`، 0.50. stance نسبت به Targetهای مختلف در یک نسبت مخلوط می‌شود.
راهنمای رسمی (`docs/how_to_run_pipeline_fa.md:55`) `--targets T01,T02,T03` را توصیه می‌کند.

## تغییر
1. در `common.py` دو تابع: `content_level(df)` (یک ردیف برای هر `content_id`، انتخاب قطعی، مثلاً اولویت T01 بعد کوچک‌ترین target) و
   `stance_rows(df, target_id)` (فقط ردیف‌های همان Target).
2. محورهای sentiment/emotion/content_type همه‌جا روی `content_level`. محور stance همیشه با Target صریح:
   - `weekly_trend`: جدول stance به تفکیک `target` (ستون جدید).
   - `group_comparison`: chi-square و Fisher روی stance برای هر Target جدا (یا پارامتر با پیش‌فرض T01).
   - `build_social_weekly_outcomes`: `support/oppose/unclear_share` برای هر Target با ستون `target_id` پرشده؛ `n_records` = محتوای یکتا.
   - `descriptive_stats`، `composition_shift`، `sensitivity_analysis`: سهم‌ها و n روی محتوای یکتا؛ Author-balanced هم روی `content_level`.
3. اسم ستون‌ها و فرمت خروجی را بی‌دلیل عوض نکن؛ فقط ستون `target` اضافه شود.

## تست
- همان مثال دو محتوایی برای هر ماژول (حداقل weekly_trend، build_social_weekly_outcomes، sensitivity positive_share).
- داده‌ی تک‌Target: خروجی قبل/بعد یکسان (رگرسیون). از `scripts/make_synthetic_annotated_dataset.py` برای داده‌ی ساختگی استفاده کن و قبل/بعد مقایسه کن.

## معیار پذیرش
تست‌ها سبز؛ اجرای Pipeline B روی داده‌ی ساختگی تک‌Target بدون تغییر عددی؛ با سه Target، n برابر تعداد محتوا.
