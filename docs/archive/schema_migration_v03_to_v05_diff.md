# Diff تحلیلی: Schema v03 (کد فعلی) → v05 (سند هدف)

> ⚠️ **این یک سند تحلیلی/پیشنهادی است، نه تصمیم نهایی و نه تغییر کد.**
> `config/schema.py` و `config/raw_schema_columns.py` در این سند **ویرایش
> نشده‌اند**. هدف فقط فهرست دقیق تفاوت‌هاست تا تیم قبل از هر migration واقعی
> روی آن تصمیم بگیرد. منابع مقایسه:
>
> - مبدأ (چیزی که کد **الان واقعاً پیاده می‌کند**): [`docs/raw_schema_v03.md`](raw_schema_v03.md) +
>   [`config/schema.py`](../config/schema.py) + [`config/raw_schema_columns.py`](../config/raw_schema_columns.py)
> - مقصد (چیزی که تیم **هدف گذاشته**): [`docs/raw_schema_v05.md`](raw_schema_v05.md) +
>   [`docs/legacy_data_intake_and_harmonization_plan_v1.md`](legacy_data_intake_and_harmonization_plan_v1.md)

---

## ۰. خلاصه اجرایی

1. **۱۱ ستون کاملاً جدید** در v05 اضافه شده‌اند که نه در `raw_schema_columns.py`
   هستند نه در `Record` — بیشترشان بخش تازه‌ی §۴.۱ («ممیزی داده تاریخی») است و
   مستقیماً برای پروژه‌ی داده‌های Legacy سه همکار لازم‌اند.
2. **۵ ستون از v03 عملاً از لایه Raw حذف و به Manifest سطح-Run منتقل شده‌اند**
   (`source_total_available`, `sampling_method`, `sampling_applied`,
   `items_kept`, `random_seed`) — یعنی دیگر per-record نیستند.
3. **۵ ستون دیگر از v03 در جدول‌های v05 اصلاً دیده نمی‌شوند**
   (`author_follower_count`, `author_is_submitter`, `automation_risk_score`,
   `geo_granularity`, `geo_limitations`) — باید تیم تصمیم بگیرد حذف عمدی
   بوده یا سهو سند.
4. **سطح الزام (`Required`/`Conditional`/`Optional`) دو فیلد کلیدی معکوس
   شده**: `query_id` از Required به Conditional تنزل کرده، `collector_version`
   از Ideal به Required ترفیع گرفته. این‌ها روی هر ولیدیشنی که روی سطح فیلد
   تکیه می‌کند اثر مستقیم دارد.
5. **مسیر فایل خروجی از یک لایه (`data/raw/{platform}/...`, JSONL/CSV) به یک
   پایپ‌لاین چهار/پنج‌لایه (`raw_original` → `raw_harmonized` → `interim` →
   `processed`, عمدتاً Parquet) تغییر کرده** — دو پوشه‌ی `data/raw_original/`
   و `data/raw_harmonized/` هنوز در ریپو وجود ندارند.
6. **ناسازگاری مستقل از v03/v05**: `config/schema.py` (فرمت داخلی `Record`)
   از قبل با `config/raw_schema_columns.py` (قرارداد export نهایی) هم‌نام
   نیست (`text` در برابر `text_raw`، `date` در برابر `created_at_utc`، ...).
   این تفاوت به v05 ربطی ندارد اما هر migration باید آن را هم حل کند —
   جزئیات در بخش ۶.

---

## ۱. فیلدهایی که اسم/نوع/سطح‌شان عوض شده

| فیلد (v03) | در v03 | در v05 | نوع تغییر |
|---|---|---|---|
| `query_id` | §۲ Core، سطح 🔴 Required (یکی از ۱۲ ستون اجباری §۱-۱) | §۴ Provenance، سطح **Conditional** | ⬇️ تنزل سطح الزام |
| `collector_version` | §۳ Source/Provenance، سطح 🟢 Ideal | §۳ Core، سطح **Required** | ⬆️ ترفیع سطح الزام + جابه‌جایی به Core |
| `author_hash` | یکی از ۱۲ ستون 🔴 Required (§۱-۱) و هم‌زمان در جدول §۵ | §۵ Author & Privacy، سطح **Conditional** | ⬇️ تنزل سطح الزام |
| `content_status` | §۶، سطح 🟢 Ideal (خودش قبلاً در v02→v03 از 🟡 تنزل کرده بود) | §۷، سطح **Optional** | بدون تغییر معنایی (فقط اسم سطح) |
| `geo_method` مقادیر مجاز | `geotag`/`profile`/`timezone`/`text_place`/`source_community`/`language_weak` (۶ مقدار) | `geotag`/`profile`/`self_reported`/`other` (۴ مقدار) | 🔁 enum بازتعریف/جمع‌شده — `timezone`, `text_place`, `source_community`, `language_weak` دیگر مقدار مجاز مستقل نیستند |
| `created_at_utc` / `collected_at_utc` نوع | `ISO 8601` (رشته) | `datetime UTC` | نوع نمایش تغییر کرده؛ اگر خروجی واقعاً Parquet شود روی نوع ستون (`string` در برابر `timestamp`) اثر می‌گذارد |
| `content_type` مقادیر مجاز | ۷ مقدار (بدون `video_context`) | ۸ مقدار، **+ `video_context`** برای YouTube video metadata (§۸) | ➕ مقدار enum جدید اضافه شده (نه ستون جدید) |
| سطح‌بندی فیلد (رده‌بندی خودش) | 🔴 Required / 🟡 Important / 🟢 Ideal — «Important» یعنی «یک تحلیل مشخص از دست می‌رود» | Required / **Conditional** / Optional — «Conditional» یعنی «اگر قابلیت پلتفرم وجود دارد، الزامی است» | تغییر تعریف، نه فقط اسم — معیار تصمیم برای هر فیلد باید دوباره از صفر خوانده شود |
| `sampling_method` | §۳ سطح رکورد (🟡)، فقط بین چهار مقدار enum فرض تلویحی «سقف = تصادفی» را رد می‌کرد | از رکورد حذف و به‌عنوان فیلد **سطح Manifest** بازتعریف شده (§۱۲) | 🔀 جابه‌جایی گرانولاریتی (per-record → per-run)؛ جزئیات در بخش ۲ و ۳ |
| `quota_consumed` (نام Manifest v03 §۱۳) | عدد واحد Quota مصرف‌شده | در v05 §۱۲ با نام **`quota_or_rate_limit_events`** | 🔁 تغییر نام + تغییر معنا (از «واحد مصرفی» به «رویداد محدودیت مشاهده‌شده») |

---

## ۲. فیلدهای کاملاً جدید در v05 (در v03/`raw_schema_columns.py` وجود ندارند)

### ۲.۱ بخش تازه §۴.۱ — «فیلدهای ممیزی داده تاریخی» (کل بخش جدید است)

| Column | Type | تعریف |
|---|---|---|
| `original_file_name` | string | نام فایل تحویلی همکار |
| `original_file_sha256` | string | Hash فایل پیش از هر تبدیل |
| `original_row_number` | int | شماره ردیف در فایل اصلی |
| `source_schema_version` | string | نسخه Schema داده‌شده به همکار، یا `unknown` |
| `source_query_registry_version` | string | نسخه Query Registry داده‌شده، یا `unknown` |
| `record_uid` | string | کلید داخلی قطعی (وقتی `platform_content_id` مبدأ ندارد) |
| `id_origin` | string | `observed` / `derived_row_key` |
| `timestamp_origin` | string | `observed` / `parsed_from_source` / `unknown` |
| `provenance_quality` | string | `complete` / `reconstructed` / `partial` / `unknown` |
| `field_origin` | string/json | منشأ فیلدهای بازسازی‌شده |
| `missing_reason` | string/json | علت فیلدهای مهم ناموجود |

این بخش مستقیماً برای جریان `docs/legacy_data_intake_and_harmonization_plan_v1.md`
لازم است (بازسازی Provenance داده‌های تاریخی سه همکار)، نه برای Collector
زنده — نکته‌ای که هنگام تصمیم‌گیری «همه‌ی این فیلدها را به `Record` اضافه
کنیم یا فقط به لایه Harmonization» باید در نظر گرفته شود.

### ۲.۲ خارج از §۴.۱

| Column | بخش v05 | Type | Level | تعریف |
|---|---|---|---|---|
| `schema_version` | §۳ Core | string | **Required** | مقدار ثابت `5.0`؛ نسخه‌ی قرارداد خروجی هماهنگ‌شده (نه لزوماً نسخه‌ای که Collector از ابتدا اجرا کرده — آن در `source_schema_version` است) |
| `source_registry_version` | §۴ Provenance | string | Conditional | نسخه Source Registry — معادلی برای `query_version` اما مخصوص Source |
| `author_id_status` | §۵ Author | string | Conditional | `available`/`deleted`/`unavailable`/`not_provided` |
| `author_type` | §۵ Author | string | Optional | `ordinary`/`media`/`official`/`organization`/`unknown` |

### ۲.۳ نکته باز — `language_method`

در متن نثر §۷ (نه در جدول ستون‌ها) آمده: «مقدار ساختگی Confidence برای روش
Rule-based ثبت نمی‌شود؛ در آن حالت `language_method` و نتیجه Rule نگهداری
می‌شود.» یعنی سند از فیلدی به نام `language_method` استفاده کرده بدون این‌که
آن را در جدول §۷ تعریف کند — مشابه دقیقاً همان الگویی که در v03 برای
`content_status` وجود داشت. **این باید قبل از قفل‌شدن v05 با نویسنده سند
شفاف‌سازی شود**، وگرنه Collectorها معنای دقیق آن را حدس می‌زنند.

---

## ۳. فیلدهایی که از لایه Raw (v03) در v05 دیگر دیده نمی‌شوند

### ۳.۱ منتقل‌شده به Collection Manifest (سطح Run، نه سطح رکورد)

| فیلد v03 (per-record، `raw_schema_columns.py` §۳) | وضعیت در v05 |
|---|---|
| `source_total_available` | در §۴/§۵ رکورد نیست؛ معادل مفهومی نزدیک در Manifest §۱۲ نیامده (باید احتمالاً از `pages_received`/`returned_count` استنتاج شود) |
| `sampling_method` | Manifest §۱۲، سطح Run |
| `sampling_applied` | در v05 حذف شده؛ معادلش این است که `sampling_method != none` |
| `items_kept` | نزدیک‌ترین معادل در Manifest §۱۲: `stored_count` (اما دقیقاً هم‌معنا نیست) |
| `random_seed` | Manifest §۱۲، سطح Run، فقط وقتی `sampling_method=random` |

نتیجه عملی: در v05 دیگر نمی‌شود از خودِ رکورد فهمید آیا آن رکورد خاص قربانی
Sampling/Cap بوده یا نه — این اطلاعات فقط در سطح `collection_run_id` در
Manifest موجود است، نه per-record.

### ۳.۲ در هیچ‌کدام از بخش‌های v05 دیده نمی‌شوند (نه Manifest، نه رکورد)

| فیلد v03 | جدول/سطح v03 | ملاحظه |
|---|---|---|
| `author_follower_count` | §۵ Author، 🟢 Ideal | در جدول §۵ سند v05 نیست |
| `author_is_submitter` | §۵ Author، 🟢 Ideal | در جدول §۵ سند v05 نیست (خاص Reddit) |
| `automation_risk_score` | §۵ Author، 🟡 Important | v05 صراحتاً آن را در §۱۱ «فیلدهای مشتق‌شده — در Raw ساخته نمی‌شوند» فهرست کرده؛ یعنی از Raw به لایه Processed منتقل شده، نه حذف کامل از پروژه |
| `geo_granularity` | §۷ Geography، 🟢 Ideal | در جدول §۷ سند v05 نیست |
| `geo_limitations` | §۷ Geography، 🟢 Ideal | در جدول §۷ سند v05 نیست |

⚠️ سند v05 توضیح صریحی برای حذف این ۴ مورد اول (غیر از `automation_risk_score`
که مقصدش مشخص است) نمی‌دهد — ممکن است سهو نگارشی سند باشد، نه تصمیم عمدی.
پیشنهاد: قبل از قفل نهایی v05 از نویسنده تأیید گرفته شود.

### ۳.۳ Manifest v03 (§۱۳) در برابر Manifest v05 (§۱۲)

| ستون Manifest v03 | معادل در v05 | تغییر |
|---|---|---|
| `query_text` | — | در v05 نیست |
| `records_in_window` | — | در v05 نیست |
| `sampling_cap` | `sampling_cap` | بدون تغییر |
| `records_sampled_out` | — | در v05 نیست (شاید از `returned_count - stored_count` استنتاج شود) |
| `quota_consumed` | `quota_or_rate_limit_events` | تغییر نام + معنا (بخش ۱) |
| `prefiltered_sources_count` | — | در v05 نیست |
| `prefiltered_sources_log_ref` | — | در v05 نیست |
| — | `requested_start_utc`, `requested_end_utc` | ➕ جدید (Window درخواستی، مجزا از `started_at_utc`/`finished_at_utc` واقعی) |
| — | `pages_requested`, `pages_received` | ➕ جدید (Pagination) |
| — | `error_types` | ➕ جدید، در کنار `error_count` |
| — | `known_gap` | ➕ جدید |

⚠️ حذف `prefiltered_sources_count`/`prefiltered_sources_log_ref` قابل توجه
است: این دو ستون در v03 §۱۲.۳ برای Audit کردن Quota-Triage Pre-filter اضافه
شده بودند (تصمیم به «کشف نکردن» یک منبع پیش از فچ اولین رکورد). اگر این
مکانیزم هنوز در Collectorهای فعال (`youtube_extract.py`) استفاده می‌شود،
حذف این دو ستون از Manifest یعنی از دست رفتن Audit trail آن — نکته‌ای که
باید صریحاً در تصمیم migration بررسی شود.

---

## ۴. مسیر فایل: از تک‌لایه فعلی به پایپ‌لاین چندلایه v05

### ۴.۱ چیزی که کد الان واقعاً می‌نویسد

| مسیر | تولیدکننده | فرمت |
|---|---|---|
| `data/raw/youtube/{topic_id}/youtube_comments_v2.jsonl` | `src/ingestion/youtube_extract.py` | JSONL |
| `data/raw/youtube/{topic_id}/youtube_raw_export.csv` | همان | CSV |
| `data/raw/youtube/{topic_id}/youtube_runs.csv` | همان (Manifest) | CSV |
| `data/raw/reddit/parent_posts/...` | `src/ingestion/reddit_parent_post_collector.py` | CSV/JSON (بر اساس کد) |

هیچ تفکیکی بین «فایل اصلی دست‌نخورده» و «خروجی هماهنگ‌شده» وجود ندارد — یک
پوشه (`data/raw/{platform}/...`) هم نقش Original و هم نقش کاری/خروجی نهایی را
هم‌زمان بازی می‌کند. پوشه‌های `data/interim/` و `data/processed/` از قبل در
ریپو هستند (برای مراحل بعدی pipeline) اما `data/raw_original/`،
`data/raw_harmonized/`، `data/manifests/` و `data/audits/` **در حال حاضر در
ریپو وجود ندارند.**

### ۴.۲ ساختار پیشنهادی v05 (§۱۴)

```text
data/raw/{platform}/{collection_run_id}.parquet          ← Collector زنده (فرمت جدید: Parquet)
data/raw_original/{platform}/{original_file_name}        ← 🆕 فایل دریافتی همکار، بدون تغییر، Read-only
data/raw_harmonized/{platform}/{original_file_stem}.parquet  ← 🆕 خروجی Mapping (نگاشت نام/نوع ستون، بدون Cleaning متن)
data/manifests/{platform}_runs.csv                        ← 🆕 پوشه اختصاصی (قبلاً کنار خود raw بود)
data/audits/raw_validation.csv                            ← 🆕
data/interim/eligible_content.parquet                     ← از قبل هست، خروجی جدید داخلش
data/interim/context_only.parquet                         ← جدید در این پوشه
data/audits/audit_only.parquet                             ← 🆕
data/processed/opinion_main.parquet                        ← از قبل هست، خروجی جدید داخلش
```

### ۴.۳ تغییرات کلیدی مسیر

| جنبه | v03 / کد فعلی | v05 |
|---|---|---|
| فرمت اصلی | JSONL (کار) + CSV (export) | Parquet (اصلی)؛ CSV فقط برای تبادل/بازبینی |
| تفکیک Original در برابر Harmonized | ندارد — یک پوشه | **دارد** — `raw_original/` (Read-only) در برابر `raw_harmonized/` (نگاشت‌شده) |
| محل Manifest | کنار داده خام، در `data/raw/{platform}/{topic}/` | پوشه مجزا `data/manifests/` |
| محل نتایج Validation | ندارد به‌صورت مجزا | پوشه مجزا `data/audits/` (`raw_validation.csv`, `audit_only.parquet`) |
| نام‌گذاری فایل خام زنده | `{topic_id}/youtube_comments_v2.jsonl` (نام ثابت دستی) | `{platform}/{collection_run_id}.parquet` (نام مبتنی بر Run ID) |

این دقیقاً همان تغییری است که کاربر در درخواست اشاره کرد
(«`data/raw/...` به `data/raw_harmonized/...`»): مسیر قبلی که هم Original و
هم خروجی را در یک پوشه نگه می‌داشت، در v05 به سه پوشه مجزا با نقش صریح تقسیم
می‌شود، و این تفکیک مشخصاً برای جریان داده‌های Legacy سه همکار
(`legacy_data_intake_and_harmonization_plan_v1.md` §۳–§۵) طراحی شده — نه برای
Collectorهای زنده‌ی فعلی که خودشان مستقیماً v05 را Native تولید می‌کنند.

---

## ۵. جمع‌بندی سطح فایل (چه کسی الان چه‌چیزی پیاده می‌کند)

| مؤلفه | نسخه‌ای که واقعاً پیاده‌سازی شده |
|---|---|
| `docs/raw_schema_v03.md` | مرجع فعلی — طبق هدر خودِ فایل، تنها سند درست «کد الان چی تولید می‌کند» |
| `config/raw_schema_columns.py` | v03 (کامنت بالای فایل صراحتاً `raw_schema_v03.md` را رفرنس می‌دهد) |
| `config/schema.py` | افزایشی روی v03، اما با نام‌گذاری داخلی متفاوت (بخش ۶) |
| `src/ingestion/youtube_extract.py` | v03 + `source_registry_v3.md` (طبق `decision_log.md`، ردیف ۲۰۲۶-۰۸-۰۷) |
| `docs/raw_schema_v05.md` | هدف — هنوز در هیچ کد Collector پیاده نشده |

---

## ۶. یافته جانبی (مستقل از v03/v05): ناسازگاری نام‌گذاری داخل خودِ کد فعلی

این به Migration v03→v05 ربط ندارد، اما هر migration واقعی باید آن را هم حل
کند، پس این‌جا ثبت می‌شود:

`config/schema.py`'s `Record` (فرمت کاری داخلی) از قبلِ v03 هم با
`config/raw_schema_columns.py` (قرارداد export نهایی که همان سه Collector
باید تولید کنند) هم‌نام نیست:

| `Record` (schema.py) | `raw_schema_columns.py` / v03 | یکی هستند؟ |
|---|---|---|
| `text` | `text_raw` | نام متفاوت، همان مفهوم |
| `date` | `created_at_utc` | نام متفاوت، همان مفهوم |
| `post_id` | نزدیک به `source_parent_id` (نه `platform_content_id`) | **مبهم** — توضیح `post_id` در کد («video_id / submission_id / message_id») به Parent شبیه‌تر است، نه به رکورد خودش |
| `content_id` | `platform_content_id` | نام متفاوت، همان مفهوم |
| `source` **و** `platform` (دو فیلد جدا) | فقط `platform` | افزونگی داخلی که در قرارداد export نیست |
| `author_metadata.author_hash` (nested) | `author_hash` (تخت) | ساختار متفاوت (nested dataclass در برابر ستون تخت) |

---

## ۷. سؤالات باز برای تصمیم تیم (نه تصمیم این سند)

1. آیا ۱۱ فیلد §۴.۱ («ممیزی داده تاریخی») فقط باید در لایه
   `data/raw_harmonized/` باشند، یا به `Record`/`raw_schema_columns.py` هم
   اضافه شوند حتی برای Collectorهای زنده (که این فیلدها برایشان بی‌معنا/همیشه
   `null` خواهند بود)؟
2. تنزل `query_id` و `author_hash` از Required به Conditional عمدی است؟ اگر
   بله، `validate_record()` در `schema.py` (که این دو را required فرض نکرده،
   ولی معادلش در سند v03 §۱-۱ ۱۲تا بود) باید صریحاً با این تصمیم هماهنگ شود.
3. حذف `author_follower_count`، `author_is_submitter`، `geo_granularity`،
   `geo_limitations` از جداول v05 عمدی است یا سهو سند؟
4. معنای دقیق `language_method` (بخش ۲.۳) چیست — باید به جدول §۷ v05 اضافه
   شود؟
5. آیا Audit trail معادل `prefiltered_sources_count`/`prefiltered_sources_log_ref`
   (Quota-Triage) در v05 حذف عمدی شده یا باید به Manifest §۱۲ برگردد؟
6. آیا migration باید یک‌باره (Big-bang روی `config/schema.py`) باشد یا
   افزایشی، مطابق همان الگویی که v01→v02→v03 قبلاً طی شد (رجوع به
   `docs/decision_log.md`)؟

هیچ‌کدام از این سؤالات در این سند پاسخ داده نشده‌اند — تصمیم‌گیری با تیم است.
