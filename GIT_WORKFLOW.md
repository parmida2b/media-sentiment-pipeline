# راهنمای کار با گیت — تیم media-sentiment-pipeline

هدف این راهنما: با ۴ نفر توی ۵ روز کار کنیم بدون این‌که روی هم رو بگیریم یا
ریپو رو با فایل‌های حجیم/کلید API خراب کنیم.

## ۱. کلون کردن ریپو (هر ۴ نفر همین یه بار)

```bash
git clone https://github.com/parmida2b/media-sentiment-pipeline.git
cd media-sentiment-pipeline
```

## ۲. ساختار پوشه‌ها (پیشنهادی)

```
media-sentiment-pipeline/
├── src/
│   ├── extraction/
│   │   ├── youtube.py          <- پارمیدا
│   │   ├── reddit.py           <- حسین
│   │   └── telegram.py         <- حسین/پارمیدا (اگه لازم شد)
│   ├── financial/
│   │   └── yahoo.py            <- علی
│   ├── sentiment/
│   │   └── llm_sentiment.py    <- پارمیدا
│   ├── analysis/
│   │   └── correlation.py      <- علی
│   └── pipeline/
│       └── run_pipeline.py     <- بخش امتیازی (Pipeline قابل‌تعمیم)
├── config/
│   └── schema.py                <- تعریف مشترک فرمت داده (فقط حسین ویرایش کنه)
├── data/
│   ├── raw/          (gitignore شده - فقط لوکاله)
│   └── processed/    (gitignore شده - فقط لوکاله)
├── docs/
│   └── methodology.md           <- ریحانه
├── outputs/           (gitignore شده)
├── requirements.txt
├── .gitignore
└── README.md
```

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
git add src/extraction/youtube.py
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
  `src/extraction/youtube.py` و `src/sentiment/`، علی فقط توی
  `src/financial/` و `src/analysis/`.
- **`config/schema.py` فقط حسینه که تغییرش می‌ده.** اگه کسی نیاز به تغییر
  فرمت داره، اول توی گروه بگه، حسین اعمال کنه، بقیه `pull` کنن.
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
موضوع تحلیل (topic/keywords) از یه فایل کانفیگ (`config/topic.yaml` یا
مشابه) خونده بشه، نه هاردکد. این دقیقاً همون چیزیه که سند برای بخش
امتیازی می‌خواد و با اسم ریپو هم هم‌خونی داره.
