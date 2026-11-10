# مرحله ۱ — Baseline (نصب، تست، اجرای pipeline)

> همه‌ی اجراها روی **کپی** ریپو در scratchpad انجام شد؛ ریپوی اصلی دست‌نخورده است
> (چون `normalize_text` و `duplicate_analysis` فایل‌ها را در جا بازنویسی می‌کنند).
> محیط: Python 3.13.18، نصب تمیز از `requirements.txt` + `pytest`.

## ۱. نصب
- هر ۱۶ بسته‌ی `requirements.txt` بدون تداخل نصب شد (نسخه‌های pin‌شده سازگارند).
- `yfinance` pin نشده (تنها مورد) ← ریسک تکرارپذیری؛ در مرحله‌ی ۲ ثبت می‌شود.
- نصب به‌خاطر کندی شبکه ~۱۱ دقیقه طول کشید؛ مشکل کد نبود.

## ۲. تست‌های موجود
`pytest`: **55 passed** در ۰.۶ ثانیه.
پوشش محدود است: فقط `config_loader`، `schema`، `automation_risk`، helperهای `apply_eligibility` و
`temporal_analysis/common`. برای collectorها، annotation، validation، event_study و بیشتر مراحل تحلیل تست وجود ندارد.

## ۳. اجرای pipeline پیش‌فرض (بدون Gateها)

| قدم | نتیجه | زمان |
|---|---|---|
| harmonize | ❌ exit 1 — **محدودیت محیط**: `data/raw/` در ریپو نیست (gitignore). با `--skip harmonize` رد شد؛ `data/raw_harmonized/*.parquet` در ریپو هست | 0.4s |
| eligibility | ✅ | 17.7s |
| normalize_text | ✅ | 180.1s |
| duplicate_analysis | ✅ | 136.0s |
| bridge (`build_annotated_dataset`) | ✅ | 2.0s |
| descriptive_stats | ✅ | 5.6s |
| weekly_trend | ✅ | 0.9s |
| composition_shift | ✅ | 17.2s |
| **group_comparison** | ❌ **`ValueError: No data; observed has size 0`** | 1.4s |
| sensitivity_analysis | ✅ (جداگانه اجرا شد) | — |
| event_study | ✅ (جداگانه اجرا شد) | — |
| social_weekly_outcomes | ✅ (جداگانه اجرا شد) | — |

Gateهای خاموش (ingestion، profiling، financial، annotation، notebooks) اجرا نشدند: API/Selenium/داده‌ی خام/هزینه‌ی LLM لازم دارند.

## ۴. وضعیت داده‌ی خروجی bridge
`data/processed/annotated_dataset.parquet`: **287,868 ردیف، 40 ستون**
- `annotation_status`: **همه `pending_annotation`** (خروجی annotation در ریپو نیست؛ `outputs/full_annotation/` gitignore است)
- پلتفرم‌ها: reddit 150,647 — youtube 121,429 — x 15,792

⚠️ پیامد: تمام مراحل Pipeline B در این baseline روی داده‌ی **بدون annotation** اجرا شده‌اند.
«موفق بودن» آن‌ها یعنی اجرا شدند، نه اینکه نتیجه‌ی آماری‌شان درست است. درستی آماری فقط با داده‌ی annotated قابل سنجش است.

## ۵. یافته‌های کاندیدا (هنوز در FINDINGS.md نهایی نشده‌اند)

### C-01 — `group_comparison.py` وقتی ردیف annotated نیست crash می‌کند (مهم)
- **شواهد:** `src/temporal_analysis/group_comparison.py:274` ← `ok = df[df["annotation_status"]=="ok"]` خالی است ←
  `chi_square_test` (خط ~164) بدون بررسی خالی بودن `scipy.stats.chi2_contingency` را صدا می‌زند ← `ValueError`.
- **ناسازگاری داخلی:** همین ماژول برای `engagement_score` ردیف شفاف «not_applicable» می‌سازد
  (`engagement_not_applicable_row`، خط ~205)؛ `composition_shift` هم ردیف data-gap تولید کرد.
  اما chi-square (و احتمالاً Fisher/Mann-Whitney/Welch در ادامه) محافظ ندارد.
- **چرا مهم است:** `run_pipeline.py` و docstring bridge هر دو ادعا می‌کنند bridge بدون annotation هم کار می‌کند
  و مراحل Pipeline B «محاسبه‌ی محلی خالص»اند. در عمل زنجیره روی `group_comparison` می‌شکند و
  `--skip` ندارد جلوتر برود (سه مرحله‌ی بعدی را فقط با اجرای جداگانه دیدیم).
- **وضعیت:** بازتولید شده (اجرای واقعی). ریشه‌ی علت (نبود annotation) محیطی است، ولی نبود محافظ باگ کد است.
- **تست بازتولید پیشنهادی (مرحله ۶):** `run()` با DataFrame بدون ردیف `ok` نباید exception بدهد.

### C-02 — پیام‌دهی گمراه‌کننده‌ی `backfill_raw_harmonized_v05.py` (جزئی)
- **شواهد:** `:264-268` — وقتی رکوردی نیست، `all_ok=False` و exit 1 می‌شود (fail-fast درست است) ولی خروجی
  فقط «Nothing to harmonize.» و `Equation holds: True [PASS]` (با 0=0) چاپ می‌کند؛ دلیل exit 1 هیچ‌جا گفته نمی‌شود.
- *تصحیح:* اولین برداشتم («exit 0 / silent success») اشتباه بود؛ کد خروج `tail` را خوانده بودم. اینجا با اجرای مستقیم تأیید شد: exit=1.

### C-03 — ادعای «idempotent» برای مراحل in-place هنوز آزموده نشده
`normalize_text` و `duplicate_analysis` فایل‌های `data/interim/` را در جا بازنویسی می‌کنند
(۳۱۶ ثانیه روی هم). اجرای دوم و مقایسه‌ی hash خروجی در مرحله‌ی ۳ انجام می‌شود.

## ۶. محدودیت‌های این baseline (صادقانه)
- داده‌ی خام و خروجی annotation در دسترس نیست؛ collectorها، annotation و Notebookها اجرا نشدند.
- scripts/ingestion (Selenium/API) فقط در مرحله‌ی ۳–۴ به‌صورت ایستا بررسی می‌شوند.
