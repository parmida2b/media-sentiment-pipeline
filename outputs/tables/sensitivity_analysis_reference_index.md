# تحلیل حساسیت — مقایسه‌های موجود در جاهای دیگر (نه اینجا محاسبه‌شده)

این‌ها به‌عنوان بخشی از اسکریپت‌های دیگر Pipeline B از قبل تولید شده‌اند؛ اینجا فقط رفرنس داده می‌شود.

| مقایسه | فایل |
|---|---|
| Spearman در برابر Pearson (همبستگی مالی) | `outputs/tables/financial/financial_social_correlation_results_v1.csv` (ستون `method`) |
| Event window ۱، ۲ و ۳ هفته‌ای | `outputs/tables/event_analysis/event_study_sensitivity_window.csv` |
| هر پلتفرم جدا در برابر Pooled observed | `outputs/tables/descriptive_stats_by_platform_week.csv` در برابر `descriptive_stats_by_week_pooled_all_platforms.csv` |
| با/بدون بزرگ‌ترین Source/Near-duplicate (رویداد) | `outputs/tables/event_analysis/event_study_sensitivity_robustness.csv` |