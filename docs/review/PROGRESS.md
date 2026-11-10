# وضعیت پیشرفت (برای ادامه بعد از قطع سشن)

**برنچ:** `claude/code-review-integrity-v2` — پایه: `main@8dc58dd`

**برای ادامه:** این فایل را بخوان، سپس از «قدم بعدی» ادامه بده. برنامه‌ی کامل در `README.md` است.

| مرحله | وضعیت | خروجی |
|---|---|---|
| ۰ نقشه‌ی پروژه | ✅ انجام شد | `01-architecture.md` |
| ۱ Baseline | ✅ انجام شد (۲ کاندیدای باگ) | `02-baseline.md` |
| ۲ ابزارهای خودکار | ✅ انجام شد (۴ کاندیدای جدید) | `03-static-analysis.md` |
| ۳ یکپارچگی ماژول‌ها | ⬜ | `04-integration.md` |
| ۴ بررسی عمیق | ⬜ | `05-deep-review.md` |
| ۵ لیست نهایی | ⬜ | `FINDINGS.md` |
| ۶ رفع | ⬜ (منتظر تأیید کاربر) | — |

## قدم بعدی
**مرحله‌ی ۳ (بررسی مرز ماژول‌ها) — نیاز به تغییر مدل: کاربر باید با `/model` به Opus 5.5 برود و effort را `high` بگذارد.**
کارهای مرحله‌ی ۳: (۱) schema/ستون‌ها بین raw_harmonized ← interim ← annotated_dataset، (۲) `config/raw_schema_columns.py` در برابر `_v05.py`،
(۳) ورودی واقعی `build_annotated_dataset.py` (docstring می‌گوید `clean.jsonl`)، (۴) آزمون idempotency مراحل in-place (C-03)،
(۵) ناسازگاری نام Salt (C-04) و پیگیری‌اش، (۶) مسیرها/کانفیگ هاردکد. خروجی: `04-integration.md`.

## یادداشت‌های کاری
- `data/raw/` و `data/raw_original/` در ریپو خالی‌اند (gitignore) ← قدم `harmonize` احتمالاً بدون داده‌ی خام اجرا نمی‌شود؛ `data/raw_harmonized/*.parquet` اما در ریپو هست.
- venv: `<scratchpad>/venv` (در سشن جدید دوباره ساخته شود؛ نصب ~۱۱ دقیقه). کپی کاری: `<scratchpad>/work`.
- برنچ کاری: `claude/code-review-integrity-v2` (از آخرین `main`؛ روی `main` هیچ کاری انجام نمی‌شود). push با `git push -u origin claude/code-review-integrity-v2`. برنچ قدیمی `...-kc1fy1` کنار گذاشته شد.
- کاندیدای باگ: C-01 (`group_comparison` crash بدون annotation، مهم)، C-02 (پیام harmonize)، C-03 (آزمون idempotency)، **C-04 (Salt: کد `AUTHOR_HASH_SALT` می‌خواند، مستندات `PROJECT_AUTHOR_SALT`؛ fallback عمومی، مهم)**، C-05 (python-dotenv)، C-06 (yfinance pin نشده)، C-07 (hygiene).
- ابزارهای مرحله‌ی ۲ در venv scratchpad نصب‌اند؛ در سشن جدید: `pip install ruff mypy vulture pip-audit detect-secrets`.
- همه‌ی ردیف‌های `annotated_dataset.parquet` در این baseline `pending_annotation` است؛ نتایج آماری قابل استناد نیستند.
