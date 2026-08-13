# راهنمای اجرای بخش مالی نسخه نهایی

## ترتیب اجرا

1. در صورت نیاز به جمع‌آوری مجدد: `python -m src.ingestion.finance_market_extract`
2. `notebooks/financial/01_financial_preparation_and_quality.ipynb`
3. تکمیل تحلیل و برچسب‌گذاری شبکه‌های اجتماعی
4. ساخت `data/processed/social_media/social_weekly_outcomes_v1.csv`
5. `notebooks/financial/02_financial_social_alignment.ipynb`

Notebook اول اکنون قابل اجراست و ورودی‌های Freeze‌شده نسخه تاریخی را به خروجی‌های هفتگی نسخه نهایی تبدیل می‌کند. Notebook دوم تا نبود فایل Outcome اجتماعی با وضعیت `pending_social_outcomes` متوقف می‌شود؛ این رفتار خطا نیست و از تولید نتیجه ساختگی جلوگیری می‌کند.

Collector هر اجرای جدید را در یک پوشه مستقل زیر `data/raw/{topic_id}/financial/runs/{run_id}/` می‌نویسد و هرگز مستقیماً `data/raw_original/` را تغییر نمی‌دهد. پس از بازبینی یک Run جدید، فقط فایل‌های `prepared/` مورد تأیید جایگزین ورودی Freeze‌شده می‌شوند و Hashهای جدید باید ثبت شوند.

## فایل‌هایی که باید بررسی شوند

| مسیر فایل | کاربرد |
|---|---|
| `outputs/tables/financial/financial_asset_decisions_v1.csv` | دارایی اصلی، زمینه، حساسیت یا فقط توصیفی |
| `outputs/tables/financial/financial_coverage_summary_v1.csv` | تاریخ ابتدا/انتها و پوشش هفتگی هر دارایی |
| `outputs/tables/financial/financial_weekly_returns_v1.csv` | ورودی مالی تحلیل آماری |
| `outputs/tables/financial/financial_primary_event_windows_v1.csv` | تحلیل توصیفی سه رویداد اصلی |
| `outputs/audits/financial/financial_quality_checks_v1.csv` | کنترل‌های قابل ارائه و بازتولید |
| `outputs/audits/financial/financial_input_inventory_v1.csv` | مسیر و SHA-256 ورودی‌های تاریخی |
| `outputs/audits/financial/financial_social_alignment_status_v1.csv` | وضعیت آمادگی اتصال به داده اجتماعی |

ورودی‌های Freeze‌شده در `data/interim/financial/frozen_inputs/` فقط خوانده می‌شوند. نسخه تاریخی پاسخ‌های خام در `data/raw_original/financial/` نگهداری و از Git خارج می‌شود؛ اجرای جدید Collector در `data/raw/{topic_id}/financial/runs/` قرار می‌گیرد.
