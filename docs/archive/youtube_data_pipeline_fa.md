# مسیر داده‌ی یوتیوب: از استخراج تا اعتبارسنجی

> **هدف این سند:** توضیح فنیِ کامل مسیری که داده‌ی یوتیوب طی می‌کند — از لحظه‌ای
> که یک کامنت از YouTube API گرفته می‌شود تا لحظه‌ای که به‌عنوان یک ردیف
> برچسب‌خورده در ارزیابی مدل شرکت می‌کند. مخاطب این سند هم‌تیمی‌هاست، نه
> کاربر تازه‌وارد؛ جزئیات پیاده‌سازی (نام فایل، فرمول، ستون) عمداً کامل آورده
> شده تا مرجع باشد، نه یک معرفی کلی.
>
> کد مرجع فعلی: [`src/ingestion/youtube_extract.py`](../src/ingestion/youtube_extract.py)
> (نسخه‌ی v3.0 — طبق [`docs/decision_log.md`](decision_log.md) ردیف
> ۲۰۲۶-۰۸-۰۷، این فایل نسخه‌های قبلی v1/v2 را یکپارچه کرده؛ اگر
> [`docs/youtube_extraction_guide.md`](youtube_extraction_guide.md) را
> می‌خوانید، آن سند مربوط به معماری قدیمی دو-فایلی است).

---

## نمای کلی مسیر

```
YouTube Data API v3
       │
       ▼
① استخراج (Ingestion)                    src/ingestion/youtube_extract.py
   discovery → relevance filter → comment fetch → sampling
   → automation risk (Tier A) → per-comment geo → dedup
       │
       ▼  data/raw/{topic_id}/youtube_comments_v2.jsonl (+ csv/manifest)
       │
② پیش‌پردازش (Preprocessing)              src/preprocessing/join_and_clean.py
   join همه‌ی هفته‌ها + automation risk (Tier B، در سطح کاربر نه کامنت)
       │
       ▼  data/interim/clean.jsonl
       │
③ نمونه‌گیری برای برچسب‌گذاری              src/annotation/build_labeling_sample.py
       │
       ▼  data/annotated/sample_sentiment_labels.csv
       │
④ برچسب‌گذاری با LLM (۴ محور)             src/annotation/{schema,prompt_contract,llm_client,model_routes,run_model_comparison}.py
       │
       ▼
⑤ اعتبارسنجی                              src/validation/{compute_annotator_agreement,evaluate_sentiment_accuracy}.py
   Cohen's Kappa بین انسان‌ها + دقت/هزینه/coverage هر مدل در برابر Gold Sample
```

---

## ① استخراج — [`youtube_extract.py`](../src/ingestion/youtube_extract.py)

### پیش‌نیاز و پیکربندی
- `YOUTUBE_API_KEY` باید در `.env` ست شده باشد؛ نبودش باعث توقف فوری با پیام خطا می‌شود (نه کرش خاموش).
- `AUTHOR_HASH_SALT` هم باید ست شود — نمک هش نویسنده‌ها.
- پنجره‌ی زمانی پروژه (`publishedAfter`/`publishedBefore`) از `project_calendar.py` می‌آید و **ثابت** است؛ ربطی به `date_range.end: auto` در `config.yaml` ندارد (آن فقط روی عمق re-check کامنت‌های شناخته‌شده اثر دارد، نه discovery).
- منابع جست‌وجو: کلیدواژه‌های `config/query_registry.yaml` (نسخه‌ی فعلی: `0.1-draft`، هنوز نهایی نشده) + کانال‌های `config.yaml`'s `youtube.channels`.

### گام به گام

**۱. خواندن state.**
`incremental_state.load_state()` واترمارک جست‌وجوی سراسری (`global_search_watermark`) و لیست ویدیوهای شناخته‌شده را از `checkpoint.json` برمی‌دارد. `checkpoint.py` جدا از این، فقط مصرف quota روزانه را ردیابی می‌کند (`QUOTA_COSTS`: search=۱۰۰، videos.list/commentThreads/channels.list=۱ واحد هرکدام، سقف روزانه پیش‌فرض `MAX_DAILY_QUOTA=8000` — قابل override با `YOUTUBE_DAILY_QUOTA_BUDGET`). این quota بین این اسکریپت و هر اسکریپت دیگری که از همان API key استفاده کند مشترک است.

**۲. Discovery (کشف ویدیو).**
دو مسیر موازی، هر دو با `order="date"` (هرگز relevance/top — طبق `raw_schema_v03.md §12.5`) و هر دو `publishedAfter` و `publishedBefore` را روی پنجره‌ی ثابت پروژه pin می‌کنند:
- **query search**: هر (query_id, query_text) از رجیستری × هر (region_code, relevance_language) از `config.yaml`
- **channel search**: کانال‌های `channel_priority_order` که handle‌شان قبلاً resolve شده (`resolved_channels.json` cache می‌شود؛ اگر handle غلط باشد فقط warning چاپ می‌شود، کرش نمی‌کند)

هر ویدیوی پیداشده با `matched_query_ids` (همه‌ی کوئری‌هایی که به آن رسیدند) و `discovery_route` (`query_search` یا `source_scope`) علامت می‌خورد.

**۳. جزئیات ویدیو.**
`videos.list` روی دسته‌های ۵۰تایی، عنوان/توضیحات/channelId/channelTitle را می‌گیرد — همان‌جا `source_id_lookup` هم ساخته می‌شود تا هر ویدیو (حتی اگر از query search پیدا شده باشد، نه channel search) در صورت تعلق به یک کانال رجیستری‌شده، `source_id`/`source_container` بگیرد.

**۴. فیلتر ربط + دیدگاه (Quota-Triage Pre-filter) — [`geo_tagger.py`](../src/ingestion/geo_tagger.py).**
یک‌بار برای هر ویدیو (نه هر کامنت)، از طریق Groq (`llama-3.3-70b-versatile` پیش‌فرض) پرسیده می‌شود: آیا این ویدیو واقعاً به موضوع پروژه مربوط است؟ لحن منبع چیست (`state_media`/`western`/`independent`/`diaspora`/`other`)؟ نتیجه در `video_geo_metadata.jsonl` کش می‌شود (کلید: video_id) تا هزینه‌ی LLM فقط یک‌بار در کل عمر ویدیو پرداخت شود.
- اگر `GROQ_API_KEY` ست نباشد: **fail-open** — یعنی ویدیو مرتبط فرض می‌شود (`is_relevant=True`, `confidence=0.0`)، نه این‌که بی‌صدا حذف شود.
- اگر `is_relevant=False`: ویدیو کامل رد می‌شود و در `youtube_skipped_videos.csv` با دلیل/perspective/confidence ثبت می‌شود.

**۵. گرفتن کامنت‌ها — `fetch_comment_pool_since()`.**
`commentThreads.list` با `order="time"` (هرگز relevance)، فقط کامنت‌های جدیدتر از واترمارک همان ویدیو. سقف pool = `MAX_COMMENTS_PER_VIDEO × COMMENT_POOL_MULTIPLIER` = `300 × 5 = 1500`. محدودیت شناخته‌شده: چون commentThreads بر اساس زمان **کامنت سطح‌بالا** مرتب می‌شود، وقتی به یک thread قدیمی‌تر از واترمارک برسیم توقف می‌کنیم — یعنی یک ریپلای که تئوریاً جدیدتر است ولی زیر یک thread قدیمی نشسته، از قلم می‌افتد (محدودیت خود API، نه باگ کد).

**۶. نمونه‌گیری — `_sample_comments()`.**
اگر pool ≤ ۳۰۰: همه نگه داشته می‌شوند (`sampling_method="none"`). اگر بیشتر: دقیقاً ۳۰۰ تا با `random.Random(seed=f"{RANDOM_SEED}:{video_id}")` (`RANDOM_SEED=42`) به‌صورت **یکنواخت تصادفی** انتخاب می‌شوند — نه truncation به «۳۰۰ تای اول». seed دترمینیستیک یعنی اجرای مجدد روی همان pool، همان نمونه را می‌دهد.
> محدودیت ساختاری مستندشده: چون جمع‌آوری incremental است، `pool` فقط دسته‌ی تازه‌ی همین اجراست، نه کل تاریخچه‌ی کامنت‌های ویدیو — اگر بین دو اجرا یک ویدیو ناگهان صدها کامنت جدید بگیرد، نمونه‌گیری از همان انفجار انجام می‌شود، نه از «کل جمعیت کامنت‌های ویدیو». جزئیات در `docs/decision_log.md`.

**۷. امتیاز ریسک ربات (Tier A) — [`automation_risk.py`](../src/ingestion/automation_risk.py).**
یک‌بار برای کل دسته‌ی کامنت‌های همان ویدیو (`score_batch`)، سه سیگنال با وزن ثابت ترکیب می‌شوند:

| سیگنال | وزن | منطق |
|---|---|---|
| تکرار متن تقریباً عینی | ۰.۵ | نرمال‌سازی متن (lowercase + فشرده‌سازی whitespace) → شمارش تکرار در همان batch؛ ۱ بار=۰، ≥۵ بار=۱.۰ |
| ارسال پشت‌سرهم | ۰.۳۵ | همان نویسنده، ≥۳ کامنت در بازه‌ی ۶۰ ثانیه |
| چگالی لینک/هشتگ | ۰.۱۵ | (تعداد لینک+هشتگ)/۳، سقف ۱.۰ |

خروجی `automation_risk_score` بین ۰ تا ۱، **نه** یک حکم «این ربات است» — طبق محدودیت مستند: YouTube API سن اکانت یا تعداد فالوور نمی‌دهد.

**۸. تگ جغرافیایی هر کامنت — [`author_geo.py`](../src/ingestion/author_geo.py).**
بدون LLM، فقط تطبیق عبارت/کانال، به این ترتیب اولویت (اولین نتیجه‌ی موفق برنده است):
1. `text_place` (confidence=`medium`): فقط اگر متن یک عبارت **خودمعرفی صریح** دارد (مثل «As an Iranian…» یا «من ایرانی‌ام»)؛ عمداً محدود، چون موضوع پروژه خودش ایران-آمریکاست و اشاره‌ی ساده به این اسم‌ها هیچ دلیلی برای محل زندگی نیست.
2. `source_community` (confidence=`low`): کشور کانال میزبان ویدیو، از رجیستری — این درباره‌ی مخاطب کانال است، نه لزوماً محل زندگی کامنت‌گذار.
3. `language_weak` (confidence=`low`, `country_or_region="unknown"` همیشه): فقط زبان تشخیص‌داده‌شده ثبت می‌شود؛ هرگز به کشور تبدیل نمی‌شود.

توجه: این جدا از تگ `perspective`ی گام ۴ است — آن یکی درباره‌ی لحن/منشأ **ویدیو**ست و در فیلدهای `geo_*` رکورد کامنت ذخیره نمی‌شود.

**۹. Dedup و ساخت رکورد نهایی.**
هر کامنت با `content_id` یکتا چک می‌شود (هم در فایل موجود، هم در همین اجرا) تا رکورد تکراری نوشته نشود. رکورد نهایی از کلاس `Record` در [`config/schema.py`](../config/schema.py) ساخته می‌شود؛ فیلدهای کلیدی:

| دسته | فیلدها |
|---|---|
| متن/زمان | `text`, `date`, `content_id`, `parent_id`, `is_reply`, `reply_count` |
| منبع | `post_id`, `post_title`, `source_id`, `source_container`, `source_container_id`, `permalink_hash` |
| کشف | `discovery_route`, `matched_query_ids`, `query_id`, `query_version` |
| جمع‌آوری | `collected_at_utc`, `collection_run_id` |
| نویسنده | `author_metadata.author_hash` (هش شده)، `author_metadata.author_channel_id`, `author_metadata.like_count` |
| زبان | `language`, `language_confidence` |
| جغرافیا | `geo_method`, `country_or_region`, `geo_confidence`, `geo_granularity`, `geo_limitations` |
| نمونه‌گیری | `sampling_method`, `sampling_applied`, `items_kept`, `random_seed`, `source_total_available` |
| زمان‌بندی پروژه | `project_week`, `in_window`, `is_partial_week` |
| ریسک | `automation_risk_score` |

نکته: کامنت‌های جدیدتر از پایان پنجره‌ی پروژه **حذف نمی‌شوند** — با `in_window=false` و `project_week="OUT"` نگه داشته می‌شوند.

### خروجی‌های روی دیسک (`data/raw/{topic_id}/`)

| فایل | محتوا |
|---|---|
| `youtube_comments_v2.jsonl` | رکوردهای کامل (JSON Lines) |
| `youtube_raw_export.csv` | همان داده، ستون‌بندی‌شده طبق قرارداد مشترک `raw_schema_v03.md` (`config/raw_schema_columns.py`) — همان قراردادی که Reddit/X هم باید رعایت کنند |
| `youtube_runs.csv` | Manifest؛ یک ردیف به ازای هر (query_id, project_week) در این اجرا — quota_consumed/error_count/prefiltered_sources_count فقط روی اولین ردیف هر اجرا نوشته می‌شود چون این‌ها run-level هستند |
| `youtube_skipped_videos.csv` | لاگ ویدیوهایی که فیلتر ربط ردشان کرد |
| `checkpoint.json` | quota مصرفی امروز |
| `video_geo_metadata.jsonl` | کش تگ ربط/perspective هر ویدیو |
| `resolved_channels.json` | کش handle→channel_id |

### رفتار در برابر خطا/quota
هر HttpError با کد ۴۰۳ حاوی «quota» به‌عنوان اتمام واقعی quota شناخته می‌شود و باعث توقف تمیز (نه crash) با ثبت در `known_gaps` می‌شود — اجرای بعدی از همان‌جا (واترمارک) ادامه می‌دهد. `checkpoint.save_checkpoint` هم در برابر قفل موقت فایل توسط OneDrive/آنتی‌ویروس روی ویندوز، ۵ بار retry می‌کند.

### نکات باز (طبق `decision_log.md`)
- Quota واقعی API بین این اسکریپت و هر اسکریپت دیگری که از همان کلید استفاده کند مشترک است — دو شمارنده‌ی مستقل نداریم.
- `config/query_registry.yaml` نسخه‌ی `0.1-draft` است، هنوز نهایی نشده.
- ۷ کانال جدید در رجیستری هنوز `channel_id`شان تأیید دستی نشده (اگر handle غلط باشد فقط warning می‌دهد، ویدیویی برایش پیدا نمی‌شود — کرش نمی‌کند).
- داده‌ی قدیمی v1 (~۷۵هزار رکورد، `youtube_comments_1404-*.jsonl`) هنوز `author_display_name` خام دارد؛ remediation آن یک کار جدا و هنوز بازه.

---

## ② پیش‌پردازش — [`join_and_clean.py`](../src/preprocessing/join_and_clean.py) + [`user_features.py`](../src/preprocessing/user_features.py)

ورودی: همه‌ی `data/raw/{topic_id}/youtube_comments_*.jsonl` (هر چند فایل/هفته باشد) + `video_geo_metadata.jsonl` اختیاری.

نکته‌ی معماری مهم: امتیاز ریسک ربات گام ① («Tier A») فقط کامنت‌های **یک ویدیو** را می‌بیند، پس نمی‌تواند بفهمد یک نفر همان متن را زیر ۴۰ ویدیوی مختلف تکرار کرده. این‌جا («Tier B») برای هر **کاربر** (کلید: `author_hash`، یا در نبودش `author_channel_id` برای رکوردهای قدیمی) در کل تاریخچه‌ی جمع‌آوری‌شده فیچر می‌سازد:

| فیچر | وزن در امتیاز نهایی |
|---|---|
| `exact_duplicate_ratio` (نسبت متن‌های عیناً تکراری) | ۰.۳۵ |
| `rapid_activity_ratio_60s` (نسبت کامنت‌های با فاصله‌ی ≤۶۰ثانیه) | ۰.۲۵ |
| `url_interaction_ratio` | ۰.۱۵ |
| `hour_coverage_ratio` (چند ساعت متفاوت UTC فعال بوده — پوشش بالا نشانه‌ی خودکاربودن) | ۰.۱۰ |
| میانگین `automation_risk_score` (Tier A، وقتی موجود باشد) | ۰.۱۵ |

نتیجه: `automation_risk_score_user` + `is_flagged_bot_suspect` (آستانه‌ی `FLAG_THRESHOLD=0.7`، فقط پیشنهاد بازبینی — فیلترکردن خودکار روی این امتیاز در همین اسکریپت انجام **نمی‌شود**، تصمیمی جداست که تیم باید بگیرد).

⚠️ این وزن‌ها در برابر ground truth واقعی validate نشده‌اند — نقطه‌ی شروع‌اند، نه عدد نهایی.

خروجی: `data/interim/clean.jsonl` (هیچ رکوردی حذف نمی‌شود، فقط فیچر اضافه می‌شود) + `outputs/audits/cleaning_report.md`.

محدودیت شناخته‌شده: بیشتر داده‌ی جمع‌آوری‌شده تا الان قبل از schema فعلی است، پس `content_id`/`parent_id` روی رکوردهای قدیمی خالی است و سیگنال‌هایی که به آن‌ها نیاز دارند (`self_reply_ratio` و مشابه) هنوز پیاده نشده‌اند.

---

## ③ نمونه‌گیری برای برچسب‌گذاری — [`build_labeling_sample.py`](../src/annotation/build_labeling_sample.py)

از `clean.jsonl` یک نمونه انتخاب می‌کند برای برچسب‌گذاری دستی/LLM. رفتار پیش‌فرض «مهاجرت schema درجا» است، **نه** نمونه‌گیری تازه — یعنی اجرای معمولی همان ۹۰ ردیف قبلی را نگه می‌دارد و فقط ستون‌های جدید را خالی اضافه می‌کند. برای نمونه‌ی واقعاً تازه باید صریحاً `--resample` بدهی. (این رفتار بعد از یک حادثه تغییر کرد: بار اول با schema جدید یک نمونه‌ی کاملاً متفاوت ساخت و ۶۰ ترجمه‌ی دستی یک هم‌تیمی صفر تا مچ پیدا کرد — جزئیات در `decision_log.md`.)

خروجی: `data/annotated/sample_sentiment_labels.csv`.

---

## ④ برچسب‌گذاری — چهار محور مستقل

طبق [`src/annotation/schema.py`](../src/annotation/schema.py)، هر متن روی **۴ محور جدا** برچسب می‌خورد (هرگز با هم قاطی نمی‌شوند):

| محور | برچسب‌ها |
|---|---|
| `sentiment` | positive / negative / neutral / mixed / unclear |
| `stance` (نسبت به یک Target مشخص) | support / oppose / neutral_or_balanced / unrelated / unclear |
| `emotion` | anger / fear / sadness / hope / joy / disgust / surprise / none_or_unclear |
| `content_type` | personal_opinion / news_or_report / quotation / satire / spam / unclear |

**Stance** همیشه نسبت به یکی از ۶ Target ثابت سنجیده می‌شود (نه «موضوع کلی»):
`T01` تشدید/اقدام نظامی، `T02` مذاکره/آتش‌بس/دیپلماسی، `T03` تحریم/فشار اقتصادی
(اصلی — تحلیل اصلی روی همین سه)، و `T04` سیاست دولت ایران، `T05` سیاست دولت
آمریکا، `T06` پیامدهای انسانی (تکمیلی — فقط در صورت کیفیت کافی Gold Sample).

مثال کلیدی از خود پرامپت: «این جنگ خیلی خطرناکه، ولی تصمیم دولت آمریکا قابل‌دفاعه» → `sentiment=negative` ولی `stance=support` (نسبت به Target=T05). این دو محور می‌توانند عمداً در جهت‌های مختلف باشند.

**پرامپت نسخه‌بندی‌شده** — [`prompt_contract.py`](../src/annotation/prompt_contract.py) (`PROMPT_VERSION` فعلی: `2026-08-07.v1`، هر تغییر در تعریف یک برچسب باید این نسخه را ببرد بالا چون روی هر رکورد annotation ثبت می‌شود). خروجی الزامی مدل یک JSON با ۶ فیلد است: چهار برچسب + `confidence` (self-reported، هرگز جایگزین اعتبارسنجی واقعی نیست) + `reason_code` کوتاه.

**مسیرهای مدل (Cost-aware)** — [`model_routes.py`](../src/annotation/model_routes.py)، هر route با provider/قیمت واقعی per-token/آستانه‌ی confidence مستند شده:

| route | مدل | provider | ورودی $/M توکن | خروجی $/M توکن |
|---|---|---|---|---|
| `groq_cheap_fast` | llama-3.1-8b-instant | Groq | ۰.۰۵ | ۰.۰۸ |
| `groq_default` | llama-3.3-70b-versatile | Groq | ۰.۵۹ | ۰.۷۹ |
| `deepseek_flash_direct` | deepseek-v4-flash | DeepSeek | ۰.۱۴ | ۰.۲۸ |
| `openrouter_deepseek_flash` | همان بالا، از طریق OpenRouter | OpenRouter | ۰.۱۴ | ۰.۲۸ |
| `openrouter_gemini_flash_lite` | gemini-2.5-flash-lite | OpenRouter | ۰.۱۰ | ۰.۴۰ |

> `GEMINI_API_KEY` فعلی برای SDK مستقیم گوگل نامعتبر است (۴۰۳)؛ تا رسیدن کلید صحیح، مدل‌های Gemini از مسیر OpenRouter در دسترس‌اند. کلید مستقیم DeepSeek هم موجودی کافی ندارد (۴۰۲)؛ از OpenRouter استفاده می‌شود.

فراخوانی واقعی مدل‌ها از [`llm_client.py`](../src/annotation/llm_client.py) (caller یکپارچه با cache/retry-backoff/لاگ هزینه-تأخیر) انجام می‌شود؛ مقایسه‌ی مسیرها روی داده‌ی واقعی در [`run_model_comparison.py`](../src/annotation/run_model_comparison.py) (جایگزین `compare_llm_sentiment.py` قدیمی که حذف شد).

---

## ⑤ اعتبارسنجی

### توافق بین انسان‌ها — [`compute_annotator_agreement.py`](../src/validation/compute_annotator_agreement.py)
دو فایل CSV می‌خواند: `sample_sentiment_labels.csv` (annotator اول، کل نمونه) و `sample_sentiment_labels_agreement_subset.csv` (annotator دوم، زیرمجموعه‌ای که هر دو نفر برچسب زده‌اند)، ردیف‌ها را با `content_id` تطبیق می‌دهد و برای هر ۴ محور جدا **Cohen's Kappa** حساب می‌کند (Percent Agreement هم گزارش می‌شود ولی فقط مکمل، نه معیار اصلی). خروجی: `outputs/audits/annotator_agreement.json`. اگر kappa پایین باشد، پیام صریح چاپ می‌شود: قبل از اعتماد به این نمونه به‌عنوان ground truth، باید اختلاف‌ها adjudicate شوند.

### دقت مدل‌ها در برابر Gold Sample — [`evaluate_sentiment_accuracy.py`](../src/validation/evaluate_sentiment_accuracy.py)
هر route از `model_routes.py` را در برابر برچسب‌های دستی می‌سنجد و برای sentiment و stance گزارش می‌دهد:
- accuracy (فقط شاخص فرعی)، precision/recall/F1 به تفکیک کلاس + F1 macro، confusion matrix
- coverage بعد از اعمال `confidence_threshold` هر route
- هزینه و تأخیر به ازای هر ۱۰۰۰ رکورد
- نرخ شکست تماس API و نرخ شکست parse کردن JSON
- شکست دقت بر اساس زبان، طول متن، content_type انسانی، Target، و زیرمجموعه‌ی satire/quotation

محدودیت مستندشده: چون Gold Sample CSV ستون تاریخ ندارد، شکست بر اساس بازه‌ی زمانی گزارش نمی‌شود.

---

## جمع‌بندی محدودیت‌های شناخته‌شده (نه نادیده‌گرفته‌شده)

| محدودیت | کجا مستند شده |
|---|---|
| YouTube API سن اکانت/فالوور نمی‌دهد → ریسک ربات فقط از ۳ سیگنال ساده | `automation_risk.py`, `user_features.py` |
| نمونه‌گیری ۳۰۰تایی فقط از دسته‌ی تازه‌ی هر اجراست، نه کل تاریخچه‌ی ویدیو | `youtube_extract.py::_sample_comments` |
| geo فقط با self-identification صریح یا کانال میزبان تخمین زده می‌شود؛ اکثر رکوردها `unknown` می‌مانند | `author_geo.py` |
| داده‌ی قدیمی v1 هنوز نام کاربری خام دارد؛ remediation باز است | `decision_log.md` |
| `query_registry.yaml` هنوز پیش‌نویس (۰.۱-draft) است | `decision_log.md` |
| Gemini/DeepSeek مستقیم فعلاً از مسیر جایگزین (OpenRouter) صدا زده می‌شوند | `model_routes.py` |
