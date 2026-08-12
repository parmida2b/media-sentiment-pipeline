# رجیستری منابع

**پلتفرم‌ها:** X، Reddit و YouTube  
**بازه:** `2026-02-28` تا `2026-07-22`

---

## ۱. نقش Registry

این سند منابع مجاز، نقش آن‌ها و ریسک انتخاب را ثبت می‌کند. Source Registry فهرست کامل کاربران یا محتوای هیچ پلتفرمی نیست.

فهرست‌های زیر منابع مرجع یا برنامه‌ریزی‌شده‌اند. وجود نام در این سند اثبات نمی‌کند که همکار مربوطه از آن Source داده گرفته است. Sourceهای واقعاً مشاهده‌شده پس از تحویل داده در `observed_source_registry.csv` از روی ID، URL/Metadata مجاز، کد و Log ثبت می‌شوند.

| پلتفرم | نقش Registry | Discovery اصلی |
|---|---|---|
| X | Seed account و Search scope | Query-first |
| Reddit | Subreddit و مسیر کشف | Query search + Source-scoped |
| YouTube | Channel و Video parent | Channel/Query → Video → Comment |

## ۲. فیلدهای اجباری

| فیلد | تعریف |
|---|---|
| `source_id` | شناسه پایدار |
| `platform` | x/reddit/youtube |
| `source_name` | نام نمایشی |
| `platform_source_id` | ID واقعی پلتفرم |
| `category` | دسته تحلیلی |
| `primary_language` | زبان اصلی |
| `role` | discovery/opinion_parent/context_only |
| `selection_risk` | ریسک اصلی |
| `status` | planned/active/restricted/archived/unavailable |
| `verified_at_utc` | آخرین بررسی |
| `verification_method` | API/manual/official page |
| `notes` | توضیح ضروری |
| `observation_status` | planned/observed_verified/observed_reconstructed/unknown |
| `evidence_source` | raw_field/run_log/collector_code/teammate_note/unknown |

Source فقط پس از تکمیل `platform_source_id` و `verified_at_utc` به `active` تغییر می‌کند.

## ۳. X — Seed accounts

Seed account برای کشف رویداد، واژگان و Conversation استفاده می‌شود. Timeline آن به‌تنهایی Opinion Dataset عمومی نیست.

| ID | Source | Category | Lang | Role | Risk | Status |
|---|---|---|---|---|---|---|
| `XS01` | Reuters | global_wire | en | discovery | news agenda | planned |
| `XS02` | Associated Press | global_wire | en | discovery | breaking-news agenda | planned |
| `XS03` | BBC World | public_broadcaster | en | discovery | institutional framing | planned |
| `XS04` | Al Jazeera English | regional_media | en | discovery | regional framing | planned |
| `XS05` | United Nations | official_international | en | event context | official communication | planned |
| `XS06` | IAEA | official_international | en | event context | nuclear-policy focus | planned |
| `XS07` | US State Department | government | en | event context | official US position | planned |
| `XS08` | Iran UN Mission | government | en | event context | official Iranian position | planned |
| `XS09` | BBC Persian | persian_media | fa | discovery | diaspora audience | planned |
| `XS10` | VOA Farsi | persian_media | fa | discovery | US-funded broadcaster | planned |

حساب‌های رسمی و رسانه‌ای با `author_type` جدا می‌شوند. نتیجه عمومی با و بدون آن‌ها گزارش می‌شود.

## ۴. Reddit — Source candidates

مسیر Query search می‌تواند Submission خارج از این فهرست پیدا کند. در آن حالت Source جدید با Status مناسب ثبت می‌شود؛ ID حدس زده نمی‌شود.

| ID | Subreddit | Category | Lang | Risk | Status |
|---|---|---|---|---|---|
| `RD01` | r/worldnews | general_news | en | news-link and moderation bias | planned |
| `RD02` | r/geopolitics | geopolitics | en | self-selected expertise | planned |
| `RD03` | r/politics | us_politics | en | US partisan composition | planned |
| `RD04` | r/PoliticalDiscussion | political_discussion | en | high-effort users | planned |
| `RD05` | r/iran | iran_focused | en/fa | diaspora and moderation effects | planned |
| `RD06` | r/NewIran | iran_focused | en/fa | opposition-oriented selection | planned |
| `RD07` | r/ProIran | iran_focused | en/fa | pro-government selection | planned |
| `RD08` | r/MiddleEast | regional | en | regional composition | planned |
| `RD09` | r/AskMiddleEast | regional | en | highly self-selected | planned |
| `RD10` | r/Israel | israel_focused | en | national-community selection | planned |
| `RD11` | r/CredibleDefense | military | en | specialist audience | planned |
| `RD12` | r/CombatFootage | military | en | visual and sensational content | planned |
| `RD13` | r/energy | energy | en | sector-specialist audience | planned |
| `RD14` | r/oil | energy | en | industry/investor audience | planned |
| `RD15` | r/Economics | economics | en | economics-oriented audience | planned |

وجود، دسترسی عمومی و نام دقیق هر Subreddit پیش از Active شدن بررسی می‌شود.

## ۵. YouTube — Channel candidates

تنوع Channel برای پوشش رسانه‌های بین‌المللی، منطقه‌ای، مالی و فارسی در نظر گرفته شده است.

| ID | Channel | Category | Lang | Risk | Status |
|---|---|---|---|---|---|
| `YT01` | Reuters | global_wire | en | wire-news agenda | planned |
| `YT02` | Associated Press | global_wire | en | breaking-news agenda | planned |
| `YT03` | BBC News | public_broadcaster | en | institutional framing | planned |
| `YT04` | Al Jazeera English | regional_media | en | regional framing | planned |
| `YT05` | CNN | us_commercial | en | US cable audience | planned |
| `YT06` | Fox News | us_commercial | en | US partisan audience | planned |
| `YT07` | Bloomberg Television | financial_media | en | market-oriented audience | planned |
| `YT08` | TRT World | international_media | en | state-linked framing | planned |
| `YT09` | BBC Persian | persian_media | fa | diaspora audience | planned |
| `YT10` | Iran International | persian_media | fa | opposition-associated audience | planned |
| `YT11` | VOA Farsi | persian_media | fa | US-funded broadcaster | planned |
| `YT12` | DW Persian | persian_media | fa | European public broadcaster | planned |

نام Channel برای Collection کافی نیست. `channel_id` واقعی باید از صفحه رسمی یا API تأیید و در Registry داده‌ای ذخیره شود.

## ۶. قواعد Active شدن

برای هر Source:

1. Source عمومی و قابل دسترسی باشد؛
2. ID واقعی پلتفرم تأیید شود؛
3. Category، Language و Risk ثبت شود؛
4. یک Pilot محدود اجرا شود؛
5. حداقل یک رکورد با Timestamp معتبر بازیابی شود؛
6. Sort، Pagination و محدودیت دسترسی در Run Manifest ثبت شود؛
7. `verified_at_utc` تکمیل شود.

## ۷. قواعد جمع‌آوری

### X

- Query-first و Recent/Latest در صورت پشتیبانی مسیر دسترسی؛
- Seed account فقط Discovery/Context؛
- Repost بدون متن فقط `audit_only`؛
- نوع Reply/Quote/Repost حفظ شود.

### Reddit

- Sort واقعی و رفتار Comment retrieval ثبت شود؛
- Submission و Comment/Reply با Parent ID حفظ شوند؛
- اگر Cap اعمال شد، Sampling method و Seed ثبت شود؛
- Top/Hot/Best مبنای نمونه اصلی نیست.

### YouTube

- Video با Channel ID و Query ثبت‌شده کشف شود؛
- تاریخ خود Comment مبنای Project Week است؛
- ترتیب واقعی Comment و Pagination ثبت شود؛
- Quota مصرف‌شده و Videoهای ردشده در Audit نگهداری شوند.

## ۸. تحلیل ترکیب Source

برای هر Platform × Week محاسبه می‌شود:

- تعداد رکورد هر Source
- سهم هر Source
- سهم بزرگ‌ترین Source
- تعداد Source فعال
- HHI سهم Sourceها
- تعداد Parentهای یکتا

اگر یک Source یا Parent غالب باشد، نتیجه با حذف آن در Sensitivity Analysis تکرار می‌شود.

## ۹. مقایسه و وزن‌دهی

1. هر پلتفرم ابتدا جداگانه تحلیل می‌شود.
2. Sourceها وزن نمایندگی جمعیتی ندارند.
3. Engagement وزن اصلی نیست.
4. تجمیع مشاهده‌شده با حفظ `platform` گزارش می‌شود.
5. Equal-platform weighting فقط حساسیت است.
6. Restricted source در تحلیل اصلی ادغام نمی‌شود و در تحلیل جداگانه گزارش می‌شود.

## ۱۰. Coverage report

| platform | source_id | weeks_requested | weeks_with_data | raw_n | eligible_n | oldest_utc | newest_utc | largest_week_share | status |
|---|---|---:|---:|---:|---:|---|---|---:|---|

این جدول پوشش عملی Collection را نشان می‌دهد و نرخ پوشش کل جامعه محسوب نمی‌شود.

برای داده موجود، Coverage از حداقل و حداکثر Timestamp مشاهده‌شده و شمار رکورد هر هفته محاسبه می‌شود. `weeks_requested` فقط وقتی پر می‌شود که Window درخواست‌شده در Log یا تنظیمات Collector وجود داشته باشد؛ در غیر این صورت `unknown` است.

## ۱۱. تغییرات Registry

هر تغییر Status یا افزودن Source با تاریخ و دلیل ثبت می‌شود. اگر Source در میانه بازه اضافه شود و Backfill کامل ممکن نباشد، اثر آن بر Composition گزارش و از تحلیل تأییدی روند جدا می‌شود.

## ۱۲. منابع رسمی

- X Developer Platform: <https://docs.x.com/>
- Reddit Data API Terms: <https://redditinc.com/policies/data-api-terms>
- Reddit Developer Terms: <https://redditinc.com/policies/developer-terms>
- YouTube Data API: <https://developers.google.com/youtube/v3>
- YouTube Quota Costs: <https://developers.google.com/youtube/v3/determine_quota_cost>
