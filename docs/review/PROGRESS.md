# وضعیت پیشرفت (برای ادامه بعد از قطع سشن)

**برای ادامه:** این فایل را بخوان، سپس از «قدم بعدی» ادامه بده. برنامه‌ی کامل در `README.md` است.

| مرحله | وضعیت | خروجی |
|---|---|---|
| ۰ نقشه‌ی پروژه | ✅ انجام شد | `01-architecture.md` |
| ۱ Baseline | ⏳ در حال انجام | `02-baseline.md` |
| ۲ ابزارهای خودکار | ⬜ | `03-static-analysis.md` |
| ۳ یکپارچگی ماژول‌ها | ⬜ | `04-integration.md` |
| ۴ بررسی عمیق | ⬜ | `05-deep-review.md` |
| ۵ لیست نهایی | ⬜ | `FINDINGS.md` |
| ۶ رفع | ⬜ (منتظر تأیید کاربر) | — |

## قدم بعدی
مرحله‌ی ۱: ساخت venv در scratchpad، `pip install -r requirements.txt`، اجرای `pytest`،
سپس `python src/pipeline/run_pipeline.py --list` و اجرای مراحل بدون Gate.

## یادداشت‌های کاری
- `data/raw/` و `data/raw_original/` در ریپو خالی‌اند (gitignore) ← قدم `harmonize` احتمالاً بدون داده‌ی خام اجرا نمی‌شود؛ `data/raw_harmonized/*.parquet` اما در ریپو هست.
