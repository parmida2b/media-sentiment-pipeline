# T04: «داده موجود نیست» به‌جای صفر ساختگی و محافظ داده‌ی خالی
- موج 1 | مهم | یافته‌ها: C-17، C-01 | مدل: Sonnet / high | وابستگی: ندارد | نیاز به کاربر: خیر
- فایل‌ها: `src/temporal_analysis/build_social_weekly_outcomes.py`، `src/temporal_analysis/group_comparison.py`، `tests/test_unavailable_outcomes.py` (جدید)

## مسئله
1. پل همیشه `is_flagged_bot_suspect = None` می‌گذارد (`build_annotated_dataset.py:193`). `build_social_weekly_outcomes.py:99-104` آن را با `== True`
   می‌شمارد و `automation_risk_share = 0.0` با CI `[0, 0.0876]` تولید می‌کند (بازتولید با ۴۰ ردیف).
2. `group_comparison.chi_square_test` (خط 164) روی جدول خالی `scipy.stats.chi2_contingency` را صدا می‌زند و کل Pipeline B متوقف می‌شود
   (بازتولید: اجرای `run_pipeline.py` روی داده‌ی بدون annotation). Fisher، Mann-Whitney و Welch هم محافظ ندارند.

## تغییر
1. `build_social_weekly_outcomes`: ستون `status` با مقادیر `ok`، `data_gap`، `not_available`. اگر ستون مبنا در کل داده null است: مقدار و CI = NaN، `status = not_available`.
   مصرف‌کننده‌ها را بررسی کن: `build_financial_outputs.py`، `notebooks/financial/02_financial_social_alignment.ipynb`، `notebooks/06_event_and_financial_analysis.ipynb`.
2. `group_comparison`: هر آزمون وقتی داده یا تنوع کافی نیست، ردیف `not_computable` با دلیل بدهد (الگوی موجود `engagement_not_applicable_row`).

## تست
- ۴۰ ردیف با `is_flagged_bot_suspect=None` ← `automation_risk_share` = NaN و `status = not_available`.
- `group_comparison.run()` روی DataFrame بدون ردیف `ok` exception ندهد و برای هر آزمون یک ردیف `not_computable` بدهد.

## معیار پذیرش
`python src/pipeline/run_pipeline.py --skip harmonize` روی کپی کاری (داده‌ی بدون annotation) تا آخر بدون خطا اجرا شود.
