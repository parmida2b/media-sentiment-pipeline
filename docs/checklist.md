فاز اول: دریافت و تثبیت داده خام

۱. Freeze فایل‌های اصلی

* هر پلتفرم پوشه مستقل داشته باشد.  
* فایل اصلی بازنویسی نشود.  
* Cleaning روی نسخه کپی‌شده انجام شود.  
* فایل آزمایشی، Log، Database، Export و Backup از هم تفکیک شوند.  
* هیچ مقدار نامعلوم از روی حدس تکمیل نشود.

ساختار پیشنهادی:

data/raw\_original/x/  
data/raw\_original/reddit/  
data/raw\_original/youtube/

۲. ساخت File Inventory

برای هر فایل ثبت شود:

* نام و مسیر  
* پلتفرم  
* نوع فایل  
* اندازه فایل  
* SHA-256  
* زمان دریافت  
* تحویل‌دهنده  
* نقش فایل: Raw، Log، Config، Code، Test یا Derived

خروجی:

data\_handoff\_manifest.csv

۳. تشخیص فایل مرجع

برای هر پلتفرم مشخص شود:

* فایل اصلی رکوردها کدام است؟  
* کدام فایل Export مشتق‌شده است؟  
* کدام فایل Summary یا Audit است؟  
* آیا چند Export شامل رکوردهای یکسان هستند؟  
* آیا SQLite، CSV و Excel نسخه‌های متفاوت یک Dataset هستند؟

فایل‌های مختلف بدون بررسی با هم Concatenate نمی‌شوند.

---

فاز دوم: بازسازی روش واقعی Collection

۴. ممیزی Collector و Run Log

برای هر پلتفرم استخراج شود:

* نسخه Collector  
* تاریخ و ساعت اجرا  
* Queryهای واقعاً اجراشده  
* Query version  
* Source، Channel یا Subreddit  
* Sort واقعی  
* Pagination  
* Cap  
* تعداد Scroll یا Page  
* Retry و Failure  
* Data cutoff  
* تعداد رکورد برگشتی  
* Rate limit یا شکاف دسترسی

خروجی:

query\_execution\_audit.csv  
observed\_collection\_manifest.csv

۵. تعریف Sampling Frame واقعی

Sampling Frame باید براساس شواهد واقعی بازسازی شود:

* X: نتایج Search/Hashtag/Conversation اجراشده  
* Reddit: Submissionهای کشف‌شده و Comment/Replyهای قابل دریافت  
* YouTube: Videoهای کشف‌شده و Comment/Replyهای قابل دریافت

نام روش Collection:

> نمونه‌گیری غیراحتمالی مبتنی بر Query و Source، همراه با نمونه در دسترس ناشی از محدودیت پلتفرم.

این داده‌ها نمونه احتمالی مردم جهان نیستند و Margin of Sampling Error جمعیتی برای آن‌ها محاسبه نمی‌شود.

---

فاز سوم: Profile و کیفیت داده خام

۶. Profile اولیه هر فایل

بدون حذف یا Cleaning محاسبه شود:

* تعداد ردیف و ستون  
* نام ستون‌ها  
* نوع داده هر ستون  
* تعداد مقدار یکتا  
* تعداد و درصد Missing  
* تعداد متن خالی  
* تعداد \[deleted\] و \[removed\]  
* تعداد Timestamp قابل Parse و غیرقابل Parse  
* حداقل و حداکثر Timestamp  
* تعداد رکورد خارج از بازه  
* تعداد ID یکتا و تکراری  
* خطاهای Encoding و Parse  
* مصرف حافظه

۷. آمار Coverage

برای هر پلتفرم، هفته، Query و Source:

* raw\_n  
* unique\_id\_n  
* eligible\_n  
* تعداد روزهای دارای داده  
* اولین و آخرین Timestamp  
* تعداد Parent یکتا  
* تعداد Source یکتا  
* تعداد نویسنده یکتا، در صورت دسترسی  
* Missing ID، Timestamp، Text، Query و Source  
* تعداد Run موفق و ناموفق  
* Duplicate rate  
* Failure rate  
* Data gap

بازه رسمی فعلی:

2026-02-28 تا 2026-07-22  
W01 تا W21

فقط W21 پنج‌روزه و ناقص است.

خروجی:

collection\_coverage.csv

۸. درجه قابلیت استفاده

هر فایل یا رکورد درجه‌بندی شود:

| درجه | کاربرد |
| ----: | ----: |
| A | همه تحلیل‌های مجاز |
| B | تحلیل اصلی با گزارش Provenance ناقص |
| C | تحلیل توصیفی یا محدود |
| D | قرنطینه |

---

فاز چهارم: Harmonization

۹. نگاشت Schema

برای هر پلتفرم مشخص شود هر ستون هدف:

* مستقیم موجود است؛  
* فقط Rename لازم دارد؛  
* تبدیل قطعی لازم دارد؛  
* با قاعده قطعی مشتق می‌شود؛  
* Missing است؛  
* برای پلتفرم کاربرد ندارد.

فیلدهای کلیدی مشترک:

platform  
platform\_content\_id  
content\_type  
created\_at\_utc  
collected\_at\_utc  
text\_raw  
author\_hash  
query\_id  
query\_version  
collection\_run\_id  
source\_id  
source\_parent\_id  
parent\_id  
discovery\_route  
project\_week  
in\_window  
is\_partial\_week

خروجی:

schema\_mapping\_x.csv  
schema\_mapping\_reddit.csv  
schema\_mapping\_youtube.csv

۱۰. ساخت raw\_harmonized

* متن خام تغییر نکند.  
* Timestamp فقط با Time zone مستند به UTC تبدیل شود.  
* نوع محتوا حفظ شود.  
* Queryهای چندگانه در matched\_query\_ids نگهداری شوند.  
* Platform-specific fieldها از بین نروند.  
* مقدار نامعلوم unknown یا Missing باقی بماند.  
* تبدیل‌ها دارای نسخه باشند.

معادله کنترل:

input\_rows  
\= harmonized\_rows  
\+ parse\_quarantine\_rows  
---

فاز پنجم: Cleaning و Eligibility

۱۱. پردازش متن

در لایه مشتق‌شده:

* Unicode normalization  
* اصلاح فاصله و Control Character  
* تشخیص زبان  
* استخراج URL، Mention، Hashtag و Emoji  
* ثبت طول متن  
* حفظ Code-switching  
* Mask کردن PII احتمالی  
* حفظ text\_raw  
* ساخت text\_normalized  
* ثبت preprocessing\_version

۱۲. بررسی Duplicate

سه حالت جدا شوند:

1. Exact ID duplicate  
2. متن یکسان با ID متفاوت  
3. Near-duplicate

قواعد:

* ID یکسان: فقط یک رکورد اصلی  
* یک ID با چند Query: یک رکورد با matched\_query\_ids  
* متن یکسان با ID متفاوت: نگهداری همراه Flag  
* Near-duplicate: نگهداری همراه Cluster  
* Repost بدون متن: audit\_only

آمار لازم:

* تعداد و نرخ Exact duplicate  
* تعداد و نرخ Unique text  
* تعداد Near-duplicate cluster  
* بزرگ‌ترین Cluster  
* نرخ Duplicate به تفکیک هفته و پلتفرم

۱۳. اجرای Eligibility

ترتیب:

Raw validation  
→ Exact-ID deduplication  
→ Date rule  
→ Text availability  
→ Provenance  
→ Topic relevance  
→ Analysis role

خروجی‌های اصلی:

* opinion\_main  
* opinion\_limited  
* opinion\_untimed  
* context\_only  
* audit\_only  
* quarantine

قواعد پلتفرمی:

* X original/reply/quote دارای متن: Opinion  
* X repost بدون متن: Audit only  
* Reddit comment/reply: Opinion  
* Reddit Submission متنی: جداگانه Opinion  
* Reddit Submission بدون متن مستقل: Context only  
* YouTube comment/reply: Opinion  
* YouTube video: Context only  
* Deleted/removed: Audit only

۱۴. Relevance Audit انسانی

برای هر پلتفرم یک نمونه تصادفی از Included و Excluded بررسی شود.

حداقل:

* ۳۰ رکورد در هر پلتفرم، با پوشش هر دو گروه  
* ثبت relevant، not\_relevant یا uncertain  
* محاسبه Precision تصمیم Inclusion  
* محاسبه نرخ Exclusion اشتباه  
* بررسی خطا به تفکیک Query و Source

اگر نرخ خطا زیاد باشد، Rule اصلاح و Eligibility دوباره اجرا می‌شود.

۱۵. Spam و Automation Risk

به‌جای حکم قطعی Bot بودن:

* automation\_risk\_score  
* spam\_rule\_flag  
* high\_frequency\_author\_flag  
* near\_duplicate\_cluster\_id  
* URL/Hashtag frequency  
* الگوی زمانی غیرعادی  
* نرخ Repost  
* سن حساب، در صورت دسترسی

محتوای پرریسک خودکار حذف نمی‌شود؛ تحلیل اصلی با و بدون آن تکرار می‌شود.

---

فاز ششم: قفل تصمیم‌های آماری

۱۶. تصمیم‌هایی که قبل از Full Annotation قفل می‌شوند

* Targetهای اصلی Stance  
* Labelهای Sentiment، Stance، Emotion، Topic و Content Type  
* روش Gold Sampling  
* Random seed  
* Confidence threshold  
* مدل و Prompt  
* حداقل حجم گزارش  
* رویدادهای اصلی  
* Event window  
* شاخص‌های مالی  
* Lagها  
* آزمون‌های آماری  
* Effect size  
* FDR correction  
* تحلیل‌های حساسیت

Targetهای اصلی فعلی:

* T01: تشدید یا اقدام نظامی  
* T02: مذاکره، آتش‌بس و دیپلماسی  
* T03: تحریم و فشار اقتصادی

T04 تا T06 در صورت کیفیت کافی Gold Sample تکمیلی‌اند.

---

فاز هفتم: Gold Sample و ارزیابی انسانی

۱۷. انتخاب Gold Sample

مبدأ:

eligible\_content

روش:

* تصادفی طبقه‌بندی‌شده  
* طبقات اصلی: Platform و Language  
* پوشش پنج بخش زمانی  
* پوشش Sourceهای بزرگ  
* Seed ثابت: 1405

حجم پایه:

* ۳۰۰ رکورد  
* ۱۰۰ رکورد برای هر پلتفرم  
* ۱۲۰ رکورد Double annotation  
* ۴۰ رکورد مشترک در هر پلتفرم

۱۸. توافق Annotatorها

برای Sentiment و Stance جداگانه:

* Percent Agreement  
* Cohen’s Kappa  
* ماتریس اختلاف  
* تعداد موارد Adjudication  
* توزیع کلاس‌ها  
* Agreement به تفکیک زبان و پلتفرم، در صورت حجم کافی

Percent Agreement به‌تنهایی کافی نیست.

---

فاز هشتم: ارزیابی مدل Annotation

۱۹. Pilot مدل

روی حداقل ۱۰۰ رکورد Gold Sample:

* Precision هر کلاس  
* Recall هر کلاس  
* F1 هر کلاس  
* Macro-F1  
* Accuracy به‌عنوان معیار تکمیلی  
* Confusion Matrix  
* Coverage پس از Confidence threshold  
* JSON failure rate  
* API failure rate  
* Cost per 1,000  
* Latency per 1,000

ارزیابی ترجیحاً به تفکیک:

* پلتفرم  
* زبان  
* Content type  
* طول متن  
* Target  
* Quote/Sarcasm

مدل و Threshold پس از Pilot قفل می‌شوند.

۲۰. Full Annotation

برای تمام eligible\_content:

* Sentiment  
* Stance همراه Target  
* Emotion  
* Topic  
* Content Type  
* Confidence  
* Model version  
* Prompt version  
* Failure status  
* Cost و Latency  
* Cache status

خروجی نامعتبر JSON وارد تحلیل نمی‌شود.

---

فاز نهم: آمار توصیفی

۲۱. آمار کل نمونه و هر پلتفرم

برای کل Dataset، هر پلتفرم و هر هفته:

* تعداد Raw، Harmonized و Eligible  
* تعداد محتوا، Parent و Author یکتا  
* تعداد Source و Query  
* نرخ Missing  
* نرخ Duplicate و Near-duplicate  
* میانه و IQR طول متن  
* میانه و IQR Engagement  
* سهم زبان‌ها  
* سهم Sourceها  
* سهم نوع محتوا  
* سهم Opinion/News/Quotation/Spam  
* سهم Automation risk  
* تعداد و سهم هر Label

برای متغیرهای چوله مانند Engagement، Median و IQR مهم‌تر از Mean هستند.

---

فاز دهم: روند زمانی

۲۲. روند هفتگی

برای هر پلتفرم جداگانه و هر Label:

project\_week  
n  
class\_count  
class\_proportion  
95% Wilson CI

نمودارهای اصلی:

* حجم هفتگی  
* Sentiment share  
* Stance share برای هر Target  
* Emotion share  
* Topic share  
* Content type  
* سهم زبان  
* سهم Automation risk

قواعد:

* هفته با n \< 30 فقط توصیفی و با علامت نمونه کم  
* W21 به‌عنوان هفته ناقص علامت‌گذاری شود  
* حجم خام W21 با هفته کامل مقایسه نشود  
* Data gap روی نمودار نمایش داده شود

در صورت وجود وابستگی:

* Cluster bootstrap براساس author\_hash  
* یا Cluster bootstrap براساس source\_parent\_id

---

فاز یازدهم: Composition Shift

۲۳. بررسی تغییر ترکیب نمونه

برای هر هفته محاسبه شود:

* سهم هر پلتفرم  
* سهم Sourceهای اصلی  
* سهم زبان‌ها  
* سهم News در برابر Personal opinion  
* سهم Queryها و Query version  
* سهم Duplicate  
* سهم کاربران پرتکرار  
* سهم محتوای پرریسک  
* سهم بزرگ‌ترین Parent

Trend خام با یکی از این موارد مقایسه شود:

* Stratified trend  
* Author-balanced trend  
* Parent-balanced sensitivity  
* Shared-period comparison

هدف این است که مشخص شود تغییر Trend ناشی از تغییر نگرش است یا تغییر ترکیب داده.

---

فاز دوازدهم: مقایسه گروه‌ها

۲۴. آزمون‌های آماری مجاز

| سؤال | آزمون | Effect size |
| ----: | ----: | ----: |
| تفاوت توزیع Stance میان پلتفرم‌ها/زبان‌ها | Chi-square | Cramér’s V |
| جدول کوچک ۲×۲ | Fisher’s Exact | Odds Ratio با CI |
| تفاوت Engagement دو گروه | Mann–Whitney U | Rank-biserial correlation |
| مقایسه Mean دو گروه مستقل | Welch’s t-test | Hedges’ g یا Cohen’s d |

برای هر آزمون گزارش شود:

* n  
* Estimate  
* Confidence interval  
* Effect size  
* p-value  
* فرض‌های آزمون  
* محدودیت وابستگی رکوردها

فقط p \< 0.05 گزارش نمی‌شود.

---

فاز سیزدهم: تحلیل رویداد

۲۵. Event Analysis

* ۳ تا ۶ رویداد تأییدشده  
* رویدادها از قبل در Event Registry ثبت شوند  
* Outcome اصلی: سهم Stance مرتبط  
* Window اصلی: دو هفته قبل و دو هفته بعد  
* Sensitivity: یک و سه هفته قبل/بعد  
* اختلاف سهم قبل و بعد همراه CI  
* حجم محتوا و Composition در همان Window  
* تحلیل جداگانه هر پلتفرم  
* حذف بزرگ‌ترین Parent/Near-duplicate به‌عنوان حساسیت  
* Placebo event در صورت امکان

نتیجه به‌صورت «همراهی زمانی» گزارش می‌شود، نه اثر علّی.

---

فاز چهاردهم: تحلیل مالی

۲۶. هم‌ترازی داده مالی

برای شاخص‌های منتخب:

* تاریخ و منبع  
* فرکانس  
* Missing  
* تعطیلات بازار  
* تبدیل به تغییر یا بازده هفتگی  
* هم‌ترازی با هفته‌های شبکه اجتماعی

از سطح قیمت برای Correlation اصلی استفاده نمی‌شود.

۲۷. آزمون مالی

روش اصلی:

* Spearman correlation  
* Lag صفر، یک و دو هفته  
* Bootstrap CI  
* تعداد هفته‌های مشترک

Sensitivity:

* Pearson correlation  
* حذف هفته‌های ناقص  
* Window یا شاخص جایگزین

اصلاح آزمون‌های متعدد:

Benjamini-Hochberg FDR

خروجی:

* ضریب  
* CI  
* p-value خام  
* p-value تعدیل‌شده  
* تعداد هفته‌های هم‌تراز

---

فاز پانزدهم: تحلیل حساسیت

حداقل شش مقایسه:

* با و بدون Duplicate/Near-duplicate  
* با و بدون Automation risk بالا  
* همه Labelها در برابر Confidence بالا  
* Content-level در برابر Author-balanced  
* با و بدون بزرگ‌ترین Source یا Parent  
* Spearman در برابر Pearson  
* Event window یک، دو و سه هفته‌ای  
* هر پلتفرم جدا در برابر Pooled observed  
* بازه کامل هر پلتفرم در برابر بازه مشترک سه پلتفرم  
* Unweighted در برابر Engagement-weighted با log1p و Cap

---

خروجی‌های نهایی اجباری

در پایان باید این موارد موجود باشند:

1. File inventory و Hash داده خام  
2. Collection Manifest  
3. Query Execution Audit  
4. Schema Mapping سه پلتفرم  
5. Collection Coverage  
6. Raw Validation Report  
7. Record Flow  
8. Eligibility Audit  
9. Relevance Audit  
10. Gold Sample  
11. Agreement Report  
12. Model Evaluation Report  
13. Annotated Dataset  
14. جدول‌های توصیفی  
15. روندهای هفتگی با n و CI  
16. Composition Shift  
17. Event Analysis  
18. Financial Analysis  
19. حداقل شش Sensitivity Analysis  
20. Claim Registry  
21. Notebook نهایی قابل اجرای کامل  
22. گزارش و ارائه حداکثر ده‌دقیقه‌ای

ترتیب Notebookهای پیشنهادی

برای جلوگیری از سردرگمی:

01\_data\_intake\_and\_harmonization.ipynb  
02\_eligibility\_and\_relevance\_audit.ipynb  
03\_gold\_sample\_and\_model\_evaluation.ipynb  
04\_full\_annotation.ipynb  
05\_descriptive\_and\_temporal\_analysis.ipynb  
06\_event\_and\_financial\_analysis.ipynb  
07\_sensitivity\_and\_final\_claims.ipynb

همین مراحل ابتدا برای هر پلتفرم جداگانه اجرا می‌شوند و سپس Notebook مقایسه سه‌پلتفرمی ساخته می‌شود. مهم‌ترین اصل آماری این پروژه آن است که تحلیل اصلی X، Reddit و YouTube جدا باشد و تجمیع سه پلتفرم فقط به‌عنوان خلاصه نمونه مشاهده‌شده گزارش شود.

