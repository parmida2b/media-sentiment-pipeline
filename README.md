# media-sentiment-pipeline

سامانه تحلیل افکار عمومی درباره یک موضوع مشخص (فعلاً: جنگ ایران و آمریکا)،
با قابلیت استفاده مجدد برای موضوعات دیگر (بخش امتیازی پروژه).

## اعضای تیم و مسئولیت‌ها
| نفر | حوزه |
|---|---|
| حسین | استخراج Reddit + یکپارچه‌سازی نهایی + schema |
| پارمیدا | استخراج YouTube/Telegram + مدل sentiment |
| علی | داده مالی/اقتصادی + تحلیل آماری/علیت |
| ریحانه | ارزیابی جامعه آماری + داشبورد + مستندسازی |

## شروع سریع
```bash
git clone https://github.com/parmida2b/media-sentiment-pipeline.git
cd media-sentiment-pipeline
pip install -r requirements.txt
cp .env.example .env   # کلیدهای API خودت رو بذار
```

## قبل از هر کاری
راهنمای کار با گیت رو بخون: [`GIT_WORKFLOW.md`](./GIT_WORKFLOW.md)
مخصوصاً بخش استراتژی برنچ و جلوگیری از conflict.

## فرمت داده مشترک
همه ماژول‌های استخراج باید طبق `config/schema.py` خروجی بدن. قبل از تغییر
فیلدها، با حسین هماهنگ کن.

## ساختار پروژه
جزئیات کامل توی `GIT_WORKFLOW.md` هست.
