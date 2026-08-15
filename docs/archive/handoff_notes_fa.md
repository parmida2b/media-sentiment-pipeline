# یادداشت تحویل داده — برای تیم تحلیل/Power BI

**آخرین به‌روزرسانی: ۲۰۲۶-۰۸-۱۴ (همین امروز)**

این سند خلاصه‌ی «همین الان چی رو باید Import کنم و چقدر بهش اعتماد کنم» است.
برای توضیح کامل هر ستون/فایل، دو سند مرجع دائمی هست که این‌جا فقط بهشون
ارجاع می‌دیم، تکرارشون نمی‌کنیم:

- [`outputs_guide_fa.md`](./outputs_guide_fa.md) — توضیح کامل هر فایل و ستون توی `outputs/tables/`
- [`data_and_features_dictionary_fa.md`](./data_and_features_dictionary_fa.md) — توضیح ستون‌های داده‌ی خام (قدیمی‌تر، فقط یوتیوب؛ کم‌کاربردتر شده)

---

## بنا به اینکه با فایل قبلی رفتی جلو
فایل‌هایی که تا امروز صبح دستت رسیده (چه `*_SYNTHETIC_FOR_POWERBI.csv`، چه
هر نسخه‌ی قدیمی‌تر `outputs/tables/*`) **روی داده‌ی ساختگی (Synthetic)**
ساخته شده بودن — برای طراحی اسکلت/Measure/Relationship داشبورد کاملاً
درستن، ولی هیچ عددشون واقعی نیست.

**امروز (۲۰۲۶-۰۸-۱۴) برای اولین بار یک نسخه‌ی واقعی — هرچند ناقص ینا به محدودیت سهمیه— ساخته
و جایگزین شد.** فایل‌های زیر رو دوباره از همین منبع واقعی گرفتم:

```
outputs/tables/descriptive_stats_overall.csv
outputs/tables/descriptive_stats_by_platform.csv
outputs/tables/descriptive_stats_by_platform_week.csv
outputs/tables/descriptive_stats_by_week_pooled_all_platforms.csv
outputs/tables/descriptive_stats_category_shares.csv
outputs/tables/descriptive_stats_missing_rates.csv
outputs/tables/descriptive_stats_annotation_coverage.csv
outputs/tables/weekly_trend_sentiment_by_platform.csv
outputs/tables/weekly_trend_stance_by_platform.csv
outputs/tables/weekly_trend_emotion_by_platform.csv
outputs/tables/weekly_trend_content_type_by_platform.csv
```

ساختار/نام ستون‌ها هیچ فرقی نکرده، فقط باید همین نسخه‌ی جدید رو
جایگزین نسخه‌ی قبلی کنی (Refresh در Power BI کافیه، مدل/رابطه‌ای که ساختی
از بین نمی‌ره).

**آپدیت:** `composition_shift_*.csv` (۱۰ فایل)، `event_study_*.csv` (۶ فایل،
توی `outputs/tables/event_analysis/`) و `financial_social_correlation_results_v1.csv`
(توی `outputs/tables/financial/` — نیاز به اجرای دوباره‌ی
`notebooks/financial/02_financial_social_alignment.ipynb` داشت چون به
`social_weekly_outcomes_v1.csv` وابسته بود، نه مستقیم annotated_dataset)
هم از همین منبع واقعی بازسازی شدن.

**یعنی الان هر ۳۳ فایل زیر `outputs/tables/` (و زیرپوشه‌هاش) روی داده‌ی
واقعی (هرچند ناقص بنا به محدودیت زمانی و اتمام سهمیه، ۳.۷٪) هستن — هیچ‌کدوم دیگه Synthetic نیست.** پنج فایل
دیگر مالی (`financial_asset_decisions_v1.csv`, `financial_daily_selected_v1.csv`,
`financial_weekly_returns_v1.csv`, `financial_coverage_summary_v1.csv`,
`financial_primary_event_windows_v1.csv`) اصلاً به annotation وابسته نبودن
(فقط داده‌ی بازار مالی خامن) — از اول هم واقعی بودن، نیازی به بازسازی نداشتن.

---

## ۱. پوشش واقعی امروز: فقط ۳.۷٪ — یعنی چی برای تو؟

از ۲۳۳,۰۰۶ رکورد واجد شرایط، فقط **۸,۵۹۸ تا (۳.۷٪) واقعاً لیبل‌خورده‌ن**
(`annotation_status = ok`). بقیه `pending_annotation`‌ان — یعنی هنوز
annotate نشدن، نه این‌که چیزی خطا داشته باشه.

**چرا الان متوقف شده:** سهمیه‌ی روزانه‌ی مدل اصلی (Groq) تموم شده و حساب
پشتیبان (OpenRouter) هم اعتبار نداره — یک مسدودکننده‌ی زیرساختی، نه باگ.
به‌محض رفع، annotation ادامه پیدا می‌کنه و همین فایل‌ها با پوشش بیشتر
Refresh می‌شن.

**خبر خوب:** این ۸,۵۹۸ تا به‌طور تصادفی/پراکنده نیستن — طبق طراحی
Stratified Sampling، تقریباً هر هفته از هر پلتفرم حداقل چند ده رکورد واقعی
داره (نه اینکه فقط چند هفته‌ی خاص پر باشه و بقیه خالی). برای همین توی
`weekly_trend_*.csv` فعلاً هیچ سلولی `is_data_gap=True` یا `is_low_sample=True`
نشده — یعنی حتی همین نسخه‌ی ناقص، از نظر آماری قابل‌نمایش‌دادنه (با ذکر
اینکه ناقصه)، فقط هنوز کل جمعیت رو پوشش نمی‌ده.

| پلتفرم | annotate شده (`ok`) | از کل eligible | نرخ خطا (`api_failure`+...) |
|---|---:|---:|---:|
| X | ۲,۵۱۹ | ۱۵,۷۹۲ | ۰.۰٪ |
| Reddit | ۴,۴۸۶ | ۱۵۲,۴۹۶ | ۵.۰٪ |
| YouTube | ۲,۴۰۰ | ۶۶,۵۶۷ | ۰.۰٪ |

**توصیه‌ی عملی:** الان می‌تونی نمودارهای واقعی (نه Synthetic) بسازی، ولی
حتماً روی داشبورد یک برچسب/تاریخ «پوشش annotation: ۳.۷٪ تا ۲۰۲۶-۰۸-۱۴» بذار
تا کسی عدد رو قطعی برداشت نکنه. وقتی پوشش بالاتر رفت، فقط Refresh کن — چیزی
توی Power BI نیاز به تغییر نداره.

---

## ۲. اگه مستقیم سراغ `data/processed/annotated_dataset.parquet` رفتی

این فایل **سطح رکورد خام** است (۲۳۴,۸۵۵ ردیف)، نه جدول آماده‌ی Power BI —
برای Power BI همیشه از `outputs/tables/*` (بالا) استفاده کن، نه این فایل.
اگه برای کار پایتونی/کد لازمش داشتی، دو نکته‌ی مهم:

1. **`content_id` یکتا نیست.** بعضی رکوردها تا ۳ ردیف دارن (یکی به‌ازای هر
   Target: T01/T02/T03 برای Stance) — `sentiment_label`/`emotion_label`/
   `content_type_label` بین این ردیف‌ها یکسانه، فقط `stance_label`/`target`
   فرق می‌کنه.
2. **`automation_risk_score_user` همیشه خالیه فعلاً** — یک Gap مستند
   (join بین دو فضای شناسه‌ی متفاوت هنوز انجام نشده)، نه باگ جدید.

جزئیات کامل هر دو مورد در `docs/decision_log.md` (۲۰۲۶-۰۸-۱۴) ثبت شده.

---

## ۳. اگه عدد عجیبی دیدی

اول `outputs_guide_fa.md` رو چک کن — اکثر چیزهایی که در نگاه اول عجیب به نظر
می‌رسن (مثلاً `parent_id` خیلی خالی، یا جمع `class_count` با `n_total` برابر
نبودن) قبلاً همون‌جا توضیح داده شدن و طبیعی‌ان. اگه چیزی واقعاً جور درنیومد،
قبل از حذف/نادیده‌گرفتن بپرس.
