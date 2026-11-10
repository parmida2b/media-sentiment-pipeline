# فهرست نهایی یافته‌ها (مرحله ۵)

> منبع جزئیات هر مورد: `02-baseline.md` (C-01..C-03)، `03-static-analysis.md` (C-04..C-07)، `04-integration.md` (C-08..C-14)، `05-deep-review.md` (C-15..C-24).
> وضعیت‌ها: **بازتولید** = با اجرای کد خود پروژه دیده شد؛ **مستند** = با `فایل:خط` ثابت شد ولی اجرا نشد؛ **باز** = نیاز به داده/پاسخ تیم.
> هیچ کدی هنوز تغییر نکرده است. مرحله‌ی ۶ (اصلاح) فقط با تأیید کاربر.

## بحرانی — نتیجه‌ی تحقیق را تغییر می‌دهند

| ID | یافته | محل | وضعیت | اثر |
|---|---|---|---|---|
| **C-08** | ردیف‌های legacy یوتیوب (بدون `platform_content_id`) هرگز به annotation نمی‌رسند؛ اصلاح ۱۴ اوت نیمه‌کاره ماند | `src/annotation/run_full_annotation.py:207-211` در برابر `build_annotated_dataset.py:118-121` | **بازتولید**؛ اعداد §۷.۱ گزارش دقیقاً بازسازی شد (۲۳۳,۰۰۶ / ۶۴ / ۶۰ / ۴ / ۷,۴۴۷) | ۵۴,۸۶۲ ردیف = ۴۵٪ یوتیوب؛ W01–W07 تا ۹۷٪؛ «کم‌داده»ی W03/W04/W07 در گزارش محصول باگ است؛ نمونه‌ی یوتیوب سوگیر به collector جدید |
| **C-09** | Pipeline B «ردیف (content×target)» می‌شمارد نه «محتوا»؛ stance روی همه‌ی Targetها مخلوط | `weekly_trend.py` (`n=len(week_df)`)، `descriptive_stats`, `composition_shift`, `group_comparison`, `sensitivity_analysis`, `build_social_weekly_outcomes` | **بازتولید** (۲ محتوا ← n=4، سهم 0.75 به‌جای 0.50)؛ **باز**: فعال بودن در اعداد منتشرشده | با `--targets T01,T02,T03` (که راهنمای رسمی توصیه می‌کند) n چندبرابر، CIها باریک، سهم‌ها سوگیر؛ شواهد حضور T02 در داده‌ی منتشرشده هست (۴۳+۳ ردیف EV-016؛ ۹,۴۰۵ ردیف ok در برابر ۷,۴۴۷ رکورد نمونه) |

## مهم

| ID | یافته | محل | وضعیت |
|---|---|---|---|
| **C-15** | CI اختلاف نسبت با Wald: در n کوچک ۵× باریک‌تر، `[0,0]` برای صفرها، مثبت کاذب (۵/۱۰→۹/۱۰) | `src/event_analysis/event_study.py:82-96` | بازتولید (مقایسه با Newcombe) |
| **C-22** | collector یوتیوب حداکثر ۵ پاسخ برای هر رشته؛ `comments.list(parentId)` هرگز صدا زده نمی‌شود | `src/ingestion/youtube_extract.py:367-445` | بازتولید روی داده: ≥۱۰,۳۷۱ پاسخ (۳۵.۶٪) دست‌نیافتنی |
| **C-23** | watermark = جدیدترینِ pool ۱۵۰۰تایی ← کامنت‌های بین دو اجرا فراتر از pool برای همیشه جا می‌مانند | `youtube_extract.py:139, 1195-1196`; `incremental_state.py:68-72` | مستند (اندازه نامعلوم؛ ۱۶۱/۶۴۳ ویدیو کاندیدا) |
| **C-17** | `automation_risk_share` از ستون تماماً null «۰٪ با CI [0, 0.088]» می‌سازد | `src/temporal_analysis/build_social_weekly_outcomes.py:99-104` + `build_annotated_dataset.py:193` | بازتولید |
| **C-19** | سقف $۱۰۰ فقط per-session؛ resume/shardهای موازی هرکدام سقف جدا؛ ادعای «hard cap» در مستندات دقیق نیست | `run_full_annotation.py:367, 404-414` | مستند |
| **C-01** | `group_comparison` بدون ردیف annotated با `ValueError` می‌شکند و زنجیره‌ی Pipeline B را متوقف می‌کند | `src/temporal_analysis/group_comparison.py:164-166, 274` | بازتولید (اجرای pipeline) |
| **C-10** | «آخرین تلاش برنده است» تضمین نمی‌شود (sort ناپایدار؛ «آخرین» = ترتیب فایل نه زمان) | `src/annotation/build_annotated_dataset.py:150-151` | بازتولید (۲۰٪ تلاش قدیمی نگه داشته شد)؛ فعال‌شدن با تغییر `--num-shards` (C-19) |
| **C-04** | کد `AUTHOR_HASH_SALT` می‌خواند؛ مشخصات schema و `.env.example` `PROJECT_AUTHOR_SALT` هم دارند؛ fallback = Salt عمومی ثابت | `src/ingestion/author_hash.py:31,38`; `.env.example:13-14`; `docs/raw_schema_v0{3,5}.md` | مستند؛ احتمال پایین، پیامد سنگین (hash قابل بازسازی)؛ **باز**: کدام Salt استفاده شده |
| **C-16** | بدون تصحیح FDR در group_comparison/event_study، با اینکه چک‌لیست قفلش کرده (بخش مالی دارد) | `group_comparison.py`, `event_study.py`; `docs/archive/checklist.md:328,592` | مستند |

## جزئی

| ID | یافته | محل |
|---|---|---|
| C-21 | exceptionهای worker annotation بی‌صدا بلعیده می‌شوند (`future.result()` صدا زده نمی‌شود) | `run_full_annotation.py:432-438` — بازتولید الگو |
| C-20 | برخورد cache هزینه‌ی تماس اصلی را دوباره ثبت می‌کند | `llm_client.py:353-354`; `run_full_annotation.py:405` — بازتولید |
| C-18 | نرمال‌سازی فارسی: ZWNJ حذف، ي/ك یکسان نه، PII ~۹۹٪ مثبت کاذب (تاریخ/عدد ← `[PHONE]`) | `src/preprocessing/normalize_text.py:73,80` — بازتولید |
| C-13 | `build_labeling_sample` برای ردیف بدون شناسه `content_id=""` (Gold فعلی سالم) | `build_labeling_sample.py:197` |
| C-24 | `author_id_status` در `yt_*` تماماً null | collector یوتیوب |
| C-05 | `python-dotenv==1.0.1` آسیب‌پذیر (PYSEC-2026-2270)؛ تابع آسیب‌پذیر استفاده نمی‌شود | `requirements.txt` |
| C-06 | `yfinance` pin نشده | `requirements.txt:11` |
| C-07 | hygiene: ۱۲ import اضافه، ۴ f-string، متغیر/کد مرده، `raise` بدون `from`، `rate_limit_events` ثبت‌نشده | ruff/vulture |
| C-02 | `harmonize` بدون رکورد exit 1 می‌دهد ولی `[PASS]` چاپ می‌کند و دلیلی نمی‌گوید | `backfill_raw_harmonized_v05.py:264-268` |
| C-11 | `docs/architecture.md` می‌گوید raw_harmonized هنوز v03 است؛ کد و داده v05‌اند | مستندات |
| C-12 | README «برای موضوع جدید فقط config.yaml» — پنجره/هفته/رویدادها hardcode (عمداً) | مستندات |

## سؤال‌های باز برای تیم
1. **C-09:** فایل‌های `outputs/full_annotation/*.jsonl` یا `annotated_dataset.parquet`ی که گزارش با آن ساخته شد — برای تعیین اینکه چند Target در داده هست.
2. **C-14:** گزارش `n_total = 289,717`، بازسازی از ریپو `287,868` (اختلاف ۱,۸۴۹) — parquet منتشرشده از کدام وضعیت داده/کد ساخته شد؟
3. **C-04:** داده با `AUTHOR_HASH_SALT` واقعی جمع شد یا fallback؟
4. **C-23:** فایل state collector یوتیوب (watermarkها) برای سنجش اندازه‌ی شکاف.

## رد شده (بررسی شد، باگ نیست)
C-03 (idempotency — آزموده شد)، `geo_confidence` رشته‌ای (مطابق v05)، `Groq` F821 (annotation رشته‌ای)، ۱۳ هشدار پرسیگنال mypy، هشدار detect-secrets، `duplicate_text_diff_id` (واقعاً بولین)، مسیریابی eligibility، اعتبارسنجی خروجی LLM، سازگاری تاریخ‌ها، schema هر ۶ فایل raw_harmonized، حسابرسی ردیف‌ها (۳۳۳,۳۹۹ → ۲۸۷,۸۶۸ بدون گم‌شدن)، نمونه‌ی Gold فعلی.

---

## برنامه‌ی پیشنهادی مرحله‌ی ۶ (منتظر تأیید)
قاعده: برای هر مورد **اول تست بازتولید** (باید قبل از اصلاح fail شود)، بعد اصلاح، بعد اجرای کل `pytest` + pipeline روی کپی؛ هر مورد یک commit.

**دسته‌ی ۱ — کد خالص، بدون هزینه، بیشترین اثر**
| ID | اصلاح پیشنهادی | تست بازتولید |
|---|---|---|
| C-08 (+C-13) | `load_eligible_records` و `build_labeling_sample` همان fallback پل (`uid::<record_uid>`) را بسازند | هر ردیف eligible دارای متن در جمعیت annotation باشد |
| C-09 | در Pipeline B: محورهای sentiment/emotion/content_type یک ردیف به‌ازای `content_id`؛ stance با فیلتر صریح Target (پیش‌فرض T01) | مثال ۲ محتوا ← n=2، سهم 0.50 |
| C-15 | Newcombe به‌جای Wald در `diff_of_proportions_ci` | ۰/۴۰→۰/۵ نباید `[0,0]` بدهد؛ ۵/۱۰→۹/۱۰ باید صفر را شامل شود |
| C-17 | ستون تماماً null ← NaN + وضعیت `not_available` | ۴۰ ردیف با `is_flagged_bot_suspect=None` ← NaN نه 0.0 |
| C-01 | محافظ «داده‌ی خالی» در تست‌های `group_comparison` ← ردیف not_computable (الگوی `engagement_not_applicable_row`) | `run()` بدون ردیف ok نباید exception بدهد |
| C-10 | `sort_values(["_ok_rank","annotated_at_utc"], kind="stable")` | دو تلاش ok ← همیشه جدیدتر |

**دسته‌ی ۲ — annotation/هزینه:** C-19 (سقف تجمعی از `cost_usd` همه‌ی فایل‌های shard)، C-20 (cache ← cost 0)، C-21 (`future.result()` + شمارش خطا؛ قفل مشترک set/save).

**دسته‌ی ۳ — کیفیت/مستندات:** C-16 (BH-FDR)، C-18 (نگه‌داشتن ZWNJ، یکسان‌سازی ي/ك، الگوی تلفن محدودتر)، C-04 (یک نام Salt + خطای بلند به‌جای fallback)، C-05/C-06 (وابستگی‌ها)، C-02، C-07، C-11، C-12.

**نیاز به تصمیم تیم (کد قابل اصلاح است، ولی داده/هزینه لازم دارد)**
- بعد از C-08: annotation دوباره‌ی سلول‌های آسیب‌دیده‌ی یوتیوب (هزینه‌ی LLM).
- C-22/C-23: اصلاح collector ممکن است (comments.list برای رشته‌های >۵ پاسخ؛ watermark هنگام پر شدن pool جلو نرود) ولی بازیابی داده یعنی جمع‌آوری دوباره (quota API).
- اصلاح C-08/C-09/C-15 اعداد گزارش فنی را تغییر می‌دهد ← `reports/technical_report_fa.md` (§۷، §۱۰، ادعاهای C1–C3) باید به‌روز شود.
