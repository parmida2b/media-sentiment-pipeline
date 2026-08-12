# رجیستری رویدادها

**بازه پروژه:** `2026-02-28` تا `2026-07-22`  
**نسخه:** `v3`  
**کاربرد:** ثبت رویدادهای مرتبط با تفسیر روند، تعیین رویدادهای آزمون تأییدی و مستندسازی رویدادهای زمینه‌ای و اختلال‌های داده

---

## ۱. منطق رجیستری

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

## ۳. فیلدهای لازم

| فیلد | تعریف |
|---|---|
| `event_id` | شناسه پایدار نسخه |
| `event_date_utc` | تاریخ آغاز رویداد به شکل `YYYY-MM-DD` |
| `event_end_date_utc` | تاریخ پایان برای رویداد چندروزه |
| `project_week` | `W01` تا `W21`، یا `PRE` و `OUT` |
| `event_type` | military/diplomatic/political/economic/humanitarian/media/calendar/infrastructure |
| `title_fa` | عنوان کوتاه، دقیق و خنثی |
| `analysis_role` | نقش رویداد در تحلیل |
| `verification_status` | وضعیت تأیید منبع |
| `source_1_url` و `source_2_url` | دو مدرک مستقل یا رسمی+مستقل |
| `attribution_note` | اختلاف درباره مسئولیت، تاریخ یا دامنه ادعا |
| `target_id` | Target مربوط به Stance، در صورت اجرای آزمون |
| `primary_outcome` | Outcome اصلی از پیش تعیین‌شده |
| `main_window` | پنجره اصلی تحلیل |
| `sensitivity_window` | پنجره جایگزین |

## ۴. رویدادهای تحلیل اصلی

| ID | تاریخ | هفته | نقش | عنوان | Target | Outcome اصلی | انتظار پیشینی | Window |
|---|---|---|---|---|---|---|---|---|
| `EV-001` | `2026-02-28` | `W01` | `study_anchor` | آغاز حملات گسترده آمریکا و اسرائیل به ایران | `T01` | حجم و ترکیب محتوای روزهای آغاز | — | فقط توصیف پسارویداد؛ دوره قبل در Dataset وجود ندارد |
| `EV-016` | `2026-04-07` | `W06` | `primary_confirmatory` | اعلام آتش‌بس دوهفته‌ای | `T02` | سهم حمایت از دیپلماسی | افزایش حمایت و Hope | اصلی: ۲ هفته قبل/بعد؛ حساسیت: ۱ هفته |
| `EV-025` | `2026-06-17` | `W16` | `primary_confirmatory` | امضای تفاهم‌نامه اسلام‌آباد | `T02` | سهم حمایت از دیپلماسی | افزایش حمایت و کاهش Fear | اصلی: ۱ هفته قبل/بعد؛ حساسیت: ۳ روز |
| `EV-031` | `2026-06-27` | `W18` | `primary_confirmatory` | ازسرگیری حملات متقابل | `T01` | سهم مخالفت با تشدید نظامی | افزایش مخالفت و Fear | اصلی: ۱ هفته قبل/بعد؛ حساسیت: ۳ روز |

پنجره اصلی `EV-025` و `EV-031` یک هفته در نظر گرفته شد، زیرا فاصله این دو رویداد ده روز است و 
پنجره‌های دوهفته‌ای به‌شدت هم‌پوشانی داشتند. حتی با پنجره یک‌هفته‌ای، روزهای نزدیک به هر دو رویداد در یادداشت هم‌پوشانی گزارش می‌شوند و نتیجه به‌صورت علّی تفسیر نمی‌شود.

### منابع رویدادهای اصلی

- `EV-001`: [Associated Press](https://apnews.com/article/8de8054f3abd4688f894c657467ee3dd) و [سند شورای امنیت سازمان ملل، S/2026/130](https://documents.un.org/api/symbol/access?l=en&s=S%2F2026%2F130&t=pdf)
- `EV-016`: [United Nations Digital Library](https://digitallibrary.un.org/record/4107634) و [Associated Press](https://apnews.com/article/421ee64fdc9a5c26460df8119c7d1b3f)
- `EV-025`: [UN DPPA](https://dppa.un.org/en/speeches-and-statements/un-calls-for-maximum-restraint-to-preserve-ceasefire-between-the) و [Associated Press](https://apnews.com/article/a7ab28d9b34edfaa2061a67616f610bc)
- `EV-031`: [UN DPPA](https://dppa.un.org/en/speeches-and-statements/un-calls-for-maximum-restraint-to-preserve-ceasefire-between-the) و [متن نشست شورای امنیت](https://transcripts.un.org/en/sc/10189/2)

## ۵.سایر رویدادهای مهم


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
| `EV-052` | `2026-03-07` | تصویب فروش اضطراری ۱۵۱٫۸ میلیون دلاری مهمات به اسرائیل | `confirmed_primary_plus_independent` | `secondary_confirmed` | [Associated Press](https://apnews.com/article/fbe9e2321aa2f54fa5bf59b0306b1928) · [U.S. Congressional Record](https://www.govinfo.gov/content/pkg/CREC-2026-04-15/pdf/CREC-2026-04-15-senate.pdf) | مبلغ و نوع فروش تأیید شد؛ نوع رویداد `sanction_policy` نبود و به `political/policy` اصلاح می‌شود. |
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

## ۶. سایر رویدادهای تأییدشده

رویدادهای زیر برای Annotation نمودار، توضیح خوشه‌های زمانی و تحلیل اکتشافی نگهداری می‌شوند، اما آزمون تأییدی مستقل ندارند و منبع دومی برای تایید این رویدادها پیدا نشد.

| دوره | شناسه‌ها | نقش |
|---|---|---|
| آغاز جنگ و هفته‌های اول | `EV-002`, `EV-005`, `EV-007`, `EV-008`, `EV-009`, `EV-010`, `EV-011`, `EV-012`, `EV-013`, `EV-014` | `secondary_confirmed` |
| اواخر مارس و آوریل | `EV-057`, `EV-015`, `EV-059`, `EV-017`, `EV-018`, `EV-019`, `EV-020`, `EV-021` | `secondary_confirmed` |
| مه | `EV-063`, `EV-022`, `EV-064` | `secondary_confirmed` |
| ژوئن، به‌جز رویدادهای اصلی | `EV-024`, `EV-026`, `EV-027`, `EV-028`, `EV-029`, `EV-030`, `EV-032` | `secondary_confirmed` |
| ژوئیه تا پایان بازه | `EV-033`, `EV-034`, `EV-035`, `EV-036`, `EV-037`, `EV-038`, `EV-039`, `EV-040` | `secondary_confirmed` |


## ۷. مناسبت‌ها و Data Artifactها

| ID | تاریخ/بازه | نقش | تعریف | استفاده |
|---|---|---|---|---|
| `EV-006` | `2026-02-28` تا `2026-05-26` | `data_artifact` | محدودیت شدید اینترنت ایران | تفسیر Coverage فارسی؛ نه تغییر نگرش |
| `EV-023` | از `2026-05-26` | `data_artifact` | آغاز بازگشت تدریجی اینترنت جهانی | بررسی شکست Coverage و تغییر ترکیب داده |
| `EV-054` | `2026-03-21` تا `2026-03-22` | `context_only` | عید فطر | تفسیر حجم پایه |
| `EV-055` | `2026-03-21` | `context_only` | نوروز | تفسیر حجم و ترکیب فارسی |
| `EV-065` | `2026-05-27` | `context_only` | عید قربان | تفسیر حجم پایه |
| `EV-069` | `2026-06-17` | `context_only` | آغاز محرم | هم‌زمانی با `EV-025` |
| `EV-070` | `2026-06-25` | `context_only` | عاشورا | هم‌زمانی با رویداد دیپلماتیک `EV-029` |

اختلال API، شکست Collector، تغییر Query و تغییر Source Registry از خبرهای عمومی استخراج نمی‌شوند؛ آن‌ها باید از `run_log`، `collection_coverage` و نسخه Query Registry ثبت شوند.

## ۸. قواعد استفاده آماری

### ۸.۱ تحلیل رویدادهای اصلی

برای `EV-016`، `EV-025` و `EV-031`:

1. تعداد رکورد، سهم پلتفرم، زبان، Query و Content Type در Window قبل و بعد گزارش می‌شود؛
2. سهم Outcome اصلی در هر Window محاسبه می‌شود؛
3. اختلاف سهم همراه فاصله اطمینان ۹۵٪ Bootstrap گزارش می‌شود؛
4. Bootstrap در سطح واحد مستقل مناسب انجام می‌شود: در صورت وجود `author_hash` در سطح نویسنده، و در غیر این صورت در سطح `parent_id` یا Thread؛
5. تحلیل حساسیت با حذف بزرگ‌ترین Parent، حذف Near-duplicateها و Window کوتاه‌تر اجرا می‌شود؛
6. نتیجه هر پلتفرم جداگانه نیز گزارش می‌شود؛
7. اگر ترکیب Platform، Language یا Query به‌طور محسوس تغییر کرده باشد، نتیجه کلی بدون گزارش تحلیل لایه‌بندی‌شده تفسیر نمی‌شود.

آمار اصلی Estimate، فاصله اطمینان و پایداری تحلیل حساسیت است. `p-value` فقط برای مدل یا آزمونی گزارش می‌شود که پیش از مشاهده نتیجه نهایی مشخص شده باشد.

### ۸.۲ رویدادهای ثانویه

برای `secondary_confirmed` فقط این موارد مجاز است:

- علامت‌گذاری روی نمودار زمانی؛
- گزارش توصیفی حجم و Outcome پیرامون رویداد؛
- تحلیل اکتشافی با برچسب روشن `exploratory`؛
- استفاده برای توضیح هم‌پوشانی Window رویدادهای اصلی.

برای این رویدادها مجموعه‌ای از `p-value`های جداگانه تولید نمی‌شود.

### ۸.۳ رویداد آغاز مطالعه

`EV-001` دوره پیشارویداد داخل Dataset ندارد. بنابراین مقایسه قبل/بعد برای آن معتبر نیست و فقط حجم، ترکیب و Outcome روزهای آغاز مطالعه توصیف می‌شود.

### ۸.۴ هم‌پوشانی و زبان گزارش

در روزهای دارای چند رویداد یا Windowهای هم‌پوشان نوشته می‌شود:

> «تغییر مشاهده‌شده با مجموعه رویدادهای این بازه هم‌زمان بود.»

نوشته نمی‌شود:

> «رویداد X باعث تغییر افکار عمومی شد.»

## ۹. فیلتر اجرایی

```python
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
]
```

## ۱۰. جدول خروجی تحلیل رویداد

| event_id | platform | period | n | outcome_share | ci_low | ci_high | difference | difference_ci_low | difference_ci_high | composition_note | overlap_note | sensitivity_status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|

