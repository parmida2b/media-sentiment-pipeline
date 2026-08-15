# media-sentiment-pipeline

سامانه تحلیل افکار عمومی درباره یک موضوع مشخص (فعلاً: جنگ ایران و آمریکا)،
با قابلیت استفاده مجدد برای موضوعات دیگر (بخش امتیازی پروژه).

## اعضای تیم و مسئولیت‌ها
| نفر | حوزه |
|---|---|
| حسین | استخراج Reddit + یکپارچه‌سازی نهایی |
| پارمیدا | استخراج YouTube + مدل sentiment + schema (ایده از یاسمن) |
| علی | داده مالی/اقتصادی + تحلیل آماری/علیت |
| ریحانه | ارزیابی جامعه آماری + داشبورد + مستندسازی |

## شروع سریع
```bash
git clone https://github.com/parmida2b/media-sentiment-pipeline.git
cd media-sentiment-pipeline
pip install -r requirements.txt
cp .env.example .env   # کلیدهای API خودت رو بذار
```

## اجرای کامل Pipeline
راهنمای مرحله‌به‌مرحله (دستور دقیق هر قدم، از داده خام تا خروجی نهایی) در
[`docs/how_to_run_pipeline_fa.md`](docs/how_to_run_pipeline_fa.md) هست —
شامل Pipeline A (جمع‌آوری/آماده‌سازی)، Full Annotation، Pipeline B (تحلیل)،
و کوتاه‌ترین مسیر برای وقتی فقط annotation جدید اضافه شده.
اگه فقط دنبال خروجی‌های آماده (مثلاً برای Power BI) هستی و نیازی به اجرای
دوباره‌ی کد نداری، به‌جاش سراغ [`docs/archive/handoff_notes_fa.md`](docs/archive/handoff_notes_fa.md) برو.

نقشه کامل مستندات پروژه (کدوم سند برای چی): [`docs/README.md`](docs/README.md)

## قبل از هر کاری
راهنمای کار با گیت (بایگانی‌شده، مخصوص فاز توسعه): [`docs/archive/GIT_WORKFLOW.md`](./docs/archive/GIT_WORKFLOW.md)
مخصوصاً بخش استراتژی برنچ و جلوگیری از conflict.

## فرمت داده مشترک
همه ماژول‌های استخراج باید طبق `config/schema.py` خروجی بدن. قبل از تغییر
فیلدها، با پارمیدا هماهنگ کن.

## تنظیمات موضوع پروژه (`config/config.yaml`)
موضوع، کلمات کلیدی، بازه زمانی و پارامترهای هر پلتفرم همگی از
`config/config.yaml` خونده می‌شن، نه هاردکد توی کد. برای تحلیل یک موضوع
جدید (بخش امتیازی سند پروژه)، فقط همین فایل رو ویرایش کن — لازم نیست کد
`src/ingestion/` تغییر کنه. خروجی هر موضوع هم زیر `data/raw/{topic_id}/`
جدا از موضوع‌های قبلی ذخیره می‌شه.

## ساختار پروژه
جزئیات کامل توی `docs/archive/GIT_WORKFLOW.md` هست.

## جریان مالی

راهنمای کامل در [`docs/financial/README_FINANCIAL_WORKFLOW_FA.md`](docs/financial/README_FINANCIAL_WORKFLOW_FA.md) قرار دارد. ورودی‌های مالی عمومی و Freeze‌شده با Notebook اول به بازده‌های هفتگی تبدیل می‌شوند و Notebook دوم، پس از آماده‌شدن Outcomeهای هفتگی X، Reddit و YouTube، هم‌ترازی زمانی را اجرا می‌کند.

```bash
python -m src.temporal_analysis.build_financial_outputs
```

جمع‌آوری مجدد اختیاری است و به `FRED_API_KEY` در فایل محلی `.env` نیاز دارد:

```bash
python -m src.ingestion.finance_market_extract
```
