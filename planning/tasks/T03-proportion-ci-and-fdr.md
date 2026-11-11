# T03: CI درست برای اختلاف نسبت و تصحیح FDR
- موج 1 | مهم | یافته‌ها: C-15، C-16 | مدل: Opus / high | وابستگی: T02 | نیاز به کاربر: خیر
- فایل‌ها: `src/event_analysis/event_study.py`، `src/temporal_analysis/group_comparison.py`، `tests/test_event_study_ci.py` (جدید)

## مسئله
`event_study.diff_of_proportions_ci` (خطوط 82 تا 96) با تقریب Wald کار می‌کند. نتیجه با Newcombe (روش 10، بر پایه‌ی Wilson):
| حالت | Wald | Newcombe |
|---|---|---|
| ۲/۴۳ به ۰/۳ (ادعای C2 گزارش) | `[-0.109, +0.016]` | `[-0.155, +0.516]` |
| ۰/۴۰ به ۰/۵ | `[0, 0]` | `[-0.088, +0.434]` |
| ۵/۱۰ به ۹/۱۰ | `[+0.039, +0.761]` (معنادار) | `[-0.002, +0.676]` |
تصحیح FDR در `group_comparison` و `event_study` نیست، با اینکه `docs/archive/checklist.md:328` آن را قفل کرده؛ بخش مالی دارد (`p_value_bh_fdr`).

## تغییر
1. `diff_of_proportions_ci` با Newcombe (از `common.wilson_confidence_interval`). کلیدهای خروجی ثابت بمانند.
   ستون p-value اگر لازم است با آزمون دقیق مناسب (Fisher) نه z.
2. ستون `p_value_bh_fdr` با `statsmodels.stats.multitest.multipletests(method="fdr_bh")`:
   - `group_comparison`: خانواده = همه‌ی آزمون‌های یک اجرا.
   - `event_study`: خانواده = رویدادهای `primary_confirmatory` × پلتفرم در پنجره‌ی اصلی؛ placebo و حساسیت جدا و علامت‌خورده.

## تست
سه حالت جدول بالا (عددها با تلورانس 0.001)؛ `q >= p` برای همه؛ ردیف not_computable (از T04) در FDR شرکت نکند.

## معیار پذیرش
تست‌ها سبز؛ جدول‌های event study و group comparison ستون q دارند؛ تغییر نتیجه‌ی ادعاهای C1 تا C3 گزارش در گزارش کار ثبت شود (برای T17).
