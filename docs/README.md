# نقشه‌ی داکیومنت‌ها

این پوشه دو نوع سند دارد: **سند روش‌شناسی/مشاور** (چه‌کاری باید انجام بشه) و
**سند فنی تیم** (چه‌کاری الان واقعاً انجام شده). قبل از خوندن هر فایل دیگه‌ای
توی `docs/`، این فهرست رو چک کن تا سراغ نسخه‌ی درست بری.

آخرین به‌روزرسانی این فهرست: ۲۰۲۶-۰۸-۱۲.

## ۰. از کجا شروع کنم؟

1. [`PROJECT_EXECUTION_ORDER_v1.md`](PROJECT_EXECUTION_ORDER_v1.md) — ترتیب
   ۱۰مرحله‌ای کل پروژه و این‌که هر مرحله کدوم سند رو می‌خواد. **همیشه اول
   همینو باز کن.**
2. [`decision_log.md`](decision_log.md) — چرا هر تصمیم مهم گرفته شده، به ترتیب
   تاریخ. وقتی چیزی عجیب به‌نظر می‌رسه (مثلاً چرا فلان فیلد اینه)، اول اینجا
   رو چک کن.
3. اگه داری برای تحلیل/Power BI داده تحویل می‌گیری: اول
   [`handoff_notes_fa.md`](handoff_notes_fa.md) رو باز کن (وضعیت لحظه‌ای —
   کدوم فایل الان واقعیه، پوشش annotation چقدره)، بعد برای جزئیات ستون‌ها
   [`outputs_guide_fa.md`](outputs_guide_fa.md).

## ۱. سند روش‌شناسی فعلی (مشاور) — نسخه‌ی هدف تیم

اینها آخرین و معتبرترین نسخه‌ی هر سند هستن. اگه کد فعلی با این‌ها فرق داره،
کد عقبه، نه این اسناد:

| سند | موضوع |
|---|---|
| [`Chapter_1_Project_Definition_and_Research_Design_v5.md`](Chapter_1_Project_Definition_and_Research_Design_v5.md) | پرسش پژوهش، بازه، دامنه استنباط |
| [`Chapter_2_Statistical_Population_and_Sampling_Design_v5.md`](Chapter_2_Statistical_Population_and_Sampling_Design_v5.md) | جامعه آماری و Sampling |
| [`Chapter_3_Platform_Selection_and_Source_Justification_v3.md`](Chapter_3_Platform_Selection_and_Source_Justification_v3.md) | چرا این سه پلتفرم |
| [`raw_schema_v05.md`](raw_schema_v05.md) | قرارداد داده خام هدف (⚠️ کد هنوز v03 رو پیاده می‌کنه — پایین رو ببین) |
| [`source_registry_v4.md`](source_registry_v4.md) | فهرست منابع مجاز/برنامه‌ریزی‌شده |
| [`query_registry_v5.md`](query_registry_v5.md) | قرارداد Query |
| [`eligibility_rules_v03.md`](eligibility_rules_v03.md) | قواعد ورود/خروج رکورد به Dataset تحلیلی |
| [`event_registry_v3.md`](event_registry_v3.md) | فهرست رویدادها برای Event window |
| [`pre_analysis_decision_table_v1.md`](pre_analysis_decision_table_v1.md) | تصمیم‌هایی که باید قبل از Annotation کامل قفل بشن |
| [`legacy_data_intake_and_harmonization_plan_v1.md`](legacy_data_intake_and_harmonization_plan_v1.md) | چطور داده‌ای که از قبل جمع کردیم رو بدون جمع‌آوری مجدد وارد Schema جدید کنیم |

### Templateهای مرحله‌ی Intake (خالی، آماده‌ی پرشدن)
[`data_handoff_manifest_template.csv`](data_handoff_manifest_template.csv) ·
[`schema_mapping_template.csv`](schema_mapping_template.csv) ·
[`query_execution_audit_template.csv`](query_execution_audit_template.csv) ·
[`collection_coverage_template.csv`](collection_coverage_template.csv)

## ۲. سند فنی تیم — وضعیت واقعی کد امروز

این‌ها مرجعِ «کد الان دقیقاً چیکار می‌کنه»ن، نه سند هدف. عمداً روی نسخه‌ی
قدیمی‌تر (v03) هستن چون کد هنوز migrate نشده — هرکدوم بالاش یه بنر داره که
دقیقاً می‌گه چه بخشیش جایگزین شده:

| سند | موضوع | وضعیت |
|---|---|---|
| [`raw_schema_v03.md`](raw_schema_v03.md) | نسخه‌ی schema که کد فعلاً واقعاً پیاده می‌کنه | جایگزین هدف: v05، migration نشده |
| [`cross_platform_alignment_guide_fa.md`](cross_platform_alignment_guide_fa.md) | فرمول تشخیص بات (بخش ۳-۴، هنوز معتبر) + وضعیت هماهنگی schema (بخش ۱-۲-۵-۶، منسوخ) | نیمه‌منسوخ، بنر بالاش رو بخون |
| [`youtube_data_pipeline_fa.md`](youtube_data_pipeline_fa.md) | مسیر فنی کامل داده‌ی یوتیوب از استخراج تا annotation | معتبر برای بخش YouTube |
| [`data_and_features_dictionary_fa.md`](data_and_features_dictionary_fa.md) | توضیح ستون‌ها برای کسی که تحلیل/داشبورد می‌سازه (نه کدنویس) | معتبر برای بخش YouTube |
| [`manual_labeling_guide_fa.md`](manual_labeling_guide_fa.md) | راهنمای annotator برای لیبل دستی (Gold Sample) | معتبر |
| [`financial/README_FINANCIAL_WORKFLOW_FA.md`](financial/README_FINANCIAL_WORKFLOW_FA.md) | ترتیب اجرای بخش مالی، ورودی‌ها و خروجی‌ها | معتبر |

## ۳. راهنمای عملیاتی/Git (بدون تاریخ انقضا)

[`setup.md`](setup.md) · [`git_github_guide_ali_hossein.md`](git_github_guide_ali_hossein.md) ·
[`../GIT_WORKFLOW.md`](../GIT_WORKFLOW.md)

## ۴. هنوز خالی‌ان (TODO)

- [`overview.md`](overview.md) — باید کوتاه به `PROJECT_EXECUTION_ORDER_v1.md`
  و Chapter 1 اشاره کنه، نه محتوا رو تکرار کنه.
- [`architecture.md`](architecture.md) — معماری واقعی pipeline بعد از این‌که
  اتصال مراحل (orchestrator) نوشته شد، اینجا مستند بشه.

## ۵. بایگانی

[`archive/`](archive/) — اسنادی که دیگه هیچ کدی بهشون رفرنس نمی‌ده و کاملاً
جایگزین شدن. هر فایل داخلش یه بنر داره که می‌گه چرا و کِی بایگانی شده.

## ۶. سایر (بیرون از `docs/`)

- [`../roadmap_pipeline.md`](../roadmap_pipeline.md) — نقشه‌راه اولیه/آرمانی
  پروژه (نه وضعیت فعلی کد). **نیمه‌منسوخ**: تلگرام/توییتر رو پلتفرم فعال
  نشون می‌ده (تلگرام طبق `decision_log.md` ۲۰۲۶-۰۸-۰۴ حذف شد) و از
  `pipeline_runner.py`ای حرف می‌زنه که هیچ‌وقت ساخته نشد. بخش ۴ (مسیر تبدیل
  به ایجنت مکالمه‌ای، فاز ۲) هنوز به‌عنوان مرجع طراحی معتبره.
