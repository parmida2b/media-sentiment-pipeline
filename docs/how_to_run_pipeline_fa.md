# راهنمای اجرای Pipeline — از صفر تا خروجی

**آخرین به‌روزرسانی:** ۲۰۲۶-۰۸-۱۴

این سند ترتیب واقعی اجرای دستورهاست، نه توضیح مفهومی (اون‌ها در `docs/checklist.md` و `docs/PROJECT_EXECUTION_ORDER_v1.md` هستن). همه‌ی دستورها از ریشه‌ی پروژه (همون پوشه‌ای که `config/`, `src/`, `data/` توشه) اجرا می‌شن.

⚠️ **اگه فقط می‌خوای از خروجی‌های آماده استفاده کنی (مثلاً برای Power BI)، نیازی به اجرای هیچ‌کدوم از این دستورها نیست** — برو سراغ [`handoff_notes_fa.md`](handoff_notes_fa.md). این سند فقط برای وقتیه که چیزی عوض شده (داده‌ی خام جدید، annotation بیشتر، ...) و باید Pipeline رو دوباره اجرا کنی.

---

## Pipeline A — جمع‌آوری و آماده‌سازی داده

فقط وقتی نیاز داری که داده‌ی خام جدید اومده یا یکی از مراحل زیر عوض شده. اگه فقط annotation بیشتر شده، مستقیم برو به «قدم ۸».

```bash
# ۱. تبدیل داده‌ی خام هر پلتفرم به Record مشترک (اگه داده‌ی خام جدید اومده)
python src/ingestion/handoff_csv_to_record.py --input data/raw_original/x/records/X_Scraper_v4_7_Target20K_Current.xlsx --sheet Raw_Tweets --platform x
python src/ingestion/handoff_csv_to_record.py --input data/raw_original/reddit/records/reddit_raw_schema.csv --platform reddit
python src/ingestion/youtube_extract.py   # یوتیوب مسیر جدا داره (Collector زنده)

# ۲. ساخت لایه‌ی raw_harmonized (v05) از روی Recordهای بالا
python src/ingestion/backfill_raw_harmonized_v05.py

# ۳. اجرای Eligibility (فیلتر/dedup/provenance) — خروجی: data/interim/{opinion_main,opinion_limited,...}.parquet
python src/preprocessing/apply_eligibility.py

# ۴. پردازش متن (Normalize، URL/Hashtag/Emoji، Mask PII) — روی خروجی قدم ۳
python src/preprocessing/normalize_text.py

# ۵. تشخیص Duplicate/Near-duplicate — روی خروجی قدم ۴ (نیاز به text_normalized داره)
python src/preprocessing/duplicate_analysis.py

# ۶. (اختیاری) بازسازی/به‌روزرسانی Inventory و Coverage — فقط اگه فایل خام جدید اومده
python src/intake/profile_platform.py --platform x
python src/intake/profile_platform.py --platform reddit
python src/intake/profile_platform.py --platform youtube
python src/intake/quality_grade.py --apply
python src/intake/sync_query_execution_audit.py --platform youtube
```

### Gold Sample و ارزیابی مدل (فقط اگه نیاز به annotator جدید/دوباره باشه)

```bash
# ساخت/به‌روزرسانی نمونه‌ی ۳۰۰تایی (پیش‌فرض: فقط Migrate، لیبل‌های موجود رو پاک نمی‌کنه)
python src/annotation/build_labeling_sample.py

# بعد از لیبل‌زنی دستی دو Annotator:
python src/validation/compute_annotator_agreement.py
python src/validation/evaluate_sentiment_accuracy.py
```

### Full Annotation (⚠️ هزینه‌ی واقعی API، فعلاً متوقف — سهمیه‌ی Groq/OpenRouter)

```bash
python src/annotation/run_full_annotation.py --confirm-cost-cap 100.0 --stratify-cap 120 --targets T01,T02,T03 --workers 20
```

### پل به Pipeline B (بعد از هر annotation جدید، این رو اجرا کن)

```bash
python src/annotation/build_annotated_dataset.py
```
این دقیقاً همون فایلی رو می‌سازه (`data/processed/annotated_dataset.parquet`) که Pipeline B بهش نیاز داره.

---

## Pipeline B — تحلیل (بعد از هر تغییر در annotated_dataset.parquet، همه‌ی این‌ها رو دوباره اجرا کن)

```bash
python -m src.temporal_analysis.descriptive_stats   --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.weekly_trend         --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.composition_shift    --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.group_comparison     --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.sensitivity_analysis --input data/processed/annotated_dataset.parquet
python -m src.event_analysis.event_study             --input data/processed/annotated_dataset.parquet

# مالی: اول جدول اجتماعی هفتگی رو بساز، بعد Notebook هم‌ترازی رو اجرا کن
python -m src.temporal_analysis.build_social_weekly_outcomes --input data/processed/annotated_dataset.parquet
python -m nbconvert --to notebook --execute --inplace notebooks/financial/02_financial_social_alignment.ipynb
```

همه‌ی خروجی‌ها می‌رن توی `outputs/tables/` (و `outputs/tables/event_analysis/`, `outputs/tables/financial/`) — دقیقاً همون فایل‌هایی که `handoff_notes_fa.md` توضیح داده.

### Notebookهای نهایی (برای دمو/ارائه — بعد از اجرای بالا)

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/05_descriptive_and_temporal_analysis.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/06_event_and_financial_analysis.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/07_sensitivity_and_final_claims.ipynb
```

---

## کوتاه‌ترین مسیر — «فقط annotation بیشتر شده، بقیه‌چیز عوض نشده»

```bash
python src/annotation/build_annotated_dataset.py
python -m src.temporal_analysis.descriptive_stats   --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.weekly_trend         --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.composition_shift    --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.group_comparison     --input data/processed/annotated_dataset.parquet
python -m src.temporal_analysis.sensitivity_analysis --input data/processed/annotated_dataset.parquet
python -m src.event_analysis.event_study             --input data/processed/annotated_dataset.parquet
```

## نکات مهم

- همیشه اول `--dry-run` بزن (اکثر اسکریپت‌های Pipeline A این فلگ رو دارن) قبل از اجرای واقعی.
- اگه `sample_sentiment_labels.csv` یا `sample_sentiment_labels_agreement_subset.csv` رو توی Excel باز می‌کنی، **قبل از ذخیره حتماً چک کن** ستون `content_id` به Scientific Notation تبدیل نشده باشه (مشکلی که دوبار پیش اومد — `docs/decision_log.md` ۲۰۲۶-۰۸-۱۴).
- اسکریپت‌های `outputs/tables/*` رو مستقیم دستکاری نکن — همیشه از اسکریپت مربوطه دوباره بساز.
