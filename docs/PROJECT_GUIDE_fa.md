# راهنمای پروژه — برای کسی که تازه این ریپو رو باز کرده

**تاریخ تهیه:** ۲۰۲۶-۰۸-۱۵

این سند برای کسیه که لینک این ریپو رو گرفته و می‌خواد بدون این‌که مجبور باشه کل تاریخچه‌ی گیت یا
۳۰+ فایل `docs/` رو بخونه، بفهمه: پوشه‌ها چیه، هر کد اصلی چجوری اجرا می‌شه، کدوم Notebook رو باید باز کنه،
و کدوم سند برای چیه. برای جزئیات عمیق‌تر، هرجا لازم بود به سند اصلی‌اش لینک دادم — این‌جا تکرارش نکردم.

---

## ۱. ساختار پوشه‌ها

```
config/          # پیکربندی (نه هاردکد توی کد): موضوع، Query، زبان، بازه زمانی، Schema
src/              # کد اصلی، به ترتیب جریان داده:
  ingestion/        - سه Collector (X, Reddit, YouTube) + هش نویسنده + geo + ریسک Bot
  preprocessing/     - Harmonization → Eligibility → Normalize متن → Duplicate detection
  annotation/         - Schema/Prompt/Model Route + اجرای واقعی Annotation با LLM
  validation/          - توافق انسانی (Kappa) + ارزیابی مدل روی Gold Sample
  temporal_analysis/    - آمار توصیفی، روند هفتگی، Composition Shift، مقایسه گروه‌ها، حساسیت، مالی
  event_analysis/        - Event Registry + Event Study
  cost_tracking/           - لاگ هزینه/Latency هر تماس LLM
  reporting/                 - ساخت Dashboard/HTML از outputs/tables
  pipeline/                   - run_pipeline.py: نقطه ورود واحد (بخش ۴)
  intake/                      - Inventory/Coverage/Quality Grade هر پلتفرم
notebooks/       # Notebookهای قابل‌اجرا (بخش ۵ و ۶)
data/
  raw_original/     # فایل خام همون‌طور که Collector تحویل داده (بزرگ، عمداً از گیت خارج)
  raw/                # خروجی میانی Collectorها (jsonl) — عمداً از گیت خارج
  raw_harmonized/      # داده هم‌نام‌شده طبق Schema مشترک، به تفکیک پلتفرم (parquet) — بخشی tracked
  interim/               # خروجی Eligibility/Preprocessing (opinion_main/limited/untimed/...)
  annotated/               # نمونه Gold (۳۰۰ رکورد لیبل‌خورده دستی) — tracked
  processed/                # annotated_dataset.parquet نهایی (پل Pipeline A→B) — عمداً از گیت خارج (حجیم)
  audits/                    # گزارش‌های کیفیت داده (Duplicate، Relevance، Eligibility funnel)
outputs/
  tables/           # همه‌ی خروجی‌های عددی Pipeline B (روند، Event Study، حساسیت، مالی، …)
  audits/             # Agreement، Cleaning report
  model_evaluation/    # مقایسه مدل‌ها، Cost estimate، Cache annotation
  figures/               # نمودار (اگر تولید شده)
docs/             # همه‌ی مستندات — نقشه کامل: docs/README.md (بخش ۷ همین‌جا)
reports/          # تحویلی‌های نهایی سطح‌بالا (خلاصه مدیریتی/گزارش فنی) — بخش ۹
tests/            # ۵۵ تست واحد (pytest) روی توابع Schema/Eligibility/Automation-risk/آماری
scripts/          # ابزارهای کمکی یک‌بارمصرف (مثلاً ساخت fixture مصنوعی)
```

نکته‌ی مهم: خیلی از زیرپوشه‌های `data/` و `outputs/` عمداً از گیت خارج‌اند (`.gitignore`) چون یا حجیم‌اند یا
داده خام غیرضروری برای انتشارند؛ فقط تحویلی‌های کوچک و قابل‌بازبینی (مثل جدول‌های `outputs/tables/*.csv`،
Gold Sample، Audit reportها) واقعاً روی گیت‌اند. لیست دقیق در `.gitignore` ریشه پروژه است.

---

## ۲. شروع سریع

```bash
git clone https://github.com/parmida2b/media-sentiment-pipeline.git
cd media-sentiment-pipeline
pip install -r requirements.txt
cp .env.example .env   # کلیدهای API خودت رو بذار (YOUTUBE_API_KEY, GROQ_API_KEYS, OPENROUTER_API_KEY, FRED_API_KEY, AUTHOR_HASH_SALT)
```

اگه فقط می‌خوای ببینی پروژه چیکار کرده — نیازی به هیچ کلید API نیست، برو سراغ بخش ۳.

---

## ۳. سریع‌ترین راه برای دیدن نتیجه (بدون کلید API، بدون اجرای پایپ‌لاین) — ⚠️ فعلاً ناقص، بخش ۱۲ رو ببین

نوت‌بوک اصلی پروژه `notebooks/final_project_notebook_readable_markdown.ipynb` است — یک روایت end-to-end
در ۱۶ بخش (سؤال پژوهش → جمع‌آوری → Eligibility → Gold Sample → انتخاب مدل → Annotation → آمار توصیفی →
روند هفتگی → Composition Shift → مقایسه گروه‌ها → Event Study → شاخص مالی → حساسیت → ادعاهای نهایی →
محدودیت‌ها). **قرار بود** بدون هیچ کلید API یا اجرای پایپ‌لاین مستقیم قابل‌اجرا باشه، چون تئوریاً فقط از
فایل‌های از‌قبل‌تولیدشده می‌خونه — ولی با بررسی واقعی `.gitignore` معلوم شد این ادعا **درست نیست**:

```bash
jupyter notebook notebooks/final_project_notebook_readable_markdown.ipynb
```

روی یک Clone تازه از GitHub، فقط بخش‌های ۱ تا ۶ نوت‌بوک (Manifest، شمارش Harmonized، Eligibility funnel،
Gold Sample، Agreement، ارزیابی مدل) واقعاً اجرا می‌شن — چون فایل‌هاشون tracked‌ان. از سلول ۷ به بعد
(`data/processed/annotated_dataset.parquet` و بیشتر `outputs/tables/*.csv`) با `FileNotFoundError` می‌شکنه،
چون این فایل‌ها الان روی گیت نیستن (دلیل دقیق و راه‌حل پیشنهادی: بخش ۱۲).
**تا وقتی اون مشکل رفع نشه، این مسیر رو به کسی بیرون تیم به‌عنوان «کافیه» معرفی نکن.**

---

## ۴. اجرای پایپ‌لاین اصلی (نقطه ورود واحد)

پایپ‌لاین اصلی و مهم پروژه یک فایل است: **`src/pipeline/run_pipeline.py`**. این فایل منطق جدیدی ندارد —
فقط همان اسکریپت‌های تک‌تک (بخش ۵) را به ترتیب درست، با Subprocess صدا می‌زند و در اولین شکست متوقف می‌شود.

```bash
python src/pipeline/run_pipeline.py --list        # فقط برنامه رو نشون بده، هیچی اجرا نکن
python src/pipeline/run_pipeline.py                 # Pipeline A (بدون جمع‌آوری/annotation جدید) + کل Pipeline B
```

مراحل پرهزینه یا پرریسک پشت Flag اختیاری‌اند (پیش‌فرض خاموش): `--with-ingestion` (جمع‌آوری زنده،
Quota واقعی مصرف می‌کند)، `--with-annotation` (هزینه واقعی $، سقف $۱۰۰)، `--with-financial`،
`--with-notebooks`، `--with-profiling`. توضیح کامل هر Flag و این‌که چرا این معماری این‌شکلی طراحی شده:
[`architecture.md`](architecture.md).

---

## ۵. اجرای دستی هر مرحله (اگه نمی‌خوای از Orchestrator استفاده کنی)

راهنمای کامل با دستور دقیق هر قدم: [`how_to_run_pipeline_fa.md`](how_to_run_pipeline_fa.md). خلاصه‌ی
جدول‌بندی‌شده:

| مرحله | اسکریپت | کار |
|---|---|---|
| جمع‌آوری | `src/ingestion/youtube_extract.py`, `handoff_csv_to_record.py` | تبدیل خام هر پلتفرم به `Record` مشترک |
| Harmonization | `src/ingestion/backfill_raw_harmonized_v05.py` | یکسان‌سازی نام/نوع ستون سه پلتفرم |
| Eligibility | `src/preprocessing/apply_eligibility.py` | فیلتر/dedup/provenance → `opinion_main/limited/untimed/...` |
| پاکسازی متن | `src/preprocessing/normalize_text.py` | Normalize، URL/Hashtag/Emoji، Mask PII |
| Duplicate | `src/preprocessing/duplicate_analysis.py` | خوشه‌بندی متن بسیار مشابه |
| Gold Sample | `src/annotation/build_labeling_sample.py` | نمونه ۳۰۰تایی طبقه‌بندی‌شده برای لیبل‌زنی دستی |
| توافق/ارزیابی | `src/validation/compute_annotator_agreement.py`, `evaluate_sentiment_accuracy.py` | Kappa + F1 روی Gold |
| Annotation کامل | `src/annotation/run_full_annotation.py` | اجرای واقعی LLM، هزینه واقعی |
| پل A→B | `src/annotation/build_annotated_dataset.py` | ساخت `data/processed/annotated_dataset.parquet` |
| تحلیل (Pipeline B) | `src/temporal_analysis/*.py`, `src/event_analysis/event_study.py` | روند، Composition Shift، مقایسه گروه‌ها، حساسیت، Event Study |
| مالی | `src/temporal_analysis/build_financial_outputs.py` | هم‌ترازی شاخص مالی با روند اجتماعی |

همه‌ی اسکریپت‌های تحلیل (Pipeline B) به `--input data/processed/annotated_dataset.parquet` نیاز دارند.

---

## ۶. بقیه Notebookها — کدوم برای چیه

| Notebook | برای چی |
|---|---|
| `final_project_notebook_readable_markdown.ipynb` | **نوت‌بوک اصلی/نهایی** — روایت کامل پروژه (بخش ۳) |
| `05_descriptive_and_temporal_analysis.ipynb` | آمار توصیفی + روند هفتگی، جدا و تمرکزی‌تر از نوت‌بوک اصلی |
| `06_event_and_financial_analysis.ipynb` | Event Study + هم‌ترازی مالی |
| `07_sensitivity_and_final_claims.ipynb` | مقایسه گروه‌ها + حساسیت + Claim Registry |
| `financial/01_financial_preparation_and_quality.ipynb` | آماده‌سازی/کیفیت داده مالی خام |
| `financial/02_financial_social_alignment.ipynb` | هم‌ترازی زمانی مالی × اجتماعی (بعد از Notebook ۱) |
| `Scraper_v_4_5_github.ipynb`, `reddit_bot_detection.ipynb`, `reddit_raw_schema.ipynb` | Notebookهای کاری/توسعه Collector — نه بخشی از تحویلی نهایی، برای دیدن نحوه کار Collectorها مفیدن |

نوت‌بوک‌های `05`/`06`/`07` و نوت‌بوک مالی دوم، همون تحلیل‌هایی هستن که `run_pipeline.py --with-notebooks`
دوباره اجراشون می‌کنه (بخش ۴).

---

## ۷. مستندات مهم — کدوم برای چیه

نقشه کامل و همیشه‌به‌روز: [`docs/README.md`](README.md) (به دو دسته «سند مشاور/هدف» و «سند فنی وضعیت فعلی
کد» تقسیم شده — قبل از خوندن هر سند دیگه، اول همون فایل رو چک کن). خلاصه‌ی مهم‌ترین‌ها:

| سند | چی توشه |
|---|---|
| [`PROJECT_EXECUTION_ORDER_v1.md`](PROJECT_EXECUTION_ORDER_v1.md) | ترتیب ۱۰مرحله‌ای کل پروژه — **همیشه اول این رو بخون** |
| [`decision_log.md`](decision_log.md) | چرا هر تصمیم مهم گرفته شده، تاریخ‌دار — وقتی چیزی عجیب به‌نظر می‌رسه، اول این‌جا رو چک کن |
| [`Chapter_1_Project_Definition_and_Research_Design_v5.md`](Chapter_1_Project_Definition_and_Research_Design_v5.md) | سؤال پژوهش، بازه، دامنه استنباط، محدودیت |
| [`Chapter_2_..._merged_readable.md`](Chapter_2_Statistical_Population_and_Sampling_Design_merged_readable.md) | جامعه آماری و Sampling Frame |
| [`Chapter_3_..._merged_readable.md`](Chapter_3_Platform_Selection_and_Source_Justification_merged_readable.md) | چرا این سه پلتفرم |
| [`eligibility_rules_v03.md`](eligibility_rules_v03.md) | قواعد دقیق ورود/خروج رکورد به دیتاست تحلیلی |
| [`source_registry_v4.md`](source_registry_v4.md) / [`query_registry_v5.md`](query_registry_v5.md) | فهرست منابع مجاز و قرارداد Query |
| [`event_registry_v3.md`](event_registry_v3.md) | فهرست رویدادها، پیش‌ثبت‌شده برای Event Study |
| [`pre_analysis_decision_table_v1.md`](pre_analysis_decision_table_v1.md) | تصمیم‌هایی که قبل از Annotation کامل قفل شدن |
| [`how_to_run_pipeline_fa.md`](how_to_run_pipeline_fa.md) | دستور دقیق اجرای هر قدم (بخش ۵ همین سند) |
| [`architecture.md`](architecture.md) | معماری Pipeline A/B و `run_pipeline.py` (بخش ۴ همین سند) |
| [`data_and_features_dictionary_fa.md`](archive/data_and_features_dictionary_fa.md) *(بایگانی، معتبر برای YouTube)* | توضیح ستون‌ها برای کسی که Dashboard/تحلیل می‌سازه |
| [`manual_labeling_guide_fa.md`](archive/manual_labeling_guide_fa.md) | راهنمای Annotator برای لیبل‌زنی دستی Gold Sample |
| [`financial/README_FINANCIAL_WORKFLOW_FA.md`](financial/README_FINANCIAL_WORKFLOW_FA.md) | ترتیب اجرای بخش مالی |

هرچی داخل `docs/archive/` هست یعنی جایگزین شده — بنر بالای هر فایل بایگانی‌شده می‌گه دقیقاً چرا و با چی
جایگزین شده؛ برای خوندن سریع کافیه.

---

## ۸. تاریخچه‌ی برنچ‌ها — از کجا اومدیم

کار تیمی روی چند Feature branch جدا پیش رفت (هرکس مسئول یک پلتفرم/بخش) و در نهایت روی برنچ
**`parmida/day5-docs-cleanup`** جمع شد — یعنی همون‌جایی که کد X (`feature/twitter-files`، از حسین)، کد
هماهنگ‌سازی X/Reddit (`yasaman/raw-harmonized-x-reddit`)، Composition Shift (`yasaman/day5-composition-shift`)
و تحلیل مالی (`analysis/finance`، از علی) merge شدن. برنچ فعلی، **`parmida/day5-docs-cleanup-final`**، ادامه‌ی
مستقیم همون برنچه (شامل تکمیل annotation، مقایسه گروه‌ها، حساسیت، Claim Registry و این گزارش‌ها).

یعنی اگه دنبال این هستی که پایپ‌لاین رو با آخرین کد یکپارچه‌شده‌ی همه اجرا کنی، باید از همین برنچ
(`parmida/day5-docs-cleanup-final`) یا از `main` (که این برنچ قرار است به آن merge شود) استفاده کنی — نه
از برنچ‌های قدیمی‌تر مثل `integration/merge-all` که خیلی عقب‌تره و خیلی از فایل‌های فعلی رو اصلاً نداره.

---

## ۹. Power BI Dashboard و گزارش‌های نهایی

- **`V_GROUP_DASHBOARD`** — داشبورد Power BI تیم، از جدول‌های `outputs/tables/` (و `outputs/tables/event_analysis/`,
  `outputs/tables/financial/`) تغذیه می‌شود. فایل `.pbix` در این ریپو نیست (باینری/بیرون از Git)؛ اگه قراره
  لینکش رو هم بدی، جای مناسبش همین بخش از این سنده.
- دو سند تحلیلی همراه داشبورد (فایل‌شون در این ریپو نیست، فقط این‌جا نام‌شون ثبت می‌شه تا فراموش نشه اضافه
  بشن): `report_final_po..._analysis_fa.md` و `scenario_filtering...deep_dive_fa.md` — قبل از پابلیش‌کردن این
  راهنما، این دو اسم رو با نام کامل و مسیر واقعی‌شون جایگزین کن (اسمی که این‌جا اومده احتمالاً توی کپی‌پیست
  کوتاه شده).
- اگه دنبال یک نسخه HTML/غیر-PowerBI از Dashboard می‌گردی، `src/reporting/build_dashboard.py` +
  `src/reporting/dashboard_template.html` از قبل توی ریپو هست.
- **گزارش فنی کامل پروژه:** [`reports/technical_report_fa.md`](../reports/technical_report_fa.md) — همه‌ی
  اعداد، محدودیت‌ها، و روش‌شناسی، رد‌یابی‌شده به فایل خروجی واقعی‌اش.

---

## ۱۰. قبل از این‌که ریپو رو Public کنی — چک کن

این‌ها رو خودم بررسی کردم؛ نتیجه رو این‌جا می‌نویسم تا لازم نباشه دوباره چک کنی:

- ✅ `.env` واقعی هیچ‌وقت commit نشده (فقط `.env.example`) — کلید API لو نرفته.
- ✅ `data/raw.zip` و `data/raw/data.zip` (خام حجیم) هیچ‌وقت commit نشدن.
- ✅ فایل‌های `data/raw_harmonized/youtube/*.parquet` که روی گیت‌ان رو نمونه‌برداری کردم — فقط `author_hash`
  دارن، نه نام نمایشی خام.
- ⚠️ **حجم `.git` تاریخچه فعلاً حدود ۷۰۰ مگابایته** — قبل از Public کردن روی GitHub بررسی کن آیا این حجم
  قابل قبوله یا باید تاریخچه Squash/Clean بشه (به‌خصوص اگه جایی توی تاریخچه — نه لزوماً HEAD فعلی — یک
  فایل خام حجیم یک‌بار commit و بعد حذف شده باشه؛ من فقط HEAD رو چک کردم، نه کل تاریخچه).
- ⚠️ **هیچ فایل LICENSE توی ریشه پروژه نیست.** اگه قراره پابلیک بشه، بدون License مشخص، از نظر قانونی
  «همه حق محفوظ» پیش‌فرضه — یعنی حتی خود اعضای تیم هم رسماً اجازه‌ی reuse ندارن. اگه هدف اشتراک آزاده،
  یک `LICENSE` (مثلاً MIT) اضافه کن.
- ⚠️ **پوشش Annotation فعلی فقط ۳٫۲٪ از داده Eligible است** (طراحی‌شده، نه نقص — توضیح کامل در
  `reports/technical_report_fa.md` بخش ۷) — اگه این راهنما رو با غریبه‌ها به اشتراک می‌ذاری، بهتره همون‌جا
  یک جمله راجع به این محدودیت باشه تا کسی داشبورد رو با «تحلیل کامل کل داده» اشتباه نگیره.

---

## ۱۱. چیزهایی که فکر می‌کنم جا افتاده (پیشنهاد، نه انجام‌شده)

- **README ریشه** فعلاً کوتاه و قدیمی‌تره (لینک به `docs/archive/GIT_WORKFLOW.md` برای «ساختار پروژه» می‌ده
  که یک سند بایگانی‌شده‌ی مخصوص فاز توسعه‌ست، نه ساختار نهایی). پیشنهاد: یا این فایل (`PROJECT_GUIDE_fa.md`)
  رو از همون README ریشه لینک بده («برای نقشه کامل پروژه، این‌جا رو ببین»)، یا خلاصه‌ای از بخش ۱-۴ همین
  سند رو مستقیم توی README ریشه هم بیار — چون README ریشه اولین چیزیه که آدم روی GitHub می‌بینه.
- **یک نسخه‌ی انگلیسی** این راهنما نداری؛ اگه قراره لینک رو با کسی خارج از تیم فارسی‌زبان به اشتراک بذاری،
  حداقل یک خلاصه انگلیسی کوتاه (چند خط: پروژه چیه، چجوری اجرا می‌شه، کجا مستندات کامل رو ببینه) به README
  ریشه اضافه کن.
- **مسیر/لینک واقعی V_GROUP_DASHBOARD و دو سند تحلیل همراهش** هنوز جایی توی این ریپو ثبت نشده (بخش ۹) —
  همین الان یادداشت شد که فراموش نشه.
- **CONTRIBUTING/نحوه گزارش مشکل** نداری — برای ریپوی صرفاً «نمایش نتیجه» شاید لازم نباشه، ولی اگه انتظار
  داری کسی روی این کد کار کنه یا مشکل گزارش بده، یک بخش کوتاه «چطور مشکل گزارش بدم / issue باز کنم» خوبه.
- **`docs/checklist.md`** در چند سند دیگه (`decision_log.md`, `pre_analysis_decision_table_v1.md`) بارها
  ارجاع داده می‌شه ولی من همچین فایلی توی `docs/` پیدا نکردم — یا حذف/تغییرنام شده و ارجاع‌ها به‌روز نشدن، یا
  جایی خارج از این مسیر نگه‌داری می‌شه. اگه واقعاً وجود نداره، بهتره قبل از پابلیش کردن یا بسازیش یا ارجاع‌ها
  رو اصلاح کنی — چون یک خواننده بیرونی که دنبال این فایل بگرده، به بن‌بست می‌خوره.

اگه هرکدوم از این‌ها رو می‌خوای الان انجام بدم (مثلاً اصلاح README ریشه، پیدا/بازسازی `checklist.md`، یا
اضافه‌کردن LICENSE)، بگو کدوم رو شروع کنم.
