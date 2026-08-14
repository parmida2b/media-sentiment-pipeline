# Claim Registry

**آخرین به‌روزرسانی:** ۲۰۲۶-۰۸-۱۴
**وضعیت پایه‌ی داده:** `data/processed/annotated_dataset.parquet` — annotation فقط **۳.۷٪** (۸,۵۹۸ از ۲۳۳,۰۰۶ رکورد Eligible) پوشش واقعی دارد؛ بقیه `pending_annotation`اند (`docs/handoff_notes_fa.md`).

## اصل بنیادین (به هر ادعای زیر اعمال می‌شود)

> نمونه‌ی این پروژه غیراحتمالی (Non-probability) است — `docs/Chapter_2_Statistical_Population_and_Sampling_Design_v5.md` و `docs/pre_analysis_decision_table_v1.md`. **هیچ ادعایی در این سند نماینده‌ی «مردم ایران»، «مردم آمریکا» یا هر جمعیت کلی دیگری نیست** — فقط توصیف نمونه‌ی مشاهده‌شده (Observed Sample) روی X/Reddit/YouTube در بازه‌ی ثبت‌شده است. علاوه بر این، تا وقتی annotation کامل نشده (بالا)، هر عدد زیر **مقدماتی/Exploratory** است، نه نهایی.

---

## بخش ۱ — وضعیت ۲۲ خروجی نهایی اجباری چک‌لیست

| # | خروجی | وضعیت | فایل |
|---|---|---|---|
| ۱ | File Inventory + Hash | ✅ | `docs/data_handoff_manifest.csv` |
| ۲ | Collection Manifest | ✅ | `docs/data_handoff_manifest.csv` |
| ۳ | Query Execution Audit | ✅ | `docs/query_execution_audit.csv` (۸۰۷ ردیف؛ Reddit بدون Run Log مستقل — `docs/reference_file_determination.md`) |
| ۴ | Schema Mapping سه پلتفرم | ✅ | `docs/schema_mapping_template.csv` |
| ۵ | Collection Coverage | ✅ | `docs/collection_coverage.csv` (با درجه A-D) |
| ۶ | Raw Validation Report | 🟡 ضمنی | داخل `apply_eligibility.py`'s `stage_raw_validation`/Reconciliation printout؛ سند مستقل جدا نیست |
| ۷ | Record Flow | 🟡 ضمنی | همون Reconciliation equation (`apply_eligibility.py`)؛ نمودار/سند جدا نیست |
| ۸ | Eligibility Audit | ✅ | `data/audits/eligibility_audit.{parquet,csv}` |
| ۹ | Relevance Audit | ✅ | `data/audits/relevance_audit_*.csv`, `docs/relevance_audit/*_labeled.csv` |
| ۱۰ | Gold Sample | ⚠️ | `data/annotated/sample_sentiment_labels.csv` — **مشکل باز: خرابی content_id (Excel Scientific Notation) روی ردیف‌های X، هنوز رفع نشده** |
| ۱۱ | Agreement Report | ⚠️ | `outputs/audits/annotator_agreement.json` — روی n=۵۱ (نه ۱۲۰) چون annotator دوم هنوز ۲۲ ردیف جدید رو لیبل نزده؛ عدد فعلی موقتیه |
| ۱۲ | Model Evaluation Report | ✅ | `outputs/model_evaluation/sentiment_accuracy_summary.json` |
| ۱۳ | Annotated Dataset | 🟡 جزئی | `data/processed/annotated_dataset.parquet` — ۳.۷٪ پوشش (بالا) |
| ۱۴ | جدول‌های توصیفی | ✅ | `outputs/tables/descriptive_stats_*.csv` |
| ۱۵ | روندهای هفتگی با n و CI | ✅ | `outputs/tables/weekly_trend_*.csv` |
| ۱۶ | Composition Shift | ✅ | `outputs/tables/composition_shift_*.csv` |
| ۱۷ | Event Analysis | ✅ | `outputs/tables/event_analysis/*.csv` |
| ۱۸ | Financial Analysis | ✅ | `outputs/tables/financial/*.csv` |
| ۱۹ | حداقل شش Sensitivity Analysis | ✅ | `outputs/tables/sensitivity_analysis_results.csv` (+ `group_comparison_results.csv`) |
| ۲۰ | Claim Registry | ✅ | همین سند |
| ۲۱ | Notebook نهایی قابل‌اجرای کامل | ❌ | فقط `05_descriptive_and_temporal_analysis.ipynb` و `06_event_and_financial_analysis.ipynb` هستن؛ `01`-`04` و `07` ساخته نشدن |
| ۲۲ | گزارش/ارائه حداکثر ده‌دقیقه‌ای | ❌ | ساخته نشده |

**خلاصه:** ۱۵ کامل، ۴ جزئی/موقت (نیازمند annotation بیشتر یا رفع باگ Gold Sample)، ۳ باز (Raw Validation/Record Flow مستقل، Notebook یکپارچه، گزارش نهایی).

---

## بخش ۲ — ادعاهای مستند (هرکدوم فقط با پوشش فعلی ۳.۷٪ معتبرند)

| # | ادعا | خروجی/سلول مرجع | محدودیت |
|---|---|---|---|
| C01 | توزیع Stance بین سه پلتفرم تفاوت معنادار آماری دارد (Cramér's V=۰.۱۴۷, p<۰.۰۰۱) | `outputs/tables/group_comparison_results.csv`, ردیف `chi_square_stance_platform` | فقط روی ۹,۴۰۵ رکورد annotate‌شده؛ فقط «همراهی»، نه علیت |
| C02 | طول متن بین X و YouTube تفاوت معنادار دارد (Hedges' g=۰.۵۴، YouTube بلندتر) | `outputs/tables/group_comparison_results.csv`, ردیف `welch_text_length_x_vs_youtube` | Effect size متوسط، نه بزرگ |
| C03 | حذف Duplicate/Near-duplicate سهم Sentiment مثبت را به‌طور معنادار جابه‌جا نمی‌کند (Shift<۱٪ در هر سه پلتفرم) | `outputs/tables/sensitivity_analysis_results.csv`, `comparison_id=duplicate_inclusion` | فقط ۳۳۵ رکورد Near-duplicate در نمونه‌ی annotate‌شده‌ی فعلی |
| C04 | Engagement-weighting (log1p) سهم مثبت یوتیوب را از ۲۴.۲٪ به ۲۹.۱٪ افزایش می‌دهد | `outputs/tables/sensitivity_analysis_results.csv`, `comparison_id=engagement_weighting` | فقط YouTube (تنها پلتفرم با `engagement_score` واقعی) |
| C05 | داده‌ی X نه مفهوم Source (کانال) دارد نه Parent مستقل — فقط Query-based Search | `outputs/tables/sensitivity_analysis_results.csv`, یادداشت `not_meaningful` روی X | محدودیت ساختاری Collector X، نه محدودیت آماری |

هر ادعای دیگری که بعداً به گزارش نهایی اضافه شود، باید همین قالب (ادعا → خروجی دقیق → محدودیت) را رعایت کند؛ ادعای بدون رفرنس مستقیم به یک فایل/ردیف مشخص در گزارش نهایی مجاز نیست.

---

## بخش ۳ — موارد باز (Open Items)

1. **خرابی content_id در Gold Sample (X)** — نیاز به تعمیر با بک‌آپ‌های تمیز موجود، قبل از اعتماد به هر عدد Agreement/Model-Evaluation جدید.
2. **Agreement روی نمونه‌ی کامل** — annotator دوم باید ۲۲ ردیف باقی‌مانده در `sample_sentiment_labels_agreement_subset.csv` را لیبل بزند.
3. **۴۷ ردیف Orphan در `agreement_subset`** — عدم تطابق content_id با فایل اصلی، هنوز بررسی/تصمیم تیمی نشده.
4. **Full Annotation** — فعلاً متوقف (سهمیه‌ی Groq/OpenRouter)؛ به تصمیم صریح کاربر، آخر کار دنبال می‌شود.
5. **Notebook یکپارچه (۰۱-۰۷)** و **گزارش نهایی/ارائه** — هنوز ساخته نشده‌اند.
