# رجیستری Query

**پلتفرم‌ها:** X، Reddit و YouTube  
**بازه اجرا:** `2026-02-28` تا `2026-07-22`

---

## ۱. هدف

Query Registry مسیر کشف محتوا را تعریف می‌کند. Query برچسب Sentiment یا Stance نیست
و حجم جامعه آماری را تعیین نمی‌کند. تمام Queryهای اجراشده باید به نسخه، پلتفرم، Run و Window زمانی متصل باشند.

### ۱.۱ نسخه پروتکل و شواهد اجرا

هر Collection Run به نسخه Query Registry تخصیص‌یافته متصل می‌شود. رشته Query اجراشده،
Window، Sort و Cap از Log، Config یا Metadata همان Run ثبت می‌شوند. برای هر Run یکی از وضعیت‌های زیر استفاده می‌شود:

| وضعیت | تعریف |
|---|---|
| `executed_verified` | رشته دقیق Query در Log، کد یا Metadata موجود است |
| `executed_reconstructed` | Query با شواهد چندگانه از فایل و توضیح همکار بازسازی شده است |
| `assigned_not_verified` | Query در Registry تحویلی بوده، اما اجرای آن اثبات نشده است |
| `unknown` | رشته یا Window اجرا قابل تعیین نیست |

Query اجراشده برای هماهنگی با نتیجه بازنویسی نمی‌شود. اختلاف Query برنامه‌ریزی‌شده و اجراشده در `query_execution_audit.csv` ثبت می‌شود.

## ۲. فیلدهای اجباری

| فیلد | تعریف |
|---|---|
| `query_id` | شناسه پایدار |
| `query_family` | خانواده مفهومی |
| `platform` | x/reddit/youtube |
| `language` | en/fa |
| `logical_query` | مفهوم مشترک |
| `actual_query` | رشته دقیق ارسال‌شده به API |
| `entity_anchor` | Iran/US یا معادل فارسی |
| `discovery_route` | query_search/hashtag/source_scope/channel_scope |
| `active_from`, `active_to` | بازه فعالیت |
| `query_version` | نسخه Registry |
| `status` | `assigned` / `archived` / `pilot`; وضعیت طراحی Query و نه مدرک اجرا |
| `precision_audit_n` | حجم نمونه ممیزی |
| `precision_estimate` | سهم نتایج مرتبط در ممیزی |
| `execution_status` | وضعیت شواهد اجرای واقعی |
| `evidence_source` | run_log/collector_code/file_metadata/teammate_note/unknown |

## ۳. خانواده‌های مشترک

| Family | هدف پوشش | Target مرتبط |
|---|---|---|
| `core_conflict` | اشاره مستقیم به مناقشه | T01، T04، T05 |
| `military` | حمله، موشک، پهپاد، تشدید | T01 |
| `diplomacy` | مذاکره، آتش‌بس، توافق | T02 |
| `sanctions_nuclear` | تحریم و مسئله هسته‌ای | T03، T04، T05 |
| `humanitarian` | غیرنظامیان و پیامد انسانی | T06 |
| `energy_hormuz` | نفت، کشتیرانی و هرمز | T03 |
| `information` | رسانه، روایت و اطلاعات نادرست | Topic media_information |
| `event_specific_operation` | نام عملیات مشخص | زمینه رویداد و Topic |
| `event_specific_hormuz` | انسداد، بازگشایی و عبور از هرمز | T03 و زمینه رویداد |
| `event_specific_mou` | تفاهم‌نامه و مذاکرات اسلام‌آباد | T02 |

Queryهای اصلی شامل Entity anchor دوطرفه‌اند تا عبارت‌های عمومی مانند `war` یا `oil` به‌تنهایی اجرا نشوند.

`query_family` برای گروه‌بندی تحلیلی است و جای `query_id` را نمی‌گیرد. برای مثال، Actor-event و Bilateral-military هر دو در خانواده `military` قرار می‌گیرند، اما دو Query مستقل باقی می‌مانند. Economic-impact و Hormuz-and-energy نیز در گزارش می‌توانند زیر خانواده کلان `energy_hormuz` جمع شوند، ولی رشته و شناسه تاریخی آن‌ها ادغام نمی‌شود.

## ۴. Queryهای X

### ۴.۱ Queryهای عمومی تخصیص‌یافته

| ID | Original family | Analytical family | Lang | Assigned query | Route | Risk | Status | Execution |
|---|---|---|---|---|---|---|---|---|
| `XQ-001` | Core conflict | `core_conflict` | en | `("Iran-US war" OR "US-Iran tensions" OR "Iran war" OR "US Iran war")` | `query_search` | low | `assigned` | `assigned_not_verified` |
| `XQ-002` | Actor-event | `military` | en | `("Iran" AND ("airstrike" OR "missile strike" OR "drone attack"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-003` | Bilateral military | `military` | en | `(("Iran" OR "IRGC") AND ("US military" OR "United States") AND ("airstrike" OR "missile strike"))` | `query_search` | low | `assigned` | `assigned_not_verified` |
| `XQ-004` | Diplomacy | `diplomacy` | en | `(("Iran" OR "United States") AND ("ceasefire" OR "negotiations" OR "peace talks"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-005` | Sanctions and nuclear | `sanctions_nuclear` | en | `(("Iran" OR "United States") AND ("sanctions" OR "nuclear programme" OR "nuclear program"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-006` | Humanitarian | `humanitarian` | en | `(("Iran" OR "Iran-US war") AND ("civilian casualties" OR "humanitarian crisis"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-007` | Information environment | `information` | en | `(("Iran" OR "Iran-US war") AND ("misinformation" OR "propaganda"))` | `query_search` | high | `assigned` | `assigned_not_verified` |
| `XQ-008` | Economic impact | `energy_hormuz` | en | `(("Iran" OR "Iran-US war") AND ("oil price" OR "exchange rate" OR "gold price" OR "market volatility"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-009` | Hormuz and energy | `energy_hormuz` | en | `(("Iran" OR "Iran-US war") AND ("Strait of Hormuz" OR Hormuz OR "oil price"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-010` | Core conflict | `core_conflict` | fa | `("جنگ ایران و آمریکا" OR "تنش ایران و آمریکا" OR "جنگ ایران آمریکا")` | `query_search` | low | `assigned` | `assigned_not_verified` |
| `XQ-011` | Actor-event | `military` | fa | `("ایران" AND ("حمله هوایی" OR "حمله موشکی" OR "حمله پهپادی"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-012` | Bilateral military | `military` | fa | `(("ایران" OR "سپاه") AND ("ارتش آمریکا" OR "ایالات متحده") AND ("حمله هوایی" OR "حمله موشکی"))` | `query_search` | low | `assigned` | `assigned_not_verified` |
| `XQ-013` | Diplomacy | `diplomacy` | fa | `(("ایران" OR "ایالات متحده" OR "آمریکا") AND ("آتش‌بس" OR "مذاکرات" OR "صلح"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-014` | Sanctions and nuclear | `sanctions_nuclear` | fa | `(("ایران" OR "ایالات متحده") AND ("تحریم‌ها" OR "برنامه هسته‌ای"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-015` | Humanitarian | `humanitarian` | fa | `(("ایران" OR "جنگ ایران و آمریکا") AND ("تلفات غیرنظامیان" OR "بحران انسانی"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-016` | Information environment | `information` | fa | `(("ایران" OR "جنگ ایران و آمریکا") AND ("اطلاعات نادرست" OR "تبلیغات سیاسی"))` | `query_search` | high | `assigned` | `assigned_not_verified` |
| `XQ-017` | Economic impact | `energy_hormuz` | fa | `(("ایران" OR "جنگ ایران و آمریکا") AND ("قیمت نفت" OR "نرخ ارز" OR "قیمت طلا" OR "نوسان بازار"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-018` | Hormuz and energy | `energy_hormuz` | fa | `(("ایران" OR "جنگ ایران و آمریکا") AND ("تنگه هرمز" OR "قیمت نفت"))` | `query_search` | medium | `assigned` | `assigned_not_verified` |

### ۴.۲ Queryهای رویدادمحور تخصیص‌یافته

| ID | Original family | Analytical family | Lang | Assigned query | Route | Risk | Status | Execution |
|---|---|---|---|---|---|---|---|---|
| `XQ-019` | Operation-specific | `event_specific_operation` | en | `("Epic Fury" OR "Operation Epic Fury" OR "Roaring Lion")` | `query_search` | low | `assigned` | `assigned_not_verified` |
| `XQ-020` | Hormuz blockade | `event_specific_hormuz` | en | `(Hormuz OR "Strait of Hormuz") AND (blockade OR closed OR reopened OR shipping OR transit)` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-021` | MOU / Islamabad | `event_specific_mou` | en | `(("Islamabad" OR MOU OR "memorandum of understanding") AND (Iran OR "United States" OR Trump))` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-022` | Operation-specific | `event_specific_operation` | fa | `("اپیک فیوری" OR "عملیات حماسه" OR "حماسه خشم" OR "روآرینگ لاین")` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-023` | Hormuz blockade | `event_specific_hormuz` | fa | `("تنگه هرمز") AND ("بسته" OR "مسدود" OR "محاصره" OR "بازگشایی" OR "کشتیرانی")` | `query_search` | medium | `assigned` | `assigned_not_verified` |
| `XQ-024` | MOU / Islamabad | `event_specific_mou` | fa | `("اسلام‌آباد" OR "تفاهم‌نامه" OR "تفاهم نامه") AND ("ایران" OR "آمریکا")` | `query_search` | medium | `assigned` | `assigned_not_verified` |

بنابراین قرارداد تحویلی X شامل **۲۴ Query متنی** است: ۱۸ Query عمومی و ۶ Query رویدادمحور. گروه‌بندی تحلیلی تعداد Queryهای اجراشده را تغییر نمی‌دهد.

### ۴.۳ مسیر مکمل Hashtag در X

| ID | Analytical family | Lang | Assigned query | Route | Status | Execution |
|---|---|---|---|---|---|---|
| `XQ-H01` | `hashtag_conflict` | en | `#IranWar OR #IranWar2026 OR #USIranWar OR #IranIsraelWar OR #EpicFury` | `hashtag` | `assigned` | `assigned_not_verified` |
| `XQ-H02` | `hashtag_regional_energy` | en | `#StraitOfHormuz OR #MiddleEastWar OR #MiddleEastConflict OR #Hormuz` | `hashtag` | `assigned` | `assigned_not_verified` |
| `XQ-H03` | `hashtag_persian_pilot` | fa | هشتگ‌های واقعی که باید از اجرای Pilot ثبت شده باشند | `hashtag` | `pilot` | `unknown` |

Hashtag مسیر مکمل است و با ۲۴ Query متنی یکی شمرده یا در تحلیل خام با آن‌ها ادغام نمی‌شود. برای `XQ-H03` اگر رشته واقعی اجراشده پیدا نشود، مقدار آن `unknown` باقی می‌ماند.

برای همه Queryهای تخصیص‌یافته، بازه پیش‌فرض قرارداد `2026-02-28` تا `2026-07-22` است. Coverage واقعی هر Query از قدیمی‌ترین و جدیدترین Timestamp بازیابی‌شده در Audit تعیین می‌شود، نه صرفاً از این بازه برنامه‌ریزی‌شده.

## ۵. Queryهای Reddit

جست‌وجوی Reddit برای کشف Submission استفاده می‌شود؛ سپس Comment و Reply همان Submission دریافت می‌شود. Registry ادعای جست‌وجوی کامل متن همه Commentها ندارد.

### ۵.۱ Queryهای عمومی Source-scoped تخصیص‌یافته

| ID | Original family | Analytical family | Lang | Assigned query | Assigned source scope | Route | Status | Execution |
|---|---|---|---|---|---|---|---|---|---|
| `RQ-001` | Core conflict | `core_conflict` | en | `"Iran-US war" OR "US-Iran tensions" OR "Iran war"` | RD-001, RD-003, RD-004 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-002` | Geopolitical | `core_conflict` | en | `("Iran" AND "United States") AND ("tensions" OR "war")` | RD-002, RD-006, RD-007 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-003` | Iran perspectives | `sanctions_nuclear` | en | `("United States" OR America) AND ("Iran-US war" OR sanctions OR airstrike)` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-004` | Regional | `energy_hormuz` | en | `("Iran" AND "United States") OR ("Strait of Hormuz" AND Iran)` | RD-013 … RD-016 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-005` | Military | `military` | en | `("Iran" OR IRGC) AND (airstrike OR "missile strike" OR "drone attack")` | RD-017 … RD-021 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-006` | Diplomacy | `diplomacy` | en | `("Iran" OR "United States") AND (ceasefire OR negotiations)` | RD-022, RD-002, RD-006 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-007` | Economic | `energy_hormuz` | en | `("Iran" OR "Iran-US war") AND ("oil price" OR "gold price" OR "market volatility")` | RD-023 … RD-027 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-008` | Escalation | `military` | en | `("Iran" AND "United States") AND ("Iran-US war" OR "missile strike")` | RD-028 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-009` | Core conflict | `core_conflict` | fa | `"جنگ ایران و آمریکا" OR "تنش ایران و آمریکا"` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-010` | Military | `military` | fa | `"ایران" AND ("حمله هوایی" OR "حمله موشکی" OR "حمله پهپادی")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-011` | Diplomacy | `diplomacy` | fa | `("ایران" OR "آمریکا") AND ("آتش‌بس" OR "مذاکرات")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-012` | Humanitarian | `humanitarian` | fa | `("ایران" OR "جنگ ایران و آمریکا") AND ("تلفات غیرنظامیان" OR "بحران انسانی")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-013` | Economic | `energy_hormuz` | fa | `("ایران" OR "جنگ ایران و آمریکا") AND ("قیمت نفت" OR "نرخ ارز" OR "قیمت طلا")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-014` | Information | `information` | fa | `("ایران" OR "جنگ ایران و آمریکا") AND ("اطلاعات نادرست" OR "تبلیغات سیاسی")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-015` | Hormuz | `energy_hormuz` | fa | `("ایران" OR "جنگ ایران و آمریکا") AND ("تنگه هرمز" OR "قیمت نفت")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-016` | Sanctions/nuclear | `sanctions_nuclear` | fa | `("ایران" OR "آمریکا") AND ("تحریم‌ها" OR "برنامه هسته‌ای")` | RD-009 … RD-012 | `source_scope` | `assigned` | `assigned_not_verified` |

### ۵.۲ Queryهای رویدادمحور Reddit

| ID | Original family | Analytical family | Lang | Assigned query | Assigned source scope | Route | Status | Execution |
|---|---|---|---|---|---|---|---|---|---|
| `RQ-017` | Operation-specific | `event_specific_operation` | en | `"Epic Fury" OR "Operation Epic Fury" OR "Roaring Lion"` | RD-001, RD-002, RD-017, RD-018 | `source_scope` | `assigned` | `assigned_not_verified` |
| `RQ-018` | Hormuz blockade | `event_specific_hormuz` | en | `(Hormuz OR "Strait of Hormuz") AND (blockade OR closed OR shipping)` | RD-001, RD-023, RD-024 | `source_scope` | `assigned` | `assigned_not_verified` |

### ۵.۳ مسیر Discovery سراسری Reddit

| ID | Analytical family | Lang | Assigned query | Route | Status | Execution |
|---|---|---|---|---|---|---|
| `RQ-A01` | `discovery_core` | en | `"Iran war" OR "Iran-US war"` | `query_search` | `assigned` | `assigned_not_verified` |
| `RQ-A02` | `discovery_bilateral` | en | `"Iran" AND "United States"` | `query_search` | `assigned` | `assigned_not_verified` |
| `RQ-A03` | `discovery_event` | en | `"Epic Fury" OR "Strait of Hormuz" OR Hormuz` | `query_search` | `assigned` | `assigned_not_verified` |

Source-scoped، Event-specific و Discovery سه مسیر جدا هستند. نتایج آن‌ها ابتدا جدا ممیزی می‌شوند و فقط پس از Deduplication با حفظ `matched_query_ids` قابل تجمیع‌اند.

## ۶. Queryهای YouTube

YouTube Boolean کامل را مانند X اجرا نمی‌کند. هر Query به‌صورت عبارت کوتاه و مستقل در Channelهای ثبت‌شده و مسیر جست‌وجوی عمومی اجرا می‌شود.

### ۶.۱ Queryهای عمومی تخصیص‌یافته

| ID | Original family | Analytical family | Lang | Assigned query | Assigned scope | Route | Status | Execution |
|---|---|---|---|---|---|---|---|---|
| `YQ-001` | Core conflict | `core_conflict` | en | `"Iran-US war" OR "US-Iran tensions" OR "Iran war"` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-002` | Military event | `military` | en | `Iran (airstrike OR "missile strike" OR "drone attack")` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-003` | Diplomacy | `diplomacy` | en | `(Iran OR "United States") (ceasefire OR negotiations)` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-005` | Humanitarian | `humanitarian` | en | `(Iran OR "Iran-US war") ("civilian casualties" OR "humanitarian crisis")` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-009` | Core conflict | `core_conflict` | fa | `"جنگ ایران و آمریکا" OR "تنش ایران و آمریکا"` | Approved FA channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-010` | Military event | `military` | fa | `ایران ("حمله هوایی" OR "حمله موشکی" OR "حمله پهپادی")` | Approved FA channels | `channel_scope` | `assigned` | `assigned_not_verified` |

### ۶.۲ Queryهای رویدادمحور YouTube

| ID | Original family | Analytical family | Lang | Assigned query | Assigned scope | Route | Status | Execution |
|---|---|---|---|---|---|---|---|---|
| `YQ-017` | Operation-specific | `event_specific_operation` | en | `"Epic Fury" OR "Operation Epic Fury"` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-018` | Hormuz | `event_specific_hormuz` | en | `Hormuz OR "Strait of Hormuz" (blockade OR closed OR shipping)` | Approved EN channels | `channel_scope` | `assigned` | `assigned_not_verified` |
| `YQ-019` | Hormuz | `event_specific_hormuz` | fa | `"تنگه هرمز" (بسته OR مسدود OR محاصره OR کشتیرانی)` | Approved FA channels | `channel_scope` | `assigned` | `assigned_not_verified` |

این رشته‌ها قرارداد تخصیص‌یافته را ثبت می‌کنند. چون YouTube Boolean کامل را تضمین نمی‌کند، `executed_query` باید از Collector یا Run log استخراج شود. وجود عبارت Boolean در Registry به‌تنهایی اثبات نمی‌کند که API آن را دقیقاً با همان منطق اجرا کرده است.

### ۶.۳ خلاصه تعداد مسیرهای تخصیص‌یافته

| Platform | General | Event-specific | Complementary discovery | جمع قابل ممیزی |
|---|---:|---:|---:|---:|
| X | 18 | 6 | 3 Hashtag route | 24 Query متنی + 3 مسیر Hashtag |
| Reddit | 16 | 2 | 3 `r/all` discovery route | 21 مسیر Query |
| YouTube | 6 | 3 | — | 9 Query |

تفاوت تعداد Query میان پلتفرم‌ها به معنی وزن آماری بیشتر یک پلتفرم نیست. تعداد رکورد، Coverage، Precision و ترکیب پلتفرم‌ها جداگانه گزارش می‌شود.

## ۷. قواعد اجرا

1. Window درخواست‌شده و Window بازیابی‌شده هر Run ثبت می‌شود.
2. Sort واقعی، Pagination، سقف و Quota در Run Manifest ثبت می‌شود.
3. یک محتوا با چند Query یک بار ذخیره و `matched_query_ids` آن حفظ می‌شود.
4. Query فارسی پیش از ارسال با نسخه ثبت‌شده Normalization هماهنگ می‌شود.
5. Query جدید فقط با نسخه جدید اضافه می‌شود.
6. اگر Query جدید برای همه هفته‌ها قابل Backfill نباشد، سهم آن در Composition گزارش و از Trend تأییدی جدا می‌شود.
7. Query آرشیوشده حذف فیزیکی نمی‌شود.

برای Runهای انجام‌شده، این قواعد به‌صورت Audit بررسی می‌شوند. عدم رعایت یا نامعلوم بودن یک قاعده ثبت می‌شود؛ داده مرتبط بدون بررسی موضوعی و کیفیت، خودکار دور ریخته نمی‌شود.

## ۸. ارزیابی Query

### Precision

برای هر `query_id` حداقل ۳۰ نتیجه تصادفی، در صورت وجود، بررسی می‌شود. پس از آن خلاصه در سطح Platform × Analytical family محاسبه می‌شود:

\[
Precision = \frac{Relevant\ retrieved}{Audited\ retrieved}
\]

Precision همراه با `n` و فاصله اطمینان Wilson گزارش می‌شود.

### Queryهای هم‌پوشان

برای زوج‌هایی مانند Actor-event/Bilateral-military و Economic-impact/Hormuz-and-energy چهار شاخص ساده گزارش می‌شود:

| شاخص | کاربرد |
|---|---|
| `returned_n` | تعداد نتیجه خام هر Query |
| `eligible_n` | تعداد نتیجه باقی‌مانده پس از Eligibility |
| `precision` | سهم نتایج مرتبط در نمونه ممیزی |
| `unique_eligible_n` | تعداد رکورد Eligible که Query دیگر بازیابی نکرده است |

Queryهای هم‌پوشان پیش از مشاهده این شاخص‌ها حذف نمی‌شوند. در Dataset، رکورد مشترک فقط یک بار نگهداری می‌شود و تمام شناسه‌های بازیابی‌کننده در `matched_query_ids` باقی می‌مانند. برای طراحی Collection آینده می‌توان Query دقیق‌تر را ترجیح داد، اما Registry تاریخی همچنان هر دو Query را حفظ می‌کند.

### بازیابی موارد شناخته‌شده

چند محتوای مرتبط که مستقل از Query و پیرامون Event Registry شناسایی شده‌اند، به‌عنوان Known-item set استفاده می‌شوند. سهم بازیابی‌شده یک شاخص تشخیصی Coverage است و Recall کل جامعه محسوب نمی‌شود.

### Composition

سهم Query family در هر هفته و پلتفرم محاسبه می‌شود. تغییر ناگهانی این سهم باید پیش از تفسیر Trend بررسی شود.

## ۹. Queryهای رویدادمحور

Queryهای رویدادمحور تخصیص‌یافته حذف یا با Queryهای عمومی ادغام نمی‌شوند. بااین‌حال، در تحلیل روند باید جداگانه قابل شناسایی باشند، زیرا نام یک عملیات یا توافق ممکن است فقط در بخشی از بازه قابل استفاده بوده باشد.

- اگر Log نشان دهد Query رویدادمحور روی کل بازه پروژه به‌صورت گذشته‌نگر اجرا شده است، پس از Deduplication می‌تواند وارد Dataset اصلی شود و `matched_query_ids` آن حفظ می‌شود.
- اگر فقط روی بخشی از بازه اجرا شده باشد، داده آن حذف نمی‌شود، اما سهم آن در Composition گزارش و تحلیل Trend تأییدی با و بدون آن مقایسه می‌شود.
- اگر زمان اجرای آن معلوم نباشد، وضعیت `unknown` می‌گیرد و تا تکمیل Audit مبنای ادعای Coverage کامل نیست.
- مقایسه Precision ابتدا در سطح `query_id` انجام می‌شود؛ جمع‌بندی در سطح `analytical_family` مرحله بعدی است.

## ۱۰. خروجی ممیزی

| query_id | platform | week | returned_n | eligible_n | precision_audit_n | precision | ci_low | ci_high | oldest_utc | newest_utc | errors |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
