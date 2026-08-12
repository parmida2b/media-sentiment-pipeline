# قرارداد داده خام

**پلتفرم‌ها:** X، Reddit و YouTube  
**بازه:** `2026-02-28` تا `2026-07-22`

---

## ۱. هدف و قاعده حاکم

هر Collector می‌تواند فرمت داخلی خود را داشته باشد،
اما باید یک خروجی استاندارد با نام ستون، نوع و تعریف یکسان تولید کند. فرمت پیشنهادی Parquet است؛ CSV فقط برای تبادل یا بازبینی استفاده می‌شود.

Raw data پس از ذخیره تغییر نمی‌کند. Cleaning، Eligibility، Annotation و Feature engineering در لایه‌های جدا انجام می‌شوند.

### ۱.۱ سازگاری نسخه و لایه هماهنگ‌سازی

هر Collector نسخه Schema تخصیص‌یافته خود را در Manifest ثبت می‌کند. این نسخه، ساختار استاندارد لایه هماهنگ‌شده را تعریف می‌کند و با خروجی نسخه‌های Collection قبلی از طریق Mapping سازگار می‌شود. در نتیجه:

1. فایل دریافتی هر همکار با نام اصلی و Hash ثابت نگهداری می‌شود؛
2. نام و نوع ستون‌های موجود ابتدا Profile می‌شوند؛
3. برای هر پلتفرم یک Mapping از ستون مبدأ به ستون استاندارد نوشته می‌شود؛
4. مقدارهای مشتق‌شده با `field_origin = derived` از مقدارهای مستقیم با `field_origin = observed` تفکیک می‌شوند؛
5. فیلد ناموجود `null` می‌ماند و علت آن در `missing_reason` ثبت می‌شود؛
6. نبود یک فیلد تکمیلی به‌تنهایی سبب رد کل فایل نمی‌شود.

لایه‌ها به‌صورت زیر از هم جدا می‌شوند:

```text
raw_original       فایل تحویلی بدون تغییر
raw_harmonized     نگاشت نوع و نام ستون، بدون Cleaning متن
eligible_content   اجرای قواعد ورود و خروج
processed          ویژگی‌ها و برچسب‌های تحلیلی
```

## ۲. سطوح فیلد

| سطح | تعریف |
|---|---|
| Required | نبود آن رکورد را برای ممیزی نامعتبر می‌کند |
| Conditional | در صورت وجود قابلیت پلتفرم الزامی است |
| Optional | برای تحلیل تکمیلی |

## ۳. فیلدهای اصلی

| Column | Type | Level | تعریف |
|---|---|---|---|
| `platform` | string | Required | `x` / `reddit` / `youtube` |
| `platform_content_id` | string | Required | شناسه یکتای محتوا در پلتفرم |
| `content_type` | string | Required | نوع محتوا مطابق بخش ۸ |
| `created_at_utc` | datetime UTC | Required | زمان انتشار محتوا |
| `collected_at_utc` | datetime UTC | Required | زمان دریافت رکورد |
| `text_raw` | string | Required | متن خام بدون Cleaning |
| `collection_run_id` | string | Required | شناسه اجرای Collector |
| `collector_version` | string | Required | نسخه کد |
| `schema_version` | string | Required | `5.0` |
| `project_week` | string | Required | `W01` تا `W21` یا `OUT` |
| `in_window` | bool | Required | داخل بازه بودن |
| `is_partial_week` | bool | Required | فقط برای `W21` داخل بازه True |

در `raw_harmonized`، `schema_version = 5.0` نسخه خروجی هماهنگ‌شده است و به معنای آن نیست که Collector از ابتدا نسخه ۵ را اجرا کرده است. نسخه قرارداد دریافتی همکار در `source_schema_version` ثبت می‌شود.

اگر `platform_content_id` در داده مبدأ وجود نداشته باشد، رکورد حذف نمی‌شود. یک `record_uid` قطعی از نام فایل، شماره ردیف و Platform ساخته و `id_origin = derived_row_key` ثبت می‌شود. چنین رکوردی برای Deduplication قطعی و برخی تحلیل‌های وابستگی محدودیت دارد و تا زمان بررسی، درجه C می‌گیرد.

## ۴. Provenance و ساختار Parent

| Column | Type | Level | تعریف |
|---|---|---|---|
| `query_id` | string | Conditional | Query اولیه |
| `matched_query_ids` | list/string | Conditional | همه Queryهای منطبق |
| `query_version` | string | Conditional | نسخه Registry |
| `source_id` | string | Conditional | شناسه Source Registry |
| `source_registry_version` | string | Conditional | نسخه Source Registry |
| `discovery_route` | string | Required | query_search/hashtag/source_scope/channel_scope/seed |
| `source_container` | string | Conditional | Subreddit، Channel یا Search scope |
| `source_container_id` | string | Conditional | ID پلتفرمی Container |
| `source_parent_id` | string | Conditional | Conversation، Submission یا Video |
| `source_parent_title` | string | Conditional | عنوان Parent، در صورت وجود |
| `parent_id` | string | Conditional | والد مستقیم Reply |
| `permalink_hash` | string | Optional | هش URL، نه URL خام |

### ۴.۱ فیلدهای ممیزی داده تاریخی

| Column | Type | تعریف |
|---|---|---|
| `original_file_name` | string | نام فایل تحویلی |
| `original_file_sha256` | string | Hash پیش از هر تبدیل |
| `original_row_number` | int | شماره ردیف در فایل اصلی |
| `source_schema_version` | string | نسخه Schema داده‌شده به همکار یا `unknown` |
| `source_query_registry_version` | string | نسخه Query Registry داده‌شده یا `unknown` |
| `record_uid` | string | کلید داخلی قطعی برای ردیابی رکورد |
| `id_origin` | string | observed/derived_row_key |
| `timestamp_origin` | string | observed/parsed_from_source/unknown |
| `provenance_quality` | string | complete/reconstructed/partial/unknown |
| `field_origin` | string/json | منشأ فیلدهای بازسازی‌شده |
| `missing_reason` | string/json | علت فیلدهای مهم ناموجود |

## ۵. نویسنده و حریم خصوصی

| Column | Type | Level | تعریف |
|---|---|---|---|
| `author_hash` | string | Conditional | شناسه مستعارشده و Platform-specific |
| `author_id_status` | string | Conditional | available/deleted/unavailable/not_provided |
| `author_type` | string | Optional | ordinary/media/official/organization/unknown |
| `author_is_verified` | bool | Optional | وضعیت گزارش‌شده پلتفرم |
| `author_account_age_days` | int | Optional | سن حساب در زمان Collection |

Username، نام واقعی، ایمیل، شماره تماس و Location خام در خروجی تحلیلی ذخیره نمی‌شود. اگر شناسه پایدار نویسنده مجاز و در دسترس باشد، Hash با Salt محرمانه ساخته می‌شود:

```python
sha256(f"{platform}:{stable_author_id}:{PROJECT_AUTHOR_SALT}")
```

Salt در متغیر محیطی نگهداری می‌شود. Hash فقط وابستگی درون همان پلتفرم را کنترل می‌کند و برای پیوند هویت میان پلتفرم‌ها استفاده نمی‌شود.

## ۶. Engagement snapshot

| Column | Type | تعریف |
|---|---|---|
| `engagement_score` | float | Like/Score اصلی پلتفرم |
| `engagement_replies` | int | تعداد Reply مستقیم |
| `engagement_shares` | int | Share/Repost، عمدتاً X |
| `engagement_quotes` | int | Quote، عمدتاً X |
| `engagement_views` | int | View، در صورت دسترسی |
| `engagement_collected_at_utc` | datetime UTC | زمان Snapshot |

Engagement بین پلتفرم‌ها هم‌مقیاس نیست و بدون حفظ Platform تجمیع نمی‌شود.

## ۷. زبان، وضعیت و مکان

| Column | Type | Level | تعریف |
|---|---|---|---|
| `language_reported` | string | Optional | زبان گزارش‌شده پلتفرم |
| `language_detected` | string | Conditional | en/fa/ar/other/unknown |
| `language_confidence` | float | Conditional | ۰ تا ۱، فقط اگر روش معتبر تولید کند |
| `content_status` | string | Optional | active/deleted/removed/unavailable |
| `geo_method` | string | Optional | geotag/profile/self_reported/other |
| `country_or_region` | string | Optional | مقدار مستقیم یا unknown |
| `geo_confidence` | string | Optional | high/medium/low |

Language به Location تبدیل نمی‌شود. مقدار ساختگی Confidence برای روش Rule-based ثبت نمی‌شود؛ در آن حالت `language_method` و نتیجه Rule نگهداری می‌شود.

## ۸. مقادیر `content_type`

| مقدار | پلتفرم | توضیح |
|---|---|---|
| `original_post` | X، Reddit | متن اصلی |
| `comment` | Reddit، YouTube | Comment سطح اول |
| `reply` | همه | پاسخ متنی |
| `quote` | X | Quote دارای متن افزوده |
| `repost` | X | بازنشر بدون متن جدید |
| `video_context` | YouTube | Metadata ویدئو؛ واحد Opinion نیست |
| `deleted_or_unavailable` | همه | فقط برای Audit |
| `unknown` | همه | نیازمند بررسی |

## ۹. نگاشت پلتفرمی

### X

```text
source_parent_id = conversation_id
parent_id        = replied_to_id، در صورت Reply
content_type     = original_post/reply/quote/repost
```

### Reddit

```text
source_container    = subreddit
source_parent_id    = submission fullname/id
source_parent_title = submission title
parent_id           = parent fullname/id
content_type        = original_post/comment/reply
```

### YouTube

```text
source_container    = channel_id
source_parent_id    = video_id
source_parent_title = video title
parent_id           = top-level comment id، برای Reply
content_type        = comment/reply/video_context
```

## ۱۰. تعریف هفته

```python
from datetime import datetime, timezone

START = datetime(2026, 2, 28, 0, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 7, 22, 23, 59, 59, tzinfo=timezone.utc)

def assign_project_week(ts):
    if not (START <= ts <= END):
        return "OUT", False, False
    week_number = (ts - START).days // 7 + 1
    return f"W{week_number:02d}", True, week_number == 21
```

`W21` شامل `2026-07-18` تا `2026-07-22` و پنج روزه است.

## ۱۱. فیلدهای مشتق‌شده

این فیلدها در Raw ساخته نمی‌شوند:

```text
text_normalized, char_count, word_count, hashtags, mentions, urls_count,
duplicate_flag, near_duplicate_cluster_id, eligibility, exclusion_reason,
sentiment, stance, emotion, topic, model_confidence, automation_risk_score
```

هرکدام باید نسخه روش تولید و Timestamp داشته باشد.

## ۱۲. Collection Manifest

یک سطر برای هر ترکیب عملیاتی `platform × query × source × requested_window` ثبت می‌شود.

| Column | تعریف |
|---|---|
| `collection_run_id` | شناسه یکتا |
| `platform` | پلتفرم |
| `query_id`, `query_version` | Query اجراشده |
| `source_id` | Source، در صورت محدودسازی |
| `requested_start_utc`, `requested_end_utc` | Window درخواست |
| `started_at_utc`, `finished_at_utc` | زمان اجرای واقعی |
| `sort_mode` | Sort واقعی |
| `pages_requested`, `pages_received` | Pagination |
| `returned_count`, `stored_count` | تعداد برگشتی و ذخیره‌شده |
| `oldest_record_utc`, `newest_record_utc` | Coverage واقعی |
| `sampling_method` | none/random/cap_newest/cap_available |
| `sampling_cap`, `random_seed` | در صورت اعمال |
| `quota_or_rate_limit_events` | محدودیت مشاهده‌شده |
| `error_count`, `error_types` | خطاها |
| `known_gap` | شکاف شناخته‌شده |
| `notes` | توضیح ضروری |

برای Collection انجام‌شده، Manifest می‌تواند از کد، نام فایل، Metadata، Registry ارسال‌شده و توضیح مکتوب همکار بازسازی شود. فیلد بازسازی‌شده با `evidence_source` و `reconstruction_status` مشخص می‌شود. خاطره همکار می‌تواند توضیح تکمیلی باشد، اما جای رشته Query یا Timestamp ثبت‌شده در Log را نمی‌گیرد.

## ۱۳. Validation و درجه پذیرش

Validation دو مرحله دارد و برای داده تاریخی به‌صورت حذف همه‌یا‌هیچ استفاده نمی‌شود.

### ۱۳.۱ پذیرش فایل

1. فایل باز شود و نوع آن مشخص باشد؛
2. Hash و تعداد ردیف ثبت شود؛
3. Platform و منشأ فایل معلوم باشد؛
4. ستون متن، شناسه و زمان، حتی با نام متفاوت، جست‌وجو و Profile شوند؛
5. فایل اصلی تغییر نکند.

### ۱۳.۲ اعتبار خروجی هماهنگ‌شده

1. ستون‌های هدف و منشأ هر نگاشت ثبت باشند؛
2. ID مشاهده‌شده یا `record_uid` قطعی وجود داشته باشد؛
3. Timestamp موجود UTC و قابل Parse باشد؛ رکورد بدون زمان از روند زمانی کنار گذاشته و شمارش شود؛
4. `project_week` با تابع بخش ۱۰ سازگار باشد؛
5. `collection_run_id` مشاهده یا در سطح فایل بازسازی شده باشد؛
6. Query و Source فقط در صورت وجود مدرک معتبر متصل شوند؛
7. `text_raw` با مقدار مبدأ کنترل Hash/Equality شود؛
8. Duplicate ID و تضاد مقدار گزارش شود؛
9. تعداد ورودی، خروجی و قرنطینه با هم آشتی داده شود.

خروجی Validation شامل Pass/Fail/Not available، تعداد رکورد متاثر، نمونه خطا، تصمیم و درجه A تا D است.

## ۱۴. ساختار فایل پیشنهادی

```text
data/raw/{platform}/{collection_run_id}.parquet
data/raw_original/{platform}/{original_file_name}
data/raw_harmonized/{platform}/{original_file_stem}.parquet
data/manifests/{platform}_runs.csv
data/audits/raw_validation.csv
data/interim/eligible_content.parquet
data/interim/context_only.parquet
data/audits/audit_only.parquet
data/processed/opinion_main.parquet
```

فایل عمومی نهایی باید داده تجمیعی و ناشناس داشته باشد؛ انتشار متن خام یا شناسه‌های قابل بازیابی نیازمند بررسی مجوز منبع است.
