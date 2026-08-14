# تشخیص فایل مرجع (چک‌لیست فاز اول، آیتم ۳)

**تاریخ:** ۲۰۲۶-۰۸-۱۴
**مبنا:** ستون `notes` در `docs/data_handoff_manifest.csv` (که خودش قبلاً — طی
یک ممیزی ۲۰۲۶-۰۸-۱۴ — برای هر فایل مشخص کرده کدام مرجع، کدام Superseded،
کدام Backup/Log/Config است). این سند فقط آن تحلیل را per-platform خلاصه و
قابل‌مرور می‌کند؛ تحلیل جدیدی اضافه نمی‌کند.

قانون کلی طبق `docs/checklist.md` فاز اول: **فایل‌های مختلف بدون این تصمیم
مکتوب Concatenate نمی‌شوند.** هر اسکریپت پایین‌دستی (`join_and_clean.py`،
`backfill_raw_harmonized_v05.py`) باید فقط از ردیف «مرجع» هر پلتفرم بخواند.

---

## YouTube

| فایل | نقش | وضعیت |
|---|---|---|
| `data/raw/iran_us_war/youtube_comments_v2.jsonl` (HF008) | **مرجع v2 (Authoritative)** | جاری؛ `author_hash` با فرمول v05 (backfill ۲۰۲۶-۰۸-۱۲) |
| `data/raw/iran_us_war/youtube_raw_export.csv` (HF009) | Export مشتق‌شده از HF008 (فرمت `raw_schema_v03` CSV) | همان رکوردهای HF008، فرمت متفاوت — نه additive |
| `data/raw/iran_us_war/youtube_comments_1404-12-09_to_ongoing.jsonl` (HF007) | **مرجع v1 (Frozen ۲۰۲۶-۰۸-۰۷)** | ⚠️ هنوز `author_display_name` خام دارد (PII remediation نشده)؛ `author_hash` فرمول قدیمی |
| `data/raw/backup_2026-07-25/...` (HF004) | Backup — Superseded by HF007 | استفاده نشود |
| `archive_before_reset_2026-07-26/...` (HF005, HF006) | Backup — Superseded by HF007 | استفاده نشود |
| `archive_before_author_hash_v05_backfill_2026-08-12/youtube_comments_v2.jsonl` (HF019) | Backup — نسخه‌ی پیش از backfill فرمول `author_hash` | **استفاده نشود** — `author_hash` ناسازگار با فرمول فعلی |
| `youtube_runs.csv`, `youtube_skipped_videos.csv`, `video_geo_metadata.jsonl`, `resolved_channels.json`, `checkpoint.json` | Run Log / Side-file / Config | نه Raw content؛ در `join_and_clean.py`/`apply_eligibility.py` به‌عنوان محتوا خوانده نمی‌شوند |

**تصمیم:** HF007 (v1) و HF008 (v2) هر دو مرجع‌اند و باید **هر دو** به `raw_harmonized`
برسند (کد فعلی این کار را می‌کند — `backfill_raw_harmonized_v05.py`، طبق
`docs/decision_log.md` ۲۰۲۶-۰۸-۱۴)؛ آن‌ها دو Collector متوالی روی همان دامنه‌اند،
نه یک فایل و مشتقاتش. Overlap واقعی بین v1/v2 (۷۳,۸۳۷ رکورد طبق یادداشت
`collection_coverage.csv`) در مرحله‌ی Exact-ID dedup (`apply_eligibility.py`)
حذف می‌شود، نه اینجا.

## Reddit

| فایل | نقش | وضعیت |
|---|---|---|
| `data/raw_original/reddit/records/reddit_raw_schema.csv` (HF012) | **مرجع (Delivered handoff)** | ۱۵۸,۹۵۹ ردیف؛ `language_reported`/`language_detected` هر دو ۱۰۰٪ خالی در تحویل اصلی |
| `data/raw/reddit/{reddit_comments_v1.jsonl, reddit_raw_export.csv}` (HF013) | Derived از HF012 توسط `handoff_csv_to_record.py` | مرجع برای Pipeline (`join_and_clean.py` از این می‌خواند)؛ `language_detected` با heuristic پرشده |
| ⚠️ Run Log مستقل | **موجود نیست** | Audit فقط از خود رکوردهای خام بازسازی شده؛ Query/Sort/Pagination واقعی مستند نیست |

## X

| فایل | نقش | وضعیت |
|---|---|---|
| `data/raw_original/x/records/X_Scraper_v4_7_Target20K_Current.xlsx` (HF010) | **مرجع (Delivered handoff)**، شیت `Raw_Tweets` | ۱۶,۴۷۵ ردیف؛ شیت‌های `Jobs`/`Subruns`/`Query_Week_Audit` منبع واقعی `query_execution_audit.csv` (۶۲۲ ردیف) هستند |
| `data/raw/x/{x_comments_v1.jsonl, x_raw_export.csv}` (HF011) | Derived از HF010 توسط `handoff_csv_to_record.py` | مرجع برای Pipeline؛ PII (`author_username`/`tweet_url`) حذف شده |

---

## نکته‌ی SHA-256 تصحیح‌شده (۲۰۲۶-۰۸-۱۴)

مقدار `sha256`/`file_size_bytes` ثبت‌شده برای HF009 (YouTube) و HF010 (X) در
ممیزی امروز با محاسبه‌ی مستقیم (`hashlib`) اصلاح شد — مقدار قبلی توسط
هم‌تیمی بدون دسترسی مستقیم به فایل ثبت شده بود و مطابقت نداشت (جزئیات در
`docs/data_handoff_manifest.csv`'s ردیف‌های HF009/HF010). **خروجی‌های
مشتق‌شده از این دو فایل که پیش از ۲۰۲۶-۰۸-۱۴ ساخته شده‌اند، دوباره در برابر
Hash تصحیح‌شده verify نشده‌اند** — یک Open item، نه یک باگ حل‌شده.
