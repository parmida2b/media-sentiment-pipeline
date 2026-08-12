# فصل سوم — انتخاب پلتفرم و توجیه منبع

**پلتفرم‌ها:** X، Reddit و YouTube  
**بازه:** `2026-02-28` تا `2026-07-22`

---

## ۱. تصمیم پلتفرم

سه پلتفرم برای پوشش سه نوع متفاوت از گفت‌وگوی عمومی انتخاب شده‌اند:

| پلتفرم | نقش در مطالعه | ویژگی متمایزکننده |
|---|---|---|
| X | واکنش سریع به رویداد | محتوای کوتاه، Reply و Quote |
| Reddit | بحث Threadمحور و توضیحی | ساختار Submission–Comment–Reply |
| YouTube | واکنش به محتوای خبری و رسانه‌ای | Commentهای وابسته به Video/Channel |

تعریف رسمی واحدهای تحلیل در فصل اول و Sampling frame هر پلتفرم در فصل دوم آمده است.

## ۲. معیار انتخاب

| معیار | الزام |
|---|---|
| دسترسی مجاز | API، Dataset یا روش تأییدشده و ثبت‌شده |
| پوشش زمانی | امکان بازیابی بخشی قابل گزارش از بازه پروژه |
| متن مستقل | مناسب برای Sentiment و Stance |
| Timestamp | قابل تبدیل به UTC |
| شناسه پایدار | برای Deduplication |
| زمینه محتوا | Parent/Conversation/Video در صورت امکان |
| قابلیت ممیزی | Query، Source و Collection Run قابل ثبت |

## ۳. مسیر جمع‌آوری

مسیرهای زیر طرح مرجع پروژه‌اند. مسیر واقعاً اجراشده برای هر همکار فقط پس از بررسی فایل، کد و Log در `observed_collection_manifest` ثبت می‌شود.
نبود مدرک با `unknown` ثبت می‌شود و با مسیر مرجع جایگزین نمی‌شود.

### ۳.۱ X

مسیر اصلی Query-first است. Queryهای متنی و هشتگ‌های مکمل با مرتب‌سازی زمانی یا Recent اجرا می‌شوند.
Timeline حساب‌های رسانه‌ای یا رسمی فقط برای کشف واژگان و رویداد استفاده می‌شود و به‌تنهایی جامعه Opinion نیست.

### ۳.۲ Reddit

Submission با Query یا Source ثبت‌شده کشف می‌شود و سپس Comment/Reply همان Thread دریافت می‌شود.
مسیر سراسری و Source-scoped با `discovery_route` جدا می‌شوند.

### ۳.۳ YouTube

Video از Query و Channelهای ثبت‌شده کشف می‌شود؛ سپس Comment و Reply دریافت می‌شود
. خود Video واحد Opinion نیست و تاریخ Comment، نه تاریخ Video، مبنای هفته تحلیل است.

## ۴. منابع و Registry

| پلتفرم | Source Unit | فیلد Registry |
|---|---|---|
| X | Search scope، Conversation یا Seed account | `source_id` |
| Reddit | Subreddit و Submission | `source_id`, `source_parent_id` |
| YouTube | Channel و Video | `source_id`, `source_parent_id` |

هر Source باید نام/ID پلتفرمی، دسته، زبان اصلی، وضعیت، ریسک انتخاب و `verified_at_utc` داشته باشد.
Source حذف‌شده از Registry پاک نمی‌شود؛ Status آن تغییر می‌کند.

## ۵. محدودیت‌ها و کنترل‌ها

| محدودیت | پلتفرم | کنترل |
|---|---|---|
| Search/Keyword bias | همه | Query familyهای متوازن و Precision audit |
| Ranking bias | همه | Recent/New/Date/Time و ثبت Sort واقعی |
| Power-user bias | X، Reddit | Author-balanced و Cluster Bootstrap |
| Channel selection | YouTube | تنوع رسانه‌ای و سهم هفتگی Channel |
| Subreddit selection | Reddit | مسیر کشف سراسری و Source-scoped جدا |
| Hashtag bias | X | هشتگ فقط مسیر مکمل |
| Moderation/deletion | Reddit، YouTube | ثبت Missing و Data Gap |
| Quota/rate limit | همه | Run Manifest و Coverage زمانی |
| Language imbalance | همه | ارزیابی مدل به تفکیک زبان |
| Viral parent content | Reddit، YouTube | Leave-one-parent-out |

## ۶. Engagement

متریک‌های تعامل بین پلتفرم‌ها هم‌مقیاس نیستند.
Like، Score، Reply و Share به‌عنوان موافقت تفسیر نمی‌شوند.

تحلیل اصلی Unweighted است. تحلیل Engagement-weighted فقط درون همان پلتفرم، با `log1p` و Cap از پیش تعیین‌شده، به‌عنوان حساسیت اجرا می‌شود.

## ۷. اصول مقایسه و تجمیع پلتفرم‌ها

سه نوع گزارش از هم تفکیک می‌شوند:

1. **Platform-specific:** نتیجه اصلی و ترجیحی؛
2. **Pooled observed:** همه رکوردها با وزن یکسان، فقط خلاصه نمونه موجود؛
3. **Equal-platform weighted:** هر پلتفرم یک‌سوم، فقط تحلیل حساسیت.

تفاوت مشاهده‌شده، تفاوت میان نمونه‌های پلتفرمی است و به تفاوت قطعی میان جمعیت کشورها تعبیر نمی‌شود. روش آماری مقایسه، کنترل Composition و قواعد CI در فصل دوم تعریف شده‌اند.

## ۸. جغرافیا

مکان فقط با Geotag یا شواهد مستقیم ثبت می‌شود. زبان، Channel، Subreddit یا Time Zone به‌تنهایی کشور نویسنده نیست. اگر پوشش معتبر مکانی کافی نباشد، تحلیل جغرافیایی از گزارش اصلی حذف می‌شود.

## ۹. معیار کفایت داده

برای هر پلتفرم پیش از تحلیل نهایی گزارش می‌شود:

- تعداد Run موفق و ناموفق
- قدیمی‌ترین و جدیدترین Timestamp
- تعداد رکورد Raw و Eligible
- تعداد هفته‌های دارای داده
- سهم Sourceهای اصلی
- پوشش `author_hash`
- سهم زبان‌ها
- نرخ Duplicate، Missing و Failure
- محدودیت دسترسی تاریخی

پلتفرمی که Coverage کافی ندارد حذف نمی‌شود؛ به‌عنوان تحلیل محدود یا پیوست گزارش می‌شود و در نتیجه تجمیعی نقش تعیین‌کننده نمی‌گیرد.

اگر یکی از پلتفرم‌ها فقط بخشی از بازه را پوشش دهد، مقایسه سه‌پلتفرمی روی بازه مشترک تکرار می‌شود. تحلیل کامل همان پلتفرم نیز جداگانه حفظ می‌شود تا داده موجود از بین نرود.

## ۱۰. منابع رسمی دسترسی

- X Developer Platform: <https://docs.x.com/>
- Reddit Data API Terms: <https://redditinc.com/policies/data-api-terms>
- Reddit Developer Terms: <https://redditinc.com/policies/developer-terms>
- YouTube Data API: <https://developers.google.com/youtube/v3>
- YouTube Data API Quota: <https://developers.google.com/youtube/v3/determine_quota_cost>

## ۱۱. نتیجه

استفاده از سه پلتفرم برای مقایسه محیط‌های گفت‌وگو مناسب است، مشروط به اینکه Provenance حفظ شود، تحلیل‌ها ابتدا جداگانه باشند و هیچ وزن نمایندگی جمعیتی به پلتفرم‌ها نسبت داده نشود.
