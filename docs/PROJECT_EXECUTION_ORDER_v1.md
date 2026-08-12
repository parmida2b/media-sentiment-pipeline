# ترتیب اجرای پروژه و اسناد

**نسخه:** 1.0  
**بازه مطالعه:** `2026-02-28` تا `2026-07-22`

این سند ترتیب منطقی اجرای پروژه را مشخص می‌کند. شماره نسخه فایل با ترتیب اجرای مرحله یکسان نیست؛ هر نسخه جدید باید سازگاری خود را با خروجی مرحله قبل حفظ کند.

## مرحله ۱ — تعریف پژوهش

**اسناد:**

- `Chapter_1_Project_Definition_and_Research_Design_v5.md`
- `Chapter_2_Statistical_Population_and_Sampling_Design_v5.md`
- `Chapter_3_Platform_Selection_and_Source_Justification_v3.md`

**تصمیم‌ها:** پرسش پژوهش، جامعه قابل‌دسترسی، Sampling frame، واحد تحلیل، پلتفرم‌ها، زبان‌ها، مرز استنباط و ساختار کلی آمار.

## مرحله ۲ — قرارداد Collection

**اسناد:**

- نسخه `raw_schema` تخصیص‌یافته به Collectorها
- نسخه `query_registry` تخصیص‌یافته به Collectorها
- Source/Channel/Subreddit list یا Config تخصیص‌یافته، در صورت وجود

**تصمیم‌ها:** ستون‌های مورد انتظار، Queryها، Window و تنظیمات Collection که واقعاً به هر Collector ابلاغ شده‌اند.

نسخه دقیق دریافت‌شده توسط هر Collector در Handoff Manifest ثبت می‌شود.

## مرحله ۳ — اجرای Collection

هر عضو تیم مسئول یک پلتفرم است:

| مسئولیت | خروجی |
|---|---|
| X Collector | Raw files، کد، Config بدون Secret و Run log |
| Reddit Collector | Raw files، کد، Config بدون Secret و Run log |
| YouTube Collector | Raw files، کد، Config بدون Secret و Run log |

در این مرحله Raw تغییر نمی‌کند و Query، Sort، Cap، Pagination، خطا و Data cutoff واقعی ثبت می‌شوند.

## مرحله ۴ — دریافت، Freeze و Validation

**اسناد اجرایی داخلی:**

- `legacy_data_intake_and_harmonization_plan_v1.md`
- `data_handoff_manifest_template.csv`
- `query_execution_audit_template.csv`
- `collection_coverage_template.csv`

**خروجی:** Hash فایل‌ها، Inventory، Coverage، Missingness، خطاهای Parse و درجه کیفیت A تا D.

## مرحله ۵ — هماهنگ‌سازی و Eligibility

**اسناد:**

- `raw_schema_v05.md`
- `schema_mapping_template.csv`
- `eligibility_rules_v03.md`
- `source_registry_v4.md` و `query_execution_audit_template.csv` برای ثبت Source و Query مشاهده‌شده

**ترتیب داده:**

```text
raw_original
→ raw_harmonized
→ eligible_content
→ opinion_main / opinion_limited / opinion_untimed / context_only / audit_only
```

هیچ مقدار نامعلوم برای کامل‌کردن Schema ساخته نمی‌شود.

## مرحله ۶ — قفل تصمیم‌های تحلیل

**اسناد:**

- `pre_analysis_decision_table_v1.md`
- `event_registry_v3.md`
- Decision Log

پیش از Full Annotation، Targetهای اصلی، Gold Sample، حداقل حجم گزارش، رویدادها، آزمون‌ها و تحلیل‌های حساسیت قفل می‌شوند.

## مرحله ۷ — Gold Sample و Pilot

1. انتخاب تصادفی طبقه‌بندی‌شده ۳۰۰ رکورد با Seed ثابت؛
2. Double annotation برای ۱۲۰ رکورد؛
3. محاسبه Agreement و Cohen’s Kappa؛
4. Pilot مدل روی ۱۰۰ رکورد؛
5. انتخاب یک مدل/Provider با معیار Macro-F1، Failure، Cost و Latency؛
6. ثبت سقف هزینه و زمان.

## مرحله ۸ — Annotation کامل و ارزیابی

Prompt و مدل قفل‌شده روی Dataset واجد شرایط اجرا می‌شوند. Confusion Matrix، Precision، Recall، F1، Macro-F1، Failure، Cost و Latency گزارش می‌شوند.

## مرحله ۹ — تحلیل آماری

ترتیب تحلیل:

1. Record flow و Data quality؛
2. آمار توصیفی؛
3. روندهای هفتگی با `n` و Wilson CI؛
4. Composition shift؛
5. مقایسه گروه‌ها با Effect size؛
6. Event windows؛
7. هم‌ترازی شاخص‌های مالی؛
8. اصلاح FDR؛
9. تحلیل‌های حساسیت.

## مرحله ۱۰ — گزارش نهایی

گزارش شامل روش، Coverage واقعی، نتیجه هر پلتفرم، مقایسه محدود سه پلتفرم، عدم قطعیت، محدودیت نمایندگی و Claim Registry است. ادعاها به نمونه مشاهده‌شده محدود می‌شوند.
