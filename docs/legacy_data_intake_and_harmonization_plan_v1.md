# برنامه دریافت و هماهنگ‌سازی داده‌های جمع‌آوری‌شده

**نسخه:** 1.0  
**پلتفرم‌ها:** X، Reddit و YouTube  
**هدف:** استفاده صحیح و قابل دفاع از داده موجود، بدون جمع‌آوری مجدد

## ۱. تصمیم اجرایی

داده سه همکار به‌عنوان داده تاریخی ثابت پذیرفته می‌شود. هدف، اثبات انطباق کامل گذشته با نسخه جدید نیست؛ هدف این است که مشخص شود چه چیزی جمع‌آوری شده، چگونه می‌توان آن را به Schema مشترک نگاشت کرد و کدام تحلیل‌ها با آن قابل دفاع‌اند.

چهار اصل اجرا می‌شود:

1. فایل اصلی بازنویسی نمی‌شود؛
2. مقدار نامعلوم حدس زده نمی‌شود؛
3. نقص یک فیلد به حذف کل فایل منجر نمی‌شود؛
4. دامنه تحلیل با کیفیت واقعی داده تطبیق داده می‌شود.

## ۲. بسته‌ای که از هر همکار دریافت می‌شود

هر همکار یک پوشه مستقل تحویل می‌دهد:

```text
handoff/{platform}/
  raw_files/
  collector_code/
  run_logs/
  config_without_secrets/
  README_handoff.md
```

`README_handoff.md` شامل این موارد است:

- نام همکار و Platform؛
- تاریخ‌های تقریبی اجرای Collection؛
- نسخه `raw_schema` و `query_registry` دریافتی؛
- نام ابزار، API، Dataset یا روش Collection؛
- Queryها و Sourceهای استفاده‌شده، تا حدی که مدرک موجود است؛
- Sort، Pagination، Cap و خطاهای شناخته‌شده؛
- فایل‌های کامل، ناقص یا آزمایشی؛
- تعریف ستون‌هایی که نام آن‌ها روشن نیست.

Token، Password، Cookie، API key و Salt تحویل داده نمی‌شود.

## ۳. مرحله Freeze و Inventory

برای هر فایل پیش از بازکردن تحلیلی ثبت می‌شود:

| مورد | خروجی |
|---|---|
| نام و مسیر نسبی | `original_file_name` |
| Platform | x/reddit/youtube |
| نوع فایل | csv/json/jsonl/parquet/xlsx/other |
| اندازه بایت | `file_size_bytes` |
| Hash | `sha256` |
| زمان دریافت | `received_at_utc` |
| مالک تحویل | `provided_by` |
| نقش فایل | raw/log/config/code/test/unknown |

نسخه اصلی در `data/raw_original/{platform}` قرار می‌گیرد و Read-only تلقی می‌شود. همه تبدیل‌ها به مسیر جدید نوشته می‌شوند.

## ۴. Profile اولیه بدون تغییر داده

برای هر فایل داده این موارد گزارش می‌شود:

- تعداد ردیف و ستون؛
- نام و نوع مشاهده‌شده ستون‌ها؛
- پنج مقدار نمونه امن از هر ستون غیرحساس؛
- درصد Missing؛
- تعداد ID یکتا و تکراری؛
- حداقل و حداکثر Timestamp قابل Parse؛
- Encoding و خطاهای Parse؛
- تعداد متن خالی، حذف‌شده و بسیار کوتاه؛
- تعداد ردیف خارج از بازه؛
- حجم به تفکیک روز و هفته؛
- سازگاری تعداد ردیف با Log یا توضیح همکار.

در این مرحله Cleaning، Deduplication یا حذف انجام نمی‌شود.

## ۵. نگاشت Schema

برای هر Platform یک فایل Mapping تکمیل می‌شود. هر ستون هدف یکی از وضعیت‌های زیر را می‌گیرد:

| وضعیت | تعریف |
|---|---|
| `direct` | ستون مبدأ مستقیم و هم‌معناست |
| `renamed` | فقط نام متفاوت است |
| `converted` | تبدیل قطعی نوع یا Timestamp لازم است |
| `derived` | با قاعده قطعی از چند فیلد ساخته می‌شود |
| `missing` | در داده و شواهد جانبی وجود ندارد |
| `not_applicable` | برای آن Platform کاربرد ندارد |

هر تبدیل باید مثال ورودی، مثال خروجی و Rule داشته باشد. Timestamp محلی فقط با Time zone مستند به UTC تبدیل می‌شود. اگر Time zone معلوم نباشد، Timestamp نامطمئن و رکورد از تحلیل زمانی اصلی کنار گذاشته می‌شود.

## ۶. بازسازی Provenance

ترتیب اعتبار شواهد برای بازسازی Query، Source و Run:

1. Run log یا Metadata ذخیره‌شده؛
2. Config و کد Collector؛
3. فیلد مستقیم در داده؛
4. نام فایل یا ساختار پوشه، اگر Convention از قبل مستند باشد؛
5. توضیح مکتوب همکار؛
6. `unknown`.

Query دقیق از `query_registry` تحویلی کپی می‌شود، اما `executed_verified` فقط زمانی ثبت می‌شود که اجرای آن در Log، Config یا Metadata قابل مشاهده باشد. Source مرجع نیز با Source مشاهده‌شده یکسان فرض نمی‌شود.

## ۷. درجه‌بندی قابلیت استفاده

### درجه A — کامل

متن، ID پلتفرمی، Timestamp، Platform و Provenance اصلی موجود و سازگار است. داده برای روند، رویداد، مقایسه درون پلتفرم و Annotation قابل استفاده است.

### درجه B — قابل استفاده با Provenance بازسازی‌شده

متن، ID، Timestamp و Platform موجود است؛ بخشی از Query، Source یا Run با مدرک جانبی بازسازی شده است. داده وارد تحلیل اصلی می‌شود و تحلیل حساسیت بدون رکوردهای B گزارش می‌شود.

### درجه C — استفاده محدود

متن موجود است، اما ID پلتفرمی، Timestamp یا Provenance مهم ناقص است. کاربرد ممکن است به تحلیل توصیفی، Annotation یا پیوست محدود شود. رکورد بدون Timestamp وارد Trend یا Event window نمی‌شود.

### درجه D — قرنطینه

فایل خراب، داده آزمایشی، خروجی تکراری غیرقابل آشتی یا رکورد فاقد متن قابل استفاده است. فایل حذف نمی‌شود؛ علت قرنطینه ثبت می‌شود.

## ۸. قواعد تبدیل Platform-specific

### X

- ID اصلی محتوا، `conversation_id` و ارجاع Reply/Quote جدا می‌شوند؛
- Repost بدون متن Opinion محسوب نمی‌شود؛
- زمان ایجاد محتوا با زمان Collection جایگزین نمی‌شود؛
- اگر داده فقط نتیجه Search را دارد، Timeline کامل حساب ادعا نمی‌شود.

### Reddit

- Submission، Comment و Reply از هم تفکیک می‌شوند؛
- `subreddit`، `submission_id` و `parent_id` در صورت وجود حفظ می‌شوند؛
- `[deleted]` و `[removed]` متن معتبر Opinion نیستند؛
- Score یا Sort به‌عنوان احتمال نمونه‌گیری تفسیر نمی‌شود.

### YouTube

- Video metadata از Comment/Reply جدا می‌شود؛
- `video_id` Parent و `channel_id` Source است؛
- تاریخ Comment مبنای هفته است، نه تاریخ Video؛
- Like count و Reply count Snapshot زمان Collection هستند.

## ۹. آشتی تعداد رکوردها

برای هر فایل این معادله باید برقرار باشد:

```text
input_rows
= harmonized_rows
+ parse_quarantine_rows
```

پس از Eligibility:

```text
harmonized_rows
= opinion_main
+ opinion_limited
+ opinion_untimed
+ context_only
+ audit_only
+ excluded
+ duplicate_exact
```

اگر یک ردیف در چند خروجی حساسیت حضور دارد، در جدول Flow فقط یک وضعیت اصلی می‌گیرد.

## ۱۰. گزارش Coverage

برای هر Platform و هفته ثبت می‌شود:

- `raw_n`، `unique_id_n` و `eligible_n`؛
- تعداد روز دارای داده؛
- Source و Parentهای یکتا؛
- قدیمی‌ترین و جدیدترین Timestamp؛
- Missing ID، Timestamp، Text، Query و Source؛
- Duplicate rate؛
- تعداد خطاهای Collection؛
- درجه A تا D.

اگر سه پلتفرم بازه مشترک کامل نداشته باشند، دو نتیجه ارائه می‌شود: نتیجه هر پلتفرم در پوشش خودش و مقایسه سه‌پلتفرمی در بازه مشترک.

## ۱۱. Gate پیش از تحلیل آماری

تحلیل نهایی فقط پس از تکمیل موارد زیر آغاز می‌شود:

1. Hash تمام Raw files ثبت شده باشد؛
2. Mapping سه پلتفرم بازبینی شده باشد؛
3. شمار ردیف‌ها آشتی داده شده باشد؛
4. Coverage و Missingness گزارش شده باشد؛
5. Query و Source مشاهده‌شده از مرجع تفکیک شده باشد؛
6. Eligibility روی نسخه هماهنگ‌شده اجرا شده باشد؛
7. طرح آماری و Event Registry پیش از مشاهده خروجی برچسب‌گذاری قفل شده باشد؛
8. Gold Sample با Seed ثبت‌شده انتخاب شده باشد.

## ۱۲. تصمیم آماری در برابر نقص داده

| نقص | تصمیم |
|---|---|
| Timestamp ناقص | حذف از Trend/Event/Financial alignment؛ حفظ در توصیف محدود |
| Author ID ناقص | حذف تحلیل Author-balanced؛ استفاده از Parent sensitivity در صورت امکان |
| Query نامعلوم | گزارش Composition ناقص و تحلیل حساسیت بر اساس Provenance |
| Source نامعلوم | حفظ Platform-level؛ حذف Source-level comparison برای رکورد متاثر |
| هفته‌های خالی | نمایش Gap؛ عدم درون‌یابی برای آزمون اصلی |
| Platform بسیار کوچک | گزارش توصیفی؛ عدم اتکا به آزمون کم‌توان |
| Class بسیار کوچک | ادغام فقط با دلیل مفهومی یا گزارش توصیفی |
| حجم نامتوازن Platform | تحلیل جداگانه؛ Pooled فقط خلاصه نمونه موجود |

## ۱۳. خروجی مرحله Intake

1. `data_handoff_manifest.csv`
2. `schema_mapping_{platform}.csv`
3. `query_execution_audit.csv`
4. `observed_source_registry.csv`
5. `collection_coverage.csv`
6. `raw_validation_report.md`
7. `record_flow.csv`
8. سه فایل `raw_harmonized`
9. Decision Log شامل همه موارد نامعلوم و تصمیم‌های محدودکننده تحلیل

پس از تحویل فایل‌ها، ابتدا این خروجی‌ها ساخته می‌شوند. هیچ نیاز پیش‌فرضی به Collection مجدد وجود ندارد.
