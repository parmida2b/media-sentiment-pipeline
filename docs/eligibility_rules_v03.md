# قواعد ورود و خروج داده

**دامنه:** X، Reddit و YouTube  
**بازه:** `2026-02-28T00:00:00Z` تا `2026-07-22T23:59:59Z`

---

## ۱. هدف

این سند تعیین می‌کند کدام رکوردهای بازیابی‌شده وارد Dataset تحلیلی می‌شوند. Raw data تغییر نمی‌کند. وضعیت Eligibility و دلیل خروج در جدول Audit جداگانه ثبت می‌شود.

## ۲. ترتیب اجرا

```text
Raw validation
→ Exact-ID deduplication
→ Date rule
→ Text availability
→ Provenance rule
→ Topic relevance
→ Analysis-role rule
→ Analytical datasets
```

## ۳. شرط عمومی ورود

یک رکورد زمانی وارد `opinion_main` می‌شود که:

1. `platform` یکی از `x`، `reddit` یا `youtube` باشد؛
2. `created_at_utc` داخل بازه پروژه باشد؛
3. `platform_content_id` یا `record_uid` قطعی موجود باشد؛
4. متن خام موجود و قابل خواندن باشد؛
5. منشأ فایل و Platform قابل ممیزی باشد؛
6. متن یا زمینه والد با موضوع مطالعه ارتباط معنادار داشته باشد؛
7. رکورد Exact duplicate نباشد.

اتصال کامل به Query، Source و Run برای کیفیت Provenance مهم است، اما نبود بخشی از آن در داده تاریخی به‌تنهایی رکورد متنی معتبر را حذف نمی‌کند.
در این حالت `provenance_quality = partial` ثبت و تحلیل با و بدون این رکوردها تکرار می‌شود.

رکورد دارای متن مرتبط اما فاقد Timestamp معتبر وارد `opinion_untimed` می‌شود و در روند هفتگی، Window رویداد یا تحلیل مالی استفاده نمی‌شود. رکورد بدون ID پلتفرمی، تا زمانی که فقط `record_uid` دارد، در تحلیل حساسیت جداگانه نگهداری می‌شود.

### ۳.۱ تصمیم مخصوص فایل‌های تحویلی تیم

- نقص Schema با Missing data یکی است، نه مدرک نامعتبر بودن کل داده.
- مقدار گمشده از روی متن، نام فایل یا حافظه همکار حدس زده نمی‌شود؛ فقط تبدیل قطعی و مستند مجاز است.
- رکوردهای مشکوک در `quarantine` نگهداری می‌شوند و حذف فیزیکی نمی‌شوند.
- شمار رکوردهای Main، Limited، Untimed، Context-only، Audit-only و Quarantine برای هر پلتفرم گزارش می‌شود.

### ۳.۲ تعریف نقش تحلیلی رکورد

| نقش | تعریف | استفاده |
|---|---|---|
| `opinion` | محتوای دارای متن مستقل و قابل تفسیر که می‌تواند برای Sentiment، Stance، Emotion یا Topic برچسب بخورد | Dataset اصلی یا محدود |
| `context_only` | رکوردی که متن مستقلِ واحد تحلیل نیست، اما زمینه Parent را فراهم می‌کند؛ مانند Metadata ویدئوی YouTube یا Submission بدون متن مستقل | اتصال و تفسیر Commentها |
| `audit_only` | رکوردی که فقط برای مستندسازی Collection نگهداری می‌شود؛ مانند Repost بدون متن یا محتوای حذف‌شده | شمارش و گزارش کیفیت، نه Annotation نگرش |

`opinion` به معنای وجود موضع صریح یا احساسی نیست. یک متن مستقل می‌تواند در Annotation برچسب `neutral`، `unclear` یا `unrelated` بگیرد. سه نقش بالا برای تصمیم اصلی Eligibility از هم جدا هستند.

## ۴. قواعد نوع محتوا

| پلتفرم و نوع | Opinion Dataset | نقش/تصمیم | توضیح |
|---|---:|---|---|
| X original post | بله | `opinion` | در صورت داشتن متن مستقل |
| X reply | بله | `opinion` | در صورت داشتن متن مستقل |
| X quote | بله | `opinion` | فقط متن افزوده تحلیل می‌شود |
| X repost بدون متن | خیر | `audit_only` | انتشار بدون نظر جدید؛ تعداد آن گزارش می‌شود |
| Reddit submission دارای عنوان یا Self-text مرتبط | بله، در لایه Post | `opinion` | جدا از Comment گزارش می‌شود |
| Reddit submission بدون متن مستقل | خیر | `context_only` | فقط زمینه Thread |
| Reddit comment/reply | بله | `opinion` | واحد اصلی Reddit |
| YouTube comment/reply | بله | `opinion` | تاریخ خود Comment مبناست |
| YouTube video | خیر | `context_only` | Parent context و Metadata |
| deleted/removed | خیر | `audit_only` | فقط Raw و گزارش کیفیت |

نتیجه Post و Comment در یک پلتفرم بدون حفظ `content_type` ادغام نمی‌شود.

## ۵. دامنه موضوعی

### داخل دامنه

- مناقشه ایران و آمریکا و اقدام نظامی مرتبط؛
- مذاکره، آتش‌بس و دیپلماسی؛
- تحریم، انرژی و پیامد اقتصادی مرتبط؛
- پیامد انسانی و واکنش بین‌المللی؛
- رسانه، اطلاعات نادرست یا روایت مرتبط با مناقشه؛
- واکنش به رویداد معتبر Event Registry.

### خارج از دامنه

- اشاره تصادفی یا نامرتبط به Iran/America؛
- محتوای تاریخی بدون ارتباط روشن با بازه؛
- تبلیغ تجاری یا Spam نامرتبط؛
- متن خالی، `[deleted]`، `[removed]` یا غیرقابل بازیابی؛
- داده آزمایشی یا تولیدشده توسط مدل.

متن کوتاه فقط به‌دلیل طول حذف نمی‌شود.

## ۶. بازه و تعریف هفته‌ها

هفته‌های پروژه از تاریخ شروع و در دوره‌های هفت‌روزه متوالی ساخته می‌شوند. فقط هفته پایانی ناقص است.

| هفته | بازه | تعداد روز | وضعیت |
|---|---|---:|---|
| `W01` | `2026-02-28` تا `2026-03-06` | ۷ | کامل |
| `W02` تا `W19` | دوره‌های متوالی هفت‌روزه | ۷ | کامل |
| `W20` | `2026-07-11` تا `2026-07-17` | ۷ | کامل |
| `W21` | `2026-07-18` تا `2026-07-22` | ۵ | ناقص |

فقط رکوردهای `W21` با `is_partial_week = true` علامت می‌خورند. رکوردهای این هفته Eligible هستند، اما حجم خام `W21` مستقیماً با حجم هفته‌های کامل مقایسه نمی‌شود.

## ۷. Relevance audit

ارتباط موضوعی در دو مرحله سنجیده می‌شود:

1. Rule-based screening با Query و Parent context؛
2. بازبینی انسانی نمونه تصادفی Included و Excluded به تفکیک پلتفرم.

برای هر پلتفرم حداقل ۳۰ رکورد بازبینی می‌شود. Precision تصمیم Inclusion و نرخ Exclusion اشتباه گزارش می‌شود.

## ۸. Duplicate و متن مشابه

| وضعیت | تصمیم اصلی | حساسیت |
|---|---|---|
| ID یکسان در همان پلتفرم | یک رکورد | — |
| یک ID با چند Query | یک رکورد + `matched_query_ids` | — |
| متن یکسان با ID متفاوت | نگهداری + Flag | `unique_text` |
| متن بسیار مشابه | نگهداری + Cluster | با و بدون Near-duplicate |
| Repost بدون متن | `audit_only` | تعداد و سهم آن جداگانه گزارش می‌شود |

کلید Exact deduplication:

```text
platform + platform_content_id
```

## ۹. Spam و Automation Risk

محتوای پرریسک به‌طور خودکار از تحلیل اصلی حذف نمی‌شود، مگر آنکه خارج از دامنه یا فاقد متن معتبر باشد. فیلدهای زیر برای تحلیل حساسیت استفاده می‌شوند:

- `spam_rule_flag`
- `near_duplicate_cluster_id`
- `automation_risk_score`
- `high_frequency_author_flag`

## ۱۰. زبان

هیچ رکوردی فقط به‌دلیل زبان حذف نمی‌شود. مقادیر پیشنهادی:

`en` · `fa` · `ar` · `other` · `unknown`

تحلیل نگرش یک زبان فقط زمانی وارد نتیجه اصلی می‌شود که مدل در Gold Sample همان زبان و پلتفرم ارزیابی شده باشد.

## ۱۱. دلایل خروج

| کد | تعریف |
|---|---|
| `out_of_window` | خارج از بازه |
| `invalid_content_type` | نوع نامعتبر برای Dataset هدف |
| `empty_text` | متن غیرقابل استفاده |
| `deleted_or_removed` | محتوا حذف یا غیرقابل دسترسی |
| `out_of_scope` | ارتباط موضوعی کافی ندارد |
| `missing_content_id` | شناسه محتوا موجود نیست |
| `invalid_provenance` | Run/Query/Source قابل ممیزی نیست |
| `missing_timestamp` | زمان معتبر برای تحلیل زمانی موجود نیست |
| `limited_provenance` | قابل استفاده با Provenance ناقص؛ دلیل خروج کامل نیست |
| `surrogate_id_only` | فقط `record_uid` مشتق‌شده موجود است؛ تحلیل حساسیت |
| `duplicate_exact_id` | ID تکراری |
| `repost_only` | خارج از Opinion و نگهداری به‌صورت `audit_only` |
| `synthetic_or_test` | داده آزمایشی یا تولیدشده |
| `other_documented` | دلیل مستند دیگر |

## ۱۲. جدول Audit

| فیلد | تعریف |
|---|---|
| `platform` | پلتفرم |
| `platform_content_id` | شناسه رکورد |
| `record_uid` | کلید ردیابی داخلی، در صورت نبود ID پلتفرمی |
| `eligible` | True فقط برای رکورد قابل ورود به یکی از Datasetهای Opinion؛ برای `context_only` و `audit_only` برابر False |
| `dataset_target` | opinion_main/opinion_limited/opinion_untimed/context_only/audit_only/quarantine/neither |
| `primary_exclusion_reason` | دلیل اصلی |
| `secondary_exclusion_reasons` | دلایل دیگر |
| `rule_version` | نسخه سند |
| `decided_at_utc` | زمان تصمیم |
| `review_status` | automatic/manual/adjudicated |
| `notes` | توضیح ضروری |

## ۱۳. گزارش Eligibility

به تفکیک پلتفرم، هفته و Source گزارش می‌شود:

- تعداد Raw، ID یکتا و Eligible
- تعداد و درصد هر دلیل خروج
- نرخ Duplicate/Near-duplicate
- تعداد و سهم `repost_only`، `context_only` و `audit_only`
- تعداد رکوردهای زبان ارزیابی‌نشده
- نتیجه Relevance audit

هر تغییر Rule با نسخه جدید ثبت می‌شود و Datasetهای متاثر دوباره ساخته می‌شوند.
