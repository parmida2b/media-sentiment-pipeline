# T01: جمعیت annotation همه‌ی ردیف‌های eligible را بپوشاند
- موج 1 | بحرانی | یافته‌ها: C-08، C-13 | مدل: Opus / high | وابستگی: ندارد | نیاز به کاربر: خیر
- فایل‌ها: `src/common/ids.py` (جدید)، `src/annotation/run_full_annotation.py` (فقط `load_eligible_records`)، `src/annotation/build_labeling_sample.py`،
  `src/annotation/build_annotated_dataset.py`، `src/preprocessing/apply_eligibility.py:265`، `src/preprocessing/duplicate_analysis.py:63-75`، `tests/test_content_id.py` (جدید)

## مسئله
قاعده‌ی کلید محتوا («`platform_content_id` اگر هست، وگرنه `uid::<record_uid>`») در سه جا جداگانه نوشته شده (`apply_eligibility.py:265`،
`duplicate_analysis.py:75`، `build_annotated_dataset.py:118-121`) ولی در `run_full_annotation.py:207-211` نیست. آنجا `dropna(subset=["content_id"])`
ردیف‌های legacy یوتیوب را حذف می‌کند: ۵۴,۸۶۲ ردیف (۴۵٪ یوتیوب، W01 تا W07 تا ۹۷٪) هرگز annotate نمی‌شوند.
`build_labeling_sample.py:197` هم برای این ردیف‌ها `content_id = ""` می‌گذارد.

## تغییر
1. `src/common/ids.py`: تابع `content_id(df) -> pd.Series` (و نسخه‌ی تک‌ردیفی اگر لازم). خالی بودن = `NaN` یا رشته‌ی خالی/فاصله.
2. هر پنج محل بالا از همین تابع استفاده کنند. خروجی پل و eligibility نباید تغییر کند (همان قاعده).
3. `load_eligible_records` ستون `record_uid` را هم بخواند و `content_id` را با این تابع بسازد؛ `dropna` فقط روی متن.

## تست (اول باید fail شود)
- ردیف با `platform_content_id=None` و `record_uid="abc"` در خروجی `load_eligible_records` با `content_id == "uid::abc"` باشد (با monkeypatch مسیر parquetها به فایل موقت).
- `build_labeling_sample` برای همین ردیف `content_id` خالی تولید نکند.
- `content_id` روی ورودی‌های مخلوط با خروجی فعلی `duplicate_analysis._row_key` برابر باشد.

## معیار پذیرش
- روی کپی کاری با داده‌ی ریپو: جمعیت annotation ≈ ۲۸۷,۸۶۸ منهای ردیف‌های بدون متن (قبلاً ۲۳۳,۰۰۶). اعداد را گزارش کن.
- `stratified_subsample(cap=120, seed=1405)`: سلول‌های یوتیوب W03، W04، W07 به ۱۲۰ برسند.
- خروجی `build_annotated_dataset.py` و `apply_eligibility.py` قبل/بعد یکسان (hash).

## خارج از محدوده
اجرای annotation پولی (T14). تغییر فرمول `record_uid` (ریسک ثبت‌شده: به نام فایل و شماره‌ی ردیف وابسته است؛ فقط در کارت T15 بررسی شود).
