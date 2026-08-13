# Reference File Determination

**تاریخ تصمیم:** 2026-08-13  
**نویسنده:** yasaman (shekofteh.y@gmail.com)  
**هدف:** مستندسازی نقش هر فایل خام (رکورد اصلی / Export مشتق‌شده / Log/Summary) و تعیین یک منبع مرجع تحلیل برای هر پلتفرم، **پیش از** هر Concatenation یا Join.

---

## اصل راهنمای این سند

`data/raw_original/README.md` Rule:  
> "Use a single declared record source per platform and retain the other files for provenance, audit, or cross-checking."

این سند آن «منبع واحد اعلام‌شده» را برای هر پلتفرم مکتوب می‌کند.

---

## پلتفرم X (Twitter)

تمام فایل‌ها زیر `data/raw_original/x/` قرار دارند.

| فایل | اندازه | تعداد رکورد | نقش | توضیح |
|------|--------|-------------|------|-------|
| `records/x_raw.csv` | 12 MB | **16,475 رکورد، 16,475 ID یکتا** | **رکورد اصلی (مرجع تحلیل)** | Schema = `raw_schema_v03`؛ دارای `platform_content_id`, `text_raw`, `query_id`, `collection_run_id`. Collector: `x-selenium-v4.4`. بدون رکورد تکراری. |
| `logs/x_runs.csv` | 184 KB | 546 سطر | Log اجرا | دارای `collection_run_id`, `started_at_utc`, `finished_at_utc` — ستون‌های RUN_LOG_MARKER. برای حسابرسی اجراها، نه تحلیل محتوا. |
| `logs/x_subruns.csv` | 373 KB | زیر‌اجراها | Log اجرا | جزئیات per-worker/per-slice. Provenance، نه رکورد محتوایی. |
| `database/twitter_data_v4.db` | 22 MB | — | پایگاه‌داده Provenance | SQLite منبع جمع‌آوری. طبق README: «not a second raw-record file to concatenate». |
| `exports/X_Twitter_Collection (1).xlsx` | 9.2 MB | — | Export انسانی | طبق README: «not an independent dataset». با `x_raw.csv` concatenate نشود. |
| `temporary/~$X_Twitter_Collection (1).xlsx` | — | — | فایل lock آفیس | طبق README: «excluded from analysis». |

**منبع مرجع تحلیل X:** `data/raw_original/x/records/x_raw.csv`

---

## پلتفرم Reddit

تمام فایل‌ها زیر `data/raw_original/reddit/` قرار دارند.

| فایل | اندازه | تعداد رکورد | نقش | توضیح |
|------|--------|-------------|------|-------|
| `records/raw_reddit_json/` (3,571 فایل JSON) | متفاوت | — | **منبع اولیه Platform-verbatim** | پاسخ مستقیم Reddit API به‌ازای هر Submission. ساختار `[Listing_post, Listing_comments]`. نزدیک‌ترین موجود به رکورد اصلی پلتفرم. |
| `exports/reddit_raw_schema.csv` | 114 MB | **353,754 رکورد** | **Export تجزیه‌شده — مرجع تحلیل** | Schema = `raw_schema_v03`؛ `collection_run_id=legacy_reddit_json_20260808`. توسط `parse_reddit_json_raw_schema_v02.ipynb` از فایل‌های JSON تولید شده. ورودی `reddit_to_record.py`. |
| `exports/interactions.csv` | 154 MB | 353,551 سطر | Export مرحله جمع‌آوری (مشتق) | Schema غیر raw_schema_v03: فیلدهای `post_id/comment_id/body_raw/author` (نام نمایشی خام، نه hash). با `reddit_raw_schema.csv` concatenate **نشود**. |
| `exports/posts.csv` | 8.4 MB | 30,421 سطر | Export Submission‌ها (مشتق) | Schema متفاوت از raw_schema. برای Submission‌های سطح بالا؛ تکمیل‌کننده، نه رکورد مستقل. |
| `exports/master_parent_posts_dedup.csv` | 1.7 MB | 5,488 سطر | خلاصه Discovery (Summary/Audit) | فهرست Parent Submission‌های کشف‌شده با `matched_query_ids`, `discovery_routes`, `eligible_for_json_collection`. ابزار غربالگری، نه مجموعه رکورد. |
| `exports/users.csv` | 11 MB | — | تجمیع سطح کاربر (Summary) | آمار تجمیعی per-author. تحلیلی، نه رکورد خام. |
| `logs/raw_json_fetch_log.csv` | 1.5 MB | — | Log جمع‌آوری | وضعیت fetch هر submission (status، http_status، timestamps). |
| `logs/parse_errors.csv` | 2 B | **0 ردیف (فقط Header)** | Log خطا | خالی؛ هیچ خطای پارسی ثبت نشده. |
| `code/parse_reddit_json_raw_schema_v02.ipynb` | — | — | کد تاریخی | تبدیل JSON→ raw_schema. داده نیست. |

### زنجیره مشتق‌سازی Reddit

```
raw_reddit_json/*.json     ←  Reddit API verbatim responses  [منبع اولیه]
        │
        ▼  (parse_reddit_json_raw_schema_v02.ipynb / reddit_raw_json_pipeline.py)
        ├── reddit_raw_schema.csv    [تجزیه‌شده به raw_schema_v03]  ← مرجع تحلیل
        ├── interactions.csv         [فرمت مرحله جمع‌آوری، نه raw_schema]
        ├── posts.csv                [فرمت مرحله جمع‌آوری]
        └── users.csv                [تجمیع per-author]

master_parent_posts_dedup.csv  ←  مرحله غربالگری Discovery [مستقل از زنجیره بالا]
```

**منبع مرجع تحلیل Reddit:** `data/raw_original/reddit/exports/reddit_raw_schema.csv`  
فایل‌های JSON خام برای Audit و بازتولید در دسترس هستند اما مستقیماً در پایپلاین تحلیل استفاده نمی‌شوند.

---

## پلتفرم YouTube

**وضعیت ویژه:** فایل‌های YouTube در `data/raw/iran_us_war/` بودند (gitignored) و **در حال حاضر روی دیسک موجود نیستند** — `data/raw/` فقط `.gitkeep` دارد. ردیف‌های HF004-HF009 در manifest ثبت شده‌اند اما Pathهای ذکرشده وجود ندارند. این وضعیت باید پیش از اجرای Inventory رفع شود.

تمام اطلاعات پایین بر اساس manifest (HF004-HF009)، decision_log.md، و کد `youtube_extract.py` است.

### نقشه فایل‌های YouTube

| HF | مسیر (نسبی در data/raw/) | اندازه | رکوردها | نقش | توضیح |
|----|--------------------------|--------|---------|------|-------|
| HF005 | `iran_us_war/archive_before_reset_2026-07-26/youtube_comments.jsonl` | 1.0 MB | ~1,668 | **آرشیو — مستثنی از تحلیل** | جمع‌آوری اولیه/آزمایشی بدون Provenance مستند (طبق `raw_original/README.md`). قبل از reset 2026-07-26 آرشیو شد. |
| HF006 | `iran_us_war/archive_before_reset_2026-07-26/youtube_comments_1404-12-09_to_1405-05-02.jsonl` | 2.9 MB | بخشی از v1 | **آرشیو backup pre-reset** | Snapshot v1 قبل از reset. با HF007 همپوشانی دارد. |
| HF004 | `backup_2026-07-25/youtube_comments_1404-12-09_to_1405-05-03.jsonl` | 0.2 MB | بخشی از v1 | **Snapshot backup (مستثنی)** | Snapshot یک روز قبل از reset. با HF007 همپوشانی دارد. |
| HF007 | `iran_us_war/youtube_comments_1404-12-09_to_ongoing.jsonl` | 43 MB | ~75,000 | **جمع‌آوری v1 — Frozen، مستثنی از تحلیل** | خروجی کالکتور v1 (قبل از یکپارچه‌سازی 2026-08-07). طبق decision_log: «دست‌نخورده و frozen موند — remediationش هنوز کار جداییه». Schema فاقد `query_id`/`collection_run_id`/`collected_at_utc` است. |
| **HF008** | **`iran_us_war/youtube_comments_v2.jsonl`** | 137 MB | **82,550** | **خروجی کاری (Working Store)** | خروجی کالکتور یکپارچه‌شده (`youtube_extract.py v3.0`). `author_hash` با `backfill_author_hash_v05.py` در 2026-08-12 به فرمول v05 به‌روز شد. |
| **HF009** | **`iran_us_war/youtube_raw_export.csv`** | 73 MB | **82,550 (همان HF008)** | **Export قرارداد raw_schema_v03 — مرجع تحلیل** | Co-output اتوماتیک `youtube_extract.py`: به‌ازای هر رکورد نوشته‌شده در HF008، یک سطر CSV نیز نوشته می‌شود. `source_schema_version=raw_schema_v03`، `collector_version=youtube_extract v3.0`. |

### زنجیره مشتق‌سازی YouTube

```
YouTube Data API
        │
        ▼  youtube_extract.py v3.0  (raw_schema_v03 + source_registry_v3)
        ├── youtube_comments_v2.jsonl  (HF008)  ← Working Store (JSONL، برای resumability)
        │       │
        │       ▼  backfill_author_hash_v05.py (2026-08-12)
        │       └── [backup در archive_before_author_hash_v05_backfill_2026-08-12/ — مستثنی]
        │
        └── youtube_raw_export.csv  (HF009)  ← Export قرارداد  [مرجع تحلیل]

── مستثنی از تحلیل (همپوشانی دارند) ──────────────────────────────────────────
HF007: youtube_comments_1404-12-09_to_ongoing.jsonl  ← v1، فاقد query_id
HF006: archive_before_reset_2026-07-26/youtube_comments_1404-12-09_to_1405-05-02.jsonl
HF004: backup_2026-07-25/youtube_comments_1404-12-09_to_1405-05-03.jsonl
HF005: archive_before_reset_2026-07-26/youtube_comments.jsonl  ← Provenance نامعلوم
```

### چرا `youtube_raw_export.csv` (HF009) مرجع است نه `youtube_comments_v2.jsonl` (HF008)؟

| معیار | HF008 (`youtube_comments_v2.jsonl`) | HF009 (`youtube_raw_export.csv`) |
|-------|-------------------------------------|-----------------------------------|
| Schema رسمی | فرمت کاری JSONL (Record object) | `raw_schema_v03` — قرارداد cross-platform |
| استفاده کالکتور | Working Store برای deduplication/resumability | Export قرارداد §0 |
| `source_schema_version` | unknown (JSONL بومی) | `raw_schema_v03` |
| همسانی با Reddit/X | نه | بله (هر سه پلتفرم به raw_schema_v03 map می‌شوند) |
| تعداد رکورد | 82,550 | 82,550 (یکسان — Co-output) |

هر دو فایل **به‌طور همزمان** توسط کالکتور نوشته می‌شوند (نه یکی از دیگری مشتق می‌شود)، اما برای تحلیل cross-platform باید از schema یکپارچه (`raw_schema_v03`) استفاده شود.

### یکپوشانی / Duplicate بین فایل‌های v1 و v2

coverage template نشان می‌دهد که مجموع raw_n از 6 فایل YouTube برابر 247,083 است اما `unique_platform_id_n = 83,637`. این تأیید می‌کند که فایل‌های HF004-HF007 با HF008 همپوشانی محتوایی دارند و **به‌هیچ‌وجه نباید بدون deduplication صریح concatenate شوند.**

---

## خلاصه تصمیمات

| پلتفرم | منبع مرجع تحلیل | چرا |
|--------|-----------------|-----|
| **X** | `data/raw_original/x/records/x_raw.csv` | raw_schema_v03، 16,475 ID یکتا، بدون duplicate |
| **Reddit** | `data/raw_original/reddit/exports/reddit_raw_schema.csv` | raw_schema_v03، تجزیه‌شده از JSON خام، ورودی `reddit_to_record.py` |
| **YouTube** | `data/raw/iran_us_war/youtube_raw_export.csv` (HF009) | raw_schema_v03، co-output کالکتور v3.0، author_hash به فرمول v05 |

**فایل‌هایی که در هیچ تحلیلی concatenate نمی‌شوند:**

- YouTube HF004, HF005, HF006, HF007 — archive/backup/v1 legacy  
- `archive_before_author_hash_v05_backfill_2026-08-12/` — snapshot قبل از backfill  
- `x/database/twitter_data_v4.db` — SQLite provenance، نه record store  
- `x/exports/X_Twitter_Collection (1).xlsx` — export انسانی  
- `reddit/exports/interactions.csv` + `posts.csv` — فرمت مرحله جمع‌آوری، نه raw_schema  
- `reddit/exports/users.csv` + `master_parent_posts_dedup.csv` — تجمیع/خلاصه  

---

## اقدامات باز (Blocking)

1. **YouTube data/raw/ خالی است:** فایل‌های HF008 و HF009 روی دیسک موجود نیستند. پیش از هر تحلیل، باید بازیابی شوند یا `--raw-dir` به محل واقعی آن‌ها اشاره کند.

2. **Reddit و X هنوز در `data/raw/` نیستند:** اسکریپت `profile_platform.py` با `--raw-dir` پیش‌فرض آن‌ها را نمی‌بیند. باید `--raw-dir data/raw_original/reddit` یا `--raw-dir data/raw_original/x` استفاده شود، **یا** فایل مرجع هر پلتفرم به `data/raw/` کپی شود.

3. **YouTube v1 (HF007):** تصمیم remediation آن طبق decision_log هنوز باز است. تا آن زمان، HF007 frozen است و در تحلیل شرکت نمی‌کند.
