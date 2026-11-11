# T11: داده تا امروز: YouTube و مالی
- موج 3 | هدف کاربر | مدل: Sonnet / medium | وابستگی: T06، T10 | **نیاز به کاربر: بله**

## پیش‌نیاز از کاربر (رهبر بپرسد)
- `YOUTUBE_API_KEY` و `FRED_API_KEY` با فرم امن (`request_credential`)، هرگز در چت.
- اجازه‌ی شبکه برای میزبان‌های لازم (مثلاً `youtube.googleapis.com`، `api.stlouisfed.org`، `query1.finance.yahoo.com`) با `update_environment`؛ کاربر تأیید می‌کند.
- اگر ترجیح کاربر اجرا روی کامپیوتر خودش است: دستورها را در یک `docs/how_to_refresh.md` کوتاه بنویس.

## کار
1. `date_range.end = today` (از T06).
2. YouTube افزایشی: quota روزانه ۱۰,۰۰۰ واحد است؛ ممکن است چند روز طول بکشد. برنامه‌ی روزانه و پیشرفت را در run log ثبت کن.
3. `backfill_raw_harmonized_v05.py` (فقط فایل‌های جدید)، `apply_eligibility.py`، `normalize_text.py`، `duplicate_analysis.py`.
4. مالی: `finance_market_extract.py` و `build_financial_outputs.py` تا امروز؛ frozen inputs نسخه‌ی جدید (نسخه‌ی قبلی بماند).

## معیار پذیرش
جدول پوشش هفتگی (پلتفرم × هفته) تا W37 با تعداد رکورد؛ هفته‌های خالی صریح نشان داده شوند. هیچ فایل `data/raw_harmonized` قدیمی بازنویسی نشود.
