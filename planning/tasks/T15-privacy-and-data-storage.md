# T15: حریم خصوصی و داده بیرون از git
- موج 4 (تصمیم زود لازم است) | مهم | یافته: C-04 | مدل: Opus / medium | **نیاز به کاربر: بله (ریپو عمومی یا خصوصی)**

## مسئله
- حدود ۱۰۰ مگابایت parquet داخل git (`data/raw_harmonized/`، ۳۳۳ هزار رکورد با `text_raw` کاربران و `author_hash`).
- C-04: کد فقط `AUTHOR_HASH_SALT` را می‌خواند (`author_hash.py:38`)؛ `.env.example:14` و `docs/raw_schema_v03.md:312`، `docs/raw_schema_v05.md:110` از `PROJECT_AUTHOR_SALT` می‌گویند.
  بدون Salt، fallback ثابت عمومی (`author_hash.py:31`) استفاده می‌شود و فقط یک بار هشدار چاپ می‌شود. شناسه‌ی کانال یوتیوب عمومی است، پس hash با Salt عمومی قابل بازسازی است.
- `record_uid = sha256(platform:file:row_number)` به نام فایل و ترتیب ردیف وابسته است.

## تغییر
1. یک نام: `AUTHOR_HASH_SALT`. `PROJECT_AUTHOR_SALT` از `.env.example` و اسناد حذف. نبود Salt در جمع‌آوری = خطا، نه fallback (برای دمو یک حالت صریح جدا).
2. داده بیرون از git: گزینه‌ها Git LFS، DVC، GitHub Release، Hugging Face Dataset خصوصی. پیشنهاد: Release یا HF خصوصی + اسکریپت `scripts/fetch_data.py`.
   فقط `data/demo/` در ریپو. پاک کردن از تاریخچه‌ی ریپوی تیم بازنویسی تاریخچه است؛ با T20 هماهنگ شود.
3. اگر ریپو عمومی می‌شود: نسخه‌ی عمومی بدون `text_raw` و `author_hash` واقعی، یا hash دوباره با Salt محرمانه. هیچ متن کاربر در README، داشبورد عمومی یا پست.

## معیار پذیرش
کاربر تصمیم را تأیید کرده؛ clone تمیز با `fetch_data.py` (با دسترسی) یا `make demo` (بدون دسترسی) کار کند؛ grep در ریپوی عمومی هیچ `text_raw` واقعی نشان ندهد.
