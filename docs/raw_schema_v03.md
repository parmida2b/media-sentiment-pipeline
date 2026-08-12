> ⚠️ **وضعیت (۲۰۲۶-۰۸-۱۲):** سند هدفِ تیم برای قرارداد داده خام دیگه
> [`raw_schema_v05.md`](raw_schema_v05.md)‌ـه، نه این فایل — برای مستندسازی
> تصمیم‌های جدید یا داده‌ی تازه به اون سند رجوع کن.
>
> این فایل (v03) رو **پاک/جابه‌جا نکردیم** چون کد فعلی تیم (`config/schema.py`,
> `config/raw_schema_columns.py`, `src/ingestion/youtube_extract.py` و چند
> فایل دیگه) هنوز دقیقاً همین نسخه (v03) رو پیاده‌سازی می‌کنه، نه v05. یعنی این
> سند فعلاً تنها مرجع درستِ «کد الان واقعاً چی تولید می‌کنه»ست. وقتی migration
> کد به v05 انجام شد (طبق `docs/PROJECT_EXECUTION_ORDER_v1.md` مرحله ۴-۵ و
> `docs/legacy_data_intake_and_harmonization_plan_v1.md`)، این فایل باید به
> `docs/archive/` منتقل بشه.

# Raw Schema v03 (پیش‌نویس اصلاحی — بر پایه‌ی v02)

**پروژه:** تحلیل افکار عمومی جهانی درباره‌ی جنگ ایران–آمریکا
**بازه‌ی پروژه:** `2026-02-28` تا `2026-07-22` (W01–W21، W21 پنج‌روزه)
**وضعیت این فایل:** پیش‌نویس برای بازبینی مشترک — قبل از قفل‌شدن نهایی باید بین
هر سه نفر (X / Reddit / YouTube) و صاحب `schema.py` تأیید شود.

> این نسخه، `raw_schema_v02.md` (فرستاده‌شده توسط همکار) را اصلاح می‌کند. هر
> جا نسبت به v02 تغییری داده شده، با 🆕 علامت خورده و در جدول زیر دلیلش آمده.
> هر چیزی که 🆕 نخورده، همان قانون v02 است و بدون تغییر باقی مانده.

## تغییرات نسبت به v02 و چرایی‌شان

| # | تغییر | چرا |
|---|---|---|
| ۱ | §۰: روشن شد این سند قرارداد **فایل export نهایی** است، نه لزوماً فرمت کاری داخلی هر تیم. | v02 این را باز نگذاشته بود؛ کد فعلی YouTube به‌صورت JSONL کار می‌کند (برای resumability/dedup) و تبدیل آن به CSV تخت فقط در مرحله‌ی export منطقی‌تر از بازنویسی کل پایپ‌لاین حول CSV است. |
| ۲ | §۱۲ قاعده‌ی ۳: تمایز صریح بین «Eligibility Filter» (ممنوع در Collector) و «Quota-Triage Pre-filter» (مجاز، با شرط ثبت/audit) اضافه شد. | v02 فرض کرده بود Collector هیچ قضاوتی نمی‌کند، اما در عمل quota واقعی (۱۰هزار/روز YouTube) این را غیرممکن می‌کند. حذف کامل فیلتر یعنی سوزاندن quota روی ویدیوهای واضحاً نامرتبط — دقیقاً همان ریسکی که باگ fail-open در `geo_tagger.py` یک‌بار نشان داد. |
| ۳ | §۳: `sampling_applied`/`random_seed`/`items_kept` با یک فیلد جدید `sampling_method` (enum) بازتعریف شد؛ `random_seed` فقط وقتی `sampling_method=random` الزامی است. | v02 فرض می‌کرد سقف‌گذاری همیشه «نمونه‌گیری تصادفی» است. کد فعلی سقف ۳۰۰تایی را با «جدیدترین‌ها اول» (قطعی، نه تصادفی) اعمال می‌کند — این هم یک bias واقعی است که باید صادقانه مستند شود، نه این‌که وانمود کنیم seed دارد. |
| ۴ | §۶: `content_status` از 🟡 Important به 🟢 Ideal تنزل کرد؛ یادداشت هزینه اضافه شد. | تشخیص حذف/عدم‌دسترسی بعدی یک محتوا نیازمند revisit دوره‌ای کامنت‌های قبلاً دیده‌شده است — quota اضافه مصرف می‌کند و در v02 اصلاً به این هزینه اشاره نشده بود. |
| ۵ | §۶: `language_confidence` مجاز شد از یک heuristic مستند (نه فقط یک مدل احتمالاتی واقعی) بیاید. | تشخیص زبان فعلی (`detect_language`) بر پایه‌ی تشخیص اسکریپت (regex) است، نه یک مدل احتمالاتی؛ الزام به «اطمینان واقعی» بدون این یادداشت عملاً غیرقابل‌اجرا بود. |
| ۶ | §۱۰: بخش «قفل بازه» (Window Lock) اضافه شد. | v02 پایان بازه را ثابت فرض کرده بود، اما `config.yaml` فعلی `end: auto` دارد. باید مشخص شود از چه لحظه‌ای بازه قفل می‌شود و با داده‌ی جمع‌شده‌ی بعد از آن لحظه چه می‌شود. |
| ۷ | §۱۱: روشن شد فرمول دقیق ورودی هش (ترتیب/پیشوندهای رشته) می‌تواند بین تیم‌ها فرق کند، به‌شرط رعایت سه قاعده‌ی اصلی (env-var only, یک SALT مشترک، بدون PII خام). | فرمول فعلی `author_hash.py` (`channel_id:{salt}:{id}`) رشته‌ی دقیق مثال v02 (`{platform}:{author_id}:{SALT}`) را عیناً ندارد؛ این تفاوت بی‌ضرر است اگر SALT مشترک باشد — نباید تیم‌ها را مجبور به یکسان‌سازی بایت‌به‌بایت فرمول کند. |
| ۸ | §۱۳: دو ستون جدید `prefiltered_sources_count` و `prefiltered_sources_log_ref` اضافه شد. | محل واقعی برای audit کردن Quota-Triage Pre-filter (تغییر #۲) در فایل اجباری مانیفست. |

---

## ۰. قاعده‌ی حاکم

هر سه نفر (X، Reddit، YouTube) باید بتوانند از داده‌ی کاری داخلی خودشان، **یک
فایل CSV با ستون‌های یکسان** به‌عنوان خروجی نهایی/export تولید کنند.

- ستونی که در پلتفرم شما موجود نیست → **خالی بماند** (حذف نشود).
- اگر ستون‌ها یکی نباشند، ادعای «سه فایل منسجم» ممکن نیست.
- این سند Contract **خروجی export** Collector است؛ فرمت کاری داخلی (staging،
  مثلاً JSONL) هر تیم آزاد است، **به شرطی که یک مرحله‌ی export قطعی و
  تکرارپذیر** دقیقاً همین ستون‌ها را با همین نام/همین نوع تولید کند. 🆕
- Eligibility، Deduplication، Annotation و محاسبات بعدی در فایل‌های بعد انجام
  می‌شود. Collector فقط داده را جمع و ذخیره می‌کند؛ تصمیم «مرتبط بودن» یا
  «حذف» با آن نیست — به‌جز استثنای محدود Quota-Triage در §۱۲.۳. 🆕

---

## ۱. سه سطح اولویت ستون‌ها

| سطح | معنی | اگر نباشد |
| --- | --- | --- |
| 🔴 **Required** | بدون آن رکورد نامعتبر است | رکورد رد می‌شود |
| 🟡 **Important** | یک تحلیل مشخص از دست می‌رود | آن تحلیل حذف و در محدودیت‌ها ثبت می‌شود |
| 🟢 **Ideal** | کیفیت را بالا می‌برد | چیزی از دست نمی‌رود |

> **اگر وقت کم آوردید: فقط ۱۲ ستون 🔴 را کامل کنید.**

### ۱-۱. دوازده ستون Required

```
platform              created_at_utc        project_week        query_id
platform_content_id   collected_at_utc      in_window           collection_run_id
content_type           text_raw
                       author_hash
```

---

## ۲. Core — هویت و زمان 🔴

| Column | Type | توضیح |
| --- | --- | --- |
| `platform` | enum | `x` / `reddit` / `youtube` |
| `platform_content_id` | string | شناسه‌ی یکتای محتوا در پلتفرم. **کلید اصلی Dedup.** |
| `content_type` | enum | نوع محتوا (مقادیر مجاز در §۸) |
| `created_at_utc` | ISO 8601 | زمان انتشار محتوا به UTC با `Z`. **هرگز epoch نباشد.** |
| `collected_at_utc` | ISO 8601 | زمان دریافت این رکورد توسط Collector |
| `text_raw` | string | متن خام، **بدون هیچ تغییری** |
| `author_hash` | string | هش نویسنده (§۱۱) |
| `project_week` | string | `W01` تا `W21` یا `OUT` |
| `in_window` | bool | آیا داخل بازه‌ی `2026-02-28` تا `2026-07-22` است؟ |
| `is_partial_week` | bool | فقط برای `W21` برابر `true` (این هفته ۵ روزه است) |
| `query_id` | string | شناسه‌ی Query‌ای که این رکورد را پیدا کرده |
| `collection_run_id` | string | شناسه‌ی اجرای جمع‌آوری |

### ۲-۱. `platform_content_id` در هر پلتفرم

| پلتفرم | چه چیزی بگذارید |
| --- | --- |
| **X** | ID توییت / پست |
| **Reddit** | ID کامنت با پیشوند — مثل `t1_oz8fsm9` یا `t3_1v449es` |
| **YouTube** | ID کامنت |

---

## ۳. Source و Provenance

| Column | Type | سطح | توضیح |
| --- | --- | --- | --- |
| `source_id` | string | 🟡 | شناسه از Source Registry (مثل `RD-014` یا `YT-001`). اگر منبع خارج از Registry بود **خالی بماند**. |
| `source_container` | string | 🟡 | ظرف اصلی: نام Subreddit، Channel ID یوتیوب، یا منبع جست‌وجوی X |
| `source_container_id` | string | 🟢 | ID پلتفرمی ظرف |
| `source_parent_id` | string | 🟡 | ID والد مستقیم: Submission ردیت، Video یوتیوب، Conversation ایکس |
| `source_parent_title` | string | 🟡 | عنوان پست یا ویدئوی والد. **برای فهم معنای کامنت ضروری است.** |
| `parent_id` | string | 🟡 | ID والد در درخت پاسخ. برای محتوای سطح اول خالی است. |
| `query_version` | string | 🟡 | نسخه‌ی Query Registry (مثل `v3.0`) |
| `discovery_route` | enum | 🟡 | `query_search` / `source_scope` / `hashtag` |
| `matched_query_ids` | string | 🟡 | اگر یک محتوا با چند Query پیدا شد، همه‌ی IDها با جداکننده‌ی **`;`** |
| `collector_version` | string | 🟢 | نسخه‌ی کد Collector |
| `permalink_hash` | string | 🟢 | SHA-256 از لینک. **خود URL ذخیره نشود.** |
| `source_total_available` | int | 🟢 | تعداد کل آیتم‌های موجود قبل از اعمال سقف |
| `sampling_method` | enum | 🟡 | 🆕 `none` / `cap_newest_first` / `cap_oldest_first` / `random` / `systematic` — روش واقعی محدودکردن تعداد، نه فقط بله/خیر |
| `sampling_applied` | bool | 🟡 | آیا به‌خاطر سقف، محدودسازی اعمال شد؟ (`sampling_method != none`) |
| `items_kept` | int | 🟡 | تعداد نگه‌داشته‌شده بعد از سقف |
| `random_seed` | string | 🟡 | 🆕 فقط وقتی `sampling_method=random` الزامی است؛ برای `cap_newest_first`/`cap_oldest_first` خالی می‌ماند چون قطعی است نه تصادفی |

> ⚠️ **جداکننده‌ی `matched_query_ids` باید `;` باشد، نه `|`.**

### ۳-۱. سلسله‌مراتب منبع در ردیت

```
source_container     = r/geopolitics       ← Subreddit
source_parent_id     = t3_1v449es          ← خودِ پست (Submission)
parent_id            = t1_yyyyyyy          ← اگر پاسخ به کامنت باشد
platform_content_id  = t1_oz8fsm9          ← خود این رکورد
```

### ۳-۲. نگاشت برای یوتیوب 🆕

```
source_container     = Channel ID          ← کانال ویدیو
source_parent_id     = Video ID
source_parent_title  = عنوان ویدیو
parent_id            = ID کامنت سطح اول    ← اگر reply باشد
platform_content_id  = ID این کامنت/reply
```

---

## ۴. Engagement

| Column | Type | توضیح |
| --- | --- | --- |
| `engagement_score` | int | متریک اصلی: لایک X، score ردیت، لایک یوتیوب |
| `engagement_replies` | int | تعداد پاسخ / کامنت مستقیم |
| `engagement_shares` | int | ریتوییت / ریپست — فقط X |
| `engagement_quotes` | int | کوت‌توییت — فقط X |
| `engagement_views` | int | بازدید، اگر پلتفرم بدهد |
| `engagement_collected_at_utc` | ISO 8601 | **زمان خواندن اعداد تعامل** |

> **قاعده: Engagement فقط درون همان لحظه و همان پلتفرم مقایسه می‌شود.**

---

## ۵. Author

| Column | Type | سطح | توضیح |
| --- | --- | --- | --- |
| `author_hash` | string | 🔴 | هش نویسنده (الزامی — §۱۱) |
| `author_is_verified` | bool | 🟢 | نشان تأیید پلتفرم، اگر باشد |
| `author_follower_count` | int | 🟢 | تعداد دنبال‌کننده — عمدتاً فقط X |
| `author_account_age_days` | int | 🟢 | سن حساب به روز — عمدتاً فقط X |
| `author_is_submitter` | bool | 🟢 | ردیت: آیا نویسنده همان صاحب پست است؟ |
| `automation_risk_score` | float | 🟡 | امتیاز ۰ تا ۱ برای رفتار مشکوک به اتوماسیون. **فقط Flag است، نه ادعای هویت.** |

---

## ۶. Language و Status

| Column | Type | سطح | توضیح |
| --- | --- | --- | --- |
| `language_reported` | string | 🟢 | زبان گزارش‌شده توسط خود پلتفرم |
| `language_detected` | string | 🟡 | زبان تشخیص‌داده‌شده توسط ما: `en` / `fa` / `other` |
| `language_confidence` | float | 🟡 | اطمینان تشخیص (۰ تا ۱). 🆕 می‌تواند از یک مدل احتمالاتی واقعی یا از یک heuristic مستند (چند رده‌ی ثابت، مثلاً ۱٫۰/۰٫۷/۰٫۴ بر اساس قطعیت الگوی تشخیص) بیاید — روش دقیق باید در کد/مستندات ذکر شود. |
| `content_status` | enum | 🟢 🆕 (بود 🟡) | `active` / `deleted` / `removed` / `unavailable`. نیازمند revisit دوره‌ای محتوای قبلاً دیده‌شده است که quota اضافه مصرف می‌کند — اگر پیاده‌سازی شد، دوره‌ی revisit باید مستند شود؛ اگر نشد، این ستون خالی می‌ماند و به‌عنوان محدودیت شناخته‌شده ثبت می‌شود. |

- زبان‌های اصلی پروژه: `en` و `fa`.
- هر زبان دیگر → `other`. **حذف نشود، صرفاً گزارش شود.**
- **زبان متن ≠ کشور نویسنده.**

---

## ۷. Geography — اختیاری و اغلب خالی

| Column | Type | سطح | توضیح |
| --- | --- | --- | --- |
| `geo_method` | enum | 🟢 | روش استنباط مکان: `geotag`/`profile`/`timezone`/`text_place`/`source_community`/`language_weak` |
| `country_or_region` | string | 🟢 | کد کشور یا `unknown` |
| `geo_confidence` | enum | 🟢 | `high` / `medium` / `low` |
| `geo_granularity` | enum | 🟢 | `country` / `region` / `city` / `unknown` |
| `geo_limitations` | string | 🟢 | توضیح محدودیت روش |

- ردیت معمولاً هیچ داده‌ی مکانی ندارد → همه خالی.
- **انتظار واقع‌بینانه: ۸۵ تا ۹۵ درصد رکوردها `unknown` خواهند بود.**
- اگر پوشش جغرافیایی زیر ۱۰٪ ماند، تحلیل جغرافیایی از دامنه‌ی پروژه خارج و
  به‌عنوان محدودیت ثبت می‌شود.

---

## ۸. مقادیر مجاز `content_type`

```
original_post              پست اصلی X یا Submission ردیت
comment                    کامنت سطح اول
reply                      پاسخ به کامنت
quote                      کوت‌توییت دارای متن اضافه‌شده
repost                     بازنشر بدون متن  →  فقط Exposure Dataset
deleted_or_unavailable     محتوای حذف‌شده یا غیرقابل دسترسی
unknown                    نوع تعیین‌نشده
```

### ۸-۱. قاعده‌ی تعیین در هر پلتفرم

| پلتفرم | قاعده |
| --- | --- |
| **Reddit** | Submission → `original_post` · `parent_id` با `t3_` → `comment` · با `t1_` → `reply` |
| **YouTube** | کامنت سطح اول → `comment` · پاسخ → `reply` |
| **X** | پست معمولی → `original_post` · پاسخ → `reply` · کوت‌توییت با متن → `quote` · بازنشر بدون متن → `repost` |

---

## ۹. فیلدهایی که Collector نباید بسازد

این‌ها در فایل‌های بعدی (staging) ساخته می‌شوند:

```
char_count      word_count      hashtags        mentions
urls            project_day     depth           thread_path
days_from_event
```

> **Collector فقط داده‌ی خام و فیلدهای همین Schema را پر می‌کند.**

---

## ۱۰. تعریف هفته‌ی پروژه — یکسان برای هر سه نفر

```
شروع W01   :  2026-02-28 00:00:00 UTC
هر هفته    :  ۷ روز کامل
پایان بازه :  2026-07-22 23:59:59 UTC
W21        :  2026-07-18 تا 2026-07-22  →  ۵ روز (partial)
```

```python
from datetime import datetime, timezone

START = datetime(2026, 2, 28, tzinfo=timezone.utc)
END   = datetime(2026, 7, 22, 23, 59, 59, tzinfo=timezone.utc)

def project_week(ts):
    """returns (project_week, in_window, is_partial_week)"""
    if not (START <= ts <= END):
        return "OUT", False, False
    w = (ts - START).days // 7 + 1
    return f"W{w:02d}", True, (w == 21)
```

### ۱۰-۱. قفل بازه (Window Lock) 🆕

تا وقتی بازه‌ی پروژه رسماً قفل نشده، `config.yaml` هر تیم می‌تواند `end:
auto` داشته باشد (یعنی «تا همین الان») — این برای توسعه/تست لازم است. اما:

1. لحظه‌ای که تیم بازه‌ی نهایی را تصویب می‌کند (`2026-07-22 23:59:59 UTC` طبق
   این سند)، `END` باید به‌صورت یک مقدار **ثابت و صریح** در `config.yaml` هر
   سه Collector نوشته شود — نه `auto`.
2. هر رکوردی که پیش از قفل‌شدن، با `end: auto` جمع شده و تاریخ انتشارش بعد از
   `END` نهایی است، **حذف نمی‌شود** — فقط `project_week/in_window` آن باید
   یک‌بار به‌صورت گذشته‌نگر (retroactively) بازمحاسبه شود (`OUT`/`false`).
   کافی است تابع `project_week()` را روی داده‌ی موجود دوباره اجرا کنید؛ نیازی
   به جمع‌آوری مجدد نیست.
3. بعد از قفل‌شدن، جمع‌آوری داده‌ی جدید برای این پروژه (نه پروژه‌ی بعدی) باید
   متوقف شود — ادامه‌ی جمع‌آوری بعد از `END` قفل‌شده یعنی جامعه‌ی آماری در حال
   تعریف مجدد است، که باید یک تصمیم آگاهانه‌ی تیمی باشد، نه پیش‌فرض کد.

---

## ۱۱. SALT و `author_hash`

`SALT` یک رشته‌ی محرمانه و ثابت است که به ID نویسنده اضافه می‌شود تا هش
ساخته شود.

**چرا لازم است:**

اگر فقط `sha256(author_id)` را ذخیره کنید، کسی می‌تواند با حدس‌زدن IDها و
ساختن همان هش، هویت را برگرداند. با `SALT`، حتی با دانستن الگوریتم، بدون
دانستن `SALT` این کار ممکن نیست.

**قواعد:**

1. `SALT` از متغیر محیطی خوانده شود — **داخل کد سخت‌کد نشود.**
2. `SALT` برای کل پروژه **یکی** باشد (وگرنه یک نویسنده در سه پلتفرم سه هش
   متفاوت می‌گیرد).
3. نام کاربری یا ID خام **هرگز روی دیسک ذخیره نشود.**
4. 🆕 فرمول دقیق ساخت رشته‌ی ورودی هش (ترتیب فیلدها، جداکننده‌ها، پیشوندها)
   می‌تواند بین تیم‌ها/پلتفرم‌ها فرق کند — مثال زیر یک الگوی پیشنهادی است، نه
   یک قالب اجباری بایت‌به‌بایت. تنها الزام این است که ورودی هش شامل
   **پلتفرم + شناسه‌ی پایدار نویسنده + همان SALT مشترک پروژه** باشد، تا تصادم
   بین پلتفرم‌ها (قاعده‌ی ۲) رخ ندهد.

```python
import hashlib
import os

SALT = os.environ["PROJECT_AUTHOR_SALT"]   # یک رشته‌ی بلند تصادفی

author_hash = hashlib.sha256(
    f"{platform}:{author_id}:{SALT}".encode()
).hexdigest()
```

---

## ۱۲. قواعد اجباری Collector

1. `author_hash` **داخل Collector** ساخته شود، با `SALT`.
2. **متن را تمیز نکنید** → `text_raw` دست‌نخورده بماند.
3. **جداسازی Eligibility از Quota-Triage** 🆕:
   - **Eligibility Filter** (رد کردن یک رکورد *از قبل جمع‌شده* بر اساس محتوا
     یا مرتبط‌بودن آن) همچنان **ممنوع** است — این کار `eligibility_rules.md`
     است، نه Collector.
   - **Quota-Triage Pre-filter** (تصمیم به *صرف‌نکردن* quota برای کشف/فچ
     کامنت‌های یک منبع — مثلاً یک ویدیو — پیش از این‌که حتی یک رکورد از آن
     منبع وجود داشته باشد) **مجاز** است، فقط با رعایت هر سه شرط زیر:
     1. تصمیم در سطح **منبع** گرفته شود (مثلاً کل یک ویدیو)، هرگز در سطح یک
        رکورد/کامنت مجزا.
     2. هر منبعی که این‌طور رد شد، در فایل مانیفست (§۱۳) با شناسه، دلیل/امتیاز
        و timestamp ثبت شود — حتی اگر هیچ رکوردی از آن هرگز روی دیسک نیامده
        باشد. رد‌شدن بی‌اثر روی هیچ رکوردی، بی‌ادعا/غیرقابل‌audit نیست.
     3. نرخ خطای این پیش‌فیلتر (چند منبع مرتبط اشتباهاً رد شده) باید دوره‌ای
        بازبینی و در مستندات پروژه گزارش شود.
4. **رکورد خارج از بازه را نگه دارید** و `in_window = false` بگذارید — اگر
   یک رکورد در پاسخ API از قبل دریافت شده، دور انداختن آن مجاز نیست. این
   قاعده به معنای جست‌وجوی نامحدود به عقب/جلو نیست — فقط یعنی هر چه *واقعاً
   فچ شده*، باید ذخیره شود، نه فیلتر.
5. مرتب‌سازی **هرگز** `top` یا `relevance` نباشد → فقط `new` / `recent` /
   `time`.
6. خطای باعث توقف کل اجرا، در Manifest ثبت شود.
7. تاریخ‌ها همیشه **رشته‌ی ISO با `Z`**.
8. اگر سقفی بر تعداد آیتم اعمال شد: `sampling_applied=true`،
   `sampling_method` (🆕 مطابق §۳)، و `items_kept` پر شود. `random_seed` فقط
   وقتی `sampling_method=random` الزامی است.

---

## ۱۳. فایل دوم — لاگ اجرا (اجباری)

> **بدون این فایل، داده‌ی خام قابل دفاع نیست.**

**نام فایل:** `{platform}_runs.csv` · **یک سطر برای هر ترکیب (Query × هفته)**

| Column | توضیح |
| --- | --- |
| `collection_run_id` | شناسه‌ی یکتای این اجرا |
| `platform` | `x` / `reddit` / `youtube` |
| `query_id` | شناسه‌ی Query |
| `query_text` | متن دقیق Query اجراشده |
| `query_version` | نسخه‌ی Registry |
| `project_week` | هفته‌ی هدف |
| `discovery_route` | `query_search` / `source_scope` / `hashtag` |
| `source_id` | اگر source-scoped بوده |
| `sort_mode` | **باید `new` یا `recent` یا `time` باشد** |
| `started_at_utc` | شروع اجرا |
| `finished_at_utc` | پایان اجرا |
| `returned_count` | تعداد برگشتی از پلتفرم |
| `stored_count` | تعداد نوشته‌شده روی دیسک |
| `records_in_window` | تعداد داخل بازه |
| `sampling_cap` | سقف اعلام‌شده (مثلاً ۳۰۰) |
| `records_sampled_out` | تعداد کنارگذاشته‌شده به‌خاطر سقف |
| `oldest_record_utc` | قدیمی‌ترین رکورد این اجرا |
| `newest_record_utc` | جدیدترین رکورد این اجرا |
| `quota_consumed` | واحد Quota مصرف‌شده، اگر معلوم باشد |
| `error_count` | تعداد خطا |
| `prefiltered_sources_count` | 🆕 تعداد منابعی (مثلاً ویدیو) که با Quota-Triage Pre-filter (§۱۲.۳) رد شدند، بدون این‌که هرگز فچ شوند |
| `prefiltered_sources_log_ref` | 🆕 مسیر/شناسه‌ی فایل جزئیات آن رد‌شدن‌ها (id منبع + دلیل/امتیاز + timestamp) |
| `notes` | توضیحات آزاد |

> `sort_mode` و `oldest_record_utc` مهم‌ترین دو ستون این فایل‌اند: اولی ثابت
> می‌کند قاعده‌ی مرتب‌سازی رعایت شده، دومی ثابت می‌کند دسترسی تاریخی واقعاً
> کار کرده.
