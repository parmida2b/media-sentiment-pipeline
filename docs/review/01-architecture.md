# مرحله ۰ — نقشه‌ی پروژه

## اندازه
- حدود ۲۶ هزار خط Python در `src/` و `config/`؛ ۵ فایل تست (`tests/`) که فقط بخش کوچکی را پوشش می‌دهند
  (`config_loader`، `schema`، `automation_risk`، helperهای `apply_eligibility`، `temporal_analysis/common`).
- بزرگ‌ترین فایل‌ها (پرریسک برای بررسی): `x_scraper.py` (۳۴۳۱)، `reddit_raw_json_pipeline.py` (۲۵۲۱)،
  `reddit_parent_post_collector.py` (۲۱۱۲)، `finance_market_extract.py` (۱۳۵۰)، `youtube_extract.py` (۱۲۵۷)،
  `profile_platform.py` (۹۴۲)، `apply_eligibility.py` (۷۸۰).
- Python محیط: 3.13. وابستگی‌ها در `requirements.txt` (همه pin شده جز `yfinance`). ابزار lint/type در پروژه تعریف نشده.

## جریان داده (از روی `src/pipeline/run_pipeline.py`)

```
Pipeline A
  [--with-ingestion] youtube_extract.py / handoff_csv_to_record.py (x, reddit)
        → data/raw/{platform}/...
  harmonize        backfill_raw_harmonized_v05.py   data/raw/ → data/raw_harmonized/{platform}/*.parquet
  eligibility      apply_eligibility.py             raw_harmonized → data/interim/{opinion_main,opinion_limited,
                                                    opinion_untimed,context_only,audit_only,quarantine}.parquet
                                                    + data/audits/eligibility_audit.parquet
  normalize_text   normalize_text.py                data/interim/* (in place)
  duplicate_analysis duplicate_analysis.py          data/interim/* (in place) + data/audits/duplicate_analysis_report.md
  [--with-profiling] profile_platform.py ×3, quality_grade.py
  [--with-financial] finance_market_extract.py, build_financial_outputs.py
  [--with-annotation] run_full_annotation.py        data/interim/* → outputs/full_annotation/shard_*.jsonl (LLM، سقف $100)
  bridge           build_annotated_dataset.py       interim + annotation → data/processed/annotated_dataset.parquet

Pipeline B (فقط از annotated_dataset.parquet)
  descriptive_stats → weekly_trend → composition_shift → group_comparison
  → sensitivity_analysis → event_study → build_social_weekly_outcomes   → outputs/tables/...
  [--with-notebooks] notebooks 02 مالی، 05، 06، 07
```

## قراردادهای داده بین مراحل (نقاط بررسی مرحله‌ی ۳)
| مرز | قرارداد اعلام‌شده |
|---|---|
| Collector → raw | `config/schema.py` (`Record`) |
| raw → raw_harmonized | `docs/raw_schema_v05.md` (سند می‌گوید کد هنوز v03 است: `docs/raw_schema_v03.md`) ← ناسازگاری بالقوه |
| raw_harmonized → interim | `docs/eligibility_rules_v03.md` |
| annotation | `src/annotation/schema.py` |
| A → B | `docs/archive/pipeline_b_input_contract.md` (سند در archive است، ولی هنوز قرارداد فعال معرفی شده) |

## نکات اولیه برای مراحل بعد (هنوز باگ نیستند؛ باید تأیید شوند)
1. `docs/architecture.md` می‌گوید raw_harmonized قرارداد v05 دارد ولی «کد فعلاً v03 را پیاده می‌کند» — دو فایل
   `config/raw_schema_columns.py` و `config/raw_schema_columns_v05.py` هم‌زمان وجود دارند.
2. `build_annotated_dataset.py` در docstring به `data/interim/clean.jsonl` اشاره می‌کند، در حالی که eligibility خروجی
   parquet می‌دهد — باید بررسی شود ورودی واقعی کدام است.
3. `normalize_text` و `duplicate_analysis` فایل‌های interim را in-place بازنویسی می‌کنند؛ ادعای idempotent بودن
   pipeline باید آزموده شود.
4. داده‌ی خام در ریپو نیست؛ قدم `harmonize` بدون آن قابل اجرای کامل نیست.
5. شکاف‌های شناخته‌شده‌ی خود پروژه (`docs/architecture.md` §۵): `automation_risk_score` به لایه‌های بعدی نرسیده؛
   داده‌ی v1 قدیمی YouTube migrate نشده.
6. مسیرهای scraping (Selenium) و تماس‌های LLM/API در این محیط قابل اجرای واقعی نیستند؛ فقط بررسی ایستا.
