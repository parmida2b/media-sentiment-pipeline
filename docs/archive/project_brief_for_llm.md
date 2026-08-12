> 🗄️ **بایگانی شده (۲۰۲۶-۰۸-۱۲):** این فایل یک عکس‌لحظه‌ای از وضعیت پروژه در
> تاریخ ۲۰۲۶-۰۸-۰۷ بود (قبل از ورود مجموعه سند v5 و `PROJECT_EXECUTION_ORDER_v1.md`).
> دیگه به‌روز نیست و هیچ کدی بهش رفرنس نمی‌ده — فقط برای تاریخچه نگه داشته
> شده. برای context دادن به یک LLM/هم‌تیمی جدید، به‌جاش از
> [`docs/PROJECT_EXECUTION_ORDER_v1.md`](../PROJECT_EXECUTION_ORDER_v1.md) و
> [`docs/README.md`](../README.md) شروع کن.

# تعریف پروژه (برای دادن به LLM دیگه)

> این فایل خلاصه‌ای از وضعیت فعلی پروژه `media-sentiment-pipeline` است — چی ساخته
> شده، چی مونده، و چه فایل‌های جدیدی پیشنهاد می‌شه. برای دادن context به یک LLM
> دیگه (یا هم‌تیمی جدید) تهیه شده. تاریخ تهیه: 2026-08-07.

**نام:** `media-sentiment-pipeline` — سامانه تحلیل افکار عمومی درباره یک موضوع
مشخص (فعلاً «جنگ ایران و آمریکا»)، طراحی‌شده برای تعمیم‌پذیری به موضوعات دیگر
فقط با تغییر `config/config.yaml` (بدون تغییر کد).

## تیم و مسئولیت‌ها
| نفر | حوزه |
|---|---|
| حسین | Reddit + یکپارچه‌سازی نهایی + `schema.py` |
| **پارمیدا (من)** | YouTube + مدل sentiment |
| علی | داده مالی + تحلیل آماری/علیت |
| ریحانه | ارزیابی جامعه آماری + داشبورد + مستندسازی |

## معماری پایپ‌لاین
طبق `roadmap_pipeline.md`:

```
config.yaml → [1] data_collection → [2] preprocessing → [3] classification (sentiment)
            → [4] analysis (KPI + correlation/causality) → [5] visualization → [6] reporting
```

قانون طلایی: هر مرحله فقط از دیسک می‌خونه/می‌نویسه (نه پاس دادن آبجکت در حافظه)،
تا هر مرحله جدا قابل تست/rerun باشه.

## فرمت داده مشترک
`config/schema.py` (dataclass `Record` + `AuthorMetadata`) — فقط حسین ویرایشش
می‌کنه؛ فیلدهای جدید باید افزایشی (Optional با default) اضافه بشن، نه تغییر
فیلدهای موجود.

## چه کاری تا الان انجام شده (بخش من — YouTube)
- **استخراج** (`src/ingestion/youtube_extract.py`) — کالکتور یکپارچه (v1 و v2
  incremental که قبلاً دو فایل جدا بودن، از ۲۰۲۶-۰۸-۰۷ در همین یک فایل ادغام
  شدن؛ جزئیات در `docs/decision_log.md`). idempotent و incremental است — هر
  اجرا فقط داده‌ی جدید رو می‌گیره (watermark در `checkpoint.json`،
  `incremental_state.py`)، ۱۸ کانال در ۶ دسته دیدگاهی، تنوع منطقه‌ای از طریق
  regionCode، فیلتر ربط + geo-tagging هر ویدیو با LLM (Groq
  llama-3.3-70b)، و همه‌ی فیلدهای `content_id/parent_id/collected_at_utc/
  collection_run_id/query_id/geo_*/automation_risk_score` که سند پروژه لازم
  داشت. توضیح فنی کامل و به‌روز مسیر داده (استخراج تا اعتبارسنجی):
  `docs/youtube_data_pipeline_fa.md`.
- **حریم خصوصی:** به‌جای ذخیره `author_display_name` خام،
  `author_hash` (sha256 نمکی روی `author_channel_id`) ذخیره می‌شه
  (`author_hash.py`). **توجه: دیتای v1 قبلی (~۷۵هزار رکورد) هنوز نام خام
  داره — remediation‌ش هنوز انجام نشده.**
- **تلگرام کلاً حذف شد** از دامنه استخراج من (بایاس نمونه، غیرقابل‌دفاع بود) —
  فقط YouTube ادامه داره.
- **زمان‌بندی خودکار:** `scripts/run_youtube_incremental_weekly.ps1` + راهنمای
  ثبت Task Scheduler هفتگی در `docs/setup.md`.
- **sentiment (Day 1، اکتشافی نه نهایی):** `src/annotation/build_labeling_sample.py`
  (ساخت نمونه برای برچسب دستی)، `src/annotation/compare_llm_sentiment.py`
  (مقایسه چند مدل LLM روی ~۲۰ نمونه)، `src/validation/evaluate_sentiment_accuracy.py`
  (سنجش دقت در برابر لیبل انسانی). این‌ها فقط تست مقیاس کوچیکن، نه pipeline
  نهایی.
- سایر پوشه‌های `src/` (preprocessing, temporal_analysis, event_analysis,
  cost_tracking, reporting) خالی‌ان — هنوز کسی شروع نکرده.

## چه کاری باقی مونده (بخش من، برای رسیدن به pipeline قابل‌اجرا)
۱. **`src/preprocessing/`** — join کردن `video_geo_metadata.jsonl` با
   `youtube_comments_*.jsonl` (بر اساس `video_id`/`post_id`)، حذف تکراری، فیلتر
   بات (با `automation_risk_score` موجود)، تشخیص زبان، نرمال‌سازی متن؛ خروجی
   اجباری `cleaning_report.md`.
۲. **batch sentiment classification واقعی** — نسخه‌ی مقیاس‌پذیر
   `compare_llm_sentiment.py` که روی کل داده (بعد از preprocessing) اجرا بشه و
   `sentiment_label/confidence/model_used` رو برای هر رکورد ذخیره کنه، نه فقط
   ۲۰ نمونه.
۳. **`comment_language_stats.py`** (فاز بعدی، هنوز پیاده نشده) — درصد کامنت
   فارسی/عربی/انگلیسی/... به‌عنوان proxy جغرافیایی.
۴. **remediation دیتای v1** — حذف/هش کردن `author_display_name` خام در
   ~۷۵هزار رکورد قدیمی.
۵. **هماهنگی merge** با خروجی Reddit (حسین)، مالی (علی)، داشبورد (ریحانه).

## تصمیم‌ها و نکات مهم (از `docs/decision_log.md`)
- `config/query_registry.yaml` فقط **پیش‌نویس** است — کلیدواژه‌های
  موافق/مخالف/هشتگ سند هنوز پوشش داده نشده.
- یک بار fail-open در `geo_tagger.py` باعث شد ۱۰۶ ویدیو بدون بررسی واقعی تگ
  بخورن (وقتی هیچ کلید LLM ست نبود) — چک‌شده و ریست شد، ولی نشون‌دهنده‌ی این
  ریسکه که باید قبل از اجراهای بعدی کلیدها verify بشن.
- `.env.example` هنوز کلید واقعی API داره (باید placeholder بشه).
- quota YouTube API بین این اسکریپت و هر اسکریپت دیگری که از همون
  `YOUTUBE_API_KEY` استفاده کنه (از جمله اجراهای بقیه‌ی تیم) مشترکه —
  هماهنگی زمان اجرا لازمه.

## پیشنهاد فایل‌های جدید برای ادامه اجرا

برای این‌که pipeline بخش من واقعاً end-to-end اجرا بشه (طبق roadmap و کاری که
هنوز باقی مونده):

| فایل پیشنهادی | نقش | ورودی → خروجی |
|---|---|---|
| `src/preprocessing/join_and_clean.py` | join جغرافیا+کامنت، dedup، فیلتر بات، تشخیص زبان، نرمال‌سازی | `data/raw/*.jsonl` + `video_geo_metadata.jsonl` → `data/interim/clean.jsonl` + `cleaning_report.md` |
| `src/annotation/llm_sentiment_batch.py` | نسخه batch (با retry/rate-limit) از `compare_llm_sentiment.py` | `data/interim/clean.jsonl` → `data/processed/sentiment_labeled.jsonl` |
| `src/annotation/comment_language_stats.py` | آمار زبان به‌عنوان proxy جغرافیا | `data/processed/sentiment_labeled.jsonl` → `outputs/tables/language_stats.json` |
| `src/cost_tracking/usage_log.py` | لاگ هزینه/توکن هر فراخوانی LLM (sentiment + geo_tagger) | append به `outputs/usage_log.json` |
| `scripts/remediate_v1_author_names.py` | هش/حذف `author_display_name` خام از دیتای قدیمی v1 | `data/raw/*.jsonl` → in-place یا نسخه جدید |
| `src/pipeline/run_pipeline.py` (اختیاری، هماهنگ با تیم) | CLI واحد `--config --stage` طبق پیشنهاد `GIT_WORKFLOW.md` | orchestrate همه مراحل بالا |
