# راهنمای کار با گیت — تیم media-sentiment-pipeline

هدف این راهنما: با ۴ نفر توی ۵ روز کار کنیم بدون این‌که روی هم رو بگیریم یا
ریپو رو با فایل‌های حجیم/کلید API خراب کنیم.

## ۱. کلون کردن ریپو (هر ۴ نفر همین یه بار)

```bash
git clone https://github.com/parmida2b/media-sentiment-pipeline.git
cd media-sentiment-pipeline
```

## ۲. ساختار پوشه‌ها

```
media-sentiment-pipeline/
├── config/
│   ├── config.yaml               <- موضوع/کلمات‌کلیدی/بازه‌زمانی/تنظیمات هر پلتفرم
│   ├── config_loader.py
│   └── schema.py                 <- تعریف مشترک فرمت داده (ایده از یاسمن؛ توسعه/نگهداری با پارمیدا)
├── src/
│   ├── ingestion/                 <- استخراج خام از هر پلتفرم
│   │   ├── youtube_extract.py، channels.py، checkpoint.py، geo_tagger.py   <- پارمیدا
│   │   └── reddit_extract.py (وقتی ساخته شد)                              <- حسین
│   ├── preprocessing/             <- پاکسازی/نرمال‌سازی قبل از annotation (خالی، هنوز ساخته نشده)
│   ├── annotation/                <- تولید لیبل sentiment (دستی/LLM)
│   │   └── build_labeling_sample.py، compare_llm_sentiment.py  <- پارمیدا
│   ├── validation/                <- سنجش دقت annotation در برابر لیبل انسانی
│   │   └── evaluate_sentiment_accuracy.py  <- پارمیدا
│   ├── temporal_analysis/         <- تحلیل روند زمانی (خالی، علی)
│   ├── event_analysis/            <- تحلیل هم‌زمانی با رویدادها (خالی، علی)
│   ├── cost_tracking/             <- ردیابی هزینه API/LLM (خالی، هنوز assign نشده)
│   └── reporting/                 <- داشبورد/گزارش نهایی (خالی، ریحانه)
├── data/
│   ├── raw/          (gitignore شده - فقط لوکاله)      <- خروجی خام هر پلتفرم، زیر {topic_id}/
│   ├── interim/      (gitignore شده - فقط لوکاله)      <- خروجی preprocessing
│   ├── annotated/                                       <- نمونه‌های لیبل‌خورده (sample_*.csv مستثنا از gitignore)
│   ├── processed/    (gitignore شده - فقط لوکاله)
│   └── reference/                                        <- دیتای مرجع غیرحجیم (مثلاً رویدادها.xlsx)
├── outputs/           (gitignore شده جز .gitkeep)
│   ├── figures/، tables/، audits/، model_evaluation/
├── notebooks/
├── reports/
├── docs/
│   ├── overview.md، architecture.md، setup.md، decision_log.md
│   └── images/
├── requirements.txt
├── .gitignore
└── README.md
```

فایل‌های داخل `src/preprocessing/`, `temporal_analysis/`, `event_analysis/`, `cost_tracking/`, `reporting/` هنوز نوشته نشدن — پوشه‌ها از قبل ساخته شدن که وقتی هرکس به مرحله‌ش رسید، مستقیم همون‌جا کد بزنه، نه این‌که ساختار رو وسط کار دوباره جابه‌جا کنیم.

**نکته کلیدی:** فایل‌های داده (`.csv`, `.jsonl`) وارد گیت نمی‌شن (توی
`.gitignore` هست). برای رد و بدل کردن دیتای واقعی بین اعضا از یه Google
Drive/لینک مشترک استفاده کنید، نه گیت — وگرنه ریپو خیلی سنگین و merge
conflict روش زیاد می‌شه.

## ۳. استراتژی برنچ (خیلی مهم برای جلوگیری از تداخل)

هر کس برای کار خودش یه برنچ جدا می‌سازه، هیچ‌وقت مستقیم روی `main` کار نمی‌کنه:

```bash
git checkout -b parmida/day1-youtube-extraction
```

قالب اسم برنچ: `<اسم>/<روز>-<توضیح کوتاه>`
مثال‌ها:
- `parmida/day1-youtube-extraction`
- `ali/day1-financial-data`
- `hossein/day1-reddit-pipeline`
- `reyhaneh/day1-source-evaluation`

## ۴. روال روزانه (هر روز صبح و عصر)

**صبح، قبل از شروع کار:**
```bash
git checkout main
git pull origin main          # آخرین تغییرات بقیه رو بگیر
git checkout -b <name>/dayN-...
```

**در طول روز:** کامیت‌های کوچیک و مکرر (نه یه کامیت غول‌پیکر آخر روز):
```bash
git add src/ingestion/youtube_extract.py
git commit -m "youtube: افزودن استخراج کامنت با pagination"
```

**عصر، قبل از standup:**
```bash
git push origin <name>/dayN-...
```
بعد یه Pull Request بساز روی گیت‌هاب به سمت `main`، حتی اگه فقط خودت
ریویو کنی — این‌جوری تاریخچه تغییرات شفاف می‌مونه و اگه چیزی خراب شد
راحت برمی‌گردید عقب.

اگه واقعاً وقت نیست برای PR، حداقل مستقیم merge کنید نه force-push:
```bash
git checkout main
git pull origin main
git merge <name>/dayN-...
git push origin main
```

## ۵. جلوگیری از Merge Conflict

- **هر کس فقط توی فایل‌های پوشه خودش کار کنه.** مثلاً پارمیدا فقط توی
  `src/ingestion/` (بخش یوتیوب) و `src/annotation/` + `src/validation/`،
  علی فقط توی `src/temporal_analysis/` و `src/event_analysis/`.
- **`config/schema.py` رو پارمیدا نگهداری/تغییر می‌ده** (ایده اولیه از یاسمن). اگه کسی نیاز به تغییر
  فرمت داره، اول توی گروه بگه، پارمیدا اعمال کنه، بقیه `pull` کنن.
- قبل از هر `push`، حتماً یه `git pull origin main` بزنید تا اگه تغییری
  اومده بود، conflict رو زودتر و کوچیک‌تر ببینید (نه آخر روز پنجم!).

### اگه conflict خوردید:
```bash
git pull origin main
# گیت فایل‌های conflict شده رو نشون می‌ده، مثلاً:
# <<<<<<< HEAD
# کد شما
# =======
# کد بقیه
# >>>>>>> branch-name
# دستی انتخاب کن کدوم بمونه (یا هر دو رو ترکیب کن)، بعد:
git add <فایل>
git commit
git push
```

## ۶. قبل از اولین push، این چک‌لیست رو رعایت کن

- [ ] هیچ کلید API‌ای (`YOUTUBE_API_KEY`, `GEMINI_API_KEY`, و غیره) توی کد
      هاردکد نشده — همیشه از `os.environ` بخون.
- [ ] فایل `.env` (اگه ساختی) توی `.gitignore` هست (هست، چک شده).
- [ ] فایل‌های داده حجیم (`.csv`, `.jsonl`) commit نشدن.
- [ ] قبل از commit یه بار `git status` بزن و مطمئن شو فقط فایل‌های کد
      اضافه شدن، نه چیز اضافه.

## ۷. یه نکته برای بخش امتیازی (Pipeline)
چون اسم ریپو `media-sentiment-pipeline`‌ـه (نه `iran-us-war-analysis`)،
بهتره از همین الان `src/pipeline/run_pipeline.py` رو طوری بنویسید که
موضوع تحلیل (topic/keywords) از یه فایل کانفیگ خونده بشه، نه هاردکد —
همون کاری که `config/config.yaml` + `config/config_loader.py` الان
برای `src/ingestion/youtube_extract.py` انجام می‌دن، همون الگو رو برای
بقیه مراحل هم ادامه بدید. این دقیقاً همون چیزیه که سند برای بخش
امتیازی می‌خواد و با اسم ریپو هم هم‌خونی داره.
