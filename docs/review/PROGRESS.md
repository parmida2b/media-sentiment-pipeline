# وضعیت پیشرفت (برای ادامه بعد از قطع سشن)

**برنچ:** `claude/code-review-integrity-v2` — پایه: `main@8dc58dd`

**برای ادامه:** این فایل را بخوان، سپس از «قدم بعدی» ادامه بده. برنامه‌ی کامل در `README.md` است.

| مرحله | وضعیت | خروجی |
|---|---|---|
| ۰ نقشه‌ی پروژه | ✅ انجام شد | `01-architecture.md` |
| ۱ Baseline | ✅ انجام شد (۲ کاندیدای باگ) | `02-baseline.md` |
| ۲ ابزارهای خودکار | ⬜ | `03-static-analysis.md` |
| ۳ یکپارچگی ماژول‌ها | ⬜ | `04-integration.md` |
| ۴ بررسی عمیق | ⬜ | `05-deep-review.md` |
| ۵ لیست نهایی | ⬜ | `FINDINGS.md` |
| ۶ رفع | ⬜ (منتظر تأیید کاربر) | — |

## قدم بعدی
مرحله‌ی ۲: نصب ruff، mypy/pyright، vulture، pip-audit، gitleaks در venv scratchpad و اجرا روی `src/` و `config/`؛
خروجی در `03-static-analysis.md`. سپس مرحله‌ی ۳ (Opus 5.5 / high).

## یادداشت‌های کاری
- `data/raw/` و `data/raw_original/` در ریپو خالی‌اند (gitignore) ← قدم `harmonize` احتمالاً بدون داده‌ی خام اجرا نمی‌شود؛ `data/raw_harmonized/*.parquet` اما در ریپو هست.
- venv: `<scratchpad>/venv` (در سشن جدید دوباره ساخته شود؛ نصب ~۱۱ دقیقه). کپی کاری: `<scratchpad>/work`.
- برنچ کاری: `claude/code-review-integrity-v2` (از آخرین `main`؛ روی `main` هیچ کاری انجام نمی‌شود). push با `git push -u origin claude/code-review-integrity-v2`. برنچ قدیمی `...-kc1fy1` کنار گذاشته شد.
- کاندیدای باگ: C-01 (`group_comparison` crash بدون annotation)، C-02 (پیام گمراه‌کننده‌ی harmonize)، C-03 (آزمون idempotency).
- همه‌ی ردیف‌های `annotated_dataset.parquet` در این baseline `pending_annotation` است؛ نتایج آماری قابل استناد نیستند.
