# ترتیب اجرای پروژه و اسناد

**نسخه:** 1.1  
**بازه مطالعه:** `2026-02-28` تا `2026-07-22`

این سند ترتیب منطقی اجرای پروژه را مشخص می‌کند. شماره نسخه فایل با ترتیب اجرای مرحله یکسان نیست؛ هر نسخه جدید باید سازگاری خود را با خروجی مرحله قبل حفظ کند.

---

## مرحله ۱ — تعریف پژوهش

**اسناد:**

- `Chapter_1_Project_Definition_and_Research_Design_v5.md`
- `Chapter_2_Statistical_Population_and_Sampling_Design_merged_readable.md` (جایگزین نسخه قبلی v5، که به `docs/archive/` منتقل شد)
- `Chapter_3_Platform_Selection_and_Source_Justification_merged_readable.md` (جایگزین نسخه قبلی v3، که به `docs/archive/` منتقل شد)

**تصمیم‌ها:** پرسش پژوهش، جامعه قابل‌دسترسی، Sampling frame، واحد تحلیل، پلتفرم‌ها، زبان‌ها، مرز استنباط و ساختار کلی آمار.

---

## مرحله ۲ — قرارداد Collection

**اسناد:**

- نسخه `raw_schema` تخصیص‌یافته به Collectorها
- نسخه `query_registry` تخصیص‌یافته به Collectorها
- Source/Channel/Subreddit list یا Config تخصیص‌یافته، در صورت وجود

**تصمیم‌ها:** ستون‌های مورد انتظار، Queryها، Window و تنظیمات Collection که واقعاً به هر Collector ابلاغ شده‌اند.

نسخه دقیق دریافت‌شده توسط هر Collector در Handoff Manifest ثبت می‌شود.

تنظیمات این مرحله به‌عنوان **تنظیمات مورد انتظار یا تخصیص‌یافته (`expected`)** ثبت می‌شوند. این مقادیر تا زمانی که با کد، Config، Log، Manifest یا خروجی Run تأیید نشده‌اند، به‌عنوان تنظیمات واقعاً اجراشده تلقی نمی‌شوند.

برای مثال:

```text
expected_query = RQ-002
expected_sort = new
expected_cap = 500
```

این مقادیر فقط نشان می‌دهند چه چیزی به Collector ابلاغ شده است، نه اینکه الزاماً همان تنظیمات در اجرای واقعی استفاده شده‌اند.

---

## مرحله ۳ — اجرای Collection

هر عضو تیم مسئول یک پلتفرم است:

| مسئولیت | خروجی |
|---|---|
| X Collector | Raw files، کد، Config بدون Secret و Run log |
| Reddit Collector | Raw files، کد، Config بدون Secret و Run log |
| YouTube Collector | Raw files، کد، Config بدون Secret و Run log |

در این مرحله، برای هر Run تا حد امکان اطلاعات واقعی زیر ثبت می‌شوند:

- Query و Query ID
- Source و Source ID
- Sort
- Cap
- Pagination
- زمان شروع و پایان Run
- خطاها و Retryها
- تعداد رکورد بازیابی‌شده
- قدیمی‌ترین Timestamp مشاهده‌شده
- جدیدترین Timestamp مشاهده‌شده
- `observed_data_cutoff`

فایل Raw همان خروجی مستقیم Collector است. پس از ایجاد فایل Raw، Cleaning، حذف رکورد، تغییر متن یا Harmonization روی نسخه اصلی انجام نمی‌شود. نسخه دریافت‌شده در مرحله ۴ Hash و Freeze می‌شود.

تنظیمات واقعاً مشاهده‌شده در این مرحله یا مرحله Validation به‌عنوان **`observed`** ثبت می‌شوند.

برای مثال:

```text
expected_cap = 500
observed_cap = 500
actual_collected = 327
```

یا اگر شواهد کافی برای Sort واقعی وجود نداشته باشد:

```text
expected_sort = new
observed_sort = unknown
```

مقادیر `expected` هیچ‌گاه برای پرکردن مقدار `observed` نامعلوم استفاده نمی‌شوند.

---

## مرحله ۴ — دریافت، Freeze و Validation

**اسناد اجرایی داخلی:**

- `legacy_data_intake_and_harmonization_plan_v1.md`
- `data_handoff_manifest_template.csv`
- `query_execution_audit_template.csv`
- `collection_coverage_template.csv`

**خروجی‌ها:**

- Hash فایل‌ها
- Inventory فایل‌ها
- Coverage زمانی
- Missingness
- خطاهای Parse
- تعداد Runهای موفق و ناموفق
- بازسازی تنظیمات `observed`
- درجه کیفیت A تا D

در این مرحله فایل Raw اصلی Freeze می‌شود و نسخه بعدی پردازش از روی Copy یا لایه جداگانه ساخته می‌شود.

اگر Query، Source، Sort، Cap، Pagination یا سایر اطلاعات Run از روی شواهد موجود قابل تأیید نباشند، مقدار آن‌ها `unknown` ثبت می‌شود.

---

## مرحله ۵ — هماهنگ‌سازی و Eligibility

**اسناد:**

- `raw_schema_v05.md`
- `schema_mapping_template.csv`
- `eligibility_rules_v03.md`
- `source_registry_v4.md`
- `query_execution_audit_template.csv`

**ترتیب داده:**

```text
raw_original
→ raw_harmonized
→ eligible_content
→ opinion_main / opinion_limited / opinion_untimed / context_only / audit_only
```

تعریف کلی Datasetها:

| Dataset | کاربرد |
|---|---|
| `raw_original` | نسخه Freeze‌شده و بدون تغییر فایل دریافتی |
| `raw_harmonized` | نسخه‌ای با نام و نوع ستون‌های استانداردشده |
| `eligible_content` | محتوای متنی که قواعد Eligibility را گذرانده است |
| `opinion_main` | Dataset اصلی تحلیل نگرش |
| `opinion_limited` | رکوردهای قابل استفاده با محدودیت مشخص |
| `opinion_untimed` | رکوردهای قابل استفاده که Timestamp مناسب برای روند زمانی ندارند |
| `context_only` | Parent یا Context؛ خارج از Annotation نگرشی اصلی |
| `audit_only` | رکوردهای صرفاً مناسب Audit و گزارش کیفیت |

هیچ مقدار نامعلوم برای کامل‌کردن Schema ساخته نمی‌شود.

Dataset ورودی Full Annotation باید پیش از مرحله ۶ مشخص شود. به‌طور پیش‌فرض `context_only` و `audit_only` وارد Annotation مربوط به Sentiment، Stance، Emotion و Topic نمی‌شوند.

اگر `opinion_limited` یا `opinion_untimed` در Annotation استفاده شوند، کاربرد آن‌ها در تحلیل نهایی باید جداگانه و از پیش ثبت شود.

---

## مرحله ۶ — قفل تصمیم‌های تحلیل

**اسناد:**

- `pre_analysis_decision_table_v1.md`
- `event_registry_v3.md`
- Decision Log

پیش از Full Annotation موارد زیر قفل می‌شوند:

- مجموعه Targetهای مجاز
- قاعده انتخاب یک `primary_target` برای هر واحد Annotation
- Dataset ورودی Full Annotation
- روش انتخاب Gold Sample
- اندازه Gold Sample
- ساختار Pilot و Final Evaluation
- حداقل حجم گزارش
- Confidence Threshold
- رویدادها و Windowها
- آزمون‌های آماری
- Effect sizeها
- تحلیل‌های حساسیت
- قواعد حذف یا نگهداری Duplicate و Near-duplicate
- نحوه برخورد با رکوردهای `opinion_limited` و `opinion_untimed`

هر تغییر پس از این مرحله باید در Decision Log با دلیل، تاریخ و اثر احتمالی آن بر تحلیل ثبت شود.

---

## مرحله ۷ — Gold Sample و Pilot

### ۷.۱ Gold Sample

Gold Sample برای ایجاد یک مرجع انسانی قابل اعتماد جهت ارزیابی کیفیت Annotation و مدل استفاده می‌شود.

فرآیند پیشنهادی شامل مراحل زیر است:

1. انتخاب تصادفی طبقه‌بندی‌شده از `eligible_content` با Seed ثابت؛
2. اجرای Double annotation روی بخشی از نمونه؛
3. محاسبه Percent Agreement و Cohen’s Kappa؛
4. بررسی اختلاف‌ها و Adjudication موارد مورد اختلاف؛
5. ایجاد Gold Label نهایی.

اندازه Gold Sample و سهم Double annotation از پیش در طرح آماری یا Decision Log مشخص و پیش از اجرای Annotation قفل می‌شود. انتخاب اندازه نمونه باید با توجه به حجم داده واجد شرایط، تعداد کلاس‌ها، تعداد پلتفرم‌ها، زبان‌ها و نیاز ارزیابی مدل انجام شود.

### ۷.۲ Pilot و انتخاب مدل

Pilot باید به‌گونه‌ای طراحی شود که مجموعه ارزیابی نهایی تا حد ممکن مستقل از فرآیند انتخاب Prompt، Model یا Provider باقی بماند.

روش ترجیحی این است که Pilot/Development Sample از Gold Sample مورد استفاده برای ارزیابی نهایی جدا باشد. در این حالت، داده‌های Pilot برای توسعه و انتخاب Prompt، Model، Provider و تنظیمات استفاده می‌شوند و Gold Sample نهایی فقط برای ارزیابی عملکرد مدل نگه داشته می‌شود.

اگر به دلیل محدودیت حجم داده لازم باشد Pilot از داخل Gold Sample انتخاب شود، تقسیم داده باید پیش از آزمایش مدل مشخص و قفل شود. در این حالت، بخشی از Gold Sample به‌عنوان `Development/Pilot subset` و بخش دیگری به‌عنوان `Held-out Final Evaluation subset` در نظر گرفته می‌شود.

رکوردهایی که در `Development/Pilot subset` برای انتخاب Prompt، Model، Provider یا تنظیمات استفاده شده‌اند، نباید دوباره به‌عنوان داده مستقل در ارزیابی نهایی عملکرد مدل تلقی شوند.

اندازه Gold Sample، Pilot/Development subset و Held-out Evaluation subset براساس طرح آماری مصوب پروژه، حجم داده واجد شرایط و الزامات ارزیابی تعیین و پیش از اجرای Pilot در Decision Log ثبت می‌شود.

### ۷.۳ معیار انتخاب مدل/Provider

انتخاب یک مدل/Provider با توجه به موارد زیر انجام می‌شود:

- Macro-F1 روی Pilot/Development set
- Precision و Recall کلاس‌ها
- Failure rate
- Cost
- Latency
- پایداری خروجی
- رعایت Schema خروجی

سقف هزینه و زمان پیش از اجرای Full Annotation ثبت می‌شود.

پس از انتخاب، Prompt، مدل، Provider، نسخه مدل و تنظیمات اصلی قفل می‌شوند.

---

## مرحله ۸ — Annotation کامل و ارزیابی

Prompt و مدل قفل‌شده روی Dataset ورودی Full Annotation اجرا می‌شوند.

### ۸.۱ اجرای Full Annotation

برای کل Run موارد زیر ثبت می‌شوند:

- تعداد رکورد ورودی
- تعداد رکورد Annotation‌شده
- تعداد Retry
- Failure rate
- Parse failure
- Schema validation failure
- Missing output
- Cost
- Latency
- نسخه Prompt و Model

Failure می‌تواند شامل مواردی مانند Request failure، Timeout، خروجی غیرقابل Parse، خروجی ناقص یا خروجی نامعتبر نسبت به Schema باشد.

### ۸.۲ ارزیابی مدل

Confusion Matrix، Precision، Recall، F1، Macro-F1 و Accuracy فقط روی **Gold/Held-out Evaluation Sample** محاسبه می‌شوند، زیرا Full Dataset دارای Gold Label انسانی برای همه رکوردها نیست.

بنابراین:

```text
Precision / Recall / F1 / Macro-F1
→ Gold or Held-out Evaluation Sample

Failure / Cost / Latency / Coverage
→ Full Annotation Run
```

اگر Confidence Threshold استفاده شود، Threshold براساس Development/Gold طراحی‌شده تعیین و سپس بدون تغییر روی Full Dataset اعمال می‌شود.

---

## مرحله ۹ — تحلیل آماری

ترتیب تحلیل:

1. Record flow و Data quality؛
2. Coverage زمانی و Data gapها؛
3. آمار توصیفی؛
4. روندهای هفتگی با `n` و Wilson CI؛
5. Composition shift؛
6. مقایسه گروه‌ها با Effect size؛
7. Event windows؛
8. هم‌ترازی شاخص‌های مالی؛
9. اصلاح FDR؛
10. تحلیل‌های حساسیت.

### ۹.۱ Coverage پیش از تحلیل روند

پیش از تفسیر هر روند هفتگی بررسی می‌شود که کاهش یا افزایش حجم داده ناشی از تغییر واقعی محتوای مشاهده‌شده است یا ممکن است با محدودیت Collection مرتبط باشد.

برای هر پلتفرم حداقل موارد زیر بررسی می‌شوند:

- هفته‌های دارای داده
- هفته‌های فاقد داده یا دارای داده کم
- تعداد Run در هر بازه
- `observed_data_cutoff`
- قدیمی‌ترین و جدیدترین Timestamp
- Data gapهای شناخته‌شده
- تغییر Source یا Query
- تغییر Sort، Cap یا Pagination
- Failureهای Collection

کاهش حجم خام یک هفته به‌تنهایی به‌عنوان کاهش گفت‌وگو یا کاهش توجه کاربران تفسیر نمی‌شود.

### ۹.۲ تحلیل روند

برای هر هفته و Label، سهم همراه با موارد زیر گزارش می‌شود:

- `project_week`
- `n`
- تعداد کلاس
- سهم کلاس
- Wilson 95% CI
- ترکیب Platform/Source/Language در صورت نیاز

### ۹.۳ تحلیل حساسیت

تحلیل‌های حساسیت حداقل شامل بررسی اثر موارد زیر هستند:

- Duplicate و Near-duplicate
- نویسندگان پرتکرار
- Parentهای بزرگ یا وایرال
- Confidence پایین
- Sourceهای غالب
- Windowهای رویدادی جایگزین
- روش‌های مختلف Correlation

---

## مرحله ۱۰ — گزارش نهایی

گزارش نهایی شامل موارد زیر است:

- روش پژوهش
- Sampling frame عملیاتی
- Collection contract
- تفاوت تنظیمات `expected` و `observed`
- Coverage واقعی
- `observed_data_cutoff`
- Record flow
- Data quality
- Gold Sample و توافق انسانی
- ارزیابی مدل
- نتیجه هر پلتفرم به‌صورت جداگانه
- مقایسه محدود سه پلتفرم
- روندهای هفتگی
- Event analysis
- تحلیل مالی
- تحلیل‌های حساسیت
- عدم قطعیت
- محدودیت نمایندگی
- Claim Registry

ادعاها فقط به نمونه مشاهده‌شده و قابل‌دفاع محدود می‌شوند.

عبارت‌هایی مانند «افکار عمومی جهان» یا «همه کاربران پلتفرم» برای نتیجه‌گیری از این Dataset استفاده نمی‌شوند، مگر اینکه طراحی پژوهش مستقلی برای چنین استنباطی وجود داشته باشد.
