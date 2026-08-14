# جدول تصمیم‌های اجرایی پروژه

**نسخه:** 1.0  
**مبنای جدول:** بخش «تصمیم‌های اجباری پیش از جمع‌آوری» در `global_public_opinion_iran_us_assignment.ipynb`  
**زمان قفل تحلیل:** پیش از مشاهده خروجی نهایی Annotation و آزمون‌ها

این Register دو نوع تصمیم را نگهداری می‌کند: تصمیم‌های Collection که با Registry تخصیص‌یافته و Run Manifest تأیید می‌شوند، و تصمیم‌های Annotation/Analysis که پیش از اجرای کامل قفل می‌شوند. هر اختلاف میان طرح و اجرای واقعی در Decision Log ثبت می‌شود.

| تصمیم اجباری | پاسخ تیم | دلیل | ریسک و کنترل | وضعیت |
|---|---|---|---|---|
| پلتفرم یا Dataset | X، Reddit و YouTube؛ تحلیل اصلی هر پلتفرم جداگانه | سه محیط گفت‌وگوی متفاوت و داده موجود از هر سه | هیچ‌کدام نماینده جهان نیست؛ Pooled فقط خلاصه نمونه مشاهده‌شده | قطعی |
| واحد تحلیل | X: Post/Reply/Quote دارای متن؛ Reddit: Comment/Reply و Submission جدا؛ YouTube: Comment/Reply | ساده‌ترین واحد متنی مستقل برای Sentiment و Stance | چند رکورد از یک Author/Parent مستقل کامل نیست؛ حساسیت Author/Parent اجرا می‌شود | قطعی |
| Targetهای Stance | اصلی: `T01` تشدید نظامی، `T02` دیپلماسی/آتش‌بس، `T03` تحریم/فشار اقتصادی؛ `T04` تا `T06` تکمیلی | سه Target اصلی برای پروژه دانشجویی قابل مدیریت و مستقیماً مرتبط با پرسش است | Multi-target برچسب‌گذاری را دشوار می‌کند؛ Targetهای تکمیلی فقط در صورت کیفیت Gold Sample استفاده می‌شوند | قطعی برای تحلیل اصلی |
| زبان‌های داخل دامنه | انگلیسی و فارسی برای تحلیل اصلی؛ عربی و سایر زبان‌ها نگهداری اما فقط در صورت ارزیابی کافی تحلیل می‌شوند | پوشش Query و توان Annotation تیم | زبان کشور یا موقعیت نیست؛ عملکرد مدل به تفکیک زبان گزارش می‌شود | قطعی |
| Query و کلیدواژه‌ها | نسخه تحویلی به هر همکار مرجع تاریخی است؛ رشته واقعاً اجراشده از Log/Config ثبت می‌شود | جلوگیری از بازنویسی گذشته و Query bias پنهان | Query نامعلوم `unknown` می‌ماند؛ Query جدید وارد Trend اصلی گذشته نمی‌شود | **Audit تا حد ممکن اجرا شد (۲۰۲۶-۰۸-۱۴):** `docs/query_execution_audit.csv` = ۸۰۷ ردیف (X=۶۲۲ از Jobs/Subruns شیت handoff، YouTube=۱۶۶ از `youtube_runs.csv` واقعی). **باز مانده:** Reddit هیچ Run Log ساختاریافته‌ای ندارد (`docs/reference_file_determination.md`) — Query/Sort/Pagination واقعی Reddit مستند نیست، فقط از رکوردهای خام قابل استنتاج است. |
| بازه زمانی و Time Zone | `2026-02-28T00:00:00Z` تا `2026-07-22T23:59:59Z`؛ همه زمان‌ها UTC؛ `W01` تا `W21` | انطباق با ۹ اسفند ۱۴۰۴ تا ۳۱ تیر ۱۴۰۵ | Timestamp بدون Zone فقط با مدرک تبدیل می‌شود؛ در غیر این صورت از Trend خارج است | قطعی |
| روش Sampling | Collection: غیراحتمالی مبتنی بر Query/Source و نمونه در دسترس محدود به خروجی پلتفرم؛ هدف، نگهداری همه رکوردهای برگشتی بوده است. Gold Sample: تصادفی طبقه‌بندی‌شده | احتمال انتخاب محتوا معلوم نیست؛ این نام‌گذاری دقیق‌ترین توصیف است | تعمیم جمعیتی و Margin of Sampling Error مجاز نیست؛ Composition و Coverage گزارش می‌شود | نوع کلی قطعی؛ Collection Audit تا حد ممکن اجرا شد (ردیف بالا). Eligibility هم روی داده واقعی هر سه پلتفرم اجرا شد (۲۳۳,۰۰۶ رکورد Eligible، ۲۰۲۶-۰۸-۱۴). |
| حداقل حجم هر Window | همه هفته‌ها با `n` گزارش می‌شوند؛ `n < 30` فقط توصیفی و با علامت نمونه کم است. Gold Sample پایه ۳۰۰ و Double annotation برابر ۱۲۰ است | قاعده ساده و قابل اجرا برای پروژه Bootcamp | عدد ۳۰ تضمین توان آماری نیست؛ CI و حجم واقعی همیشه گزارش می‌شود | قطعی، مشروط به حجم داده |
| Duplicate و Repost | Exact ID یک رکورد؛ چند Query در `matched_query_ids`؛ متن تکراری/مشابه Flag؛ Repost بدون متن خارج از Opinion و در `audit_only` | جلوگیری از چندبارشماری همراه با ثبت حجم بازنشر | Dedup متن ممکن است نظرهای مستقل مشابه را ادغام کند؛ نتیجه با و بدون Near-duplicate مقایسه می‌شود | قطعی |
| Bot/Spam احتمالی | ادعای «Bot قطعی» نمی‌شود. فقط Risk براساس تکرار زیاد، Near-duplicate، نرخ ارسال بسیار بالا و الگوی غیرعادی ثبت می‌شود | تشخیص هویت Bot از محتوای محدود قابل اتکا نیست | نتیجه اصلی با و بدون High-risk تکرار می‌شود و Ruleها نسخه‌بندی می‌شوند | قطعی |
| تعیین موقعیت | فقط Geotag، Location مستقیم معتبر یا Self-report مستند؛ در غیر این صورت `unknown` | زبان، Subreddit و Channel مکان فرد را اثبات نمی‌کنند | اگر پوشش کم باشد تحلیل جغرافیایی از نتیجه اصلی حذف می‌شود | قطعی |
| مدل و Provider LLM | یک Pipeline واحد با خروجی JSON و Prompt نسخه‌بندی‌شده؛ انتخاب مدل پس از Pilot روی ۱۰۰ رکورد و پیش از Full run قفل می‌شود | انتخاب بدون دیدن زبان، حجم و خطای Pilot قابل دفاع نیست | مقایسه بی‌پایان مدل ممنوع؛ انتخاب با Macro-F1، Failure، Cost و Latency ثبت می‌شود | **قفل شد (۲۰۲۶-۰۸-۱۴):** `openrouter_gemini_flash_lite` (`src/annotation/model_routes.py`'s `LOCKED_ROUTE_NAME`)، بر اساس Pilot کامل روی هر ۳۰۰ رکورد Gold Sample (F1 sentiment=۰.۶۰۹, stance=۰.۵۰۲, failure=۰٪, coverage=۹۹.۳٪) — جزئیات در `decision_log.md`. |
| سقف هزینه و زمان اجرا | Data intake بدون LLM انجام می‌شود. پیش از Full run، سقف عددی هزینه و زمان بر اساس حجم داده و Pilot در Decision Log تأیید می‌شود؛ تا آن زمان Full run مجاز نیست | حجم داده هنوز تحویل نشده و هزینه قابل محاسبه نیست | هزینه کنترل‌نشده؛ با Batch، Cache بر اساس Hash متن و اجرای آزمایشی کنترل می‌شود | **قفل شد (۲۰۲۶-۰۸-۱۴):** سقف $۱۰۰ (`src/annotation/run_full_annotation.py`'s `APPROVED_COST_CAP_USD`)، بر مبنای ۲۳۳,۰۰۶ رکورد Eligible × هزینه‌ی Pilot. به‌دلیل محدودیت واقعی TPM/سرعت، حجم واقعی Full run به زیرنمونه‌ی طبقه‌ای (حداکثر ۱۲۰ رکورد به‌ازای هر سلول پلتفرم×هفته، Seed=۱۴۰۵) کاهش یافت — نه به‌دلیل سقف هزینه. اجرای واقعی ۲۰۲۶-۰۸-۱۴ آغاز شد. |

## تصمیم نهایی Sampling برای دفاع شفاهی

> «نمونه Collection ما احتمال‌محور نیست؛ محتوا با Queryها و Sourceهای ثبت‌شده و در حد دسترسی پلتفرم بازیابی شده است. در Dataset اصلی همه رکوردهای واجد شرایط موجود را نگه می‌داریم. فقط برای Gold Sample و Audit، نمونه‌گیری تصادفی طبقه‌بندی‌شده با Seed ثابت انجام می‌دهیم. بنابراین CIهای ما عدم قطعیت نسبت‌های مشاهده‌شده را توصیف می‌کنند و ادعای نمایندگی مردم جهان ندارند.»

## مواردی که پس از تحویل داده تکمیل می‌شوند

1. ✅ رشته Query، Sort، Cap و Pagination واقعاً اجراشده — X و YouTube کامل، Reddit باز (بدون Run Log ساختاریافته).
2. ✅ تعداد رکورد و Coverage واقعی هر Platform — `docs/collection_coverage.csv`.
3. ⏳ امکان اجرای Author-balanced analysis — Pipeline B (`composition_shift.py`) این را پیاده کرده؛ روی داده واقعی annotation‌شده هنوز اجرا نشده (منتظر Full Annotation).
4. ⏳ اندازه نهایی Gold Sample در صورت کوچک‌بودن یک Platform — هر سه پلتفرم ۱۰۰/۱۰۰/۱۰۰ رسیدند؛ ۶۲/۳۰۰ رکورد به‌دلیل عدم تطابق با Eligibility واقعی در حال جایگزینی هستند (`docs/decision_log.md` ۲۰۲۶-۰۸-۱۴).
5. ✅ نام دقیق مدل/Provider و Threshold — بالا.
6. ✅ سقف عددی هزینه و زمان — بالا.

## منابع روش‌شناختی

- AAPOR, Non-Probability Sampling Task Force: <https://aapor.org/wp-content/uploads/2022/11/NPS_TF_Report_Final_7_revised_FNL_6_22_13.pdf>
- AAPOR Transparency Initiative: <https://aapor.org/standards-and-ethics/transparency-initiative/>
- scikit-learn, stratified random splitting and fixed `random_state`: <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html>
- statsmodels, Wilson proportion interval: <https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html>
