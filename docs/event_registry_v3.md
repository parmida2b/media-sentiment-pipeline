# رجیستری رویدادها

**بازه پروژه:** `2026-02-28` تا `2026-07-22`  
**نسخه:** `v3`  
**کاربرد:** ثبت رویدادهای مرتبط با تفسیر روند، تعیین رویدادهای آزمون تأییدی و مستندسازی رویدادهای زمینه‌ای و اختلال‌های داده

---

## ۱. منطق رجیستری

هر رویداد در این رجیستری دو ویژگی جداگانه دارد که نباید با یکدیگر اشتباه شوند:

1. **`analysis_role` یا نقش تحلیلی:** مشخص می‌کند رویداد در تحلیل پروژه چگونه استفاده می‌شود؛ برای مثال، آیا رویداد اصلی مقایسه آماری قبل/بعد است، فقط روی نمودار علامت‌گذاری می‌شود، یا صرفاً برای تفسیر زمینه و Coverage نگهداری شده است.
2. **`verification_status` یا وضعیت تأیید منبع:** مشخص می‌کند از نظر منابع تا چه اندازه مطمئن هستیم رویداد با همین ادعا و همین تاریخ رخ داده است.

در نتیجه، «تأییدشدن رویداد» الزاماً به معنی «اجرای آزمون آماری مستقل برای آن» نیست. یک رویداد می‌تواند با دو منبع مستقل کاملاً تأیید شده باشد، اما چون جزء فرضیه‌های اصلی پروژه نیست، فقط نقش `secondary_confirmed` داشته باشد.

> قاعده ساده: `verification_status` درباره **اعتبار مدرک رویداد** است؛ `analysis_role` درباره **نحوه استفاده از رویداد در تحلیل** است.

وجود یک رویداد در رجیستری به معنی اجرای آزمون آماری مستقل برای آن نیست. رویدادها براساس نقش تحلیلی در یکی از گروه‌های زیر قرار می‌گیرند:

| `analysis_role` | کاربرد |
|---|---|
| `study_anchor` | نقطه آغاز مطالعه؛ فاقد دوره پیشارویداد در داده |
| `primary_confirmatory` | رویداد از پیش انتخاب‌شده برای مقایسه اصلی قبل/بعد |
| `secondary_confirmed` | رویداد تأییدشده برای تفسیر روند، Annotation نمودار و تحلیل اکتشافی |
| `context_only` | مناسبت یا ادعای رسانه‌ای مؤثر بر تفسیر؛ بدون آزمون تأییدی مستقل |
| `data_artifact` | رویدادی که Coverage یا قابلیت جمع‌آوری را تغییر می‌دهد |
| `not_verified` | رویدادی که پس از جست‌وجو مدرک کافی برای همان تاریخ و همان ادعا ندارد |
| `out_of_window` | رویداد خارج از بازه پروژه |

این تفکیک مانع اجرای تعداد زیادی آزمون هم‌پوشان و انتخاب رویداد صرفاً براساس Spike مشاهده‌شده می‌شود.

## ۲. معیار تأیید و وضعیت منبع

این بخش فقط کیفیت و نوع شواهد مربوط به وقوع رویداد را نشان می‌دهد و درباره اصلی یا فرعی‌بودن تحلیل آماری تصمیم نمی‌گیرد. برای مثال:

- رویدادی با `confirmed_2plus` می‌تواند `primary_confirmatory` یا `secondary_confirmed` باشد؛
- رویدادی با `confirmed_primary_plus_independent` نیز می‌تواند فقط برای Annotation نمودار استفاده شود؛
- رویدادی با `not_verified_after_search`، صرف‌نظر از اهمیت ظاهری آن، وارد تحلیل رویدادهای تأییدشده نمی‌شود.

### مثال کاربردی

| رویداد | وضعیت تأیید منبع | نقش تحلیلی | تفسیر |
|---|---|---|---|
| `EV-011`؛ برآورد آوارگی موقت | `confirmed_primary_plus_independent` | `secondary_confirmed` | وقوع و رقم اولیه با منبع رسمی و گزارش مستقل پشتیبانی می‌شود، اما برای آن آزمون تأییدی مستقل اجرا نمی‌شود. |
| `EV-025`؛ تفاهم‌نامه اسلام‌آباد | `confirmed_primary_plus_independent` | `primary_confirmatory` | هم از نظر منبع تأیید شده و هم یکی از رویدادهای اصلی مقایسه آماری قبل/بعد است. |
| `EV-055`؛ نوروز | `context_only` | `context_only` | برای توضیح تغییر احتمالی حجم و ترکیب محتوای فارسی ثبت می‌شود، نه برای آزمون اثر یک رویداد جنگی. |

| `verification_status` | تعریف | مجاز در تحلیل اصلی؟ |
|---|---|---|
| `confirmed_2plus` | دو منبع مستقل، اصل رویداد و تاریخ را تأیید می‌کنند | بله، مشروط به نقش تحلیلی |
| `confirmed_primary_plus_independent` | یک منبع رسمی/اولیه و یک منبع خبری مستقل | بله، مشروط به نقش تحلیلی |
| `confirmed_direct_plus_news` | متن مستقیم یک اظهارنظر و گزارش مستقل از انتشار آن | فقط برای رویداد رسانه‌ای |
| `reported_disputed` | اصل گزارش وجود دارد، اما تاریخ، انتساب یا جزئیات مهم محل اختلاف است | فقط زمینه یا حساسیت |
| `not_verified_after_search` | برای همان ادعا و همان تاریخ مدرک کافی پیدا نشد | خیر |
| `context_only` | منبع برای ثبت زمینه کافی است، نه برای آزمون اثر رویداد | خیر |
| `out_of_window` | خارج از بازه پروژه | خیر |

بازنشر یک گزارش Reuters، AP یا AFP در چند وب‌سایت، چند منبع مستقل محسوب نمی‌شود. عنوان رویداد باید فقط بخشی را بیان کند که منابع واقعاً تأیید کرده‌اند. اگر وقوع حمله تأیید، اما مسئولیت آن محل اختلاف باشد، عنوان خنثی نوشته می‌شود و اختلاف انتساب در یادداشت می‌آید.

## ۳. قرارداد فیلدها

فیلدهای رجیستری به دو گروه تقسیم می‌شوند. فیلدهای پایه برای تمام ردیف‌ها لازم‌اند؛ فیلدهای آزمون فقط برای رویدادهایی تکمیل می‌شوند که واقعاً وارد مقایسه آماری اصلی می‌شوند. خالی‌بودن یک فیلد شرطی برای نقش‌های دیگر، نقص داده محسوب نمی‌شود و با `—` نمایش داده می‌شود.

| فیلد | تعریف | الزام |
|---|---|---|
| `event_id` | شناسه پایدار و یکتای رویداد | همه ردیف‌ها |
| `event_date_utc` | تاریخ آغاز رویداد به شکل `YYYY-MM-DD` | همه ردیف‌ها |
| `event_end_date_utc` | تاریخ پایان رویداد چندروزه؛ برای رویداد یک‌روزه خالی | شرطی |
| `project_week` | `W01` تا `W21`، یا `PRE` و `OUT` | همه ردیف‌ها |
| `event_type` | یکی از `military`، `diplomatic`، `political`، `economic`، `humanitarian`، `media`، `calendar` یا `infrastructure` | همه ردیف‌ها |
| `title_fa` | عنوان کوتاه، دقیق و خنثی | همه ردیف‌ها |
| `analysis_role` | یکی از نقش‌های تعریف‌شده در بخش ۱ | همه ردیف‌ها |
| `verification_status` | یکی از وضعیت‌های تعریف‌شده در بخش ۲ | همه ردیف‌ها |
| `source_1_url` | مدرک اول؛ ترجیحاً منبع رسمی/اولیه یا خبرگزاری معتبر | رویدادهای خبری، تحلیلی و Data Artifactها |
| `source_2_url` | مدرک مستقل دوم؛ بازنشر همان گزارش، منبع مستقل نیست | رویدادهای تأییدشده؛ برای مناسبت تقویمی یک مرجع رسمی کافی است |
| `attribution_note` | توضیح اختلاف درباره مسئولیت، تاریخ، دامنه ادعا یا محدودیت مدرک؛ در صورت نبود اختلاف خالی | شرطی |
| `target_id` | Target مربوط به Stance | فقط `study_anchor` یا `primary_confirmatory` در صورت ارتباط |
| `primary_outcome` | Outcome اصلی از پیش تعیین‌شده | `primary_confirmatory`؛ برای `study_anchor` شاخص توصیفی |
| `expected_direction` | جهت تغییر مورد انتظار که پیش از مشاهده نتیجه نهایی تعیین شده است | فقط `primary_confirmatory` |
| `main_window` | پنجره اصلی مقایسه قبل/بعد | فقط `primary_confirmatory`؛ برای `study_anchor` دوره توصیفی پسارویداد |
| `sensitivity_window` | پنجره زمانی جایگزین برای بررسی پایداری نتیجه | فقط `primary_confirmatory` |

در جدول‌های Markdown، برای خوانایی ممکن است `source_1_url` و `source_2_url` در ستون «منابع» و `attribution_note` در ستون «یادداشت» نمایش داده شوند. همچنین بازه تاریخ ممکن است در یک خانه نوشته شود. هنگام تبدیل رجیستری به DataFrame یا CSV، این مقادیر باید در ستون‌های مستقل بالا قرار گیرند؛ نام فارسی ستون‌های نمایشی، Schema جداگانه‌ای ایجاد نمی‌کند.

## ۴. رویدادهای تحلیل اصلی

| ID | تاریخ آغاز | تاریخ پایان | هفته | نوع | وضعیت تأیید | نقش | عنوان | Target | Outcome اصلی | انتظار پیشینی | پنجره اصلی | پنجره حساسیت |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `EV-001` | `2026-02-28` | — | `W01` | `military` | `confirmed_primary_plus_independent` | `study_anchor` | آغاز حملات گسترده آمریکا و اسرائیل به ایران | `T01` | حجم و ترکیب محتوای روزهای آغاز | — | توصیف پسارویداد | — |
| `EV-016` | `2026-04-07` | — | `W06` | `diplomatic` | `confirmed_2plus` | `primary_confirmatory` | اعلام آتش‌بس دوهفته‌ای | `T02` | سهم حمایت از دیپلماسی | افزایش حمایت و Hope | ۲ هفته قبل/بعد | ۱ هفته قبل/بعد |
| `EV-025` | `2026-06-17` | — | `W16` | `diplomatic` | `confirmed_primary_plus_independent` | `primary_confirmatory` | امضای تفاهم‌نامه اسلام‌آباد | `T02` | سهم حمایت از دیپلماسی | افزایش حمایت و کاهش Fear | ۱ هفته قبل/بعد | ۳ روز قبل/بعد |
| `EV-031` | `2026-06-27` | — | `W18` | `military` | `confirmed_2plus` | `primary_confirmatory` | ازسرگیری حملات متقابل | `T01` | سهم مخالفت با تشدید نظامی | افزایش مخالفت و Fear | ۱ هفته قبل/بعد | ۳ روز قبل/بعد |

پنجره اصلی `EV-025` و `EV-031` یک هفته در نظر گرفته شد، زیرا فاصله این دو رویداد ده روز است و 
پنجره‌های دوهفته‌ای به‌شدت هم‌پوشانی داشتند. حتی با پنجره یک‌هفته‌ای، روزهای نزدیک به هر دو رویداد در یادداشت هم‌پوشانی گزارش می‌شوند و نتیجه به‌صورت علّی تفسیر نمی‌شود.

Windowهای این جدول مخصوص Outcomeهای محتوای شبکه‌های اجتماعی‌اند. تحلیل مالی، به‌دلیل روزهای غیرمعاملاتی و تفاوت تقویم بازار، از سه بازده مشاهده‌شده قبل و سه بازده شامل روز نگاشت‌شده استفاده می‌کند و مطابق سند مالی فقط یک هم‌ترازی توصیفی است؛ بنابراین Window مالی با Window محتوای اجتماعی یکسان فرض نمی‌شود.

### منابع رویدادهای اصلی

- `EV-001`: [Associated Press](https://apnews.com/article/8de8054f3abd4688f894c657467ee3dd) و [سند شورای امنیت سازمان ملل، S/2026/130](https://documents.un.org/api/symbol/access?l=en&s=S%2F2026%2F130&t=pdf)
- `EV-016`: [United Nations Digital Library](https://digitallibrary.un.org/record/4107634) و [Associated Press](https://apnews.com/article/421ee64fdc9a5c26460df8119c7d1b3f)
- `EV-025`: [UN DPPA](https://dppa.un.org/en/speeches-and-statements/un-calls-for-maximum-restraint-to-preserve-ceasefire-between-the) و [Associated Press](https://apnews.com/article/a7ab28d9b34edfaa2061a67616f610bc)
- `EV-031`: [UN DPPA](https://dppa.un.org/en/speeches-and-statements/un-calls-for-maximum-restraint-to-preserve-ceasefire-between-the) و [متن نشست شورای امنیت](https://transcripts.un.org/en/sc/10189/2)

## ۵. سایر رویدادهای ممیزی‌شده

تمام رویدادهایی که جزء چهار رویداد بخش تحلیل اصلی نیستند، در این بخش و در یک رجیستری واحد نگهداری می‌شوند. میزان بررسی موردنیاز برای تأیید هر رویداد، مبنای ایجاد گروه تحلیلی جداگانه نیست. تصمیم استفاده از هر ردیف فقط از روی دو ستون زیر گرفته می‌شود:

- `verification_status`: اعتبار شواهد وقوع رویداد؛
- `analysis_role`: نحوه استفاده از رویداد در تحلیل.

بنابراین همه ردیف‌های دارای نقش `secondary_confirmed`، صرف‌نظر از محل نمایش آن‌ها، کاربرد یکسان دارند: Annotation نمودار و تحلیل اکتشافی، بدون آزمون تأییدی مستقل. ردیف‌های `context_only` فقط برای تفسیر زمینه استفاده می‌شوند و ردیف `not_verified` وارد تحلیل نمی‌شود. برای خوانایی، رجیستری طولانی زیر در دو بلوک جدولِ ادامه‌دار نمایش داده شده است؛ این دو بلوک دو گروه تحلیلی متفاوت نیستند.

| ID | تاریخ نهایی | عنوان نهایی | وضعیت نهایی | نقش | منابع | تصمیم و یادداشت |
|---|---|---|---|---|---|---|
| `EV-041` | `2026-02-27` (`PRE`) | مجوز خروج کارکنان غیرضروری مأموریت آمریکا در اسرائیل | `confirmed_primary_plus_independent` | `context_only` | [U.S. State Department](https://travel.state.gov/content/travel/en/News/visas-news/limited-visa-services-available-at-us-embassy-in-jerusalem-and-branch-office-in-tel-aviv.html) · [Washington Post](https://www.washingtonpost.com/national-security/2026/02/27/us-iran-war-israel-embassy-evacuation//) | عبارت «تخلیه سفارت» دقیق نبود؛ خروج کارکنان غیرضروری و خانواده‌ها مجاز شد. چون پیش از بازه است، فقط زمینه است. |
| `EV-003` | `2026-02-28` | اصابت موشک به مدرسه شجره طیبه در میناب | `confirmed_2plus` | `secondary_confirmed` | [Associated Press](https://apnews.com/article/3f55b6ca193a3295bef5735a45a06368) · [Amnesty International](https://www.amnesty.org/en/latest/news/2026/03/usa-iran-those-responsible-for-deadly-and-unlawful-us-strike-on-school-that-killed-over-100-children-must-be-held-accountable/) | وقوع حمله و تلفات تأیید شده است. شواهد علنی مسئولیت احتمالی آمریکا را تقویت می‌کند، اما نتیجه نهایی تحقیق رسمی منتشر نشده؛ عنوان، مسئول حمله را قطعی اعلام نمی‌کند. |
| `EV-004` | `2026-02-28` | اصابت به سالن ورزشی و مدرسه مجاور در لامرد | `confirmed_2plus` | `secondary_confirmed` | [The World/PRX](https://theworld.org/stories/2026/03/27/more-civilian-casualties-come-to-light-from-a-strike-that-hit-a-sports-hall-killing-children-in-southern-iran) · [Airwars](https://airwars.org/civilian-casualties/jir260228f-february-28-2026/) | وقوع حادثه تأیید شده است. شواهد تصویری منتشرشده انتساب به مهمات آمریکایی را مطرح می‌کند؛ عنوان خنثی باقی می‌ماند. |
| `EV-042` | `2026-02-28` | حملات موشکی ایران به امارات و رهگیری بر فراز ابوظبی و دبی | `confirmed_primary_plus_independent` | `secondary_confirmed` | [UAE Ministry of Foreign Affairs](https://www.mofa.gov.ae/en/MediaHub/News/2026/2/28/UAE-Iran) · [Reuters Connect](https://www.reutersconnect.com/item/missiles-intercepted-over-dubai-after-iran-retaliates-for-israel-us-strikes/dGFnOnJldXRlcnMuY29tLDIwMjY6bmV3c21sX1ZBOTQ4MDI4MDIyMDI2UlAx) | عنوان «حمله به اهدافی در دبی و ابوظبی» بیش از مدرک موجود قطعی بود؛ عنوان بر حمله و رهگیری مستند تمرکز دارد. |
| `EV-043` | `2026-03-02` | ورود حزب‌الله به درگیری با شلیک به اسرائیل | `confirmed_2plus` | `secondary_confirmed` | [Associated Press](https://apnews.com/article/c94313277641ce409718d0a2e7ae2cd2) · [Reuters report](https://www.straitstimes.com/world/middle-east/israeli-military-says-projectiles-were-fired-from-lebanon/) | تاریخ `2026-03-01` نادرست بود؛ منابع آغاز این مرحله را ۲ مارس ثبت کرده‌اند. |
| `EV-044` | `2026-03-01` | آغاز کار شورای موقت رهبری ایران | `confirmed_2plus` | `secondary_confirmed` | [Reuters report](https://www.investing.com/news/world-news/in-khameneis-absence-pragmatist-larijani--emerges-as-power-broker-in-iran-4533479) · [ABC News](https://abcnews.com/International/iran-forms-interim-leadership-council-president-pezeshkian-resurfaces/story?id=130650550) | عبارت «به ریاست لاریجانی» حذف شد؛ ترکیب قانونی شورا با ریاست رسمی لاریجانی یکسان نیست. |
| `EV-045` | `2026-03-01` | اصابت موشک ایران به بیت‌شمش | `confirmed_2plus` | `secondary_confirmed` | [Amnesty International](https://www.amnesty.org/en/latest/news/2026/03/israel-irans-missile-strike-that-killed-nine-civilians-must-be-investigated-as-a-war-crime-new-investigation/) · [EFE](https://efe.com/latest-news/2026-03-01/8-dead-after-iranian-missile-hits-israeli-town-near-jerusalem/) | وقوع، مکان و نوع سلاح با بررسی مستقل تأیید شده است. |
| `EV-046` | `2026-03-01` | آسیب به ورودی‌های تأسیسات زیرزمینی نطنز | `confirmed_2plus` | `secondary_confirmed` | [Institute for Science and International Security](https://isis-online.org/isis-reports/damage-at-the-natanz-uranium-enrichment-plant) · [Reuters report](https://theprint.in/world/iaea-confirms-entrances-to-irans-natanz-enrichment-plant-were-bombed/2868791/) | تصاویر ۲ مارس منتشر شد، اما بازه زمانی حمله از بعدازظهر ۱ مارس تا صبح ۲ مارس برآورد شده است؛ تاریخ آغاز ۱ مارس ثبت می‌شود. |
| `EV-047` | `2026-03-16` | آغاز عملیات زمینی محدود اسرائیل در جنوب لبنان | `confirmed_2plus` | `secondary_confirmed` | [Reuters Connect](https://www.reutersconnect.com/item/wrap-israel-expands-its-ground-campaign-in-lebanon-continues-to-pound-iran/dGFnOnJldXRlcnMuY29tLDIwMjY6bmV3c21sX1ZBNDQ5MDE2MDMyMDI2UlAx/dGFnOnJldXRlcnMuY29tLDIwMjY6bmV3c21sX0xWQTAwSDQ0OTAxNjAzMjAyNlJQMQ) · [Al Jazeera](https://www.aljazeera.com/news/2026/3/16/israeli-military-launches-limited-ground-operations-in-southern-lebanon) | تاریخ ۲ مارس برای حملات متقابل درست بود، اما عملیات زمینی محدود در ۱۶ مارس اعلام شد. هفته از `W01` به `W03` اصلاح می‌شود. |
| `EV-048` | `2026-03-04` | گزارش انهدام یا آسیب چند شناور نیروی دریایی ایران | `confirmed_2plus` | `secondary_confirmed` | [BBC Verify report](https://www.yahoo.com/news/articles/satellite-images-show-iranian-navy-135208742.html) · [Associated Press](https://apnews.com/article/14916ad657e50f048bbeb42b38224ecb) | رویداد یک لحظه واحد در ۳ مارس نبود؛ خسارت چندروزه بود. ۴ مارس تاریخ گزارش مستقل و غرق‌شدن شناور Dena ثبت می‌شود. |
| `EV-049` | `2026-03-03` | ممنوعیت موقت صادرات مواد غذایی و محصولات کشاورزی ایران | `confirmed_2plus` | `secondary_confirmed` | [UK Government country bulletin](https://www.gov.uk/government/publications/iran-country-policy-and-information-notes/country-bulletin-iran-security-situation-march-2026-accessible--2) · [AFP report](https://www.spacewar.com/afp/260303115101.76yp06cs.html) | ممنوعیت صادرات تأیید شد؛ این رویداد به معنی اثبات کمبود بالفعل غذا نیست. |
| `EV-050` | `2026-03-04` | اصابت پرتابه به کشتی تجاری Safeen Prestige در تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [Reuters report](https://www.streetinsider.com/Reuters/Malta-flagged%2Bcontainer%2Bship%2Bhit%2Bby%2Bprojectile%2Bin%2BHormuz%2C%2Bvessel%2Babandoned%2C%2Bsources%2Bsay/26107538.html) · [Lloyd's List](https://www.lloydslist.com/LL1156514/AD-Ports-Group-controlled-feeder-boxship-hit-by-projectile-in-Strait-of-Hormuz) | عنوان جمع «کشتی‌ها» به یک کشتی مشخص و تأییدشده محدود شد. عامل حمله در عنوان تعیین نمی‌شود. |
| `EV-051` | `2026-03-05` | اصابت پهپادها به فرودگاه نخجوان و نزدیکی یک مدرسه | `confirmed_primary_plus_independent` | `secondary_confirmed` | [Azerbaijan Ministry of Foreign Affairs](https://mfa.gov.az/en/news/no07226) · [The Guardian](https://www.theguardian.com/world/2026/mar/05/azerbaijan-accuses-iran-drone-attack-airport-injured-people) | وقوع و مسیر ادعایی از خاک ایران گزارش شد؛ ایران مسئولیت را رد کرد. انتساب قطعی در تحلیل استفاده نمی‌شود. |
| `EV-052` | `2026-03-07` | تصویب فروش اضطراری ۱۵۱٫۸ میلیون دلاری مهمات به اسرائیل | `confirmed_primary_plus_independent` | `secondary_confirmed` | [Associated Press](https://apnews.com/article/fbe9e2321aa2f54fa5bf59b0306b1928) · [U.S. Congressional Record](https://www.govinfo.gov/content/pkg/CREC-2026-04-15/pdf/CREC-2026-04-15-senate.pdf) | مبلغ و نوع فروش تأیید شد؛ نوع رویداد `sanction_policy` نبود و مطابق واژگان کنترل‌شده به `political` اصلاح شد. |
| `EV-053` | `2026-03-08` | حمله به انبارهای سوخت شهران، شهرری و چند سایت پیرامون تهران | `confirmed_2plus` | `secondary_confirmed` | [Human Rights Watch](https://www.hrw.org/news/2026/04/14/iran-israels-oil-depot-strikes-endanger-environment-health) · [ABC News Australia](https://www.abc.net.au/news/2026-03-13/verify-oil-supplies-disrupted-across-middle-east/106448892) | منابع زمان حمله را شب ۷ تا بامداد ۸ مارس گزارش می‌کنند؛ برای تحلیل روزانه تاریخ ۸ مارس حفظ می‌شود. |
| `EV-056` | `2026-03-21` | حمله مجدد به مجموعه نطنز | `confirmed_2plus` | `secondary_confirmed` | [IAEA event report](https://www-news.iaea.org/ErfView.aspx?mId=af2c233e-7ac5-4f41-a5eb-991faa06df2c) · [ISIS imagery report](https://isis-online.org/uploads/isis-reports/documents/Natanz-attack-late-march-2026.pdf) | وقوع آسیب تازه تأیید شد. ایران آمریکا و اسرائیل را مسئول دانست و اسرائیل دخالت خود را رد کرد؛ عنوان خنثی است. |
| `EV-058` | `2026-03-27` | حمله به مجتمع آب سنگین خنداب/اراک | `confirmed_2plus` | `secondary_confirmed` | [ISIS imagery analysis](https://isis-online.org/uploads/isis-reports/documents/Comprehensive-Analysis-of-Nuclear-Related-Facilities-Iran-War-2026-May-7-2026_2026-05-07-192124_gzfh.pdf) · [Iran Watch](https://www.iranwatch.org/news-brief/iran-says-nuclear-facilities-have-been-targeted-after-israel-said-attacks-will-escalate-expand) | وقوع حمله و تأیید طرف‌های ایرانی و اسرائیلی گزارش شده است. عبارت «رآکتور» به «مجتمع آب سنگین» اصلاح شد، زیرا گزارش‌ها هدف دقیق را تفکیک می‌کنند. |
| `EV-060` | `2026-04-11` | عبور دو ناوشکن آمریکا از تنگه هرمز برای ایجاد مسیر کشتیرانی | `confirmed_primary_plus_independent` | `secondary_confirmed` | [Reuters report](https://www.marketscreener.com/news/us-military-says-two-of-its-ships-crossed-through-strait-of-hormuz-ce7e50d9df8bff22) · [USNI News](https://news.usni.org/2026/04/11/two-u-s-warships-sail-through-strait-of-hormuz-to-establish-new-route-for-merchant-ships) | مدرکی برای نام یک «عملیات» رسمی در این تاریخ پیدا نشد؛ عنوان به اقدام مستندشده محدود شد. |
| `EV-061` | `2026-04-15` | ادعای رئیس‌جمهور آمریکا درباره بازکردن دائمی تنگه هرمز | `confirmed_2plus` | `context_only` | [The Independent](https://www.independent.co.uk/news/world/middle-east/donald-trump-xi-jinping-china-iran-war-strait-hormuz-b2958209.html) · [Fortune—پیگیری وضعیت عملی در ۱۷ آوریل](https://fortune.com/2026/04/17/iran-white-house-strait-hormuz-completely-open-but-definitely-remains-closed/) | انتشار ادعای ۱۵ آوریل تأیید شده است؛ این ردیف «ادعای رسانه‌ای» است. اعلام رسمی بازشدن در ۱۷ آوریل و وضعیت عملی کشتیرانی موضوعی جدا بود، بنابراین این رویداد اثبات بازشدن دائمی تنگه نیست. |
| `EV-062` | `2026-05-06` | توقف موقت Project Freedom | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/may/06/trump-project-freedom-strait-of-hormuz-ships-iran-ceasefire) · [ABC News Australia](https://www.abc.net.au/news/2026-05-06/will-project-freedom-restart-shipping-in-strait-of-hormuz-/106646098) | «پایان عملیات» به «توقف موقت» اصلاح شد؛ عملیات ۴ مه آغاز و ۵/۶ مه متوقف شد. [CENTCOM](https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4476318/us-military-supports-launch-of-project-freedom-in-strait-of-hormuz/) تاریخ آغاز را ثبت کرده است. |
| `EV-066` | `2026-06-01` | بن‌بست یک دور مذاکرات | `not_verified_after_search` | `not_verified` | [Pakistan MoFA—تاریخ واقعی گفت‌وگوهای بعد از تفاهم‌نامه](https://mofa.gov.pk/press-releases/technical-level-talks-under-the-islamabad-memorandum-of-understanding) · [DW—بن‌بست مستند مذاکرات آوریل](https://www.dw.com/en/us-iran-talks-what-prevented-a-deal-and-whats-next/a-76755660) | برای دور مذاکره یا بن‌بست مشخص در ۱ ژوئن دو منبع معتبر پیدا نشد. بن‌بست مستند مربوط به ۱۲ آوریل و قبلاً با `EV-019` ثبت شده است؛ این ردیف از تحلیل حذف می‌شود. |
| `EV-067` | `2026-06-07` | تبادل مستقیم آتش ایران و اسرائیل پس از آتش‌بس | `confirmed_2plus` | `secondary_confirmed` | [Reuters report](https://www.investing.com/news/world-news/trump-says-new-israel-iran-strikes-wont-affect-peace-deal-4729741) · [Le Monde](https://www.lemonde.fr/en/international/article/2026/06/08/israel-iran-missile-exchanges-raise-fears-of-fresh-regional-escalation_6754248_4.html) | عنوان «ازسرگیری درگیری» ممکن بود جنگ پایدار را القا کند؛ منابع یک تبادل مستقیم کوتاه و سپس توقف حملات را گزارش می‌کنند. |
| `EV-068` | `2026-06-09` | سقوط بالگرد آپاچی آمریکا نزدیک تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [Military Times](https://www.militarytimes.com/news/your-military/2026/06/09/us-soldiers-rescued-after-apache-helicopter-goes-down-near-the-coast-of-oman/) · [Associated Press](https://apnews.com/article/50d7a8ecbb2cf33836af152679adb40e) | سقوط و نجات خدمه تأیید شد. ادعای سرنگونی توسط ایران بعداً از سوی آمریکا مطرح شد؛ عنوان فقط بخش قطعی را بیان می‌کند. |
| `EV-071` | `2026-07-18` | اعلام تعلیق تعهدات ایران ذیل تفاهم‌نامه اسلام‌آباد | `confirmed_2plus` | `secondary_confirmed` | [Dawn](https://www.dawn.com/news/amp/2016487) · [The National](https://www.thenationalnews.com/news/gulf/2026/07/18/iran-hits-second-power-and-water-plant-in-kuwait-after-another-night-of-us-strikes/) | اصل اعلام تعلیق تأیید شد؛ این ردیف درباره اعلام رسمی ایران است، نه داوری درباره اینکه کدام طرف ابتدا توافق را نقض کرده است. |

برای تکمیل فیلدهای پایه بلوک ممیزی بالا، `project_week` و `event_type` آن ردیف‌ها در جدول فشرده زیر ثبت شده‌اند. اتصال فقط با `event_id` انجام می‌شود؛ این جدول رویداد تازه‌ای ایجاد نمی‌کند.

| ID | هفته | نوع |
|---|---|---|
| `EV-041` | `PRE` | `political` |
| `EV-003` | `W01` | `humanitarian` |
| `EV-004` | `W01` | `humanitarian` |
| `EV-042` | `W01` | `military` |
| `EV-043` | `W01` | `military` |
| `EV-044` | `W01` | `political` |
| `EV-045` | `W01` | `military` |
| `EV-046` | `W01` | `military` |
| `EV-047` | `W03` | `military` |
| `EV-048` | `W01` | `military` |
| `EV-049` | `W01` | `economic` |
| `EV-050` | `W01` | `military` |
| `EV-051` | `W01` | `military` |
| `EV-052` | `W02` | `political` |
| `EV-053` | `W02` | `economic` |
| `EV-056` | `W04` | `military` |
| `EV-058` | `W04` | `military` |
| `EV-060` | `W07` | `military` |
| `EV-061` | `W07` | `media` |
| `EV-062` | `W10` | `military` |
| `EV-066` | `W14` | `diplomatic` |
| `EV-067` | `W15` | `military` |
| `EV-068` | `W15` | `military` |
| `EV-071` | `W21` | `diplomatic` |

ادامه رجیستری سایر رویدادها، همراه با هفته و نوع رویداد، در جدول زیر آمده است. تاریخ پایان فقط برای رویدادهای واقعاً چندروزه ثبت می‌شود.

| ID | تاریخ/بازه | هفته | نوع | عنوان نهایی | وضعیت نهایی | نقش | منابع و یادداشت ممیزی |
|---|---|---|---|---|---|---|---|
| `EV-002` | `2026-02-28` | `W01` | political | کشته‌شدن آیت‌الله علی خامنه‌ای و چند مقام ارشد در حملات آغاز جنگ | `confirmed_2plus` | `secondary_confirmed` | [AP](https://apnews.com/article/c2f11247d8a66e36929266f2c557a54c) · [Reuters](https://www.investing.com/news/commodities-news/irans-supreme-leader-khamenei-killed-iranian-state-media-confirm-4533456)؛ عنوان به افراد تأییدشده محدود می‌شود. |
| `EV-005` | `2026-02-28` تا `2026-03-02` | `W01` | military | آغاز حملات تلافی‌جویانه موشکی و پهپادی ایران در منطقه | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://sg.news.yahoo.com/iran-fires-missiles-gulf-arab-113144977.html) · [Axios](https://www.axios.com/2026/02/28/us-israel-strikes-iran-middle-east-dubai-airports)؛ این ردیف آغاز موج چندروزه را ثبت می‌کند، نه یک حمله منفرد. |
| `EV-007` | `2026-02-28` تا `2026-03-11` | `W01` | economic | کاهش شدید و توقف عملی بخش بزرگی از کشتیرانی در تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/mar/11/attacks-iran-oil-tankers-strait-hormuz) · [AP](https://apnews.com/article/49a1901c35cf2507830776a29706cf98)؛ «توقف عملی/محدودیت شدید» دقیق‌تر از ادعای بسته‌شدن کامل همه ترددهاست. |
| `EV-008` | `2026-03-05` | `W01` | humanitarian | تأیید ۱۳ حمله به مراکز و زیرساخت‌های درمانی ایران توسط WHO | `confirmed_primary_plus_independent` | `secondary_confirmed` | [WHO](https://www.who.int/news-room/feature-stories/detail/health-impact-of-the-escalation-of-conflict-in-the-middle-east) · [Reuters](https://www.investing.com/news/stock-market-news/four-medics-killed-in-iran-ambulances-damaged-who-says-4544378). |
| `EV-009` | `2026-03-07` | `W02` | media | عذرخواهی مسعود پزشکیان از کشورهای همسایه بابت حملات ایران | `confirmed_direct_plus_news` | `secondary_confirmed` | [Reuters Connect—ویدئوی اظهارنظر](https://www.reutersconnect.com/item/refile-pezeshkian-iran-to-suspend-strikes-on-neighbours-unless-they-attack/dGFnOnJldXRlcnMuY29tLDIwMjY6bmV3c21sX1ZBMTgwOTA3MDMyMDI2UlAx) · [AP](https://apnews.com/article/9edb192be983f9ede197cb6612a83dc6). |
| `EV-010` | `2026-03-08` | `W02` | political | انتخاب مجتبی خامنه‌ای به‌عنوان رهبر جدید ایران | `confirmed_2plus` | `secondary_confirmed` | [AP](https://apnews.com/article/209cec036068b40fcfcba2be7ac7e2b0) · [BBC](https://www.ecoi.net/en/document/2137701.html). |
| `EV-011` | `2026-03-12` | `W02` | humanitarian | برآورد اولیه آوارگی موقت تا ۳٫۲ میلیون نفر در داخل ایران | `confirmed_primary_plus_independent` | `secondary_confirmed` | [UNHCR](https://www.unhcr.org/asia/news/press-releases/unhcr-3-2-million-iranians-temporarily-displaced-iran-conflict-intensifies) · [AP](https://apnews.com/article/0e036a109d7e5b819a0fd6db5a6f3ddd)؛ رقم، برآورد اولیه است و به‌صورت شمارش قطعی بیان نمی‌شود. |
| `EV-012` | `2026-03-13` تا `2026-03-14` | `W02` | military | حمله آمریکا به اهداف نظامی جزیره خارک | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.investing.com/news/world-news/both-sides-dig-in-as-iran-war-approaches-twoweek-mark-4558794) · [Washington Post](https://www.washingtonpost.com/politics/2026/03/13/trump-us-iran-war-kharg-island-oil//)؛ هدف‌گرفتن زیرساخت نفتی در عنوان قطعی نمی‌شود. |
| `EV-013` | `2026-03-17` | `W03` | political | کشته‌شدن علی لاریجانی و غلامرضا سلیمانی، فرمانده بسیج | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.investing.com/news/world-news/ali-larijani-irans-ultimate-backroom-powerbroker-dies-at-67-4566995) · [AP](https://apnews.com/article/c6438088e9cc88aa56de3ae3a0557b68). |
| `EV-014` | `2026-03-18` | `W03` | economic | حمله به تأسیسات انرژی پارس جنوبی و عسلویه | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.marketscreener.com/news/oil-industry-facilities-targeted-in-southern-iran-tasnim-agency-reports-ce7e5ed9d980f22c) · [AP](https://apnews.com/article/d7ca062ba1bf99d1f8dc00c8073cf10f). |
| `EV-057` | `2026-03-23` | `W04` | media | اعلام تعویق پنج‌روزه حملات آمریکا به نیروگاه‌ها و زیرساخت انرژی ایران | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/live/2026/mar/23/middle-east-crisis-live-iea-chief-says-iran-war-energy-crunch-worse-than-1970s-oil-crises-and-ukraine-war-combined?page=with%3Ablock-69c14c838f08c1f048b00215) · [Al Jazeera](https://www.aljazeera.com/news/2026/3/23/trump-postpones-military-strikes-on-iranian-power-plants). |
| `EV-015` | `2026-03-30` | `W05` | media | تهدید ترامپ علیه نیروگاه‌ها، چاه‌های نفت و جزیره خارک | `confirmed_direct_plus_news` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/us-news/2026/mar/30/trump-threatens-to-obliterate-irans-energy-grid-if-ceasefire-not-reached-shortly) · [Euronews](https://www.euronews.com/2026/03/30/trump-threatens-to-obliterate-irans-kharg-island-oil-hub-if-no-deal-reached-shortly)؛ هر دو گزارش متن اظهارنظر مستقیم را ثبت کرده‌اند. |
| `EV-059` | `2026-04-06` | `W06` | economic | حمله مجدد به مجتمع پتروشیمی عسلویه | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.sahmcapital.com/news/content/%D9%88%D9%83%D8%A7%D9%84%D8%A9-%D9%87%D8%AC%D9%88%D9%85-%D8%B9%D9%84%D9%89-%D9%85%D9%86%D8%B4%D8%A3%D8%A9-%D9%84%D9%84%D8%A8%D8%AA%D8%B1%D9%88%D9%83%D9%8A%D9%85%D8%A7%D9%88%D9%8A%D8%A7%D8%AA-%D9%81%D9%8A-%D8%B9%D8%B3%D9%84%D9%88%D9%8A%D8%A9-%D8%A8%D8%A5%D9%8A%D8%B1%D8%A7%D9%86-2026-04-06) · [AP](https://apnews.com/article/29e03d9dd5e31c5ea10d2bdc87d68257). |
| `EV-017` | `2026-04-08` | `W06` | diplomatic | آغاز اجرای آتش‌بس ایران–آمریکا و ادامه جداگانه درگیری در لبنان | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/live/2026/apr/08/iran-war-ceasefire-live-updates-trump-deadline-middle-east-crisis-latest-news?filterKeyEvents=false&page=with%3Ablock-69d619d38f08175574780238) · [Le Monde](https://www.lemonde.fr/en/international/article/2026/04/08/netanyahu-continues-war-against-hezbollah-in-lebanon-despite-iran-ceasefire_6752229_4.html)؛ آتش‌بس ایران لزوماً لبنان را در عمل متوقف نکرد. |
| `EV-018` | `2026-04-11` تا `2026-04-12` | `W07` | diplomatic | برگزاری مذاکرات طولانی ایران و آمریکا در اسلام‌آباد | `confirmed_2plus` | `secondary_confirmed` | [Washington Post](https://www.washingtonpost.com/world/2026/04/11/us-iran-islamabad-hormuz-ceasefire/) · [The Guardian](https://www.theguardian.com/world/live/2026/apr/11/middle-east-crisis-live-iranian-officials-arrive-in-islamabad-for-conditional-peace-talks-with-us?page=with%3Ablock-69d9c8718f08ff62487f73f7). |
| `EV-019` | `2026-04-12` | `W07` | diplomatic | پایان دور نخست مذاکرات اسلام‌آباد بدون توافق | `confirmed_2plus` | `secondary_confirmed` | [PBS/AP](https://www.pbs.org/newshour/world/historic-u-s-and-iran-negotiations-in-pakistan-end-without-agreement) · [The Guardian](https://www.theguardian.com/world/live/2026/apr/11/middle-east-crisis-live-iranian-officials-arrive-in-islamabad-for-conditional-peace-talks-with-us?page=with%3Ablock-69da8f348f08dd48307746a1). |
| `EV-020` | `2026-04-13` | `W07` | military | آغاز محاصره دریایی آمریکا علیه تردد ورودی و خروجی بنادر ایران | `confirmed_primary_plus_independent` | `secondary_confirmed` | [اعلامیه مبتنی بر دستور CENTCOM](https://seapowermagazine.org/u-s-to-blockade-ships-entering-or-exiting-iranian-ports/?print=pdf) · [AP](https://apnews.com/article/ed7a6cd4bc61dc47f317a2c82afcc1c9). |
| `EV-021` | `2026-04-22` | `W08` | military | توقیف دو کشتی تجاری توسط ایران در تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [Washington Post](https://www.washingtonpost.com/world/2026/04/22/hormuz-strait-us-iran-talks-war//) · [Al Jazeera](https://www.aljazeera.com/news/2026/4/22/iranian-gunboat-fires-on-container-ship-off-oman-coast). |
| `EV-063` | `2026-05-07` | `W10` | military | تبادل حمله هنگام عبور سه ناوشکن آمریکا از تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [AP](https://apnews.com/article/73fd3ca47f6c19a736993b45310afcac) · [The Guardian](https://www.theguardian.com/world/2026/may/07/iran-accuses-us-of-violating-ceasefire-by-targeting-civilian-areas-and-ships-on-strait-of-hormuz)؛ روایت طرفین درباره آغاز حمله متفاوت است، بنابراین عنوان انتساب آغازگر ندارد. |
| `EV-022` | `2026-05-17` | `W12` | military | اصابت پهپاد به ژنراتور بیرون از محدوده داخلی نیروگاه براکه | `confirmed_2plus` | `secondary_confirmed` | [AP](https://apnews.com/article/71e7e58f45193b7dee3df28740532a7b) · [Reuters](https://www.marketscreener.com/news/uae-reports-drone-strike-at-nuclear-power-plant-as-iran-war-deadlock-endures-ce7f5bd3d18ef225)؛ عامل حمله در تاریخ رویداد قطعی نبود و در عنوان ذکر نمی‌شود. |
| `EV-064` | `2026-05-25` | `W13` | political | دستور بازگرداندن دسترسی جهانی اینترنت در ایران | `confirmed_primary_plus_independent` | `secondary_confirmed` | [Amnesty International](https://www.amnesty.org/en/latest/news/2026/05/iran-mass-arbitrary-arrests-and-political-executions-mark-intensifying-repression/) · [The Guardian](https://www.theguardian.com/world/2026/may/26/iran-internet-blackout)؛ بازگشت عملی تدریجی بود و با `EV-023` تفسیر می‌شود. |
| `EV-024` | `2026-06-14` | `W16` | diplomatic | اعلام دستیابی ایران و آمریکا به چارچوب اولیه توافق | `confirmed_2plus` | `secondary_confirmed` | [AP](https://apnews.com/article/e0a9e4e1152ea8da10ea066ad174a23a) · [The Guardian](https://www.theguardian.com/world/2026/jun/14/trump-calls-for-restraint-israel-airstrikes-beirut-us-iran-peace-deal)؛ این اعلام اولیه با امضای `EV-025` یکی نیست. |
| `EV-026` | `2026-06-21` تا `2026-06-22` | `W17` | diplomatic | مذاکرات اجرایی تفاهم‌نامه در بورگن‌اشتاک سوئیس | `confirmed_primary_plus_independent` | `secondary_confirmed` | [دولت سوئیس](https://www.post2015.admin.ch/en/memorandum-of-understanding-between-the-usa-and-iran) · [The Guardian](https://www.theguardian.com/world/live/2026/jun/21/iran-us-israel-war-middle-east-lebanon-peace-talks-switzerland-vance-trump-strait-of-hormuz-latest-news-updates?page=with%3Ablock-6a37b5cf8f087fb1fe063313). |
| `EV-027` | `2026-06-22` | `W17` | diplomatic | توافق بر نقشه راه برای دستیابی به توافق نهایی ظرف ۶۰ روز | `confirmed_2plus` | `secondary_confirmed` | [Al Jazeera](https://www.aljazeera.com/news/2026/6/22/us-iran-agree-on-roadmap-towards-final-deal-in-switzerland-talks) · [Anadolu](https://www.aa.com.tr/en/europe/switzerland-hails-constructive-work-during-iran-us-burgenstock-summit/3974315). |
| `EV-028` | `2026-06-24` | `W17` | diplomatic | اعلام وقفه موقت در گفت‌وگوهای فنی و برنامه ازسرگیری آن‌ها | `confirmed_2plus` | `secondary_confirmed` | [Al Jazeera](https://www.aljazeera.com/amp/news/liveblog/2026/6/24/iran-war-live-trump-tehran-at-odds-over-nuclear-inspections-hormuz) · [Xinhua](https://www.china.org.cn/world/Off_the_Wire/2026-06/24/content_118565230.shtml)؛ عنوان از «وقوع وقفه» به «اعلام وقفه و زمان ازسرگیری» دقیق‌تر شد. |
| `EV-029` | `2026-06-25` | `W17` | diplomatic | رد مسیرهای موقت کشتیرانی پیشنهادشده از سوی IMO و عمان توسط ایران | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/jun/25/un-backed-plan-ships-trapped-strait-of-hormuz-rejected-iran) · [Reuters](https://www.investing.com/news/world-news/oil-back-to-prewar-levels-as-hormuz-traffic-rebounds-us-tries-to-reassure-gulf-allies-4760411)؛ موضوع رد مختصات مسیرهاست، نه رد همه همکاری‌ها با عمان. |
| `EV-030` | `2026-06-26` | `W17` | military | حمله به کشتی Ever Lovely و حملات پاسخ‌جویانه آمریکا | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/jun/26/us-says-it-struck-iran-targets-after-attack-on-cargo-ship-on-the-strait-of-hormuz) · [Al Jazeera](https://www.aljazeera.com/news/2026/6/26/us-strikes-iran-in-response-to-drone-strike-on-commercial-ship). |
| `EV-032` | `2026-06-28` | `W18` | diplomatic | توافق ایران و آمریکا برای توقف حملات اخیر و ازسرگیری گفت‌وگوها | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.investing.com/news/world-news/us-carries-out-fresh-strikes-against-iran-after-tanker-struck-in-hormuz-escalating-hostilities-4764056) · [Axios](https://www.axios.com/2026/06/28/us-and-iran-agree-to-halt-strikes-and-meet-this-week-us-official-says)؛ عنوان قدیمی «توقف موقت حملات» به توافق اعلام‌شده و دامنه آن محدود شد. |
| `EV-033` | `2026-07-07` | `W19` | economic | حمله به سه کشتی تجاری در تنگه هرمز | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/jul/07/qatar-says-iran-fully-responsible-after-tankers-struck-in-strait-of-hormuz) · [Axios](https://www.axios.com/2026/07/07/iran-resumes-hormuz-attacks-us-officials)؛ اختلاف در انتساب برخی حملات جداگانه گزارش می‌شود. |
| `EV-034` | `2026-07-08` | `W19` | military | حمله آمریکا به بیش از ۸۰ هدف در ایران در پاسخ به حملات کشتیرانی | `confirmed_2plus` | `secondary_confirmed` | [Al Jazeera](https://www.aljazeera.com/news/2026/7/8/why-have-us-iran-strikes-resumed-and-what-does-it-mean-for-peace-talks) · [Le Monde](https://www.lemonde.fr/en/videos/video/2026/07/08/video-us-strikes-iran-in-response-to-new-attacks-in-strait-of-hormuz_6755263_108.html)؛ «لغو مجوز فروش نفت» اقدام سیاستی جدا و از عنوان این رویداد نظامی حذف شد. |
| `EV-035` | `2026-07-08` | `W19` | media | اعلام ترامپ مبنی بر پایان‌یافتن توافق آتش‌بس/تفاهم موقت | `confirmed_direct_plus_news` | `secondary_confirmed` | [Reuters](https://www.investing.com/news/world-news/trump-says-interim-accord-with-iran-to-end-war-is-over-4780838) · [Axios](https://www.axios.com/2026/07/08/trump-iran-ceasefire-over)؛ این ردیف ثبت اظهارنظر است، نه داوری حقوقی درباره خاتمه توافق. |
| `EV-036` | `2026-07-12` | `W20` | military | حمله آمریکا به حدود ۱۴۰ هدف و اعلام دوباره بسته‌شدن هرمز از سوی ایران | `confirmed_2plus` | `secondary_confirmed` | [The Guardian](https://www.theguardian.com/world/2026/jul/12/us-and-iran-exchange-strikes-as-tehran-again-says-strait-of-hormuz-is-closed) · [Reuters](https://ca.investing.com/news/commodities-news/iran-and-us-stage-new-attacks-battle-over-control-of-strait-of-hormuz-4732556)؛ «اعلام بسته‌شدن» از وضعیت واقعی عبور کشتی‌ها تفکیک می‌شود. |
| `EV-037` | `2026-07-13` تا `2026-07-14` | `W20` | economic | اعلام طرح عوارض ۲۰درصدی عبور از هرمز و عقب‌نشینی بعدی آمریکا | `confirmed_2plus` | `secondary_confirmed` | [Washington Post](https://www.washingtonpost.com/world/2026/07/14/oil-prices-jump-after-trumps-threats-strait-hormuz/) · [The Guardian](https://www.theguardian.com/world/2026/jul/14/us-strikes-iran-bahrain-jordan-uae-tankers). |
| `EV-038` | `2026-07-14` | `W20` | military | اجرای مجدد محاصره دریایی بنادر ایران از ساعت ۲۰:۰۰ UTC | `confirmed_2plus` | `secondary_confirmed` | [Washington Post](https://www.washingtonpost.com/world/2026/07/13/airstrikes-intensify-between-us-iran/) · [The Guardian](https://www.theguardian.com/world/2026/jul/13/us-iran-war-missile-strikes-news-attacks-strait-of-hormuz)؛ تاریخ v02 از ۱۵ ژوئیه به زمان اجرای اعلام‌شده در ۱۴ ژوئیه اصلاح شد. |
| `EV-039` | `2026-07-17` تا `2026-07-21` | `W20` | military | حمله به پایگاه آمریکا در اردن و تأیید نهایی کشته‌شدن سه نظامی | `confirmed_2plus` | `secondary_confirmed` | [Washington Post](https://www.washingtonpost.com/world/2026/07/18/iran-us-strikes-widen-fighting-hits-critical-infrastructure/) · [AP](https://apnews.com/article/5ec21d4f12fbdee658ec15ed8d3750ee)؛ ۱۷ ژوئیه تاریخ حمله و ۲۱ ژوئیه تاریخ تأیید نفر سوم است. |
| `EV-040` | `2026-07-20` | `W21` | economic | اعلام محاصره دریایی عربستان توسط حوثی‌ها در جبهه دریای سرخ | `confirmed_2plus` | `secondary_confirmed` | [Reuters](https://www.al-monitor.com/originals/2026/07/houthis-impose-saudi-naval-blockade-opening-new-front-us-iran-war) · [Le Monde](https://www.lemonde.fr/en/international/article/2026/08/07/iran-s-network-of-allies-reorganizes-around-iraq-and-yemen-after-setbacks-in-syria-and-lebanon_6756253_4.html)؛ عنوان v02 طوری اصلاح شد که اعلام‌کننده و جغرافیای رویداد روشن باشد. |


## ۶. مناسبت‌ها و Data Artifactها

| ID | تاریخ/بازه | هفته آغاز | نوع | وضعیت تأیید | نقش | تعریف | منبع | استفاده |
|---|---|---|---|---|---|---|---|---|
| `EV-006` | `2026-02-28` تا `2026-05-26` | `W01` | `infrastructure` | `confirmed_2plus` | `data_artifact` | محدودیت شدید اینترنت ایران | [Amnesty International](https://www.amnesty.org/zh-hant/wp-content/uploads/2026/04/MDE1308832026ENGLISH.pdf) · [The Guardian](https://www.theguardian.com/technology/2026/apr/06/iran-internet-blackout-is-longest-national-shutdown-since-arab-spring) | تفسیر Coverage فارسی؛ نه تغییر نگرش |
| `EV-023` | از `2026-05-26` | `W13` | `infrastructure` | `confirmed_2plus` | `data_artifact` | آغاز بازگشت تدریجی اینترنت جهانی | [Cloudflare Radar](https://blog.cloudflare.com/iran-internet-partially-restored-may-2026/) · [The Guardian](https://www.theguardian.com/world/2026/may/26/iran-internet-blackout) | بررسی شکست Coverage و تغییر ترکیب داده |
| `EV-054` | `2026-03-21` تا `2026-03-22` | `W04` | `calendar` | `context_only` | `context_only` | عید فطر و تعطیلی روز بعد | [تقویم ۱۴۰۵](https://timestamp.ir/events-list/1405) | تفسیر حجم پایه |
| `EV-055` | `2026-03-21` | `W04` | `calendar` | `context_only` | `context_only` | روز آغاز نوروز | [تقویم ۱۴۰۵](https://timestamp.ir/events-list/1405) | تفسیر حجم و ترکیب فارسی |
| `EV-065` | `2026-05-27` | `W13` | `calendar` | `context_only` | `context_only` | عید قربان | [تقویم ۱۴۰۵](https://timestamp.ir/events-list/1405) | تفسیر حجم پایه |
| `EV-069` | `2026-06-16` | `W16` | `calendar` | `context_only` | `context_only` | آغاز محرم | [تقویم ۱۴۰۵](https://timestamp.ir/events-list/1405) | یک روز پیش از `EV-025` |
| `EV-070` | `2026-06-25` | `W17` | `calendar` | `context_only` | `context_only` | عاشورا | [تقویم ۱۴۰۵](https://timestamp.ir/events-list/1405) | هم‌زمانی با رویداد دیپلماتیک `EV-029` |

در `EV-006`، تاریخ `2026-05-26` روز گذار از محدودیت شدید به آغاز بازگشت تدریجی است و عمداً با تاریخ آغاز `EV-023` مشترک ثبت شده است. فیلد `project_week` فقط هفته آغاز هر رویداد را نگه می‌دارد؛ پوشش چند‌هفته‌ای از `event_date_utc` و `event_end_date_utc` محاسبه می‌شود.

### ۶.۱ عوامل بیرونی مؤثر بر مشاهده داده

`data_artifact` در این رجیستری به اتفاقی بیرون از Pipeline گفته می‌شود که می‌تواند مقدار یا ترکیب داده قابل‌مشاهده را تغییر دهد، بدون اینکه الزاماً نگرش کاربران تغییر کرده باشد. برای مثال، محدودیت اینترنت ممکن است تعداد محتوای فارسی را کاهش دهد؛ این کاهش به‌تنهایی مدرک کاهش توجه یا تغییر نظر کاربران نیست.

- وقوع و بازه `data_artifact`هایی مانند محدودیت یا بازگشت اینترنت با منبع رسمی، حقوق‌بشری یا خبری معتبر ممیزی می‌شود؛
- مناسبت‌هایی مانند نوروز، عید فطر و عاشورا ممکن است حجم یا ترکیب گفتگوها را تغییر دهند. برای تأیید تاریخ آن‌ها یک تقویم رسمی یا مرجع تقویمی معتبر کافی است؛
- این عوامل هنگام تفسیر Coverage، حجم روزانه، ترکیب زبان و نتایج رویدادهای اصلی بررسی می‌شوند؛
- برای این ردیف‌ها آزمون مستقل قبل/بعد تعریف نشده است. در نتیجه `target_id`، `primary_outcome`، `expected_direction`، `main_window` و `sensitivity_window` آن‌ها با `—` ثبت می‌شود و خالی‌بودن این فیلدها نقص داده نیست.

برای نمونه، اگر حجم محتوای فارسی در دوره `EV-006` کاهش یابد، ابتدا محدودیت اینترنت و Coverage بررسی می‌شود و این کاهش مستقیماً به تغییر نگرش کاربران نسبت داده نمی‌شود.

### ۶.۲ اختلال‌ها و تغییرات داخلی Pipeline

اختلال داخلی Pipeline با رویداد خبری یا `data_artifact` بیرونی تفاوت دارد. این گروه شامل مواردی مانند خطای API، Rate Limit، توقف یا شکست Collector، تغییر Query و اضافه یا حذف‌شدن Source است. این اطلاعات از خبرهای عمومی استخراج نمی‌شوند و باید از مدارک اجرای خود پروژه ثبت شوند:

| نوع تغییر یا اختلال | مرجع ثبت | کاربرد در تحلیل |
|---|---|---|
| زمان اجرا، موفقیت یا خطای Collector و محدودیت API | `run_log` یا Fetch log هر پلتفرم | تشخیص توقف فنی یا اجرای ناقص |
| تعداد رکورد، ابتدا و انتهای بازه و روزهای بدون داده | `collection_coverage` | تشخیص شکاف زمانی و کاهش Coverage |
| اضافه، حذف یا تغییر Query | Query Registry نسخه اجراشده | تفسیر تغییر ترکیب موضوعی داده |
| اضافه، حذف یا تغییر Subreddit، Channel یا Source | Source Registry نسخه اجراشده | تفسیر تغییر ترکیب منابع |

برای مثال، اگر داده X در سه روز کاهش یافته باشد، `run_log` مشخص می‌کند آیا Collector اجرا نشده یا با Rate Limit روبه‌رو شده است. اگر در همان بازه گزارش معتبر محدودیت اینترنت نیز وجود داشته باشد، عامل بیرونی و اختلال فنی جداگانه ثبت و هر دو در تفسیر Coverage گزارش می‌شوند؛ هیچ‌کدام از روی حدس تکمیل نمی‌شود.

## ۷. قواعد استفاده آماری

### ۷.۱ تحلیل رویدادهای اصلی

برای `EV-016`، `EV-025` و `EV-031`، روز رویداد از دو Window کنار گذاشته و جداگانه توصیف می‌شود. «هفت روز قبل» یعنی روزهای `D-7` تا `D-1` و «هفت روز بعد» یعنی `D+1` تا `D+7`. این تعریف مانع دوباره‌شماری روز رویداد در هر دو دوره می‌شود.

#### خروجی‌های ضروری

1. تعداد رکورد و سهم پلتفرم، زبان، Query و Content Type در دوره قبل و بعد گزارش می‌شود؛
2. سهم Outcome اصلی در هر دوره و اختلاف ساده سهم بعد منهای قبل محاسبه می‌شود؛
3. برای سهم‌ها و اختلاف آن‌ها فاصله اطمینان ۹۵٪ Bootstrap خوشه‌ای گزارش می‌شود؛
4. نتیجه هر پلتفرم جداگانه گزارش می‌شود و نتیجه تجمیعی بدون نمایش ترکیب پلتفرم‌ها تفسیر نمی‌شود؛
5. رویدادهای دیگری که داخل هر Window قرار دارند در `overlap_note` ثبت می‌شوند؛
6. به دلیل نمونه‌گیری غیراحتمالی و وجود رویدادهای هم‌زمان، نتیجه به‌صورت «تغییر مشاهده‌شده پیرامون رویداد» گزارش می‌شود، نه اثر علّی رویداد بر افکار عمومی.

اگر تعداد رکوردهای قابل‌تحلیل در دوره قبل یا بعد کمتر از `30` باشد، مقایسه فقط توصیفی و با علامت «نمونه کم» گزارش می‌شود. این حد یک قاعده عملی گزارش‌دهی است و تضمین توان آماری نیست.

واحد Bootstrap باید رکورد منفرد نباشد، زیرا چند رکورد ممکن است از یک نویسنده یا یک بحث مشترک آمده باشند. در صورت پوشش مناسب `author_hash`، بازنمونه‌گیری در سطح نویسنده انجام می‌شود. در غیر این صورت، واحد جایگزین برای Reddit پست/Thread والد، برای YouTube ویدئو و برای X مکالمه یا `conversation_id` است. در تحلیل تجمیعی، شناسه خوشه همراه نام پلتفرم ساخته می‌شود تا شناسه‌های مشابه بین پلتفرم‌ها یکی فرض نشوند.

#### تحلیل‌های حساسیت

- Window کوتاه‌تر ثبت‌شده در بخش ۴ اجرا می‌شود؛ این تحلیل به دلیل هم‌پوشانی رویدادها برای هر سه رویداد اصلی ضروری است؛
- حذف Near-duplicateها بخشی از آماده‌سازی داده است و نتیجه اصلی باید روی داده Deduplicate‌شده اجرا شود؛
- حذف بزرگ‌ترین Parent/Video/Conversation یک بررسی تمرکز پیشنهادی است، نه شرط لازم برای تکمیل پروژه. اگر سهم یک خوشه بسیار بزرگ باشد، این بررسی اجرا و گزارش می‌شود؛
- در صورت تغییر محسوس ترکیب Platform، Language یا Query، نتیجه به تفکیک همان متغیر گزارش می‌شود.

آمار اصلی پروژه Estimate، فاصله اطمینان و پایداری نتیجه در Window کوتاه‌تر است. فاصله اطمینان Bootstrap، عدم‌قطعیت داخل داده مشاهده‌شده و ساختار خوشه‌ای آن را نشان می‌دهد؛ چون نمونه‌گیری پروژه احتمالی نیست، این فاصله به معنی خطای نمونه‌گیری از کل کاربران شبکه‌های اجتماعی یا افکار عمومی جهان نیست. گزارش `p-value` برای این پروژه ضروری نیست و فقط در صورت تعریف قبلی یک آزمون مشخص و سازگاری فرض‌های آن انجام می‌شود.

### ۷.۲ رویدادهای ثانویه

منظور از رویداد ثانویه، رویدادی است که وقوع آن با منبع کافی تأیید شده، اما جزء سه فرضیه اصلی قبل/بعد پروژه نیست. «ثانویه» به معنی کم‌اهمیت یا نامعتبر نیست؛ فقط یعنی برای جلوگیری از آزمون‌های متعدد و انتخاب نتیجه‌محور، آزمون تأییدی مستقل برای آن تعریف نشده است.

برای `secondary_confirmed` فقط این موارد انجام می‌شود:

- علامت‌گذاری روی نمودار زمانی؛
- گزارش توصیفی حجم و Outcome پیرامون رویداد؛
- تحلیل اکتشافی با برچسب روشن `exploratory`؛
- استفاده برای توضیح هم‌پوشانی Window رویدادهای اصلی.

برای این رویدادها مجموعه‌ای از `p-value`های جداگانه تولید نمی‌شود.

### ۷.۳ رویداد آغاز مطالعه

`EV-001` دوره پیشارویداد داخل Dataset ندارد. بنابراین مقایسه قبل/بعد برای آن معتبر نیست و فقط حجم، ترکیب و Outcome روزهای آغاز مطالعه توصیف می‌شود.

### ۷.۴ هم‌پوشانی و زبان گزارش

بررسی تقویمی پنجره‌های اصلی چنین است:

| رویداد اصلی | Window اصلی بدون روز رویداد | رویدادها و زمینه‌های داخل Window اصلی | موارد باقی‌مانده در Window حساسیت | نتیجه ممیزی هم‌پوشانی |
|---|---|---|---|---|
| `EV-016` | `2026-03-24` تا `2026-04-06` و `2026-04-08` تا `2026-04-21` | `EV-006`، `EV-058`، `EV-015`، `EV-059`، `EV-017`، `EV-060`، `EV-018`، `EV-019`، `EV-020` و `EV-061` | `EV-006`، `EV-059`، `EV-017`، `EV-060`، `EV-018`، `EV-019` و `EV-020` | هم‌پوشانی زیاد؛ نتیجه فقط مقایسه پیرامون آتش‌بس است. |
| `EV-025` | `2026-06-10` تا `2026-06-16` و `2026-06-18` تا `2026-06-24` | رژیم Coverage پس از `EV-023`، همچنین `EV-024`، `EV-069`، `EV-026`، `EV-027` و `EV-028` | رژیم Coverage پس از `EV-023`، `EV-024` و `EV-069` | هم‌پوشانی زیاد؛ Window سه‌روزه حتماً گزارش می‌شود. |
| `EV-031` | `2026-06-20` تا `2026-06-26` و `2026-06-28` تا `2026-07-04` | رژیم Coverage پس از `EV-023`، همچنین `EV-026`، `EV-027`، `EV-028`، `EV-029`، `EV-070`، `EV-030` و `EV-032` | رژیم Coverage پس از `EV-023`، `EV-028`، `EV-029`، `EV-070`، `EV-030` و `EV-032` | هم‌پوشانی زیاد؛ Window سه‌روزه نیز چند رویداد نزدیک دارد. |

Window اصلی `EV-025` و `EV-031` در روزهای `2026-06-20` تا `2026-06-24` با یکدیگر مشترک است. Windowهای حساسیت سه‌روزه این دو رویداد با یکدیگر تداخل ندارند، اما همچنان شامل رویدادهای ثانویه نزدیک‌اند. بنابراین تحلیل حساسیت، مشکل انتساب علّی را کاهش می‌دهد ولی آن را از بین نمی‌برد.

در روزهای دارای چند رویداد یا Windowهای هم‌پوشان نوشته می‌شود:

> «تغییر مشاهده‌شده با مجموعه رویدادهای این بازه هم‌زمان بود.»

نوشته نمی‌شود:

> «رویداد X باعث تغییر افکار عمومی شد.»

## ۸. فیلتر اجرایی

وجود کد در این سند الزام آماری نیست؛ این بلوک فقط قواعد بخش‌های ۱، ۲ و ۷ را به یک فیلتر قابل‌بازتولید تبدیل می‌کند. اجرای واقعی باید در Notebook تحلیل و روی نسخه جدولی رجیستری انجام شود. نگه‌داشتن این بلوک مفید است، زیرا دقیقاً نشان می‌دهد کدام رویدادها وارد تحلیل اصلی یا نمودار می‌شوند.

```python
required_columns = {
    "event_id", "event_date_utc", "project_week", "analysis_role",
    "verification_status",
}
missing_columns = required_columns.difference(events.columns)
if missing_columns:
    raise ValueError(f"Missing event-registry columns: {sorted(missing_columns)}")

CONFIRMED = {
    "confirmed_2plus",
    "confirmed_primary_plus_independent",
    "confirmed_direct_plus_news",
}

primary_events = events[
    events["analysis_role"].eq("primary_confirmatory")
    & events["verification_status"].isin(CONFIRMED)
    & events["project_week"].isin([f"W{i:02d}" for i in range(1, 22)])
]

plot_events = events[
    events["analysis_role"].isin(
        ["study_anchor", "primary_confirmatory", "secondary_confirmed", "context_only", "data_artifact"]
    )
    & ~events["verification_status"].isin(["not_verified_after_search", "out_of_window"])
]
```

## ۹. جدول خروجی تحلیل رویداد

| event_id | platform | period | n | low_n_flag | outcome_share | ci_low | ci_high | difference | difference_ci_low | difference_ci_high | cluster_unit | composition_note | overlap_note | sensitivity_status |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|---|
