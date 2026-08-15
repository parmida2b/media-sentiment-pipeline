# Architecture

**آخرین به‌روزرسانی:** ۲۰۲۶-۰۸-۱۵ — این سند دیگر TODO نیست؛ از وقتی `src/pipeline/run_pipeline.py`
(اتصال‌دهنده/Orchestrator مراحل) نوشته شد، معماری واقعی زیر مستقیماً از روی همان فایل مستند شده،
نه از روی نیت اولیه. اگر `run_pipeline.py` تغییر کرد و این سند به‌روز نشد، `run_pipeline.py` منبع درست است.

## ۱. تصویر کلی

پروژه دو Pipeline مستقل ولی زنجیره‌شده دارد (مرز دقیق در `docs/archive/pipeline_b_input_contract.md`):

```
Pipeline A (جمع‌آوری → آماده‌سازی → Annotation)
  raw_original → raw_harmonized → eligible_content (opinion_main/limited/untimed/context_only/audit_only)
      → [Gold Sample + ارزیابی مدل، دستی/نیمه‌دستی]
      → Full Annotation (LLM)
      → build_annotated_dataset.py  ← «پل» Pipeline A → B
                                          data/processed/annotated_dataset.parquet
                                                │
Pipeline B (تحلیل، فقط از روی فایل بالا)        ▼
  descriptive_stats → weekly_trend → composition_shift → group_comparison
      → sensitivity_analysis → event_study → build_social_weekly_outcomes
      → (Notebookهای دمو ۰۵/۰۶/۰۷ + Notebook هم‌ترازی مالی)
```

قاعده‌ی مرزی مهم: **Pipeline B هیچ‌وقت مستقیم از `data/raw/` یا `data/interim/` نمی‌خواند** — فقط و فقط از
`data/processed/annotated_dataset.parquet`. تا وقتی annotation واقعی کامل نبود، Pipeline B با یک fixture
مصنوعی هم‌schema توسعه داده می‌شد (امروز دیگر لازم نیست؛ فایل واقعی موجود است).

## ۲. چرا این تفکیک؟

هر مرحله ورودی مرحله‌ی قبل را مصرف می‌کند و مستقل تست/اجرا می‌شود؛ اگر یک مرحله خراب شود، مراحل قبلی و
خروجی‌شان دست‌نخورده می‌مانند (fail-fast، نه fail-silent):

- **Ingestion** (`src/ingestion/`) — سه پلتفرم، سه Collector مستقل (X/Reddit با Selenium، YouTube با API رسمی)،
  همه در نهایت یک `Record` مشترک تولید می‌کنند (`config/schema.py`). فایل خام هرگز بعداً دستکاری نمی‌شود.
- **Preprocessing** (`src/preprocessing/`) — Harmonization نام/نوع ستون‌ها، Eligibility (فیلتر/dedup/provenance)،
  Normalize متن، تشخیص Near-duplicate. هرکدام یک فایل ورودی مشخص می‌خواهند و خروجی جدا می‌نویسند، نه in-place
  روی خام.
- **Annotation** (`src/annotation/`) — Schema/Prompt/Model Route/Client جدا از اجرای واقعی (`run_full_annotation.py`)
  تا انتخاب مدل قابل تست/مقایسه باشد پیش از خرج پول واقعی.
- **Validation** (`src/validation/`) — Agreement انسانی و ارزیابی مدل، مستقل از annotation کامل — باید قبل از آن
  اجرا و قفل شود (`docs/pre_analysis_decision_table_v1.md`).
- **Temporal / Event analysis** (`src/temporal_analysis/`, `src/event_analysis/`) — محاسبات محلی خالص روی
  `annotated_dataset.parquet`، بدون تماس API؛ به همین دلیل idempotent و رایگان‌اند و در `run_pipeline.py`
  بدون Gate همیشه اجرا می‌شوند.
- **Cost tracking** (`src/cost_tracking/`) — لاگ هزینه/Latency هر تماس LLM، مستقل از منطق annotation.
- **Reporting** (`src/reporting/`) — ساخت خروجی Dashboard/HTML از جدول‌های `outputs/tables/`.

## ۳. `run_pipeline.py` — نقطه ورود واحد

`src/pipeline/run_pipeline.py` منطق جدیدی اضافه نمی‌کند — فقط همان اسکریپت‌های از‌قبل-تأییدشده را به همان
ترتیبی که `docs/how_to_run_pipeline_fa.md` توضیح می‌دهد، به‌صورت Subprocess صدا می‌زند (fail-fast: به محض
شکست یک قدم، اجرا متوقف می‌شود و خلاصه‌ی وضعیت هر قدم چاپ می‌شود). هر اجرای مجدد Idempotent است.

مراحل پرهزینه/خطرناک پشت Flag اختیاری‌اند و پیش‌فرض خاموش‌اند:

| Flag | چه چیزی روشن می‌کند | چرا پیش‌فرض خاموش است |
|---|---|---|
| `--with-ingestion` | Collector زنده‌ی YouTube + تبدیل فایل‌های Handoff جدید X/Reddit | Quota واقعی API مصرف می‌کند |
| `--with-profiling` | بازسازی Inventory/Coverage docs | فقط وقتی داده‌ی خام جدید آمده لازم است |
| `--with-financial` | جمع‌آوری/بازسازی داده مالی | عمداً Freeze شده؛ فقط برای رفرش دستی |
| `--with-annotation` | Full Annotation واقعی (`run_full_annotation.py`) | هزینه واقعی $، سقف $۱۰۰ مطابق `docs/decision_log.md` ۲۰۲۶-۰۸-۱۴، توسط خودِ اسکریپت annotation هم اجباری می‌شود |
| `--with-notebooks` | اجرای مجدد Notebookهای دمو (۰۵/۰۶/۰۷) + Notebook هم‌ترازی مالی با `nbconvert` | کندتر و فایل `.ipynb` را in-place بازمی‌نویسد |

Gold Sample (لیبل‌زنی دستی دو Annotator) عمداً در `run_pipeline.py` نیست — نیاز به انسان دارد، نه اسکریپت.

استفاده رایج:

```bash
python src/pipeline/run_pipeline.py --list        # فقط نشون بده قراره چی اجرا بشه، هیچی رو اجرا نکن
python src/pipeline/run_pipeline.py                # Pipeline A (بدون ingestion/annotation) + کل Pipeline B
python src/pipeline/run_pipeline.py --with-annotation --annotation-limit 10   # تست ارزان annotation
```

## ۴. قرارداد داده مشترک بین مراحل

هر لایه یک قرارداد Schema صریح دارد (نه فقط قرارداد ضمنی از روی کد):

- `config/schema.py` → `Record` مشترک هر سه Collector.
- `docs/raw_schema_v05.md` → قرارداد لایه `raw_harmonized` (هدف؛ کد فعلاً v03 را پیاده می‌کند، `docs/raw_schema_v03.md`).
- `docs/eligibility_rules_v03.md` → قواعد ورود/خروج به `opinion_main`/`opinion_limited`/`opinion_untimed`/`context_only`/`audit_only`.
- `docs/archive/pipeline_b_input_contract.md` → قرارداد دقیق `annotated_dataset.parquet` (مرز A→B).
- `src/annotation/schema.py` → قرارداد خروجی annotation (Sentiment/Stance/Emotion/Content-Type + Target + Confidence).

## ۵. مسیرهای موازی/جداگانه که هنوز به هم وصل نیستند (شکاف شناخته‌شده)

- `automation_risk_score` فقط لایه خام JSONL (v03) را پوشش می‌دهد؛ هنوز به `raw_harmonized`/`annotated_dataset.parquet`
  نرسیده (نیاز به تصمیم گسترش Schema v05 دارد).
- داده v1 قدیمی YouTube (~۷۵ هزار رکورد) هنوز فرمت قدیم دارد و migrate نشده.
- `docs/collection_coverage.csv` / Query Execution Audit فقط با `--with-profiling` به‌روز می‌شوند؛ اگر داده خام
  جدید آمد ولی این Flag اجرا نشد، این دو فایل با واقعیت داده هماهنگ نمی‌مانند.

جزئیات کامل هر مرحله (دستور دقیق، ورودی/خروجی هر اسکریپت): [`how_to_run_pipeline_fa.md`](how_to_run_pipeline_fa.md).
نقشه کامل مستندات: [`README.md`](README.md).
