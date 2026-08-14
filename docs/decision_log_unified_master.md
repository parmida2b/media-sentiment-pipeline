# Decision Log — Unified Master Version

> **Purpose**  
> ما اجرای پروژه «تحلیل نگرش مشاهده‌شده کاربران درباره مناقشه ایران و آمریکا» را از تاریخ ۱ مرداد ۱۴۰۵ آغاز کردیم. این سند تصمیم‌های مشترک تیم درباره جمع‌آوری، پردازش، تحلیل، داشبورد، مستندسازی و ارائه نهایی و همچنین گزارش‌های تغییرات فنی و مهندسی را ثبت می‌کند تا تمام اعضا براساس یک مسیر واحد و قابل پیگیری پیش بروند.

## Guidelines

- فقط تصمیم‌های اثرگذار بر دامنه، داده، نمونه‌گیری، تحلیل یا گزارش ثبت می‌شوند.
- شناسه‌های اصلی `D-001` تا `D-020` مطابق Chapter 1 حفظ شده‌اند.
- شناسه‌های محلی `SD-*`، `SD-3-*`، `SR-*` و `ER-*` در بخش «Related Resources» به تصمیم اصلی متناظر ارجاع داده می‌شوند.
- تاریخ‌ها براساس تقویم رسمی اجرای تیم از ۲۳ ژوئیه تا ۱۵ اوت ۲۰۲۶ ثبت شده‌اند؛ در مواردی که ساعت جلسه مشخص نیست فقط تاریخ روز کاری درج می‌شود.
- هر تغییر با وضعیت جدید، دلیل، اثر و نسخه سند ثبت می‌شود و سوابق تصمیم‌های قبلی برای پیگیری مسیر پروژه حفظ می‌گردد.

---

## Document Information

| Item | Value |
| --- | --- |
| Project Name | Global Public Opinion Analysis on the Iran–US Conflict |
| Team Members | حسین، پارمیدا، علی، ریحانه، یاسمن |
| Project Start | 2026-07-23 = ۱ مرداد ۱۴۰۵ = روز ۱ |
| Project Presentation | 2026-08-15 = ۲۴ مرداد ۱۴۰۵ = روز ۲۴ |
| Project Documents | ۹ سند هماهنگ برای روش‌شناسی، Schema، منابع، Queryها، رویدادها و تصمیم‌ها |
| Decision Log Completed | 2026-08-14 |
| Last Updated | 2026-08-14 |
| Status of This Version | Accepted — نسخه تجمیع‌شده تصمیم‌های کلان متدولوژی و لاگ تغییرات فنی/مهندسی |

## Team Roles and Labels

| Member | Role label | مسئولیت اصلی |
| --- | --- | --- |
| حسین | Data Lead / Reddit & Integration | معماری استخراج، Reddit، قرارداد Schema، یکپارچه‌سازی، SQL، رفع باگ و نهایی‌سازی کد |
| پارمیدا | YouTube & LLM Lead | استخراج YouTube، ارزیابی و اجرای LLM، Sentiment Pipeline و بخش Pipeline قابل‌تعمیم |
| علی | Financial & Statistical Analysis Lead | داده‌های مالی/اقتصادی، تقسیم‌بندی هفتگی، همبستگی، Granger، Event Analysis و استدلال آماری |
| ریحانه | Power BI, Methodology & Demo Lead | ارزیابی کیفیت و دفاع از منابع، داشبورد، گزارش روش‌شناسی، نگارش یافته‌ها و ویدیوی دمو |
| یاسمن | Documentation QA, Annotation & X Support | اسکلت و کنترل مستندات، لیبل‌زنی مستقل، کمک استخراج X، یکدست‌سازی منابع و کنترل نهایی تحویل |

## Project Calendar

| Project day | Gregorian date | Solar Hijri date | Phase / gate |
| --- | --- | --- | --- |
| Day 1 | 2026-07-23 | ۱ مرداد ۱۴۰۵ | استخراج موازی، نمونه اولیه، تعریف Schema مشترک و شروع مستندات |
| Day 2 | 2026-07-24 | ۲ مرداد ۱۴۰۵ | تکمیل استخراج اولیه، ارزیابی کیفیت و جلسه Go/No-Go |
| Day 3 | 2026-07-25 | ۳ مرداد ۱۴۰۵ | یکپارچه‌سازی، SQL، Sentiment batch اولیه، چارچوب آماری و اسکلت داشبورد |
| Day 4 | 2026-07-26 | ۴ مرداد ۱۴۰۵ | تحلیل عمیق، Event/Financial Analysis، داشبورد واقعی و تجمیع مستندات |
| Day 5 | 2026-07-27 | ۵ مرداد ۱۴۰۵ | جمع‌بندی نسخه اول، مرور روایت، کد، مستندات و دمو اولیه |
| Days 6–16 | 2026-07-28 تا 2026-08-07 | ۶ تا ۱۶ مرداد ۱۴۰۵ | تکمیل Pipeline، داده‌ها، Annotation، تحلیل‌ها و نسخه قابل استفاده داشبورد |
| Days 17–23 | 2026-08-08 تا 2026-08-14 | ۱۷ تا ۲۳ مرداد ۱۴۰۵ | صیقل‌کاری، رفع باگ، تکمیل داده کم، رفع نواقص نسخه اول و تمرین ارائه |
| Day 24 | 2026-08-15 | ۲۴ مرداد ۱۴۰۵ | ارائه نهایی، تحویل کد، مستندات، داشبورد و ویدیوی حداکثر ۱۰ دقیقه |

> **قاعده زمانی:** تصمیم تغییر/تقویت منبع باید در پایان Day 2 گرفته شود. عقب‌انداختن Go/No-Go داده پس از ۲۴ ژوئیه مجاز نیست.

## Decision Authority and Conflict Resolution

| Priority | Governing document | Scope |
| --- | --- | --- |
| 1 | `raw_schema_v02.md` | نام ستون، Type، مقادیر مجاز و قرارداد Collector |
| 2 | `eligibility rules.md` | ورود/خروج، Dedup و ساخت Eligible/Excluded |
| 3 | `query_registry_v3.md` + `source_registry_v3.md` | مسیر Discovery، منبع مجاز، Sort و سقف جمع‌آوری |
| 4 | Chapter 1–3 | مرز مسئله، جامعه، نمونه‌گیری، پلتفرم و دامنه ادعا |
| 5 | `event_registry_v1.md` | رویداد معتبر و قواعد Event Study |
| 6 | این Decision Log | تاریخچه و دلیل تغییرات؛ در تعارض محتوایی تابع اسناد حاکم بالاتر است |

## Traceability Summary

| Decision | Short title | Main supporting decisions |
| --- | --- | --- |
| `D-001` | انتخاب و نقش پلتفرم‌ها | `SD-3-01`، `SD-3-03`، `SD-3-04`، `SD-3-08`، `SR-001` تا `SR-003` |
| `D-002` | واحد مشاهده و Dedup | Chapter 1 §9–10، Eligibility §4 و §6 |
| `D-003` | خوشه نویسنده و حریم خصوصی | Chapter 1 §9 و §16، `SD-07`، Raw Schema §11 |
| `D-004` | مرجع زمانی UTC | Chapter 1 §5، Raw Schema §2 و §10 |
| `D-005` | واحد روند Project Week | Chapter 1 §4–5، Query Registry §2 |
| `D-006` | دامنه تعمیم محدود | `SD-08`، `SD-3-02`، `SR-008` |
| `D-007` | جغرافیا فقط با Evidence | Chapter 1 §11، Raw Schema §7 |
| `D-008` | Raw-preserving و Audit | `SD-02`، Eligibility §1 و §9، Raw Schema §12–13 |
| `D-009` | پایان بازه 2026-07-22 | `ER-005`، `SR-012` |
| `D-010` | W21 به‌عنوان بازه پنج‌روزه | Chapter 1 §4، Raw Schema §10 |
| `D-011` | عدم حذف براساس زبان | Chapter 1 §7، Query Registry §2، Raw Schema §6، `SR-006` |
| `D-012` | اعتبارسنجی تدریجی | Chapter 1 §6.2 و §18، Source Registry §9 |
| `D-013` | Event Registry پیش از تحلیل | Chapter 1 §14–15، `ER-001` تا `ER-009` |
| `D-014` | جمع‌آوری حداکثری و Gold Sample | `SD-04` تا `SD-07`، Source Registry §3.1 و §4.1 |
| `D-015` | خروجی‌های Annotation و Stance Targets | Chapter 1 §2 و §2.1 |
| `D-016` | Go/No-Go داده در پایان روز ۲ | برنامه اجرایی تیم، 2026-07-24 |
| `D-017` | رفع وابستگی پارمیدا → علی با Early Labeled Sample | برنامه روزهای ۲ و ۳ |
| `D-018` | Pivot در صورت کم‌اثر بودن متغیرهای مالی | برنامه روز ۴ |
| `D-019` | مستندسازی و کنترل کیفیت پیوسته | برنامه روزهای ۱ تا ۲۴ |
| `D-020` | Standup روزانه و فاز صیقل‌کاری | برنامه اجرایی ۲۴روزه |

---

# بخش اول: تصمیم‌های راهبردی و روش‌شناسی کلان تیم (D-001 تا D-020)

---

## Decision D-001

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-001 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead) با مشارکت پارمیدا، علی، ریحانه و یاسمن |
| Meeting / Discussion | جمع‌بندی تیم براساس Chapter 1، Chapter 3 و Source Registry |

### Title

انتخاب X، Reddit و YouTube با نقش‌های مکمل و بدون وزن ثابت پیشینی

### Context

یک پلتفرم به‌تنهایی تنوع گفت‌وگوی مشاهده‌شده را پوشش نمی‌دهد. X برای واکنش سریع، Reddit برای بحث جامعه‌محور و YouTube برای واکنش به روایت رسانه‌ای ارزش متفاوتی دارند. تفاوت حجم نیز معادل تفاوت اهمیت یا نمایندگی نیست.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | فقط X | روند زمانی سریع و متراکم | Access محدود؛ Platform Bias بالا |
| B | وزن برابر 33/33/33 برای سه پلتفرم | خروجی ترکیبی ساده | وزن دل‌بخواهی و غیرقابل دفاع |
| C | سه پلتفرم با تحلیل مستقل و مقایسه ثانویه | حفظ تفاوت ساختاری و Bias هر منبع | مدل و گزارش پیچیده‌تر |

### Decision

> X پلتفرم اصلی عملیاتی است و Reddit و YouTube نقش مکمل دارند. نتایج ابتدا برای هر پلتفرم جداگانه گزارش می‌شوند؛ هر مقایسه یا تجمیع بعدی باید `platform` و Platform Mix را حفظ کند و هیچ وزن ثابتی پیش از ارزیابی Coverage و کیفیت اعمال نمی‌شود.

### Rationale

- هر پلتفرم یک نوع گفت‌وگوی متفاوت را مشاهده می‌کند.
- تعداد رکورد بیشتر دلیل نمایندگی یا کیفیت بیشتر نیست.
- تحلیل جداگانه امکان شناسایی Platform Bias و Composition Shift را فراهم می‌کند.
- مسیرهای Collection مطابق Source Registry هستند: X به‌صورت Query-first، Reddit به‌صورت Source-scoped + `r/all` و YouTube به‌صورت Channel → Video → Comment.

### Expected Consequences

#### Positive

- قابلیت ساخت داشبورد مستقل و ترکیبی با یک Schema مشترک.
- محدودشدن تفسیرهای نادرست ناشی از سلطه حجمی یک پلتفرم.
- شفاف‌شدن تفاوت Coverage و Bias.

#### Negative

- مقایسه مستقیم درصدها نیازمند کنترل Platform Mix است.
- یک KPI ترکیبی ساده و بدون فرض اضافی قابل دفاع نیست.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ساخت صفحات مستقل X/Reddit/YouTube و نمایش Platform Mix در Overview | ریحانه | 2026-08-14 / ۲۳ مرداد |
| ثبت Coverage و محدودیت Access هر پلتفرم | حسین، پارمیدا و یاسمن | 2026-08-07 / ۱۶ مرداد |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §6
- `Chapter_3_Platform_Selection_and_Source_Justification_vo2.md`؛ `SD-3-01`، `SD-3-03`، `SD-3-04`، `SD-3-08`
- `source_registry_v3.md`؛ `SR-001`، `SR-002`، `SR-003`، `SR-008`

---

## Decision D-002

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-002 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead / Schema & Integration) |
| Meeting / Discussion | Chapter 1، Eligibility Rules و Raw Schema |

### Title

واحد مشاهده = محتوای متنی عمومی و یکتا؛ کلید Dedup = پلتفرم + شناسه محتوا

### Context

پست، کامنت، ریپلای، Quote و Repost نقش یکسانی ندارند و یک محتوا ممکن است با چند Query بازیابی شود. شمارش هر Match به‌عنوان رکورد مستقل حجم را مصنوعی افزایش می‌دهد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | هر Query Match یک Observation | ساده برای Collection | تکرار مصنوعی شدید |
| B | کلید فقط `platform_content_id` | Dedup ساده | احتمال برخورد شناسه میان پلتفرم‌ها |
| C | کلید `platform + platform_content_id` و حفظ همه Queryها | یکتایی قابل دفاع و Provenance کامل | نیازمند `matched_query_ids` |

### Decision

> هر محتوای متنی عمومی و یکتا یک Observation است. Dedup با `platform + platform_content_id` انجام می‌شود. اگر محتوا با چند Query پیدا شود یک رکورد می‌ماند و همه شناسه‌ها با جداکننده `;` در `matched_query_ids` حفظ می‌شوند.

### Rationale

- شناسه پلتفرمی درون یک پلتفرم پایدار است.
- افزودن `platform` برخورد احتمالی شناسه‌های مشابه را رفع می‌کند.
- حفظ `matched_query_ids` مسیر کشف را بدون تکرار رکورد نگه می‌دارد.
- Near-duplicate متنی حذف قطعی نمی‌شود و فقط برای Sensitivity علامت می‌خورد.

### Expected Consequences

#### Positive

- جلوگیری از شمارش چندباره و تورم حجم.
- حفظ قابلیت Audit مسیرهای Discovery.

#### Negative

- Dedup باید پیش از Eligibility نهایی و با منطق چندQuery اجرا شود.
- تحلیل Near-duplicate به مرحله حساسیت منتقل می‌شود.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ساخت `ContentKey = platform & "|" & platform_content_id` در Staging | حسین و ریحانه | 2026-07-27 / ۵ مرداد |
| نگه‌داری `matched_query_ids` با جداکننده `;` | حسین، پارمیدا و یاسمن | در هر Run |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §9–10
- `eligibility rules.md` §4 و §6
- `raw_schema_v02.md` §2–3

---

## Decision D-003

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-003 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead)؛ اجرا توسط مالک Collector هر پلتفرم |
| Meeting / Discussion | Chapter 1، Chapter 2 و Raw Schema |

### Title

واحد خوشه = `author_hash` با SALT ثابت و بدون ذخیره شناسه خام

### Context

چند رکورد از یک نویسنده مستقل نیستند و کاربران پرکار می‌توانند روند را منحرف کنند. هم‌زمان، ذخیره نام کاربری یا ID خام ریسک حریم خصوصی دارد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | ذخیره نام یا ID خام | اتصال مستقیم رکوردها | ریسک حریم خصوصی و بازشناسایی |
| B | `sha256(author_id)` بدون SALT | ساده | قابل حمله با حدس ID |
| C | هش `platform:author_id:SALT` با SALT محیطی | حریم خصوصی و خوشه‌بندی درون‌پلتفرمی | نیازمند مدیریت امن SALT؛ هویت بین‌پلتفرمی اثبات نمی‌شود |

### Decision

> Collector باید `author_hash` را با SHA-256 و SALT محرمانه ثابت پروژه بسازد؛ شناسه یا نام خام نویسنده روی دیسک ذخیره نمی‌شود. تحلیل عدم قطعیت با Cluster Bootstrap روی `author_hash` انجام می‌شود.

### Rationale

- خوشه نویسنده برای کنترل وابستگی و Power-user Bias ضروری است.
- SALT از بازیابی ساده هویت جلوگیری می‌کند.
- وجود `platform` در فرمول یعنی هش برای خوشه‌بندی درون‌پلتفرمی معتبر است و نباید به‌عنوان هویت واحد بین‌پلتفرمی تفسیر شود.

### Expected Consequences

#### Positive

- کنترل وابستگی رکوردها و کاربران پرکار.
- کاهش ریسک افشای هویت.

#### Negative

- گم‌شدن SALT یا تغییر آن خوشه‌بندی را ناسازگار می‌کند.
- مقایسه یک شخص میان پلتفرم‌ها ممکن نیست.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| قراردادن `PROJECT_AUTHOR_SALT` در Environment و منع Hard-code | حسین با هماهنگی Collectorها | 2026-07-25 / ۳ مرداد |
| کنترل کامل‌بودن `author_hash` و ثبت نتیجه در گزارش کیفیت | ریحانه و حسین | 2026-08-07 / ۱۶ مرداد |

### Related Resources

- `raw_schema_v02.md` §5 و §11
- `Chapter_2_Statistical_Population_and_Sampling_Design_v4.md`؛ `SD-07`
- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §9 و §16

---

## Decision D-004

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-004 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead) |
| Meeting / Discussion | Chapter 1 و Raw Schema |

### Title

ذخیره همه زمان‌ها در UTC و قالب ISO 8601 با `Z`

### Context

سه پلتفرم و کاربران در منطقه‌های زمانی متفاوت‌اند. نگه‌داری زمان محلی یا Epoch بدون قرارداد مشترک، مرزبندی هفته و تحلیل رویداد را ناسازگار می‌کند.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | زمان محلی هر پلتفرم | نزدیک به نمایش رابط | غیرقابل مقایسه و مبهم |
| B | Epoch | فشرده و قابل محاسبه | خوانایی کم و احتمال خطای واحد |
| C | UTC در ISO 8601 با `Z` | استاندارد، خوانا و مشترک | تبدیل اولیه لازم دارد |

### Decision

> `created_at_utc`، `collected_at_utc` و `engagement_collected_at_utc` در UTC و قالب ISO 8601 با `Z` ذخیره می‌شوند. Epoch و زمان بدون Zone در Raw مجاز نیست.

### Rationale

- مرز هفته‌ها و رویدادها باید در هر سه پلتفرم یکسان باشد.
- ISO با `Z` برای Audit انسانی و پردازش ماشینی مناسب است.

### Expected Consequences

#### Positive

- محاسبه یکسان Project Week و Lag رویداد.
- جلوگیری از خطای DateTime/DateTimeZone در Power Query.

#### Negative

- تمام Collectorها باید تبدیل صحیح Zone را انجام دهند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| اعتبارسنجی `Z` و Type تاریخ در هر سه Staging Query | حسین و ریحانه | 2026-07-25 / ۳ مرداد |
| نگه‌داری زمان محلی فقط در صورت نیاز و در فیلد جدا | حسین، پارمیدا و یاسمن | در صورت نیاز |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §5
- `raw_schema_v02.md` §2 و §10 و §12

---

## Decision D-005

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-005 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | علی (Financial & Statistical Lead) با همکاری حسین |
| Meeting / Discussion | Chapter 1، Query Registry و Raw Schema |

### Title

واحد روند = Project Week و اجرای ثابت Query × Week

### Context

تحلیل روزانه برای داده کم‌حجم ناپایدار است و تحلیل ماهانه شکست روند را پنهان می‌کند. همچنین افزودن Query فقط در هفته‌های جدید جهش مصنوعی می‌سازد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | گزارش روزانه | جزئیات زیاد | نویز و حجم کم در برخی روزها |
| B | گزارش ماهانه | ساده | فقط پنج نقطه و از دست‌رفتن رویدادها |
| C | W01–W21 و Query ثابت در همه هفته‌ها | تعادل جزئیات و پایداری | نیازمند اجرای پنجره‌ای و Backfill |

### Decision

> واحد اصلی روند `project_week` است. هر Query به‌صورت پنجره‌ای برای هر هفته اجرا می‌شود و مجموعه Queryها در ۲۱ هفته ثابت می‌ماند. Query جدید فقط با Backfill همه هفته‌ها فعال می‌شود؛ Query قدیمی حذف فیزیکی نمی‌شود و `archived` می‌گردد.

### Rationale

- هفته برای نمایش روند و Event Study قابل دفاع‌تر است.
- ثابت‌بودن Query از تغییر مصنوعی Composition جلوگیری می‌کند.
- اجرای Query × Week قابلیت Resume و Audit را بالا می‌برد.

### Expected Consequences

#### Positive

- ۲۱ نقطه زمانی قابل مقایسه.
- پایش شفاف وضعیت اجرای هر Query در هر هفته.

#### Negative

- Query جدید هزینه Backfill دارد.
- W21 نیازمند علامت و تفسیر جداگانه است.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ساخت/تکمیل `{platform}_runs.csv` برای هر Query × Week | حسین، پارمیدا و یاسمن | 2026-08-07 / ۱۶ مرداد |
| جلوگیری از فعال‌سازی Query جدید بدون Backfill | حسین | دائمی |

### Related Resources

- `query_registry_v3.md` §2
- `raw_schema_v02.md` §10 و §13
- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §4–5

---

## Decision D-006

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-006 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | ریحانه (Methodology & Source Justification Lead) |
| Meeting / Discussion | Chapters 1–3 و Source Registry |

### Title

دامنه تعمیم = محتوای Eligible مشاهده‌شده، نه افکار عمومی جهان

### Context

هدف پروژه برآورد تمام مردم جهان نیست. ما تحلیل را روی محتوای عمومی قابل مشاهده و واجد شرایط در پلتفرم‌های منتخب انجام می‌دهیم و تفاوت‌های Self-selection، Access و Platform را در تفسیر نتایج لحاظ می‌کنیم.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | تعمیم به همه مردم جهان | تیتر ساده و جذاب | از نظر آماری نادرست |
| B | تعمیم به همه کاربران سه پلتفرم | محدودتر | همچنان Sampling Frame کامل وجود ندارد |
| C | محدودکردن ادعا به محتوای Eligible مشاهده‌شده | قابل دفاع و شفاف | ادعای محدودتر |

### Decision

> عبارت استاندارد گزارش: «در میان محتواها و کاربران مشاهده‌شده در پلتفرم‌های منتخب…». هیچ درصدی به کل مردم، کشورها یا کل کاربران پلتفرم‌ها تعمیم داده نمی‌شود.

### Rationale

- چارچوب پروژه بر تحلیل محتوای قابل مشاهده و واجد شرایط متمرکز است.
- حجم داده، نمایندگی را ثابت نمی‌کند.
- محدودکردن ادعا شرط دفاع روش‌شناختی پروژه است.

### Expected Consequences

#### Positive

- جلوگیری از ادعای آماری بیش از داده.
- گزارش قابل دفاع در برابر نقد Sampling Bias.

#### Negative

- نتایج درباره «نگرش جهانی» فقط به‌عنوان داده مشاهده‌شده تفسیر می‌شوند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| بازبینی همه عنوان‌ها و Narrativeهای داشبورد برای حذف ادعای جمعیتی | ریحانه و یاسمن | 2026-08-14 / ۲۳ مرداد |
| افزودن بخش Limitations به هر صفحه پلتفرم | ریحانه با بازبینی یاسمن | 2026-08-14 / ۲۳ مرداد |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §8
- `Chapter_2_Statistical_Population_and_Sampling_Design_v4.md`؛ `SD-08`
- `Chapter_3_Platform_Selection_and_Source_Justification_vo2.md`؛ `SD-3-02`
- `source_registry_v3.md`؛ `SR-008`

---

## Decision D-007

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-007 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | ریحانه (Data Quality / Power BI) با همکاری علی |
| Meeting / Discussion | Chapter 1 و Raw Schema |

### Title

Location فقط با Evidence؛ زبان متن جایگزین کشور نویسنده نیست

### Context

برای حفظ دقت تحلیل، جغرافیای نویسنده را فقط زمانی گزارش می‌کنیم که شواهد مشخص و قابل سنجش در دسترس باشد. زبان، کانال و Subreddit به‌تنهایی مبنای تعیین کشور نیستند.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | کشور = زبان متن | تکمیل سریع نقشه | استنتاج نادرست و غیرقابل دفاع |
| B | کشور = کشور رسانه/منبع | ساده | مکان نویسنده را نشان نمی‌دهد |
| C | ثبت مکان فقط با Evidence و گزارش Coverage | قابل دفاع و شفاف | تعداد رکوردهای قابل استفاده برای نقشه محدودتر است |

### Decision

> ما `country_or_region` را فقط همراه با شواهد و فیلدهای `geo_method`، `geo_confidence`، `geo_granularity` و `geo_limitations` وارد تحلیل می‌کنیم. زبان، کشور منبع یا رسانه برای تعیین کشور کاربر کافی نیست.

### Rationale

- زبان و جغرافیا دو متغیر مستقل‌اند.
- تحلیل جغرافیایی باید به رکوردهای دارای شواهد محدود شود.
- نمایش Geography Coverage در کنار نقشه از برداشت نادرست جلوگیری می‌کند.

### Expected Consequences

#### Positive

- جلوگیری از نسبت‌دادن اشتباه دیدگاه به کشورها.
- شفافیت سطح اطمینان داده جغرافیایی.

#### Operational Rule

- نقشه فقط زمانی منتشر می‌شود که Coverage و Confidence برای تفسیر قابل دفاع باشد؛ در غیر این صورت تمرکز صفحه روی زبان و منبع قرار می‌گیرد.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| محاسبه Geography Coverage پیش از ساخت Map | ریحانه با داده حسین | 2026-08-07 / ۱۶ مرداد |
| غیرفعال‌کردن نقشه در صورت Coverage کمتر از آستانه سند | ریحانه | پس از ارزیابی Coverage |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §11
- `raw_schema_v02.md` §7

---

## Decision D-008

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-008 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead) و ریحانه (Data Quality / Power BI) |
| Meeting / Discussion | Chapters 1–2، Eligibility و Raw Schema |

### Title

Raw بدون تغییر حفظ می‌شود؛ Eligibility و Exclusion قابل Audit هستند

### Context

پاک‌کردن متن، حذف رکورد خارج بازه یا حذف بی‌ردپای محتوای نامرتبط بازتولیدپذیری را از بین می‌برد. Collector نباید درباره ارتباط موضوعی تصمیم بگیرد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | پاکسازی و حذف داخل Collector | فایل کوچک‌تر | از دست‌رفتن شواهد و Audit |
| B | فقط فایل Clean نگه داشته شود | مدل ساده | علت حذف‌ها قابل بررسی نیست |
| C | Raw immutable + Eligible + Excluded Audit | بازتولیدپذیر و شفاف | فضای ذخیره و Pipeline بیشتر |

### Decision

> Raw دست‌نخورده باقی می‌ماند. Cleaning در Staging انجام می‌شود. Eligibility پس از Raw و پیش از Analytical Dataset اجرا می‌شود و رکوردهای کنارگذاشته‌شده با `exclusion_reason` و notes در Exclusion Audit حفظ می‌شوند.

### Rationale

- Raw مبنای بازتولید و رفع خطاست.
- Collector فقط Contract داده را اجرا می‌کند.
- شمارش Exclusion به تفکیک پلتفرم و هفته بخشی از گزارش کیفیت است.
- فایل `{platform}_runs.csv` برای اثبات Sort، Access و Coverage اجباری است.

### Expected Consequences

#### Positive

- امکان بازسازی Clean و اصلاح قواعد بدون استخراج مجدد.
- شفافیت کنترل کیفیت و دلایل کنارگذاری رکوردها.

#### Negative

- چند لایه داده و نیاز به مدیریت Version.
- حجم ذخیره بیشتر.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ایجاد خروجی‌های `Eligible` و `Excluded` به‌جای حذف خاموش | حسین | 2026-07-27 / ۵ مرداد |
| خاموش‌کردن Enable Load برای Staging/Raw Referenceهای تکراری در Power BI | ریحانه | 2026-08-07 / ۱۶ مرداد |

### Related Resources

- `eligibility rules.md` §1، §5 و §9
- `raw_schema_v02.md` §0، §9، §12 و §13
- `Chapter_2_Statistical_Population_and_Sampling_Design_v4.md`؛ `SD-02`

---

## Decision D-009

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-009 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | حسین (Data Lead)؛ تأیید تیمی |
| Meeting / Discussion | Chapter 1، Event Registry و Source Registry |

### Title

پایان رسمی بازه پروژه = 2026-07-22 23:59:59 UTC

### Context

تبدیل تاریخ شمسی 31 تیر 1405 باید در همه اسناد، Queryها، Collectorها و Event Registry یکسان باشد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | پایان 2026-07-23 یا تاریخ اجرای پروژه | پوشش بیشتر | مغایر دامنه رسمی و ایجاد W21 متفاوت |
| B | پایان 2026-07-22 | منطبق با 31 تیر 1405 و اسناد | هفته پایانی پنج‌روزه |

### Decision

> بازه رسمی از `2026-02-28T00:00:00Z` تا `2026-07-22T23:59:59Z` است. رکوردهای بعد از آن در Raw نگه داشته می‌شوند اما `in_window=false` و `project_week=OUT` می‌گیرند.

### Rationale

- هماهنگی صریح Chapter 1، Raw Schema، Event Registry و Source Registry.
- جلوگیری از تفاوت شمارش بین پلتفرم‌ها.

### Expected Consequences

#### Positive

- یک Filter رسمی و مشترک.
- Event و داده خارج بازه قابل شناسایی می‌مانند.

#### Negative

- داده جمع‌آوری‌شده تا تاریخ‌های بعد وارد تحلیل اصلی نمی‌شود.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| انتقال START/END به Config و حذف تاریخ Hard-code متناقض | حسین | 2026-07-24 / ۲ مرداد |
| کنترل `in_window` با `created_at_utc`، نه `collected_at_utc` | حسین و ریحانه | 2026-07-25 / ۳ مرداد |

### Related Resources

- `event_registry_v1.md`؛ `ER-005`
- `source_registry_v3.md`؛ `SR-012`
- `eligibility rules.md` §3.1

---

## Decision D-010

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-010 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | علی (Statistical Lead) و ریحانه (Power BI Lead) |
| Meeting / Discussion | Chapter 1 و Raw Schema |

### Title

W21 بازه پنج‌روزه است و با نرخ روزانه گزارش می‌شود

### Context

W21 بازه 18 تا 22 جولای را شامل می‌شود و پنج روز داده داخل محدوده رسمی پروژه دارد. برای مقایسه منصفانه، طول این بازه را در محاسبات و نمودارها لحاظ می‌کنیم.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | حذف W21 | سری هم‌طول | از دست‌رفتن پنج روز داده معتبر |
| B | رفتار مانند هفته کامل | ساده | مقایسه گمراه‌کننده |
| C | حفظ با `is_partial_week=true` و نمایش نرخ روزانه | استفاده کامل و قابل مقایسه از داده | نیازمند منطق Visual جدا |

### Decision

> رکوردهای 18–22 جولای Eligible هستند و `project_week=W21` و `is_partial_week=true` می‌گیرند. ما حجم W21 را با Badge «بازه ۵ روزه» و معیار Volume per Day نمایش می‌دهیم.

### Rationale

- داده داخل بازه نباید حذف شود.
- تفاوت طول دوره باید در محاسبه و Visual قابل مشاهده باشد.

### Expected Consequences

#### Positive

- حفظ داده معتبر و جلوگیری از تفسیر کاذب.

#### Negative

- KPI و Tooltip اضافی لازم است.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| افزودن Badge «W21: بازه ۵ روزه» به Visualها | ریحانه | 2026-08-14 / ۲۳ مرداد |
| محاسبه Volume per Day برای مقایسه تکمیلی | علی | 2026-08-07 / ۱۶ مرداد |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §4
- `raw_schema_v02.md` §10
- `eligibility rules.md` §3.1

---

## Decision D-011

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-011 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | پارمیدا (YouTube & LLM Lead) با همکاری حسین و یاسمن |
| Meeting / Discussion | Chapter 1، Query Registry، Raw Schema و Source Registry |

### Title

هیچ رکورد بازیابی‌شده‌ای صرفاً به دلیل زبان حذف نمی‌شود؛ EN/FA زبان‌های Discovery هستند

### Context

تمرکز Query بر انگلیسی و فارسی برای کنترل دامنه لازم است، اما حذف رکورد مرتبط با زبان دیگر Bias ایجاد می‌کند. هم‌زمان، زبان متن کشور نویسنده را تعیین نمی‌کند.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | فقط English | هزینه کمتر | حذف فارسی و Language Bias شدید |
| B | فقط EN/FA و حذف سایر رکوردها | دامنه ساده | حذف مشاهده‌های مرتبط |
| C | Discovery اصلی EN/FA؛ حفظ `other` | شفاف و کم‌حذف | نیازمند Language Detection و گزارش Coverage |

### Decision

> Queryهای اصلی به EN و FA محدودند، اما هر رکورد مرتبط بازیابی‌شده با زبان دیگر به `other` نگاشت و حفظ می‌شود. حذف براساس زبان ممنوع است. کانال‌های عربی از Source Registry فعال خارج‌اند، ولی محتوای عربی که از مسیر مجاز دیگر بازیابی شود حذف نمی‌شود.

### Rationale

- جداسازی دامنه Discovery از Eligibility تناقض ظاهری Source Registry و Eligibility را رفع می‌کند.
- `language_detected` برای تحلیل Composition Shift ضروری است.
- زبان و کشور نویسنده یکی نیستند.

### Expected Consequences

#### Positive

- حفظ مشاهده‌های مرتبط و امکان گزارش Language Mix.
- سنجش و گزارش Coverage فارسی Reddit و سایر زبان‌ها.

#### Negative

- مدل زبان باید `en/fa/other` را با Confidence تولید کند.
- ادعای چندزبانه بودن به Coverage واقعی محدود می‌شود.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| اجرای Language Detection روی داده Reddit و استانداردسازی زبان | پارمیدا با تحویل داده از حسین | 2026-08-07 / ۱۶ مرداد |
| حفظ `language_reported` و `language_detected` جداگانه | حسین و پارمیدا | دائمی |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §7
- `query_registry_v3.md` §2 و §8
- `raw_schema_v02.md` §6
- `source_registry_v3.md`؛ `SR-006`

---

## Decision D-012

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-012 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | حسین (Collection Lead)، پارمیدا (YouTube)، یاسمن (X Support) |
| Meeting / Discussion | Chapter 1، Query Registry و Source Registry |

### Title

اعتبارسنجی دسترسی، Query و کیفیت به‌صورت تدریجی در Main Collection انجام می‌شود

### Context

ما اعتبارسنجی را هم‌زمان با Main Collection انجام می‌دهیم تا Historical Access، Sort واقعی، Precision و Coverage هر پلتفرم از همان اجرای اول ثبت و کنترل شود.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | Pilot مستقل پیش از Main Collection | تفکیک کامل دو فاز | زمان اجرای طولانی‌تر |
| B | کنترل فقط در انتهای استخراج | اجرای اولیه سریع | کشف دیرهنگام خطا |
| C | Validation تدریجی با Gate و Runs Audit | عملی، سریع و قابل Audit | نیازمند ثبت منظم Runها |

### Decision

> اعتبارسنجی در جریان Main Collection انجام می‌شود. برای هر پلتفرم Access، Rate/Quota، `sort_mode`، تاریخ قدیمی‌ترین رکورد و بازیابی W01 را در Runs/Access Notes ثبت می‌کنیم. آزمون W01 گیت تصمیم‌گیری درباره روش دسترسی و دامنه Coverage است.

### Rationale

- اعتبارسنجی هم‌زمان، زمان پروژه را حفظ و کیفیت Collection را کنترل می‌کند.
- Gate تاریخی باعث می‌شود Coverage روند پیش از تحلیل تثبیت شود.
- Query جدید فقط پس از Backfill همه هفته‌ها فعال می‌شود.
- Query high-risk بدون Entity Anchor اجرا نمی‌شود و Sort باید زمانی باشد.

### Expected Consequences

#### Positive

- ادامه کار بدون حذف کنترل کیفیت.
- ثبت شفاف محدودیت Access و Query.

#### Operational Rule

- هر اصلاح Query یا Access با Run جدید ثبت و در صورت نیاز برای همه هفته‌ها Backfill می‌شود.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| تکمیل `verified_at` و آزمون W01 برای همه منابع | حسین، پارمیدا و یاسمن | 2026-07-24 / ۲ مرداد |
| ثبت عدد واقعی Rate Limit/Quota و مسیر API | حسین، پارمیدا و یاسمن | 2026-07-24 / ۲ مرداد |
| Archive کردن Query ضعیف به‌جای حذف و ثبت دلیل | حسین با تأیید تیم | هنگام تغییر Registry |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §6.2 و §18
- `source_registry_v3.md` §9
- `query_registry_v3.md` §1–2 و §9

---

## Decision D-013

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-013 |
| Date | 2026-07-25 / ۳ مرداد ۱۴۰۵ / Day 3 |
| Status | Accepted |
| Decision Owner(s) | علی (Event & Statistical Analysis) و یاسمن (Documentation QA) |
| Meeting / Discussion | Chapter 1 و Event Registry |

### Title

ثبت و نسخه‌بندی Event Registry پیش از تحلیل؛ ورود فقط رویدادهای تأییدشده

### Context

انتخاب رویداد پس از مشاهده نمودار Cherry-picking ایجاد می‌کند. رویدادهای هم‌روز، تقویمی و قطعی اینترنت نیز می‌توانند حجم گفتگو یا قابلیت جمع‌آوری را تغییر دهند.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | انتخاب رویداد بعد از دیدن Spike | سریع | Cherry-picking و ادعای علت کاذب |
| B | استفاده از همه رویدادهای گزارش‌شده | Coverage زیاد | ورود ادعاهای تک‌منبعه و disputed |
| C | Registry پیشینی با Status و حداقل دو منبع | قابل دفاع و حساسیت‌پذیر | نیازمند راستی‌آزمایی منابع |

### Decision

> ما Event Registry را پیش از تحلیل نهایی ثابت و نسخه‌بندی می‌کنیم. فقط رویدادهای دارای وضعیت `confirmed_2plus`، `confirmed_primary_plus_independent` و برای Media مقدار `confirmed_direct_plus_news` وارد تحلیل تأییدی می‌شوند. سایر وضعیت‌ها در تحلیل حساسیت یا مسیر راستی‌آزمایی مدیریت می‌شوند.

### Rationale

- دو منبع مستقل احتمال خطای رویداد را کاهش می‌دهد.
- `event_class` رویداد جنگی را از `context` و `data_artifact` جدا می‌کند.
- رویدادهای هم‌روز مانع نسبت‌دادن Spike به یک علت منفرد می‌شوند.
- گزارش فقط از زبان هم‌زمانی/همبستگی استفاده می‌کند، نه علت.

### Expected Consequences

#### Positive

- Event Study بازتولیدپذیر و مقاوم‌تر به Cherry-picking.
- شناسایی اثر قطع اینترنت و رویدادهای تقویمی بر داده.

#### Negative

- رویدادهای تک‌منبعه تا زمان تأیید کنار می‌مانند.
- رویدادهای خوشه‌ای تفسیر منفرد ندارند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| کنترل نهایی وضعیت و شمارش رویدادها در Registry | علی و یاسمن | 2026-08-14 / ۲۳ مرداد |
| راستی‌آزمایی منابع رویدادها و تعیین مسیر Confirmatory/Sensitivity | علی با کنترل یاسمن | 2026-08-14 / ۲۳ مرداد |
| محاسبه خودکار `is_clustered` و پنجره‌های pre/post | علی | 2026-08-07 / ۱۶ مرداد |

### Related Resources

- `event_registry_v1.md` §2، §5–7؛ `ER-001` تا `ER-009`
- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §14–15

---

## Decision D-014

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-014 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | حسین (Collection)، پارمیدا (LLM/Gold Sample) و یاسمن (Independent Annotation) |
| Meeting / Discussion | Chapter 2، Source Registry و Raw Schema |

### Title

جمع‌آوری حداکثری در چارچوب دسترسی؛ نمونه‌گیری تصادفی فقط برای Gold Sample و سقف‌های ثبت‌شده

### Context

جامعه تحلیل ما Eligible Population حاصل از مسیرهای مجاز Query و Source Registry است. از آنجا که هدف پروژه تحلیل روند در محتوای مشاهده‌شده است، به‌جای فرمول کوکرن از جمع‌آوری حداکثری استفاده می‌کنیم. برای Submission/Videoهای بسیار بزرگ نیز سقف عملی 300 با نمونه‌گیری تصادفی ثبت‌شده به کار می‌رود.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | فرمول کوکرن و نمونه ثابت | روش آشنا | با چارچوب مشاهده‌ای و روند زمانی پروژه سازگار نیست |
| B | فقط Top/Hot یا Quota از پیش | ارزان | Ranking/Composition Bias شدید |
| C | Max Collection + Full Eligible برای روند + Gold Sample تصادفی | Coverage زمانی و ارزیابی مدل | هزینه بیشتر و نیازمند Audit سقف‌ها |

### Decision

> تا حد مجاز API و Registry، جمع‌آوری حداکثری انجام می‌شود. همه Eligibleها با LLM برچسب می‌خورند و Gold Sample تصادفی با seed ثابت و طبقه‌بندی `Platform × Language` برای ارزیابی انسانی ساخته می‌شود. اگر سقف 300 کامنت برای Submission/Video اعمال شد، انتخاب تصادفی با seed ثابت انجام و `source_total_available`، `sampling_applied`، `items_kept` و `random_seed` ثبت می‌شوند.

### Rationale

- هدف اصلی روند و Event Study نیازمند Coverage زمانی است.
- Gold Sample برای سنجش F1/Kappa است، نه ساخت روند.
- Sort زمانی و نمونه تصادفی از سلطه Top comments جلوگیری می‌کند.
- سقف عملی به‌صورت شفاف در متادیتای Collection ثبت می‌شود.

### Expected Consequences

#### Positive

- استفاده از تمام Eligible قابل دسترس برای روند.
- ارزیابی کمی عدم قطعیت مدل با Gold Sample.
- تکرارپذیری سقف 300 با seed ثابت.

#### Reporting Rule

- نتایج با عبارت «در میان محتوای واجد شرایط مشاهده‌شده» گزارش می‌شوند و موارد اعمال سقف در Coverage Summary نمایش داده می‌شوند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ساخت Gold Sample تصادفی `Platform × Language` با seed ثابت | پارمیدا و یاسمن | 2026-07-27 / ۵ مرداد |
| ثبت کامل فیلدهای Sampling برای موارد عبور از 300 | حسین و پارمیدا | در هر Run |
| گزارش F1/Kappa و Cluster Bootstrap | پارمیدا و علی | 2026-08-14 / ۲۳ مرداد |

### Related Resources

- `Chapter_2_Statistical_Population_and_Sampling_Design_v4.md`؛ `SD-04` تا `SD-07`
- `source_registry_v3.md` §3.1 و §4.1
- `raw_schema_v02.md` §3 و §12

---

## Decision D-015

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-015 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | پارمیدا (Annotation/LLM Lead) و یاسمن (Independent Annotator) |
| Meeting / Discussion | Chapter 1 و Chapter 2 |

### Title

Sentiment جایگزین Stance نیست؛ هفت Target اولیه برای Stance تعریف می‌شود

### Context

منفی‌بودن لحن مشخص نمی‌کند کاربر با کدام بازیگر یا اقدام موافق یا مخالف است. تحلیل پروژه علاوه بر Sentiment به Stance، Emotion و Topic/Frame نیاز دارد.

### Options Considered

| Option | Description | Advantages | Disadvantages |
| --- | --- | --- | --- |
| A | فقط Sentiment | ساده و ارزان | پاسخ‌ندادن به موضع نسبت به Target |
| B | یک Stance کلی بدون Target | ساده‌تر | ابهام معنایی بالا |
| C | خروجی‌های جدا + Stance نسبت به Target مشخص | تفسیر دقیق | Annotation پیچیده‌تر و پرهزینه‌تر |

### Decision

> چهار خروجی مستقل `sentiment`، `stance`، `emotion` و `topic_frame` تولید می‌شوند. Stance همیشه نسبت به Target مشخص است. فهرست اجرایی شامل T-01 دولت ایران، T-02 دولت آمریکا، T-03 تشدید نظامی، T-04 دیپلماسی، T-05 تحریم/فشار اقتصادی، T-06 پیامد انسانی و T-07 رسانه/اطلاعات است و در Annotation Guide اعمال می‌شود.

### Rationale

- Sentiment و Stance مفاهیم متفاوت‌اند.
- Target مشخص از برچسب‌های متناقض و غیرقابل تفسیر جلوگیری می‌کند.
- Gold Sample امکان ارزیابی کیفیت هر خروجی را فراهم می‌کند.

### Expected Consequences

#### Positive

- تحلیل دقیق‌تر تغییر نگرش و روایت.
- امکان پاسخ به پرسش‌های سیاسی، انسانی و اقتصادی به‌صورت جدا.

#### Negative

- Prompt، Annotation Guide و Validation پیچیده‌تر می‌شوند.
- Targetهای کم‌نمونه ممکن است نیازمند ادغام یا گزارش عدم قطعیت باشند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| تصویب نهایی Targetها و Label definitionها | Annotation/Research team | پیش از Annotation گسترده |
| ثبت هر تغییر Target به‌عنوان Decision جدید یا Superseding entry | یاسمن با تأیید پارمیدا | هنگام تغییر |
| ارزیابی F1/Kappa به تفکیک Platform × Language و خروجی | پارمیدا و یاسمن | پس از Gold Sample |

### Related Resources

- `Chapter_1_Project_Definition_and_Research_Design_v3.md` §2 و §2.1
- `Chapter_2_Statistical_Population_and_Sampling_Design_v4.md` §2 و §6

---

## Decision D-016

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-016 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / پایان Day 2 |
| Status | Accepted — Hard Gate |
| Decision Owner(s) | حسین به‌عنوان Data Lead؛ تصمیم نهایی با مشارکت همه اعضا |

### Title

تصمیم Go/No-Go داده نباید بعد از پایان روز دوم عقب بیفتد

### Context and Options

در پایان دو روز اول باید حجم، کیفیت، تنوع دیدگاه، زبان و Coverage هفتگی بررسی شود. گزینه‌ها: ادامه با منابع فعلی، تقویت/جایگزینی منبع ضعیف، یا کوچک‌کردن دامنه. ادامه بدون تصمیم باعث انتقال ریسک داده به روزهای تحلیل می‌شود.

### Decision and Rationale

> جلسه ۳۰ تا ۴۵ دقیقه‌ای Go/No-Go در پایان ۲۴ ژوئیه برگزار می‌شود. اگر منبعی حجم یا کیفیت کافی نداشته باشد، همان شب تقویت/جایگزین می‌شود یا دامنه پروژه کوچک‌تر می‌گردد. این تصمیم به روزهای بعد منتقل نمی‌شود.

- حجم توصیه‌شده برای روند: حداقل چندصد رکورد در هفته، با گزارش استثناها.
- کافی‌بودن حجم به‌تنهایی کافی نیست؛ Language/Platform Mix و تنوع دیدگاه هم بررسی می‌شود.
- X فقط زمانی تقویت می‌شود که منابع اصلی نتوانند Coverage لازم را بدهند یا مسیر استخراج با کمک حسین قابل دفاع باشد.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| ارائه آمار حجم، هفته، Null، Duplicate و Source Mix | حسین | 2026-07-24 |
| ارزیابی دفاع‌پذیری منابع و جامعه مشاهده‌شده | ریحانه | 2026-07-24 |
| ثبت تصمیم Go/No-Go و اقدام اصلاحی | یاسمن | همان جلسه |

---

## Decision D-017

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-017 |
| Date | 2026-07-24 / ۲ مرداد ۱۴۰۵ / Day 2 |
| Status | Accepted |
| Decision Owner(s) | پارمیدا و علی؛ یاسمن برای Annotation مستقل |

### Title

تحویل زودهنگام نمونه Labeled برای حذف گلوگاه پارمیدا → علی

### Context and Options

تحلیل رابطه Sentiment با متغیرهای مالی به خروجی LLM وابسته است. انتظار برای Label کل دیتاست، علی را در روز ۳ متوقف می‌کند. گزینه انتخابی، تحویل زودهنگام نمونه ۵۰ تا ۱۰۰ رکوردی مستقل و قابل‌تعویض با خروجی کامل است.

### Decision and Rationale

> پارمیدا تا پایان روز ۲ یک نمونه کوچک Sentiment/Stance-labeled آماده می‌کند. یاسمن همان نمونه را مستقل لیبل می‌زند و بدون مشاهده لیبل پارمیدا برای Agreement استفاده می‌شود. علی Framework آماری را با این نمونه تست می‌کند و پس از آماده‌شدن داده کامل فقط Dataset را Swap می‌کند.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| آماده‌سازی Sample و راهنمای Label | پارمیدا | 2026-07-24 |
| Annotation مستقل و ثبت Confidence/Notes | یاسمن | 2026-07-24 تا 2026-07-25 |
| ساخت Framework آماری مستقل از حجم نهایی | علی | 2026-07-25 |

---

## Decision D-018

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-018 |
| Date | 2026-07-26 / ۴ مرداد ۱۴۰۵ / Day 4 |
| Status | Accepted — Analysis Pivot Rule |
| Decision Owner(s) | علی؛ اطلاع‌رسانی به کل تیم |

### Title

Pivot همان‌روز در صورت کم‌اثر بودن متغیرهای مالی

### Context and Options

ممکن است همبستگی یا رابطه وقفه‌دار معناداری میان Sentiment و نفت/طلا/ارز/بورس دیده نشود. نگه‌داشتن اجباری روایت مالی نتیجه را غیرقابل دفاع می‌کند؛ اعلام دیرهنگام نیز فرصت تحلیل عوامل جایگزین را از بین می‌برد.

### Decision and Rationale

> علی باید در Day 4 نتیجه اولیه تحلیل مالی را اعلام کند. اگر اثر پررنگ یا پایدار نبود، تیم همان روز تمرکز توضیحی را به رویدادهای سیاسی، نظامی، رسانه‌ای، حجم پوشش و Composition Shift منتقل می‌کند. نبود رابطه مالی خودش یک یافته معتبر است و نباید پنهان شود.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| تحلیل همبستگی، Lag و Granger با کنترل محدودیت علیت | علی | 2026-07-26 |
| آماده‌سازی Event/Media alternatives | علی و یاسمن | 2026-07-26 تا 2026-08-07 |
| تطبیق Visualها و Narrative داشبورد با عامل منتخب | ریحانه | حداکثر 2026-08-14 |

---

## Decision D-019

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-019 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted |
| Decision Owner(s) | یاسمن (Documentation QA) و ریحانه (Report/Dashboard)؛ همه اعضا Contributor هستند |

### Title

مستندسازی از روز اول و کنترل نهایی مستقل از تولیدکننده هر بخش

### Context and Options

قرار دادن مستندسازی در روز آخر باعث ناهماهنگی روایت، فراموش‌شدن پارامترهای استخراج و لینک‌های شکسته می‌شود. بنابراین مستندات هم‌زمان با کار فنی ساخته و هر بخش توسط فردی غیر از تولیدکننده نهایی کنترل می‌شود.

### Decision and Rationale

> یاسمن از Day 1 اسکلت `docs/` و چک‌لیست تحویل را نگه می‌دارد؛ در Day 3 شکاف‌ها را گزارش می‌کند؛ از Day 4 متن اعضا را یکدست می‌سازد و در Day 5 و فاز صیقل‌کاری کنترل نهایی کد، گزارش، منابع، داشبورد و ویدیو را انجام می‌دهد. ریحانه مالک روایت داشبورد، گزارش و دمو است.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| تحویل Access/Extraction Notes | حسین و پارمیدا | 2026-08-07 |
| تحویل Method/Statistics Notes | علی | 2026-08-07 |
| یکپارچه‌سازی گزارش و داشبورد | ریحانه | 2026-08-14 |
| کنترل بسته کامل با چک‌لیست الزام‌ها | یاسمن | 2026-08-14 |

---

## Decision D-020

### General Information

| Field | Value |
| --- | --- |
| Decision ID | D-020 |
| Date | 2026-07-23 / ۱ مرداد ۱۴۰۵ / Day 1 |
| Status | Accepted — Operational Cadence |
| Decision Owner(s) | حسین برای هماهنگی فنی؛ همه اعضا برای گزارش روزانه |

### Title

Standup روزانه و تثبیت فاز صیقل‌کاری روزهای ۱۷ تا ۲۳

### Context and Options

وابستگی میان استخراج، LLM، تحلیل آماری و داشبورد می‌تواند گلوگاه‌ها را پنهان کند. همچنین فاصله Day 5 تا ارائه باید به تکمیل و رفع نقص اختصاص یابد، نه افزودن بی‌قاعده Scope جدید.

### Decision and Rationale

> هر روز یک Standup ده تا پانزده دقیقه‌ای با سه سؤال «دیروز چه کردم؟ امروز چه می‌کنم؟ کجا گیر کردم؟» برگزار می‌شود. روزهای ۶ تا ۱۶ برای تکمیل Pipeline و خروجی قابل استفاده‌اند؛ روزهای ۱۷ تا ۲۳ فقط برای صیقل‌کاری، رفع باگ، تکمیل موارد ضروری، QA و تمرین ارائه استفاده می‌شوند. Day 24 روز ارائه است.

### Action Items

| Task | Responsible | Due Date |
| --- | --- | --- |
| اجرای Standup و ثبت Blockerهای بین‌نفره | همه؛ هماهنگی حسین | روزانه تا 2026-08-14 |
| Freeze تصمیم‌های تحلیلی اصلی | حسین، علی، پارمیدا و ریحانه | 2026-08-07 / ۱۶ مرداد |
| رفع باگ، QA، تکمیل موارد ضروری و تمرین ارائه | همه با کنترل یاسمن | 2026-08-08 تا 2026-08-14 |
| ارائه و تحویل نهایی | همه؛ دمو توسط ریحانه | 2026-08-15 / ۲۴ مرداد |

---

# بخش دوم: لاگ وقایع، تغییرات مهندسی و تصمیم‌های فنی (Engineering & Technical Changelog)

تصمیم‌های کلیدی پیاده‌سازی فنی، رفع باگ‌ها، و جریان داده پایپ‌لاین به ترتیب تاریخ:

| تاریخ | عنوان و شرح تصمیم فنی | دلیل و زمینه تصمیم |
|---|---|---|
| 2026-08-14 | **خرابی content_id (Excel Scientific Notation) در هر دو فایل Gold Sample رفع شد (`src/annotation/fix_gold_sample_content_id_corruption.py`).** ۱۰۰ رکورد X در فایل اصلی و ۴۷ رکورد X در `agreement_subset` تصحیح شدند — با تطبیق بر اساس `sample_id` (نه حدس) از دو منبع تمیز: بک‌آپ پیش‌از-جایگزینی (۲۳۸ رکورد قدیمی) و `gold_sample_replacement_delta_2026-08-14.csv` (۶۲ رکورد جدید). **نتیجه‌ی جانبی مهم:** مشکل «۴۷ رکورد Orphan در agreement_subset» که قبلاً به‌عنوان یک مسئله‌ی جداگانه ثبت شده بود، کاملاً حل شد — چون واقعاً همون خرابی مشترک بود، نه یک مشکل هویتی مستقل؛ الان هر ۱۲۰ رکورد `agreement_subset` دقیقاً با فایل اصلی مطابقت دارند (قبلاً ۷۳/۱۲۰). صفر ID تکراری باقی مانده. | تیم می‌خواست همه‌چیز را به `main` merge کند؛ داده‌ی خراب با ID تکراری/اشتباه نباید وارد شاخه‌ی اصلی شود. |
| 2026-08-14 | **روشن شد که سند اصلی Assignment («۰۱ تا ۰۷» را الزام نکرده) — `notebooks/07_sensitivity_and_final_claims.ipynb` ساخته و با موفقیت (بدون خطا) اجرا شد.** بررسی مستقیم متن سند اصلی (بخش ۴۱ مورد ۴ و بخش ۴۷ Submission Checklist) نشون داد فقط «Notebook نهایی» (مفرد) خواسته شده، نه دقیقاً ۷ فایل با نام‌گذاری خاص — اون ساختار «۰۱-۰۷» فقط پیشنهاد سازمان‌دهی خودِ `docs/checklist.md` بوده («ترتیب Notebookهای پیشنهادی»)، نه الزام Rubric. بر این اساس، تصمیم گرفته شد **Notebookهای ۰۱-۰۴ (که معادل تبدیل اسکریپت‌های از‌قبل‌کامل Pipeline A هستن) ساخته نشن** — کار غیرضروری بود؛ به‌جاش فقط ۰۷ (که واقعاً تحلیل جدید Pipeline B رو روایت می‌کنه: مقایسه‌ی گروه‌ها §24، حساسیت، Claim Registry) ساخته شد، و بعدش یک Notebook جمع‌بندی/Master (در صورت نیاز) به‌جای بازنویسی Pipeline A. | جلوگیری از صرف وقت روی کاری که نه Rubric خواسته نه ارزش تحلیلی جدیدی اضافه می‌کنه — فقط بازنویسی کد از‌قبل‌کارکرده به فرمت Notebook بود. |
| 2026-08-14 | **`src/temporal_analysis/sensitivity_analysis.py` ساخته شد (فاز پانزدهم چک‌لیست، حداقل ۶ مقایسه) — تا امروز هیچ تحویل‌شدنی مستقلی برای این فاز نبود.** ۶ مقایسه مستقیم محاسبه شد (با/بدون Duplicate، Content-level در برابر Author-balanced، با/بدون بزرگ‌ترین Source، با/بدون بزرگ‌ترین Parent، Confidence بالا در برابر همه، Unweighted در برابر Engagement-weighted با log1p+Cap فقط برای youtube) روی معیار مشترک «سهم Sentiment مثبت»؛ ۳ مقایسه‌ی دیگر (Spearman/Pearson، Event window، Platform جدا/Pooled) چون از قبل به‌عنوان محصول جانبی اسکریپت‌های دیگه تولید می‌شن، دوباره محاسبه نشدن — فقط یک فایل رفرنس (`sensitivity_analysis_reference_index.md`) بهشون اشاره می‌کنه. **کشف شد:** `source_container` و `post_id` برای X مقدار عملاً ثابت/بی‌معنی دارن (X مفهوم Channel/Parent واقعی نداره، فقط Query-based Search) — به‌جای گزارش عدد خالی/گمراه‌کننده، `not_meaningful` صریح ثبت شد. خروجی: `outputs/tables/sensitivity_analysis_results.csv` (۱۶ ردیف). | چک‌لیست حداقل شش مقایسه رو الزام کرده بود؛ تا امروز این‌ها پراکنده و بدون یک محل واحد بودن. |
| 2026-08-14 | **`src/temporal_analysis/group_comparison.py` ساخته شد (فاز دوازدهم/§۲۴ چک‌لیست).** هر ۴ آزمون جدول §۲۴ پیاده شد: Chi-square+Cramér's V (Stance×Platform، Stance×Language)، Fisher's Exact+Odds Ratio (support/oppose، هر جفت پلتفرم، CI دقیق از `statsmodels.Table2x2`)، Mann-Whitney U+rank-biserial (Engagement)، Welch's t-test+Hedges' g (طول متن، هر جفت پلتفرم؛ CI تحلیلی Hedges & Olkin ۱۹۸۵، بدون Bootstrap). برای CIهایی که فرم بسته ندارن (Cramér's V، rank-biserial) از Bootstrap (۱۰۰۰ تکرار) استفاده شد. **کشف شد:** `engagement_score` توی `annotated_dataset.parquet` برای X و Reddit کاملاً خالیه (فقط YouTube پرشده) — هیچ Collectoری این فیلد رو براشون پر نمی‌کنه. به‌جای گزارش NaN بی‌توضیح، برای هر ۳ جفت پلتفرم یک ردیف `not_applicable` صریح با دلیل نوشته می‌شه؛ به‌جاش یک مقایسه‌ی معنادار و واقعاً محاسبه‌پذیر جایگزین شد: Engagement بین کامنت‌های مثبت/منفی **داخل خودِ یوتیوب** (تنها پلتفرمی که این داده رو داره). خروجی: `outputs/tables/group_comparison_results.csv` (۱۲ ردیف، هر ۱۲ تا گزارش شدن نه فقط p<0.05). | چک‌لیست صریحاً می‌گه «فقط p<0.05 گزارش نمی‌شود» و هر آزمون باید n/Estimate/CI/Effect-size/فرض‌ها/محدودیت‌وابستگی داشته باشه — یک جدول NaN بی‌توضیح برای Engagement بدتر از گزارش صادقانه‌ی «این مقایسه با داده‌ی فعلی ممکن نیست» بود. |
| 2026-08-14 | **آیتم ۱۷ چک‌لیست — ۶۲ رکورد نامعتبر Gold Sample با رکورد واقعی جایگزین شدند (`src/annotation/replace_invalid_gold_sample_rows.py`، اجرای هدفمند، نه Resample کامل — تصمیم صریح کاربر).** از ۳۰۰ رکورد Gold Sample فعلی (که دو Annotator واقعاً دستی لیبل زده بودن و Kappa رویش حساب شده بود)، ۴۹ تا اصلاً در `eligibility_audit.parquet` واقعی پیدا نشدن و ۱۳ تا `dataset_target ∈ {quarantine, audit_only}` بودن. این ۶۲ تا، هم‌سلول (همان Platform×Language) و با Seed=۱۴۰۵، از استخر eligible واقعی (`opinion_main`/`opinion_limited`/`opinion_untimed`) جایگزین شدند؛ ۲ مورد (هر دو `reddit`/`fa`، استخر آن سلول کاملاً خالی بود) با Fallback هم‌پلتفرم/زبان دیگر (`reddit`/`en`) پر شدند، با WARNING صریح در خروجی. ۲۳۸ رکورد سالم و لیبل‌های دستی موجودشان کاملاً دست‌نخورده ماندند (Verify شد: صفر اختلاف در ستون‌های لیبل). نسخه‌ی پیش از تغییر در `data/annotated/_backup_before_content_id_fix_2026-08-13/*_pre_62_replacement_2026-08-14.csv` نگه داشته شد. همان نگاشت روی `sample_sentiment_labels_agreement_subset.csv` هم اعمال شد (۲۲ ردیف از ۱۲۰ تا). خروجی جانبی `data/annotated/gold_sample_replacement_delta_2026-08-14.csv` (۶۲ ردیف، لیبل خالی) برای لیبل‌زنی دستی توسط تیم آماده است. **مشکل جداگانه و پیش‌موجود که این تغییر عمداً حل نکرد:** ۴۷ از ۱۲۰ `content_id` در `agreement_subset` اصلاً در فایل اصلی ۳۰۰تایی پیدا نمی‌شن (احتمالاً از قبل از رفع باگ scientific-notation در ۲۰۲۶-۰۸-۱۳ باقی مونده) — نیاز به تصمیم جداگانه‌ی تیم دارد. | حفظ کار دستی دو Annotator (که واقعی و پرهزینه بود) در حالی که Gold Sample را با eligibility واقعی هم‌راستا می‌کند؛ Resample کامل این کار را دور می‌ریخت. |
| 2026-08-14 | **آیتم ۱۵ چک‌لیست (Spam/Automation Risk) — کشف شد که هم X و هم Reddit در داده‌ی واقعی، نه فقط X، `automation_risk_score=None` داشتن.** بررسی نشون داد داده‌ی واقعی هر دو پلتفرم از `handoff_csv_to_record.py` عبور کرده (نه از `x_to_record.py`/`reddit_to_record.py`'s own `main()` که `automation_risk.score_batch()` رو صدا می‌زنن) — پس هیچ‌کدوم واقعاً اجرا نشده بودن روی داده‌ی نهایی. یک تابع جدید `compute_automation_risk_scores_for_raw_schema_rows()` به `handoff_csv_to_record.py` اضافه شد: Batch بر اساس `source_parent_id` وقتی پر است (Reddit: به‌ازای هر Submission، هم‌معنی با batching یوتیوب/`reddit_to_record.py` خودش)، وگرنه یک Batch سراسری (X: چون هیچ توییتی Parent ندارد). `x_to_record.py`'s `build_record()` هم برای پذیرفتن `risk_scores` گسترش یافت. با اجرای دوباره روی هر دو فایل Handoff اصلی (نه --limit)، هر ۱۶,۴۷۵ رکورد X و ۱۵۸,۹۵۹ رکورد Reddit حالا `automation_risk_score` واقعی دارند (X: ۶ رکورد ≥۰.۷؛ Reddit: صفر). **مهم:** این فقط لایه‌ی خام (`data/raw/{platform}/*_comments_v1.jsonl`, فرمت v03) را پوشش می‌دهد — `automation_risk_score` عضو `RAW_SCHEMA_V05_COLUMNS` نیست (طبق طراحی v05 §11، «فیلد Derived، در Preprocessing ساخته می‌شود»)، پس به `data/raw_harmonized/`/`data/interim/`/`annotated_dataset.parquet` نمی‌رسد؛ گسترش Schema v05 برای این، هماهنگی با مالک `config/schema.py` می‌خواهد، در این تغییر انجام نشد. | خروجی `data/raw_harmonized/{x,reddit}/*.parquet` که از این فایل‌های JSONL بازسازی می‌شوند (`backfill_raw_harmonized_v05.py`) دست‌نخورده ماندند چون این ستون اصلاً به آن لایه نمی‌رود — نیازی به Backfill مجدد eligibility/interim نبود. |
| 2026-08-14 | `src/temporal_analysis/composition_shift.py` روی داده‌ی واقعی با `UnicodeEncodeError` کرش می‌کرد (فقط ۱ از ۱۰ جدول نوشته شد، بعد کرش) — برخلاف بقیه‌ی اسکریپت‌های پروژه، این فایل `sys.stdout.reconfigure(encoding="utf-8")` نداشت، پس پرینت کاراکتر `→` روی Console پیش‌فرض ویندوز (cp1252) خطا می‌داد. رفع شد (همون الگوی بقیه‌ی اسکریپت‌ها). بعد از رفع، هر ۱۰ جدول + هر ۶ جدول `event_study.py` روی `data/processed/annotated_dataset.parquet` واقعی بازسازی شدن. **باز مونده (کم‌اهمیت):** همین الگو (نبود `reconfigure`) در `build_financial_outputs.py`, `build_social_weekly_outcomes.py`, `event_registry.py` هم دیده شد ولی چون تا امروز خطای واقعی نداده بودن (کاراکتر مشکل‌ساز پرینت نشده)، دست‌نخورده موندن — اگه بعداً کرش مشابه دیدید، همین fix رو بزنید. | تیم Power BI منتظر این ۱۶ جدول (Composition Shift + Event Study) هم بود؛ اگه فقط با پیام خطا رها می‌شد، همه‌ی جدول‌ها همچنان Synthetic می‌موندن. |
| 2026-08-14 | **`data/processed/annotated_dataset.parquet` (پل رسمی Pipeline A→B که `docs/pipeline_b_input_contract.md` نامش را برده بود، اما تا امروز هیچ اسکریپتی برایش نبود) ساخته شد — `src/annotation/build_annotated_dataset.py`.** خروجی `apply_eligibility.py` (۲۳۳,۰۰۶ رکورد eligible) با خروجی `run_full_annotation.py` (`outputs/full_annotation/shard_0of1.jsonl`) روی `content_id` Left-join شد. **دو انحراف آگاهانه از قرارداد که نیاز به تایید تیم Pipeline B دارد:** (۱) `content_id` در خروجی یکتا نیست — چون Full Annotation تا ۳ Target (T01-T03) را جدا Stance می‌زند، هر رکورد تا ۳ ردیف (یکی به‌ازای هر Target) دارد؛ فشرده‌کردن به یک ردیف باعث از‌دست‌رفتن ۲ از ۳ قضاوت Stance واقعی می‌شد که `event_study.py`/چک‌لیست §۲۵ برای هر Target جدا لازم دارند. (۲) `automation_risk_score_user`/`is_flagged_bot_suspect` همیشه null است — این دو فقط در `data/interim/clean.jsonl` (فضای شناسه‌ی متفاوت: `author_channel_id` خام، نه `author_hash` هش‌شده‌ی این فایل) موجودند و join امن بین این دو فضای شناسه هنوز انجام نشده. **وضعیت فعلی جزئاً واقعی است، نه کامل:** از ۲۳۳,۰۰۶ رکورد eligible، فقط ۸,۵۹۸ تا (۳.۷٪) واقعاً annotate شده‌اند (`annotation_status=ok`)؛ ۹۲.۷٪ هنوز `pending_annotation`‌اند چون Full Annotation وسط اجرا متوقف شد (سهمیه‌ی روزانه‌ی Groq تمام و حساب OpenRouter $۰ اعتبار — همزمان کشف و مستند شد). بعد از رفع این مسدودکننده‌ها، همین اسکریپت باید دوباره اجرا شود تا فایل با پوشش کامل‌تر جایگزین شود. | تیم Pipeline B/Power BI منتظر این فایل بودند تا کار Dashboard را از داده‌ی Synthetic به داده‌ی واقعی سوییچ کنند؛ زیر فشار زمانی، نسخه‌ی جزئی‌واقعی (با Coverage صادقانه‌ی خودش، نه پنهان‌شده) بهتر از معطلی کامل تا اتمام صددرصدی Annotation بود — دقیقاً مطابق اصل §۴۵ سند («مخفی‌کردن Data Gap» ممنوع). |
| 2026-08-14 | **باگ pandas 3.0 در `run_full_annotation.py`'s `stratified_subsample()` رفع شد.** `timed.groupby([...]).apply(lambda g: g.sample(...))` روی pandas 3.0.3 (نصب‌شده روی این سیستم) ستون‌های Grouping (`platform`, `project_week`) را از `g` داخل Lambda حذف می‌کند (نسخه‌ی نهایی‌شده‌ی چیزی که pandas از ۲.۲ به بعد با اخطار "operated on the grouping columns" هشدار می‌داد) — یعنی هر ردیفی که از این تابع خارج می‌شد `platform=NaN`/`project_week=NaN` داشت، بدون هیچ خطا یا هشداری. با یک اجرای واقعی کشف شد (~۱۷ هزار ردیف نوشته‌شده با platform=NaN قبل از توقف). رفع شد با جایگزینی `.groupby().apply()` با پیمایش صریح `for key, group in timed.groupby([...])` (که ستون‌های Grouping را در `group` نگه می‌دارد) + `pd.concat` دستی. تست شد: `platform`/`project_week` دیگر null نیستند، توزیع پلتفرمی منطقی (x=2526, reddit=2520, youtube=2401 از مجموع ۷۴۴۷). | یک باگ واقعی و ساکت (بدون Exception) که داده‌ی annotation را برای همیشه بی‌فایده می‌کرد (بدون platform/week قابل‌استفاده در هیچ تحلیل Pipeline B نیست) — باید قبل از ادامه‌ی Full Annotation واقعی رفع می‌شد، نه بعدش. |
| 2026-08-14 | **`src/temporal_analysis/composition_shift.py` ساخته شد (فاز یازدهم/§۲۳ چک‌لیست).** از چهار روش پیشنهادی checklist برای مقایسه‌ی Adjusted Trend (Stratified / Author-balanced / Parent-balanced / Shared-period)، **Author-balanced trend** انتخاب شد: برای هر (author_hash × platform × project_week) ابتدا میانگین positive گرفته می‌شود (هر کاربر یک رأی)، سپس میانگین کاربران به‌عنوان balanced_positive_rate گزارش می‌شود. Wilson CI هم روی این نرخ حساب می‌شه (با n_authors به‌عنوان مخرج). دلیل رد Stratified: همان کاری است که weekly_trend.py قبلاً کرده، بُعد جدیدی نمی‌افزاید. دلیل رد Parent-balanced: parent_id در داده‌ی synthetic اغلب null است و coverage پایین‌تری دارد. دلیل رد Shared-period: پروژه یک stream پیوسته است، نه دو cohort مستقل. Author-balanced مستقیماً bias کاربران پرتکرار را می‌سنجد که از ستون top_author_share در composition_shift_author_concentration.csv کمّی قابل رصد است و در pipeline_b_input_contract.md صراحتاً برای همین هدف ذکر شده. ده جدول خروجی در outputs/tables/composition_shift_*.csv تولید می‌شود. روی fixture مصنوعی تست شد: بدون خطا اجرا شد، جمع سهم‌ها ~۱، data-gap فقط reddit/W05، is_partial_week فقط W21. | composition_shift.py باید مشخص کند تغییر روند سنتیمنت ناشی از تغییر نگرش واقعی است یا تغییر ترکیب داده — بدون این تفکیک، هر نتیجه‌گیری از روند زمانی احتمال confounding بالایی دارد. |
| 2026-08-14 | `ollama_llama3_local` به `MODEL_ROUTES` اضافه شد (`model_routes.py`) — یک Route کاملاً افزایشی، `LOCKED_ROUTE_NAME` دست‌نخورده موند (`groq_cheap_fast`). Ollama's `/v1/chat/completions` سازگار با فرمت OpenAI‌ه (تست شد: `choices[0].message.content` + `usage.prompt_tokens/completion_tokens` درست می‌آد)، پس به‌جای نوشتن Caller جدید، `_call_openai_compatible()` موجود (که برای OpenRouter/DeepSeek استفاده می‌شد) عیناً reuse شد — فقط یک شاخه‌ی provider="ollama" در `_call_provider()` اضافه شد. `OLLAMA_BASE_URL` (پیش‌فرض `http://localhost:11434`) به دیکشنری `api_keys` هر ۳ اسکریپت (`run_model_comparison.py`, `evaluate_sentiment_accuracy.py`, `run_full_annotation.py`) اضافه شد. تست سرعت روی سیستم کاربر (Ollama، مدل `llama3:latest`، ۸B): تک‌تماس=۱۶.۶ ثانیه، ولی با ۴ Worker موازی=۶.۶ ثانیه کل (۴ تماس) و با ۸ Worker=۰.۷۲ رکورد/ثانیه — یعنی سخت‌افزار محلی همزمانی رو تحمل می‌کنه. تست annotate() واقعی (بدون Cache) موفق و ساختاریافته بود. **هنوز روی Gold Sample ارزیابی نشده و قفل نشده** — فقط در دسترسه، استفاده‌ی جدی منوط به ارزیابی. | Plan B موازی با Plan A (کلیدهای بیشتر Groq): اگه سهمیه‌ی Groq دوباره تموم بشه، یک مسیر رایگان/بدون Rate Limit از قبل آماده و تست‌شده باشه، بدون این‌که چیزی از تنظیمات فعلی (مدل قفل‌شده، اجرای در حال انجام) دست بخوره. |
| 2026-08-14 | **حجم Full Annotation کاهش یافت (اجباری، به‌دلیل سرعت):** بعد از سوییچ به `groq_cheap_fast`، محاسبه شد که حتی با هر ۴ کلید Groq (سقف ترکیبی ~۲۴,۰۰۰ TPM) و پخش بار بین‌شون، annotate کردن کل ۲۳۳,۰۰۶ رکورد Eligible ~۱۳۳ ساعت (۵.۵ روز) طول می‌کشه — غیرقابل‌قبول. به‌جای برش اول-N (که می‌تونست هفته/پلتفرم‌های کامل رو خالی کنه)، `run_full_annotation.py`'s `stratified_subsample()` اضافه شد: سقف ۱۲۰ رکورد به‌ازای هر سلول (پلتفرم × project_week)، Seed=۱۴۰۵. نتیجه: ۷,۴۴۷ رکورد (از ۶۴ سلول غیرخالی، ۶۰ تاش کامل به سقف ۱۲۰ رسیدن، ۴ تا کمتر از ۱۲۰ داشتن و کامل نگه داشته شدن)، تخمین زمان ~۴.۲ ساعت. چون هر دو عضو تیم از همون ۴ کلید مشترک استفاده می‌کنن، Sharding سرعت رو زیاد نمی‌کنه (سقف مشترکه) — پس با `--num-shards 1` توسط یک نفر اجرا می‌شه؛ نفر دوم به‌جاش روی بخش‌های دیگه (Composition Shift، مقایسه‌ی گروه‌ها، حساسیت) کار می‌کنه. | این محدودیت واقعی زیرساخته (TPM حساب‌های رایگان Groq)، نه یک انتخاب کیفیتی. Stratified (نه Truncated) بودن نمونه تضمین می‌کنه هر هفته/پلتفرمی که داده‌ی کافی داشته حداقل n=۱۲۰ (فراتر از آستانه‌ی n≥۳۰ چک‌لیست §۲۲) براش annotate بشه، تا تحلیل روند زمانی/مقایسه‌ی پلتفرم هنوز روی داده‌ی واقعی معنادار بمونه. |
| 2026-08-14 | **مدل قفل‌شده موقتاً عوض شد:** `LOCKED_ROUTE_NAME` از `openrouter_gemini_flash_lite` به `groq_cheap_fast` تغییر کرد، وسط اجرای واقعی Full Annotation (`shard_0of2`، حدود ۷۰۰۰ ردیف پردازش‌شده، ۸۴٪ Fail). علت: حساب OpenRouter پشت این route موجودی واقعی نداشت (`HTTP 402: Insufficient credits. This account never purchased credits`) — ربطی به سقف $۱۰۰ ما نداشت، فقط $۰.۱۲ خرج شده بود. کاربر پیشنهاد داد ۵ کلید OpenRouter «حساب جدید بدون شارژ» رو چک کنیم؛ هر ۵ تا از طریق `/api/v1/credits` تست شدن و هرکدوم دقیقاً $۰ موجودی داشتن (نه فقط غیرمجاز طبق §۳/§۲۱ سند چون حساب تازه‌ساز بدون شارژ بودن، بلکه عملاً هم بی‌فایده بودن). به‌جای صبر برای شارژ واقعی، تصمیم گرفته شد موقتاً با `groq_cheap_fast` (۰٪ Fail، تست‌شده کامل روی ۳۰۰ ردیف Gold) ادامه بدیم. رکوردهایی که با annotation_status=api_failure قبلاً ثبت شدن، خودکار توسط منطق Resume دوباره تلاش می‌شن (چون `ok` نیستن). اگه بعداً حساب OpenRouter شارژ واقعی شد، می‌شه دوباره `LOCKED_ROUTE_NAME` رو برگردوند. | این یک انتخاب کیفیت‌محور یا «مقایسه‌ی بی‌پایان مدل» (که §۷ سند ممنوع کرده) نیست — یک Fallback اجباری به‌خاطر مشکل واقعی پرداخت/حساب است، با دلیل مستند و قابل‌رهگیری. |
| 2026-08-14 | `src/event_analysis/{event_registry.py, event_study.py}` ساخته شد (فاز سیزدهم/§۲۵ چک‌لیست). `event_registry.py` عیناً همون ۴ رویداد جدول §۴ سند `docs/event_registry_v3.md` رو (که قبل از این کد ثبت شده بودن) کپی می‌کنه — چیزی انتخاب/اختراع نشده. `event_study.py` برای هر رویداد `primary_confirmatory` (EV-016/EV-025/EV-031): سهم Stance قبل/بعد (به تفکیک پلتفرم) با CI اختلاف نسبت، بازه‌ی حساسیت (Window باریک‌تر)، حساسیت با/بدون بزرگ‌ترین Source و Near-duplicate، یک Placebo (تاریخ ساختگی، صریحاً برچسب `PLACEBO-` و توضیح «رویداد واقعی نیست»)، و جدول Composition/Volume هم‌زمان. EV-001 (`study_anchor`، بدون Window قابل‌مقایسه چون خودِ آغاز جنگه) فقط توصیفی گزارش می‌شه. مثل بقیه‌ی Pipeline B، فعلاً روی fixture مصنوعی تست شده. تست شد: بدون خطا اجرا شد، ۶ جدول تولید کرد. | نتیجه همه‌جا «همراهی زمانی» نامیده می‌شه، نه اثر علّی (§۲۹). |
| 2026-08-14 | `run_full_annotation.py` پیاده‌سازی شد (قبلاً Skeleton بود). طراحی: (۱) Concurrency واقعی با `ThreadPoolExecutor` (`--workers`) چون `annotate()` یه تماس Blocking‌ه، نه async. (۲) قابلیت Shard-کردن (`--shard-id`/`--num-shards`، هش قطعی `zlib.crc32(content_id)`) تا چند همکار هم‌زمان روی تیکه‌های جدا اجرا کنن — بدون هماهنگی اضافه، فقط توافق روی عدد `--num-shards`. (۳) Resume خودکار: هر Shard خروجی JSONL خودشو داره، هر اجرای جدید جفت‌های `(content_id, target_id)` قبلاً انجام‌شده رو می‌خونه و رد می‌کنه. (۴) `AnnotationCache`/usage-log توی `llm_client.py` Thread-safe شدن (Lock روی save/append) چون قبلاً فقط برای اجرای تک‌رشته‌ای طراحی شده بودن. (۵) `--targets` (پیش‌فرض فقط T01) به‌جای قفل‌کردن تعداد Target در کد. تست شد: ۴۰ ردیف واقعی annotate شد (۲۰ + ۲۰ Resume، بدون تکراری)، Sharding روی ۵ تیکه تقریباً مساوی و بدون همپوشانی تقسیم کرد. | با latency واقعی (میانه ۴.۲ ثانیه/تماس)، Sequential روی ۲۳۳K رکورد ~۲۷۲ ساعت می‌شد — غیرقابل‌اجرا. با ۵ نفر هم‌زمان (هرکدوم Shard خودشون، هرکدوم ~۳۰ Worker) تخمین به ~۱.۵-۲ ساعت می‌رسه. |
| 2026-08-14 | **سقف هزینه‌ی Full Annotation تایید شد:** `src/annotation/run_full_annotation.py`'s `APPROVED_COST_CAP_USD = 100.0`. مبنا: بعد از رفع دو باگ Harmonization (یوتیوب/Reddit، ردیف‌های بالاتر همین جدول)، `apply_eligibility.py` واقعی روی داده‌ی کامل اجرا شد — ۲۳۳,۰۰۶ رکورد Eligible (`opinion_main`=163192 + `opinion_limited`=69808 + `opinion_untimed`=6). با هزینه‌ی مدل قفل‌شده (`openrouter_gemini_flash_lite`، $۰.۱۰۶۷/۱۰۰۰ از Pilot ۳۰۰ رکوردی): حالت ۱ Target = $۲۴.۹، حالت ۳ Target اصلی (T01+T02+T03) = $۷۴.۶. سقف $۱۰۰ برای پوشش هر دو حالت + حاشیه‌ی اطمینان تعیین شد. زمان تخمینی: با latency واقعی (میانه ۴.۲ ثانیه/تماس، تایید‌شده از ۳۰۰ نمونه‌ی واقعی، نه فرضی)، حالت ۱ Target با Concurrency تیمی (چند نفر، هرکدوم چند Worker موازی) به‌جای Sequential اجرا می‌شود (`run_full_annotation.py`'s `--shard-id/--num-shards/--workers`). | طبق `docs/pre_analysis_decision_table_v1.md` ردیف «سقف هزینه و زمان اجرا»: باید قبل از Full run، عدد صریح از روی Pilot در Decision Log ثبت بشه. تعداد Target (۱ یا ۳) به‌جای قفل‌شدن، به یک آرگومان اجرای‌زمان (`--targets`) تبدیل شد تا تیم بتونه با ۱ Target شروع کنه و بر اساس توان واقعی زمانی تصمیم بگیره گسترشش بده یا نه — بدون نیاز به تغییر کد. |
| 2026-08-14 | `src/ingestion/backfill_raw_harmonized_v05.py` باگ پیدا شد و رفع شد: `_YOUTUBE_JSONL` فقط به `youtube_comments_v2.jsonl` (~۸۲,۵۵۰ رکورد) اشاره می‌کرد، نه به `data/raw/{topic_id}/youtube_comments_*.jsonl` (همون glob که `join_and_clean.py` از قبل استفاده می‌کنه) — یعنی `youtube_comments_1404-12-09_to_ongoing.jsonl` (۷۴,۹۲۴ رکورد واقعی، تقریباً نیم کل داده‌ی یوتیوب) هیچ‌وقت harmonize نشده بود، بدون هیچ خطا یا هشدار. `_PLATFORM_JSONL` به `dict[str, list[Path]]` تغییر کرد (Reddit/X هنوز تک‌فایلی‌ان، فقط YouTube چندفایلی) و `run()` حالا روی همه‌ی فایل‌های هر پلتفرم جمع می‌زنه قبل از harmonize. اجرا شد: `input_rows=157474 == harmonized_rows=157474` (معادله‌ی §۱۰ چک‌لیست Pass) — رکوردهای فایل ongoing (که `collection_run_id` نداشتن) رفتن توی `backfill_youtube_orphan.parquet`. فایل‌های قبلی (`yt_20260808...`, `yt_20260811...`) دست‌نخورده موندن (idempotent). | بدون این فیکس، `apply_eligibility.py` (که مستقیم از `data/raw_harmonized/` می‌خونه) بی‌سروصدا ~۷۵ هزار کامنت واقعی یوتیوب رو از کل تحلیل نهایی حذف می‌کرد. کاربر تایید کرد همین الان رفع بشه، نه بعداً. |
| 2026-08-14 | **مدل نهایی برای Full Annotation قفل شد:** `src/annotation/model_routes.py`'s `LOCKED_ROUTE_NAME = "openrouter_gemini_flash_lite"`. مبنا: اجرای کامل `evaluate_sentiment_accuracy.py` روی هر ۳۰۰ ردیف Gold Sample (annotator اول، بعد از تعمیر content_id)، با هر ۳ Provider واقعاً در دسترس (بعد از رفع باگ `max_tokens` و multi-key شدن Groq — هر دو در همین روز، بالاتر در همین جدول): `groq_cheap_fast` (F1 sentiment=0.377, stance=0.349, failure=0%, coverage=100%, cost=$0.043/1000)، `groq_default` (F1 sentiment=0.510, stance=0.386, failure=0%, coverage=98.7%, cost=$0.495/1000)، `openrouter_gemini_flash_lite` (F1 sentiment=**0.609**, stance=**0.502**, failure=**0%**, coverage=**99.3%**, cost=$0.107/1000). Gemini هم‌زمان بالاترین کیفیت (هر دو محور)، پوشش عالی، صفر خطا، و هزینه‌ی میانه (نه ارزون‌ترین، نه گرون‌ترین) رو داره — روی هیچ معیاری توسط `groq_default` (گرون‌تر و ضعیف‌تر) شکست نمی‌خوره. | طبق `docs/pre_analysis_decision_table_v1.md` ردیف «مدل و Provider LLM»: قفل باید بعد از Pilot روی Gold Sample کامل و با معیار Macro-F1+Failure+Cost+Latency باشه، نه انتخاب زودهنگام. این اولین‌باره که هر ۳ route بدون هیچ خطا و روی کل ۳۰۰ ردیف مقایسه شدن (نه نسخه‌ی ناقص/۲تایی قبلی) — تصمیم روی همین عدد نهایی گرفته شد. |
| 2026-08-14 | `src/annotation/llm_client.py`'s `_call_groq` هم multi-key شد — دقیقاً همون الگوی `src/ingestion/geo_tagger.py` (۲۰۲۶-۰۸-۱۲): `GROQ_API_KEYS` (comma-separated، از قبل با ۴ کلید واقعی همکاران توی `.env` موجود بود) پول می‌شه؛ وقتی یه کلید به سقف روزانه‌ش (TPD) می‌رسه، فقط همون کلید Skip می‌شه و به کلید بعدی می‌ره (`_is_daily_quota_message` همون heuristic geo_tagger.py رو داره: `"per day"`/`"rpd"`/`"tpd"` توی پیام خطا). فقط وقتی **همه‌ی** کلیدها تموم بشن خطا برمی‌گرده. تست شد: ۳ تماس روی `groq_default` که قبلاً با کلید اول ۴۲۹ (`Used 99901/100000 TPD`) می‌گرفت، بعد از این تغییر هر ۳ تا موفق شدن (رفت سراغ کلید بعدی). تایید شد با کاربر که این مصداق «چند حساب واقعی همکاران، نه حساب جعلی/تکراری» است — طبق ToS Groq و همون سابقه‌ی تایید‌شده‌ی ۲۰۲۶-۰۸-۱۲، نه «دور زدن Rate Limit» ممنوع‌شده‌ی §۳/§۲۱ سند. | رفع مسدودشدن `groq_default` بدون نیاز به حساب جعلی یا صبر تا بازنشانی روزانه‌ی سهمیه؛ همون منطق multi-key که تیم قبلاً برای `geo_tagger.py` تایید کرده بود، اینجا هم به‌کار رفت به‌جای اختراع یه راه‌حل جدید. |
| 2026-08-14 | `src/annotation/llm_client.py` هیچ‌جا `max_tokens` برای تماس API تنظیم نمی‌کرد — یعنی Provider پیش‌فرض سقف خروجی خودِ مدل رو در نظر می‌گرفت (۶۵,۵۳۵ توکن برای `gemini-2.5-flash-lite`). OpenRouter پیش از هر تماس چک می‌کنه «آیا حساب می‌تونه بدترین حالت (همون سقف) رو بپردازه؟» — با این‌که خروجی واقعی annotation فقط ~۷۰ توکنه، همین چک باعث `HTTP 402: requires more credits` می‌شد (نه کمبود واقعی اعتبار برای annotation). یک ثابت `MAX_OUTPUT_TOKENS=500` اضافه شد و به هر دو تماس (`_call_groq`, `_call_openai_compatible`) پاس داده شد. تست شد: ۳ تماس جدید روی `openrouter_gemini_flash_lite` که قبلاً ۴۰۲ می‌گرفتن، بعد از فیکس همه موفق شدن (`output_tokens=70`). چون فقط جواب‌های موفق Cache می‌شن (نه Failure)، دوباره‌اجراکردن `evaluate_sentiment_accuracy.py` همین ردیف‌های Fail‌شده‌ی قبلی رو خودکار Retry می‌کنه. | راه‌حل واقعی برای مشکل ۴۰۲ که قبلاً باعث Coverage=۵۹.۷٪ برای Gemini شده بود — بدون نیاز به شارژ حساب یا حساب اضافه (که طبق §۳/§۲۱ سند مجاز هم نبود). |
| 2026-08-14 | ۴ Provider واقعاً در دسترس برای `evaluate_sentiment_accuracy.py` تست شدن (نه فقط ۲ تا که اول گمان می‌رفت): `groq_cheap_fast`, `groq_default`, `openrouter_gemini_flash_lite`, `openrouter_deepseek_flash` — هر ۴ کلید API معتبرن (`deepseek_flash_direct` تنها استثناست: `HTTP 402 Insufficient Balance`, واقعاً بلاک‌شده، نه انتخاب زمانی). از این ۴ تا، `openrouter_deepseek_flash` طی اجرای واقعی روی هر ۳۰۰ ردیف annotator اول به‌شدت Rate-Limit خورد (~۴۰٪ کامل شد در بازه‌ی زمانی موجود، خیلی کندتر از ۳ تای دیگه) و اجرا متوقف شد. تلاش دوم برای اضافه‌کردن `groq_default` هم متوقف شد: لاگ نشون داد سهمیه‌ی روزانه‌ی توکن حساب Groq (که با `groq_cheap_fast` مشترکه) عملاً تمومه (`TPD: Used 99901/100000`، مدل `llama-3.3-70b-versatile`) — هر تماس ۴۲۹ می‌گرفت، ادامه بی‌فایده بود. هم‌زمان `openrouter_gemini_flash_lite` هم به سقف اعتبار OpenRouter نزدیک می‌شد (`HTTP 402: requires more credits`). مقایسه‌ی نهایی مدل فقط با ۲ Provider ماند: `groq_cheap_fast` (F1 sentiment=0.377, stance=0.349, failure=0%, coverage=100%) و `openrouter_gemini_flash_lite` (F1 sentiment=0.578, stance=0.573, failure=39.7%, coverage=59.7%) — همون اجرای اولیه‌ی موفق، قبل از برخورد به این سقف‌ها. | با فشار زمانی پروژه، ادامه‌دادن به `openrouter_deepseek_flash`/`groq_default` (که با سهمیه‌ی تمام‌شده عملاً هیچ‌وقت جواب نمی‌داد) توجیه نداشت؛ به‌جای مخفی‌کردنش، همین‌جا صریح ثبت می‌شه که ۴ Provider بررسی شد و ۲ تا به‌دلیل محدودیت واقعی سهمیه/اعتبار حساب (نه کیفیت) از مقایسه‌ی نهایی کنار گذاشته شدن — طبق §۴۵ سند، «مخفی‌کردن Data Gap» جزو خطاهای رایج غیرقابل‌قبوله. |
| 2026-08-14 | **چک‌لیست آیتم‌های ۹ و ۱۰ — Schema Mapping کامل شد و لایه raw_harmonized برای هر سه پلتفرم ساخته شد.** (۱) `docs/schema_mapping_template.csv` با ردیف‌های کامل Reddit (۵۴ ردیف) و X (۵۴ ردیف) تکمیل شد — هر ستون v05 با وضعیت `verified` مقابل کد واقعی Collector بررسی و مستند شد؛ تفاوت‌های کلیدی ثبت‌شده: Reddit's `content_type=submission` → `original_post` در v05، X's `engagement_*`/`language_reported`/`author_is_verified`/`collector_version` در Record نیستند (فقط در CSV خام موجودند). (۲) `record_to_raw_harmonized_row(r: Record) -> dict` و `export_to_raw_harmonized(records, run_id) -> pd.DataFrame` به `reddit_to_record.py` و `x_to_record.py` اضافه شدند — دقیقاً همان الگوی `youtube_extract.py`؛ تفاوت‌های مستند: Reddit نیاز به `run_id` صریح دارد (collection_run_id در JSONL نیست)، X همین الگو را دارد. (۳) `src/ingestion/backfill_raw_harmonized_v05.py` ساخته شد — یک اسکریپت one-off برای هر سه پلتفرم که JSONL-های موجود را می‌خواند، Record بازسازی می‌کند، از `record_to_raw_harmonized_row()` هر پلتفرم رد می‌کند، و Parquet به `data/raw_harmonized/{platform}/` می‌نویسد؛ YouTube بر اساس `collection_run_id` گروه‌بندی می‌شود (یک فایل per run)، Reddit/X یک فایل واحد با ID مصنوعی `backfill_{platform}_v1` می‌گیرند. معادله کنترل بعد از هر پلتفرم چاپ می‌شود: `input_rows == harmonized_rows + parse_quarantine_rows`. | `docs/checklist.md` آیتم‌های ۹ و ۱۰ این را الزام می‌کردند؛ `apply_eligibility.py` مستقیماً از `data/raw_harmonized/{platform}/*.parquet` می‌خواند — بدون این لایه، Eligibility pipeline نمی‌تواند روی داده‌ی واقعی اجرا شود. عمداً `config/schema.py`'s `Record` دست‌نخورده ماند (مسئولیت حسین) و `x_scraper.py`/`config.yaml` هم دست‌نخورده ماندند. |
| 2026-08-13 | مشکل واقعی در Gold Sample پیدا و رفع شد: (۱) `data/annotated/sample_sentiment_labels.csv` (annotator اول، ۳۰۰ ردیف) ۹۵ `content_id` تکراری داشت — علت: Excel شناسه‌های عددی بزرگ X (پلتفرم `x`) رو به نماد علمی گرد کرده بود (مثلاً `2.06E+18`) و دقتشون از دست رفته بود. با بازسازی قطعی نمونه (همون `RANDOM_SEED=1405`، از `data/interim/clean.jsonl` که دست‌نخورده مونده بود) و تطبیق روی ۲۰۰ ردیف سالم (۰ اختلاف) تایید و تعمیر شد؛ یک ردیف تکراری واقعی (`sample_id=101`، یکی annotator_id خالی) هم حذف شد. نسخه‌ی قبل از تعمیر در `data/annotated/_backup_before_content_id_fix_2026-08-13/` نگه داشته شده. (۲) اولین نسخه‌ی `data/annotated/sample_sentiment_labels_agreement_subset.csv` که به‌عنوان annotation مستقل annotator دوم ارائه شد، معلوم شد **کپی دقیق لیبل‌های annotator اول** بوده (حتی `confidence` — یک مقدار عددی subjective — روی هر ۱۲۰ ردیف دقیقاً یکسان بود؛ از نظر آماری برای annotation مستقل غیرممکنه) — Kappa=۱.۰۰۰ روی هر ۴ محور که از این فایل به‌دست اومد **رد شد** چون از کپی بود، نه توافق واقعی. با پیگیری از یاسمن، فایل درست جایگزین شد؛ نرخ توافق خام این‌بار واقعی به‌نظر می‌رسه (نه ۱۰۰٪، `confidence` فقط ۴٪ مواقع دقیقاً یکسان) و Kappa واقعی محاسبه شد: sentiment=۰.۵۱۷ (moderate), stance=۰.۴۷۱ (moderate), emotion=۰.۲۶۲ (fair — پایین، نیاز به Adjudication قبل از اعتماد کامل), content_type=۰.۶۶۲ (substantial). ستون `annotator_id` این فایل مقدار `annotator2_ai_draft` داره — هنوز باید با تیم روشن بشه دقیقاً یعنی «پیش‌نویس AI که یاسمن بازبینی/اصلاح کرده» یا چیز دیگه، تا در گزارش نهایی درست افشا بشه. | حفظ صداقت روش‌شناسی Gold Sample — طبق §۱۹ سند، Kappa فقط وقتی معناداره که واقعاً از annotation مستقل به‌دست اومده باشه؛ گزارش یک عدد جعلی (چه از کپی، چه از دستکاری عمدی) اعتبار کل ادعاهای بعدی پروژه رو زیر سوال می‌برد. |
| 2026-08-13 | `scripts/make_synthetic_annotated_dataset.py` اضافه شد — ۸۰۰ ردیف کاملاً ساختگی طبق schema دقیق `docs/pipeline_b_input_contract.md` تولید می‌کنه (`data/processed/annotated_dataset.sample.parquet` + دو CSV برای اکسل/Power BI: `annotated_dataset.SYNTHETIC_FOR_POWERBI.csv` و `weekly_summary.SYNTHETIC_FOR_POWERBI.csv`، شکل‌گرفته طبق جدول پیشنهادی §۲۶ سند مشاور). هر ردیف صریحاً علامت‌گذاری شده (`is_synthetic=True`, `content_id` با پیشوند `SYN-`, `text_raw` با پیشوند `[SYNTHETIC SAMPLE]` و متن کاملاً عمومی/بی‌معنی، نه شبیه‌سازی یک نظر واقعی درباره‌ی ایران/آمریکا) تا هیچ‌وقت به‌اشتباه به‌عنوان داده‌ی واقعی در گزارش یا Dashboard راه پیدا نکنه. `data/processed/` توی `.gitignore` هست، پس این فایل‌ها با گیت به تیم نمی‌رسن — باید مستقیم (Drive/Telegram/...) دست کسی که Power BI می‌زنه یا روی Pipeline B کار می‌کنه برسه. | همکار مسئول Power BI منتظر annotation واقعی نمی‌تونست بمونه؛ این فایل بهش اجازه می‌ده الان طراحی/Measureها/Relationshipها رو بسازه و بعداً فقط منبع داده رو با فایل واقعی (همون schema) عوض کنه. همون کد قدم ۱ پرامپت Pipeline B (تولید fixture مصنوعی) رو هم پوشش می‌ده. |
| 2026-08-13 | پروژه به دو Pipeline مستقل تقسیم شد: **Pipeline A** (جمع‌آوری→Harmonization→Eligibility→Gold Sample→ارزیابی مدل→Full Annotation) و **Pipeline B** (آمار توصیفی→روند زمانی→Composition Shift→مقایسه‌ی گروه‌ها→رویداد→مالی→حساسیت→گزارش). مرز دقیق و قرارداد ورودی بین‌شون در `docs/pipeline_b_input_contract.md` قفل شد: Pipeline B فقط و فقط از `data/processed/annotated_dataset.parquet` می‌خونه، هیچ‌وقت مستقیم از `data/raw/`/`data/interim/`. تا annotation واقعی آماده بشه، Pipeline B با یه fixture مصنوعی هم‌schema (`data/processed/annotated_dataset.sample.parquet`) توسعه داده می‌شه. | با فشار زمانی ۱۸ساعته و تیم ۵نفره، این مرز اجازه می‌ده کار Pipeline B (که الان `src/temporal_analysis/`, `src/event_analysis/`, `src/reporting/` کاملاً خالی‌ان) موازی با تکمیل annotation شروع بشه، بدون این‌که دو تیم به فایل‌های همدیگه دست بزنن یا منتظر هم بمونن. |
| 2026-08-13 | `build_labeling_sample.py`'s `SAMPLE_SIZE` از ۹۰ به ۳۰۰ رفت و تقسیم زبان از سه‌طرفه‌ی مساوی (۳۰/۳۰/۳۰) به سهمیه‌ی ثابت `LANGUAGE_QUOTAS = {"fa": 135, "en": 135, "ar": 30}` تغییر کرد؛ `AGREEMENT_SUBSET_MIN` از ۱۰ به ۱۲۰ رفت (همون منطق `max(MIN, fraction)` قبلی، فقط با عدد هدف جدید، چون ۲۰٪ از ۳۰۰ = ۶۰ کافی نبود). با `--resample --force` نمونه‌ی قبلی (بدون هیچ annotation ثبت‌شده‌ای) عوض شد: خروجی نهایی ۳۰۰ ردیف (`en=135, fa=135, ar=30`) در `sample_sentiment_labels.csv` و ۱۲۰ ردیف زیرمجموعه (`en=58, fa=52, ar=10`) در `sample_sentiment_labels_agreement_subset.csv`. | `docs/pre_analysis_decision_table_v1.md` و `docs/PROJECT_EXECUTION_ORDER_v1.md` مرحله ۷ صریحاً «انتخاب تصادفی طبقه‌بندی‌شده ۳۰۰ رکورد با Seed ثابت؛ Double annotation برای ۱۲۰ رکورد» رو الزام کرده‌ن — عدد ۹۰/۱۰ قبلی این‌ها رو برآورده نمی‌کرد. تقسیم مساوی سه‌طرفه‌ی زبان هم با `docs/source_registry_v4.md`'s SR-006 و `config.yaml` (که عربی رو صریحاً خارج از دامنه‌ی تحلیل اصلی EN+FA دونسته) در تضاد بود؛ سهمیه‌ی ثابت fa=en=135 و ar=30 اطمینان می‌ده بودجه‌ی annotator بین دو زبان اصلی برابر تقسیم بشه و عربی سهم برابر نگیره، بدون این‌که کاملاً از نمونه حذف بشه. |
| 2026-08-13 | `build_labeling_sample.py`'s `load_records()` به خروجی‌های `apply_eligibility.py` وصل شد: وقتی هر سه فایل `data/interim/{opinion_main,opinion_limited,opinion_untimed}.parquet` موجود باشن (یعنی eligibility pipeline حداقل یک‌بار اجرا شده)، سمپل از همون‌ها کشیده می‌شه (ستون‌های `source_parent_id`→`post_id`، `platform_content_id`→`content_id`، `text_raw`→`text`، `language_detected`/`language_reported`→`language`، `source_parent_title`→`post_title` نگاشت شدن)؛ وگرنه (فایل‌ها هنوز موجود نیستن) رفتار قبلی — خواندن از `data/interim/clean.jsonl` — با یک هشدار صریح در stdout ادامه پیدا می‌کنه که می‌گه سمپل بدون فیلتر eligibility (دوپلیکیت/بازه‌زمانی/provenance) ساخته شده. رفتار پیش‌فرض بدون `--resample` (migrate-in-place روی ۳۰۰ ردیف موجود) دست‌نخورده موند چون اصلاً `load_records()` رو صدا نمی‌زنه — تست شد و همون ۳۰۰ ردیف (`en=135, fa=135, ar=30`) بدون خطا reuse شدن. | نمونه‌ی annotation قبلاً مستقیماً از دیتای خام (raw comments، بدون فیلتر deduplication/بازه‌زمانی/provenance که `apply_eligibility.py` پیاده می‌کنه) کشیده می‌شد — یعنی annotator‌ها ممکن بود روی رکوردهایی زمان بذارن که در نهایت در تحلیل نهایی quarantine/audit_only/context_only می‌شدن. وصل‌کردن مستقیم دو تا اسکریپت باعث می‌شه سمپل annotation همون universe رکوردهای واقعاً eligible-for-analysis رو نمونه‌گیری کنه؛ fallback با هشدار (نه خطا) نگه داشته شد چون eligibility pipeline هنوز روی دیتای واقعی کامل اجرا نشده و اسکریپت نباید قبل از اون کار بیفته. |
| 2026-08-13 | سه ناسازگاری بین `docs/checklist.md` (که تا امروز در `docs/README.md` لیست نشده بود) و کد فعلی رفع شد: (۱) `src/annotation/schema.py`'s `TARGETS` از ۵ Target دلبخواهی (`iran_government_policy`/`us_government_policy`/`military_action`/`negotiation_diplomacy`/`human_economic_impact`) به همون ۶ Target با ID رسمی `T01`-`T06` که `docs/Chapter_1_Project_Definition_and_Research_Design_v5.md`، `docs/pre_analysis_decision_table_v1.md`، `docs/event_registry_v3.md` و `docs/query_registry_v5.md` از قبل بهشون رفرنس می‌دادن عوض شد؛ `PRIMARY_TARGET_IDS=[T01,T02,T03]`/`SUPPLEMENTARY_TARGET_IDS=[T04,T05,T06]` هم اضافه شد. (۲) `build_labeling_sample.py`'s `RANDOM_SEED` از `42` به `1405` عوض شد (چک‌لیست §۱۷: «Seed ثابت: 1405»). (۳) نمونه‌گیری Gold Sample از طبقه‌بندی تک‌بعدی (فقط زبان) به دوبعدی (Platform × Language) عوض شد: `LANGUAGE_QUOTAS` جای خودش رو به `PLATFORM_LANGUAGE_QUOTAS` داد (هر پلتفرم ۱۰۰ = ۴۵ فارسی + ۴۵ انگلیسی + ۱۰ عربی، جمعاً ۳۰۰) — چک‌لیست §۱۷ صریحاً «طبقات اصلی: Platform و Language» و «۱۰۰ رکورد برای هر پلتفرم» رو خواسته بود ولی کد قبلی هیچ سهمیه‌ی جداگانه‌ای برای پلتفرم نداشت. `platform` به `GOLD_SAMPLE_COLUMNS` (`schema.py`) و `CSV_COLUMNS`/`_load_from_eligibility_outputs` (`build_labeling_sample.py`) اضافه شد تا این ستون اصلاً قابل ذخیره و قابل stratify باشه. `stratified_sample()` حالا دو پاس leftover-redistribution داره (اول داخل همون پلتفرم بین زبان‌ها، بعد فقط اگر لازم شد بین پلتفرم‌ها با یک WARNING صریح). تست شد: با pool مصنوعی کافی در هر ۹ سلول (Platform×Language) خروجی دقیقاً ۱۰۰/۱۰۰/۱۰۰ و ۴۵/۴۵/۱۰ می‌ده؛ با pool مصنوعی کمبود، backfill بین پلتفرم‌ها با WARNING درست کار می‌کنه. **باز مونده:** `data/interim/clean.jsonl` (منبع fallback فعلی، چون eligibility pipeline هنوز اجرا نشده) صرفاً ۱۴۵٬۷۴۲ رکورد YouTube داره — هیچ رکورد Reddit/X روش join نشده (نه در `data/raw/reddit/` و نه هیچ‌جای دیگه فایلی هست)، پس اجرای واقعی `--resample` امروز فقط یک نمونه‌ی تماماً-YouTube با WARNING بزرگ می‌ده، نه واقعاً ۱۰۰/۱۰۰/۱۰۰. به همین دلیل عمداً `--resample` روی فایل واقعی (`data/annotated/sample_sentiment_labels.csv`) اجرا نشد — کد آماده‌ست، منتظر join شدن Reddit/X به `clean.jsonl` (یا اجرای `apply_eligibility.py` بعد از اون join) می‌مونه. | کاربر درخواست کرد این سه مورد که در بررسی چک‌لیست پیدا شده بودن مطابق چک‌لیست اصلاح بشن. |
| 2026-08-13 | همکاران دو فایل handoff تحویل دادن که از قبل دقیقاً به شکل `config/raw_schema_columns.py`'s `RAW_SCHEMA_COLUMNS` بودن، نه به فرمت خام هرکدوم از کالکتورهای موجود: `data/raw/iran_us_war/X_Scraper_v4_7_Target20K_Current.xlsx`'s شیت `Raw_Tweets` (۱۶,۴۷۵ ردیف) و `data/raw/iran_us_war/reddit_raw_schema.csv` (۱۵۸,۹۵۹ ردیف). چون `x_to_record.py`/`reddit_to_record.py` هرکدوم فرمت خامِ مخصوص کالکتور خودشون رو می‌خونن (نه این شکل از‌قبل-map‌شده)، یک اسکریپت جدید و عمومی اضافه شد: `src/ingestion/handoff_csv_to_record.py` که `x_to_record.py`'s `build_record()`/`record_to_raw_schema_row()` رو (import، نه کپی) روی هر فایل ورودی که ستون‌هاش با `RAW_SCHEMA_COLUMNS` یکی باشه صدا می‌زنه — چون آن تابع خودش platform-agnostic است (`platform` رو از خودِ ردیف می‌خونه). ورودی می‌تونه csv یا xlsx (با `--sheet`) باشه. دو نکته‌ی خاص این اجرا: (۱) برای Reddit، چون هش نویسنده از قبل توسط کالکتور Reddit محاسبه شده (نه placeholder همیشه‌پر مثل X)، ستون `author_hash_method` مصنوعاً `handle_fallback_v1` ست شد هرجا `author_hash` واقعاً پر بود — وگرنه منطق fallback مخصوص X (که بر پایه‌ی `author_username` تصمیم می‌گیره) همه‌ی ۱۵۸,۹۵۹ هش واقعی رو دور می‌ریخت (تست شد: قبل از این fix `author_hash present: 0/158959`، بعدش `158959/158959`). (۲) فایل Reddit ستون‌های `language_reported`/`language_detected` رو کاملاً خالی داشت (هیچ‌وقت language-detection روش اجرا نشده بود)؛ چون `build_labeling_sample.py`'s سهمیه‌ی Platform×Language (چک‌لیست §۱۷) بدون یک زبان fa/en/ar واقعی برای هر ردیف کار نمی‌کنه (تست شد: بدون این fix، سهمیه‌ی ۱۰۰تایی Reddit کاملاً صفر می‌موند و به یوتیوب/X بازتوزیع می‌شد)، همون heuristic سبکی که خودِ `reddit_to_record.py` قبلاً برای همین منظور استفاده می‌کنه (`geo_tagger._detect_text_language`، بدون تماس LLM) این‌جا هم صدا زده شد، فقط وقتی هر دو ستون زبان خالی بودن. بعد از این دو اسکریپت: `join_and_clean.py` اجرا شد (`data/interim/clean.jsonl` حالا ۳۳۲,۹۰۸ رکورد هر سه پلتفرم: youtube=157474, reddit=158959, x=16475) و `build_labeling_sample.py --resample --force` (نمونه‌ی ۳۰۰تایی Platform×Language، دقیقاً ۱۰۰/۱۰۰/۱۰۰ به تفکیک پلتفرم، بدون duplicate/متن خالی/PII). **باز مونده، عمداً:** این نمونه هنوز از `clean.jsonl` (fallback بدون فیلتر Eligibility) کشیده شده، نه از خروجی `apply_eligibility.py` (که خودش به `data/raw_harmonized/{platform}/*.parquet` نیاز داره — این لایه هنوز برای X/Reddit ساخته نشده) — تصمیم آگاهانه‌ی کاربر برای سرعت، با این‌که annotator‌ها ممکنه روی رکوردهایی وقت بذارن که در تحلیل نهایی quarantine/audit_only بشن؛ باید قبل از تحلیل نهایی جبران بشه. | کاربر (پارمیدا) با فشار زمانی ۱۸ساعته، صریحاً «مسیر سریع» رو به‌جای ساخت کامل لایه‌ی `raw_harmonized` + اجرای `apply_eligibility.py` انتخاب کرد تا نمونه‌ی لیبل‌زنی هرچه زودتر (بلندترین صف کار، باید موازی با بقیه‌ی مراحل شروع بشه) دست annotatorها برسه. |
| 2026-08-13 | X هم به «مسیر یوتیوب/ردیت» (`config/schema.py`'s `Record`) وصل شد — یک اسکریپت جدید و جداگانه (`src/ingestion/x_to_record.py`) اضافه شد که خروجی موجود `x_scraper.py` (`export_raw_csv()`'s `{X_OUTPUT_ROOT یا default_local_output_root}/exports/x_raw.csv`) رو می‌خونه و `data/raw/x/{x_comments_v1.jsonl, x_raw_export.csv}` رو طبق `config/raw_schema_columns.py` می‌سازه؛ خودِ `x_scraper.py` (حسین) کاملاً دست‌نخورده موند. برخلاف Reddit، این پل نیازی به تبدیل فرمت timestamp نداشت (`x_scraper.py`'s `iso_z()`/`utc_now()` از قبل همون فرمت `...Z` که `Record.date` می‌خواد رو تولید می‌کنن) و اکثر ستون‌های `parse_article()` از قبل با نام `RAW_SCHEMA_COLUMNS` یکی بودن — پس این بریج به‌مراتب ساده‌تر از Reddit's بود. تصمیم‌های خاص این اسکریپت: (۱) `AuthorMetadata.author_id_status` رو با presence صرف `author_hash` تعیین نکرد — چون ستون `author_hash` در `x_raw.csv` هیچ‌وقت خالی نیست (وقتی handle قابل‌استخراج نبوده، `parse_article()` یک fallback hash بر پایه‌ی `content_id` می‌سازه که هیچ نویسنده‌ای رو واقعاً شناسایی نمی‌کنه)؛ به‌جاش از ستون `author_hash_method` ('handle_fallback_v1' در برابر 'content_id_fallback_v1') استفاده کرد و فقط در حالت اول hash رو وارد `Record` می‌کنه. (۲) `Record.post_id` رو به `platform_content_id` ست کرد (نه `None`) چون هر توییت خودش یک آیتم top-level مستقله (بدون رابطه‌ی parent/reply واقعی در داده‌ی `x_scraper.py`) — این باعث می‌شه فیچر «تعداد پست‌های متفاوت» در `user_features.py` برای X صفر نمونه، نه این‌که واقعاً محاسبه بشه. (۳) `collector_version` مستقیماً از ستون `collector_version` خودِ `x_raw.csv` (`x-selenium-v4.5`) کپی شد، نه یک ثابت مخصوص این بریج (برخلاف Reddit، چون خطِ‌لوله‌ی خام Reddit اصلاً این ستون رو نداشت ولی `x_scraper.py` داره). همراهش: `join_and_clean.py`'s `_load_all_comments()` حالا `data/raw/x/x_comments_*.jsonl` رو هم (کنار Reddit/یوتیوب) می‌خونه. تست: با یک fixture مصنوعی سه‌ردیفی (یک handle-resolved، یک fallback بدون‌handle، یک OUT-of-window) اجرا و خروجی JSONL/CSV دستی چک شد — ۲/۳ رکورد `author_hash` گرفتن (دقیقاً همونی که handle داشت)، ۰/۳ `content_status != active` (چون `x_scraper.py` فعلاً همیشه `active` می‌نویسه)، هیچ PII خامی (`author_username`/`author_display_name`/`tweet_url`) در خروجی نبود. **باز مونده (عمداً، طبق تصمیم Reddit مشابه):** `automation_risk.score_batch()` و geo/Tier-0 relevance tagging برای X وصل نشدن — `x_scraper.py` خودش هم فعلاً این ستون‌ها رو همیشه خالی می‌ذاره، پس این بریج هم عیناً خالی نگهشون داشت. **یافته‌ی جانبی، رفع‌نشده:** `config.yaml`'s `x:` بلاک تنظیمات (`collector_version`, `runtime.output_root_env_var`, ...) یک سطح اشتباه، زیر `youtube:` تو در تو شده (باید مثل `youtube:` یک کلید top-level مستقل باشه — `platforms: [...]` از قبل `x` رو به‌عنوان یک پلتفرم مستقل لیست کرده). یعنی `config_loader.load_config().x` امروز `{}` برمی‌گرده و خودِ `x_scraper.py`'s چک `if not X_CONFIG: raise ValueError(...)` هم با کانفیگ فعلی fire می‌شه. این باگ در `config.yaml` (نه در کد این تغییر) هست؛ عمداً fix نشد چون این تغییر مسئولیت `x_scraper.py`/`config.yaml` رو نداره — `x_to_record.py`'s `_x_runtime_config()` با fallback به همون مسیر تو در تو خودش رو در برابرش محافظت می‌کنه، اما خودِ `x_scraper.py` باید توسط مالکش (حسین) اصلاح بشه. | کاربر صریحاً خواست X همون مسیری رو بره که Reddit رفت (`docs/cross_platform_alignment_guide_fa.md`'s بالای فایل، هشدار «X هنوز export مطابق schema استاندارد نداره» رو resolve کنه)، با همون الگوی `reddit_to_record.py`. مسئولیت مالکیت کد X در `cross_platform_alignment_guide_fa.md` §۶ عمداً «مشخص نشده» باقی موند — کاربر نخواست این تغییر خودش این تصمیم رو بگیره. |
| 2026-08-13 | جریان مالی نهایی یکپارچه شد: `finance_market_extract.py` Collector مرجع، `build_financial_outputs.py` ماژول آماده‌سازی، و دو Notebook جدا برای Quality/Preparation و Social Alignment ثبت شدند. نسخه تاریخی پاسخ‌های خام در `data/raw_original/financial/` بازنویسی نمی‌شود و هر جمع‌آوری جدید زیر `data/raw/{topic_id}/financial/runs/{run_id}/` قرار می‌گیرد؛ ورودی‌های عمومی Freeze‌شده در `data/interim/financial/frozen_inputs/` نگهداری می‌شوند؛ جدول‌ها و Auditها نیز از هم جدا هستند. کلید FRED فقط از `.env` خوانده می‌شود. Collectorهای ساده `finance_yahoo.py` و `finance_tgju.py` بازنشسته شدند. | جلوگیری از چند مسیر اجرایی متناقض، همسان‌کردن بازه با `config.yaml`، امکان بازتولید بدون تکرار اجباری جمع‌آوری وب، جلوگیری از بازنویسی داده خام، و اجرای تحلیل هفتگی قابل‌دفاع با چهار شاخص اصلی از پیش تعیین‌شده. |
| 2026-08-12 | فرمول `author_hash` (`src/ingestion/author_hash.py`) از `sha256("channel_id:{SALT}:{channel_id}")` (+ fallback به `sha256("display_name:{SALT}:{display_name}")` وقتی `channel_id` نبود) به فرمول `docs/raw_schema_v05.md` §۵ عوض شد: `sha256(f"{platform}:{channel_id}:{SALT}")`. Fallback به نام نمایشی کاملاً حذف شد (v05 فرمتی برایش تعریف نکرده؛ `author_hash` حالا در نبود `channel_id` صرفاً `None` می‌ماند). داده‌های قبلاً جمع‌آوری‌شده (`data/raw/iran_us_war/youtube_comments_v2.jsonl`, ۸۲,۵۵۰ رکورد) با اسکریپت یک‌بارهٔ `src/ingestion/backfill_author_hash_v05.py` دوباره هش شدند (نسخهٔ قبل از Backfill در `data/raw/iran_us_war/archive_before_author_hash_v05_backfill_2026-08-12/` نگه داشته شده). | فرمول قدیم با v05 هم‌مقدار نبود (هش یک نویسنده‌ی یکسان زیر دو فرمول متفاوت است) — طبق بررسی `docs/schema_mapping_template.csv` (نگاشت youtube→v05). چون بازهٔ پروژه (`END=2026-07-22`) از قبل تمام شده، ریسک Cutover وسط یک Collection زنده نبود؛ کاربر تصمیم گرفت هم فرمول عوض شود هم داده‌های قبلی Backfill شوند، نه فقط از این پس. |
| 2026-08-12 | Reddit به «مسیر یوتیوب» (`config/schema.py`'s `Record`) وصل شد — یک اسکریپت جدید و جداگانه (`src/ingestion/reddit_to_record.py`) اضافه شد که خروجی موجود `reddit_raw_json_pipeline.py` (`master_parent_posts_dedup.csv` + `comments_from_raw_json.csv`) را می‌خواند و `data/raw/reddit/{reddit_comments_v1.jsonl, reddit_raw_export.csv}` را طبق `config/raw_schema_columns.py` می‌سازد؛ خودِ اسکریپت‌های Selenium (`reddit_parent_post_collector.py`, `reddit_raw_json_pipeline.py`) دست‌نخورده ماندند. همراهش: (۱) `config/schema.py` دو فیلد افزایشی گرفت: `author_id_status` (`AuthorMetadata`) و `content_status` (`Record`) — هر دو در `raw_schema_v05.md`/`raw_schema_columns.py` از قبل بودند ولی هیچ‌وقت به `Record` اضافه نشده بودند؛ (۲) `reddit_raw_json_pipeline.py` حالا `author_fullname` و `subreddit_id` (شناسه‌های پایدار ردیت، نه یوزرنیم/نام نمایشی قابل‌تغییر) را هم به‌ازای هر کامنت ذخیره می‌کند؛ (۳) گره‌های `more` (کامنت‌های جمع‌نشده‌ی ردیت) دیگر بی‌صدا دور ریخته نمی‌شوند — تعداد و برآورد کامنت‌های ازدست‌رفته در `more_nodes_not_expanded.csv` ثبت می‌شود؛ (۴) تشخیص بلاک‌شدن قبل از باز کردن فایرفاکس یک‌بار با `requests` واقعی status-code می‌گیرد (۴۰۳/۴۲۹/۵۰۳ = بلاک قطعی، نه فقط matching متن صفحه)؛ (۵) `automation_risk.score_batch()` و `author_geo.tag_geo()` — که از قبل platform-agnostic بودند — عیناً برای ردیت هم صدا زده می‌شوند؛ (۶) `join_and_clean.py` حالا `data/raw/reddit/reddit_comments_*.jsonl` را هم (کنار مسیر topic-scoped یوتیوب) می‌خواند، پس `user_features.py`'s Tier B هم روی هر دو پلتفرم اجرا می‌شود. `requirements.txt` هم `selenium`/`webdriver-manager` را که کد ردیت از قبل import می‌کرد ولی توی لیست نبود، گرفت. | کاربر (پارمیدا) صریحاً خواست Reddit همون مسیری رو بره که یوتیوب می‌ره (`Record`/schema، نه مسیر جداگانه‌ی X). طبق `GIT_WORKFLOW.md` پایپ‌لاین Reddit مسئولیت حسین/علی است نه پارمیدا — کاربر این هماهنگی رو تأیید کرد. **باز مونده (عمداً، جزئیاتش در `src/ingestion/reddit_to_record.py`'s docstring):** متن خودِ Submission (selftext) هنوز جایی استخراج نمی‌شود، فقط عنوان؛ `geo_tagger.py`'s LLM relevance/perspective tagging (نسخه‌ی سطح-پست) وصل نشد چون به همون selftext نیاز داره؛ `author_geo.tag_geo`'s `channel_hint` برای ردیت `None` است چون `SOURCE_REGISTRY` نقشه‌ی subreddit→کشور نداره (تصمیم محتوایی، نه فنی). مسیر PRAW/OAuth رسمی به‌جای Selenium هنوز تصمیم‌گیری نشده — نیاز به ثبت اپ در `reddit.com/prefs/apps` توسط تیم داره. |
| 2026-08-12 | فالوآپ همون تغییر بالا — دو مورد از سه مورد باز رفع شدن: (۱) `reddit_raw_json_pipeline.py` حالا `data[0]` (Listing خودِ Submission، نه فقط `data[1]`'s کامنت‌ها) رو هم پارس می‌کنه (`parse_submission()`) و `selftext`/`is_self`/`external_url`/`score`/`num_comments`/`permalink`/`link_flair_text` رو در `submissions_from_raw_json.csv` جدا از کامنت‌ها ذخیره می‌کنه (طبق قاعده‌ی §۸ سند: Submission/Comment/Reply باید از هم تفکیک بشن، نه قاطی). (۲) `reddit_to_record.py` این فایل رو می‌خونه و برای هر Self-post که واقعاً متن داره یک `Record` جدا با `content_type="submission"` می‌سازه (`content_id=post_id`, `parent_id=None`, `automation_risk_score=None` چون Tier A نیاز به یک batch از چند آیتم هم‌نوع داره که یک Submission تنها نداره)؛ پست‌های فقط-لینک بدون Selftext عمداً Record نمی‌گیرن (متن Opinion‌ای وجود نداره). هم‌زمان `geo_tagger.tag_video_cached()` («Tier ۰» یوتیوب) حالا یک‌بار به‌ازای هر `post_id` یکتا صدا زده می‌شه (عنوان+Selftext به‌عنوان description)، نتیجه در `data/raw/reddit/video_geo_metadata.jsonl` کش می‌شه — دقیقاً همون فایل/فرمتی که یوتیوب داره، پس `join_and_clean.py`'s `_load_geo_lookup` هم برای هر دو پلتفرم merge می‌کنه. طبق خودِ docstring `geo_tagger.py`، این متادیتا روی `Record` نوشته نمی‌شه (side-file می‌مونه، در تحلیل بعداً join می‌شه). مورد سوم (نگاشت subreddit→کشور برای `channel_hint`) عمداً دست‌نخورده موند — تصمیم محتوایی تیمه. تست: یک fixture مصنوعی (شامل یک Self-post با متن، یک Link-post بدون متن) با `GROQ_API_KEY` عمداً خالی (fail-open، بدون تماس واقعی با API) اجرا و خروجی دستی چک شد — Link-post درست Record نگرفت، Self-post درست `content_type=submission` گرفت. | کاربر (پارمیدا) از بین ۴ مورد باز، همین دو تا رو برای این فالوآپ انتخاب کرد؛ نگاشت subreddit→کشور و مسیر PRAW/OAuth رو صریحاً کنار گذاشت (اولی چون تصمیم محتوایی نه فنیه، دومی چون به credential نیاز داره که فقط خودش می‌تونه بسازه). |
| 2026-08-12 | `geo_tagger.py` چند-کلیدی شد: `GROQ_API_KEYS` (comma-separated) به‌جای تک `GROQ_API_KEY` — چند کلید Groq (هرکدوم مال یک همکار واقعی، نه حساب تکراری/جعلی طبق ToS Groq) پول می‌شن. وقتی یک کلید به سقف روزانه‌ش (RPD/TPD) می‌رسه، فقط همون کلید برای بقیه‌ی همون اجرا کنار گذاشته می‌شه (`_exhausted_keys`) و به کلید بعدی می‌ره؛ `GroqQuotaExceeded` فقط وقتی propagate می‌شه که **همه‌ی** کلیدها تموم شده باشن — یعنی قرارداد بیرونی تابع عوض نشده، پس `youtube_extract.py` و `reddit_to_record.py` بدون هیچ تغییری همچنان درست کار می‌کنن. تست شد با کلیدهای fake (بدون تماس واقعی شبکه، با monkeypatch کردن `_call_groq_with_retry`): rotation روی quota-exceeded، skip کلید already-exhausted در فراخوانی بعدی، و raise صحیح وقتی همه تموم شدن — هر سه تأیید شد. `.env.example` مستند شد. | کاربر پرسید می‌شه چند نفر API key بدن تا سهمیه‌ی Groq/OpenRouter حل بشه؛ جواب داده شد (بله اگه هرکدوم حساب واقعی خودشونه، نه حساب جعلی) و پیاده‌سازی تأیید شد. |
| 2026-08-11 | به‌جای نگه‌داشتنِ دائمیِ ۲۱ query متوقف‌شده، رفع محدودیت quota به‌شکل region rotation پیاده شد: `youtube_extract.py` تابع `regions_for_today()` رو اضافه کرد که هر روز فقط `REGIONS_PER_DAY` (پیش‌فرض ۲) تا از ۵ region رو انتخاب می‌کنه (چرخه‌ی ۳روزه، بر اساس `date.toordinal() % group_count` — قطعی/deterministic روی تاریخ تقویمی، نه شمارهٔ اجرا، تا اجرای دوباره در همون روز idempotent باشه و یک روز جاافتاده چرخه رو جابه‌جا نکنه). همه‌ی ۲۱ query متوقف‌شده در `query_registry.yaml` دوباره فعال شدن (`active_to` → `null`)، `registry_version` رفت رو `0.3-draft`. | با ۲۹ query × ۲ region/روز = ۵۸ ترکیب × ۱۰۰ = ۵,۸۰۰ واحد discovery (زیر سقف ۸۰۰۰، ۲,۲۰۰ واحد برای video-details/comment-fetch می‌مونه)، و در عرض ۳ روز هر ۵ region پوشش داده می‌شن — بدون از‌دست‌رفتن دائمیِ پوشش هیچ query‌ای، برخلاف راه‌حل ۲۰۲۶-۰۸-۰۸ که econ/diplomacy/hashtag/oppose رو نامحدود متوقف نگه می‌داشت. توجه: rotation فقط `REGION_CODES` رو تحت تأثیر قرار می‌ده، نه discovery کانال‌های curated (`config.yaml`'s `channels`) که اصلاً region-multiplied نیست. |
| 2026-08-08 | یک اجرای واقعی `youtube_extract.py` کل quota روزانه (۸۰۰۰) رو در مرحله‌ی discovery خرج کرد و ۰ کامنت نوشت. علتش: `config/query_registry.yaml` (نسخه ۰.۱-draft) ۲۹ query غیرعربی فعال داشت × ۵ region (`config.yaml`) = ۱۴۵ ترکیب `search.list` × ۱۰۰ واحد = ۱۴,۵۰۰ واحد لازم — تقریباً دو برابر سقف روزانه، پس هیچ‌وقت به مرحله‌ی گرفتن جزئیات ویدیو/کامنت نمی‌رسید (نه فقط اون روز، هر روز، چون هیچ کش «این ترکیب امروز جست‌وجو شده» نداریم). به همین دلیل تعداد query فعال در `query_registry.yaml` از ۲۹ به ۸ (۴ فارسی + ۴ انگلیسی: `topic_1`, `actor_2`, `support_1`, `support_2` هر زبان) کاهش یافت — بقیه با `active_to` غیرفعال شدن (نه حذف، طبق قرارداد خودِ فایل)، `registry_version` رفت رو `0.2-draft`. | همون تصمیم بازِ ردیف ۲۰۲۶-۰۸-۰۴ («کاهش به ۶ Query یک تصمیم محتوایی/آماریه که هنوز گرفته نشده») بالاخره باید گرفته می‌شد؛ ۸ (نه ۶) انتخاب شد تا `support_1`+`support_2` (هر دو جهت موافق/مخالف) حفظ بشه و `oppose_1`/`oppose_2` که پوشش تکراری همون تقابل بودن حذف بشن. ۸×۵=۴۰ ترکیب × ۱۰۰ = ۴۰۰۰ واحد discovery، ۴۰۰۰ واحد دیگه برای video-details/comment-fetch می‌مونه. کاهش econ/diplomacy/hashtag موقتیه، نه نهایی — قابل فعال‌سازی مجدد وقتی headroom واقعی quota مشخص‌تر شد. |
| 2026-08-07 | `docs/raw_schema_v03.md` نوشته شد — نسخه‌ی اصلاحی همکار (`raw_schema_v02.md`)، با تفکیک صریح Eligibility Filter از Quota-Triage Pre-filter، `sampling_method` به‌جای فرض تلویحی تصادفی‌بودن سقف، تنزل `content_status` به Ideal، و بخش «قفل بازه» (§۱۰-۱). | مقایسه‌ی سند با کد فعلی چند تناقض واقعی نشون داد (فیلتر relevance داخل Collector، drop رکورد خارج از بازه، `order=relevance` در v1، مانیفست ناقص) که باید قبل از پیاده‌سازی حل می‌شدن، نه صرفاً کپی می‌شدن. |
| 2026-08-07 | همکار `docs/source_registry_v3.md` رو فرستاد (فهرست ۱۵ کانال Active یوتیوب با `source_id`، Reddit/X مشابه، و قواعد اجرایی دقیق‌تر از raw_schema_v03). | این سند چند نکته رو نسبت به raw_schema_v03 دقیق‌تر/قطعی‌تر کرد: `publishedBefore` باید همین الان ثابت بشه (نه موکول به آینده)، سقف ۳۰۰ کامنت باید واقعاً random sampling با seed ثابت (`42`) باشه نه truncation قطعی، و زبان عربی صراحتاً خارج از دامنه‌ست (SR-006). |
| 2026-08-07 | `youtube_extract.py` (v1) و `youtube_extract_incremental.py` (v2) در یک فایل (`src/ingestion/youtube_extract.py`) یکپارچه شدن؛ v1 کاملاً بازنشسته شد. `checkpoint.py` از توابع مخصوص v1 (`mark_discovered`, `all_discovered_video_ids`, `mark_comments_fetched`, `mark_geo_tagged`) پاک شد. | کاربر خواست یک کد استخراج یوتیوب داشته باشیم که مطابق `raw_schema_v03.md` + `source_registry_v3.md` باشه. v2 هنوز هیچ داده‌ای جمع نکرده بود (صفر رکورد در `youtube_comments_v2.jsonl`) پس یکپارچه‌سازی بدون ریسک از‌دست‌رفتن داده انجام شد. **داده‌ی قدیمی v1 (~۷۵هزار رکورد) دست‌نخورده و frozen موند — remediationش طبق `docs/project_brief_for_llm.md` هنوز کار جداییه.** |
| 2026-08-07 | `config/schema.py`'s `Record` با ۱۶ فیلد افزایشی جدید گسترش یافت (`content_type`, `matched_query_ids`, `query_version`, `discovery_route`, `source_id`, `source_container[_id]`, `permalink_hash`, `source_total_available`, `sampling_method/applied`, `items_kept`, `random_seed`, `language_confidence`, `project_week`, `in_window`, `is_partial_week`). | نگاشت مستقیم قرارداد `raw_schema_v03.md` روی `Record`. **این تغییر باید با حسین هماهنگ/تأیید بشه** — طبق قرارداد تیم `schema.py` مسئولیت اونه؛ حجم این تغییر (۱۶ فیلد یک‌جا) بیشتر از افزایش‌های قبلیه. |
| 2026-08-07 | `config.yaml`'s `youtube.channels` با ۱۵ کانال Active از `source_registry_v3.md` جایگزین شد (Press TV/IRIB News/NYT/CBS/Sky News/France24/euronews/RFI/CSIS/DW-News حذف؛ AP/Fox News/Bloomberg TV/TRT World/WION/Middle East Eye/DW Persian اضافه)؛ `keywords_ar` و ریجن `["AE","ar"]` هم حذف شدن. | تطبیق مستقیم با فهرست Active سند + SR-006 (عربی خارج از دامنه). **باز:** `channel_id` واقعی ۷ کانال جدید هنوز verify نشده (خودِ سند هم این رو در چک‌لیست §۹ باز گذاشته) — هندل‌های فعلی بهترین حدسن، نه تأییدشده؛ اگه غلط باشن فقط لاگ warning می‌دن و رد می‌شن، کرش نمی‌کنن. **باز:** `query_registry.yaml` هنوز ۲۳ Query غیرعربی داره در حالی که حساب quota سند فرض ۶ تا کرده — کاهش به ۶ یک تصمیم محتوایی/آماریه که هنوز گرفته نشده. |
| 2026-08-07 | بخش Annotation/Model-Evaluation کلاً بازسازی شد تا با سند پروژه (§۱۸-۲۳) بخونه: `src/annotation/schema.py` (Sentiment/Stance/Emotion/Content-Type + ۵ Target ثابت + validator خروجی)، `src/annotation/model_routes.py` (`ModelRoute` + registry قیمت واقعی Groq/OpenRouter/DeepSeek)، `src/annotation/prompt_contract.py` (پرامپت نسخه‌بندی‌شده `PROMPT_VERSION`)، `src/annotation/llm_client.py` (caller یکپارچه چندprovider با cache/retry-backoff/cost-latency logging)، `src/annotation/run_model_comparison.py` (جایگزین `compare_llm_sentiment.py` که حذف شد). | نسخه قبلی فقط sentiment سه‌کلاسه رو با یک پرامپت نسخه‌بندی‌نشده و بدون هزینه/تأخیر/coverage می‌سنجید — سند صریحاً هر ۴ لایه + معماری cost-aware (§۲۱) + Prompt Contract نسخه‌بندی‌شده (§۲۲) رو الزام کرده. |
| 2026-08-07 | کلید `GEMINI_API_KEY` که کاربر فرستاد (`AQ.Ab8...`) برای SDK `google-generativeai` نامعتبره (تست شد: HTTP 403) — فرمت کلیدهای واقعی AI-Studio با `AIzaSy...` شروع می‌شه. تا رسیدن کلید درست، مدل‌های Gemini از طریق روت `openrouter_gemini_flash_lite` (همون مدل، یک هاپ اضافه از OpenRouter) در دسترس‌ان. کلید مستقیم DeepSeek هم موجودی حساب کافی نداره (HTTP 402 «Insufficient Balance») — از روت `openrouter_deepseek_flash` به‌جاش استفاده می‌شه. | جلوگیری از هدررفت زمان روی retry بی‌فایده؛ `llm_client.py` دیگه روی خطاهای 4xx غیر-429 (کلید بد/موجودی ناکافی) دوباره تلاش نمی‌کنه. |
| 2026-08-07 | `build_labeling_sample.py` پیش‌فرضش از «هر بار نمونه تصادفی تازه» به «مهاجرت schema درجا» تغییر کرد (فلگ `--resample` برای نمونه واقعاً تازه). | اجرای اول با schema جدید (منبع `data/interim/clean.jsonl` به‌جای raw glob) یه نمونه ۹۰تایی کاملاً متفاوت از نمونه قبلی ساخت و ۶۰ ترجمه فارسی دستی یه هم‌تیمی (ستون `translation_fa`) که با تطبیق متنی قرار بود منتقل بشه صفر تا مچ پیدا کرد — چون خودِ ۹۰ ردیف عوض شده بودن، نه فقط ترتیبشون. فایل قبلی از گیت (`git checkout`) بازیابی و رفتار پیش‌فرض اسکریپت طوری تغییر کرد که دیگه بدون درخواست صریح (`--resample`) هیچ‌وقت نمونه رو عوض نکنه، فقط ستون‌های جدید رو خالی اضافه کنه. |
| 2026-08-04 | تلگرام کلاً از دامنه استخراج پارمیدا حذف شد؛ فقط YouTube ادامه پیدا می‌کنه. | دیتای تلگرام قابل‌دفاع نبود (بایاس نمونه). |
| 2026-08-04 | برای پوشش شکاف‌های سند (content_id/parent_id/collected_at_utc/collection_run_id/query_id/geo_*/automation_risk_score) یک کالکتور YouTube **جدید و جداگانه** (`src/ingestion/youtube_extract_incremental.py`) ساخته شد، نه ویرایش `youtube_extract.py` موجود. | جلوگیری از دست‌خوردن دیتای در حال جمع‌آوری v1 و `checkpoint.json` آن حین استخراج فعال؛ خروجی/Manifest جدا (`youtube_comments_v2.jsonl`, `collection_manifest_v2.jsonl`). |
| 2026-08-04 | `config/schema.py` به‌شکل افزایشی گسترش داده شد (فیلدهای Optional جدید با default، بدون تغییر فیلدهای موجود). | این فیلدها الزام مستقیم بخش‌های ۱۰/۱۱/۱۶/۱۷ سند مشاورن. طبق قرارداد تیم schema.py مسئولیت حسینه — این تغییر باید باهاش هماهنگ/تأیید بشه. |
| 2026-08-04 | رکوردهای جدید دیگه `author_display_name` خام ذخیره نمی‌کنن؛ به‌جاش `author_hash` (sha256 نمکی روی `author_channel_id`، `AUTHOR_HASH_SALT` در `.env`). | بخش‌های ۳/۱۰/۴۳ سند صراحتاً ذخیره نام‌کاربری غیرضروری رو ممنوع کرده — v1 این‌کار رو می‌کرد. **توجه:** دیتای v1 قبلی (~۷۵هزار رکورد `youtube_comments_*.jsonl`) هنوز `author_display_name` خام داره؛ remediation اون یک تصمیم/کار جداست، هنوز انجام نشده. |
| 2026-08-04 | Quota واقعی YouTube API بین v1 و v2 مشترک نگه داشته شد (همون `checkpoint.json`، با namespace کلید جدا `v2_incremental` برای state خود v2). | هر دو اسکریپت از یک `YOUTUBE_API_KEY` استفاده می‌کنن؛ دو شمارنده quota مستقل می‌تونست quota واقعی روزانه رو جمعاً رد کنه بدون این‌که هیچ‌کدوم متوجه بشن. |
| 2026-08-04 | `config/query_registry.yaml` (پیش‌نویس نسخه `0.1-draft`) اضافه شد؛ `keywords_fa/en/ar` در `config.yaml` دست‌نخورده موند و همچنان توسط v1 استفاده می‌شه. | بخش ۱۲ سند پوشش بازیگران/هشتگ/عبارات موافق و مخالف رو الزام کرده که ۴ کلیدواژه فعلی نداره. **این یک پیش‌نویسه — تیم باید قبل از تکیه‌کردن روش برای دفاع نهایی از منبع، بازبینی/تکمیلش کنه.** |

---

## Final Coordination Checklist

ما پیش از ارائه، کنترل‌های زیر را برای هماهنگی کامل داده، تحلیل و مستندات اجرا می‌کنیم.

| Workstream | Final control | Owner | Due Date |
| --- | --- | --- | --- |
| Access Notes | ثبت API، Rate Limit، Quota، Sort و Historical Coverage هر پلتفرم | حسین، پارمیدا و یاسمن | 2026-08-14 |
| Source Registry | کنترل وضعیت منابع و تاریخ راستی‌آزمایی | حسین، پارمیدا و یاسمن | 2026-08-14 |
| Event Registry | کنترل شمارش، Status، منابع و مسیر Confirmatory/Sensitivity | علی و یاسمن | 2026-08-14 |
| YouTube Query/Quota | هم‌ترازی تعداد Queryهای فعال با برنامه Quota و Runs | پارمیدا با تأیید حسین | 2026-08-14 |
| Provenance | اجرای Contract واحد `query_id`، `source_id` و `collection_run_id` طبق Raw Schema | حسین | 2026-08-14 |
| Dashboard & Report | کنترل KPIها، Narrative، منابع، لینک‌ها و محدودیت‌های روش‌شناختی | ریحانه و یاسمن | 2026-08-14 |

## Change History

| Version | Date | Change | Status |
| --- | --- | --- | --- |
| v01 | 2026-08-04 | ثبت لاگ‌های اولیه استخراج و توسعه کالکتورها | Historical |
| v02 | 2026-08-12 | اتصال ردیت و X به استاندارد مشترک و فرمول هشینگ | Historical |
| v03-team | 2026-08-13 | ثبت تصمیم‌های روش‌شناسی و اجرایی تیم، نقش‌ها و تقویم ۲۴روزه پروژه | Historical |
| v04-unified | 2026-08-14 | تجمیع کامل و یکپارچه‌سازی تمام تصمیم‌های استراتژیک تیمی (D-001 تا D-020) و لاگ‌های فنی/مهندسی | Current |
