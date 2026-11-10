# وضعیت پیشرفت (برای ادامه بعد از قطع سشن)

**برنچ:** `claude/code-review-integrity-v2` — پایه: `main@8dc58dd`

**برای ادامه:** این فایل را بخوان، سپس از «قدم بعدی» ادامه بده. برنامه‌ی کامل در `README.md` است.

| مرحله | وضعیت | خروجی |
|---|---|---|
| ۰ نقشه‌ی پروژه | ✅ انجام شد | `01-architecture.md` |
| ۱ Baseline | ✅ انجام شد (۲ کاندیدای باگ) | `02-baseline.md` |
| ۲ ابزارهای خودکار | ✅ انجام شد (۴ کاندیدای جدید) | `03-static-analysis.md` |
| ۳ یکپارچگی ماژول‌ها | ✅ انجام شد (۲ بحرانی، C-03 رد شد) | `04-integration.md` |
| ۴ بررسی عمیق | ⬜ | `05-deep-review.md` |
| ۵ لیست نهایی | ⬜ | `FINDINGS.md` |
| ۶ رفع | ⬜ (منتظر تأیید کاربر) | — |

## قدم بعدی
مرحله‌ی ۴ (Opus 5.5 / high) — بررسی عمیق به ترتیب ریسک:
(۱) روش‌های آماری `group_comparison`, `event_study`, `sensitivity_analysis`, `composition_shift`؛
(۲) `normalize_text.py` (فارسی/عربی، نیم‌فاصله، PII)؛ (۳) `apply_eligibility.py` قواعد و `duplicate_analysis.py`؛
(۴) `llm_client.py` / `run_full_annotation.py` (سقف هزینه، retry، parse خروجی LLM)؛ (۵) `geo_confidence` رشته‌ای و `author_id_status` خالی در `yt_*`؛
(۶) collectorها فقط ایستا. خروجی: `05-deep-review.md`.
**سؤال‌های باز برای تیم (C-09, C-14, C-04):** فایل‌های `outputs/full_annotation/*.jsonl` و `annotated_dataset.parquet` منتشرشده؛ Salt استفاده‌شده.

## یادداشت‌های کاری
- `data/raw/` و `data/raw_original/` در ریپو خالی‌اند (gitignore) ← قدم `harmonize` احتمالاً بدون داده‌ی خام اجرا نمی‌شود؛ `data/raw_harmonized/*.parquet` اما در ریپو هست.
- venv: `<scratchpad>/venv` (در سشن جدید دوباره ساخته شود؛ نصب ~۱۱ دقیقه). کپی کاری: `<scratchpad>/work`.
- برنچ کاری: `claude/code-review-integrity-v2` (از آخرین `main`؛ روی `main` هیچ کاری انجام نمی‌شود). push با `git push -u origin claude/code-review-integrity-v2`. برنچ قدیمی `...-kc1fy1` کنار گذاشته شد.
- کاندیدای باگ: C-01 (`group_comparison` crash بدون annotation، مهم)، C-02 (پیام harmonize)، C-03 (آزمون idempotency)، **C-04 (Salt: کد `AUTHOR_HASH_SALT` می‌خواند، مستندات `PROJECT_AUTHOR_SALT`؛ fallback عمومی، مهم)**، C-05 (python-dotenv)، C-06 (yfinance pin نشده)، C-07 (hygiene).
- **مرحله‌ی ۳:** C-08 بحرانی تأییدشده (۴۵٪ یوتیوب annotate نمی‌شود؛ اعداد §۷.۱ گزارش دقیقاً بازتولید شد)، C-09 بحرانی-اگر-فعال (شمارش ردیف به‌جای محتوا)، C-10 (sort ناپایدار)، C-11..C-14 جزئی/سؤال. C-03 رد شد (idempotent است).
- ابزارهای مرحله‌ی ۲ در venv scratchpad نصب‌اند؛ در سشن جدید: `pip install ruff mypy vulture pip-audit detect-secrets`.
- همه‌ی ردیف‌های `annotated_dataset.parquet` در این baseline `pending_annotation` است؛ نتایج آماری قابل استناد نیستند.
