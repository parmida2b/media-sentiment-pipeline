# مرحله ۲ — ابزارهای خودکار

> محیط: همان venv مرحله‌ی ۱ (Python 3.13). ابزارها: ruff 0.17.4، mypy، vulture، pip-audit، detect-secrets.
> **gitleaks نصب نبود** (برنامه‌ی Go است، با pip نصب نمی‌شود) ← به‌جایش detect-secrets + جستجوی regex روی کل فایل‌های ردیابی‌شده.
> در پروژه هیچ پیکربندی lint/type (ruff، mypy) و هیچ CI (`.github/`) وجود ندارد.

## خلاصه
| ابزار | خروجی خام | بعد از بررسی دستی |
|---|---|---|
| ruff (قواعد باگ‌محور F, E9, PLE, B) | 20 مورد | 0 باگ زمان اجرا؛ 20 مورد hygiene |
| mypy | 144 خطا | 13 مورد پرسیگنال بررسی شد ← 0 باگ واقعی؛ بقیه (عمدتاً نویز تایپ pandas) **بررسی نشده** |
| vulture | 0 مورد در 80٪؛ 31 مورد در 60٪ | کد مرده/استفاده‌نشده (جزئی) |
| pip-audit | 1 بسته‌ی آسیب‌پذیر | تأثیر عملی ندارد (جزئی) |
| detect-secrets + regex | 1 هشدار | false positive؛ **هیچ کلید/رمز واقعی‌ای نیست** |

## کاندیدای باگ‌های جدید

### C-04 — نام متغیر Salt در کد با مستندات/`.env.example` نمی‌خواند (مهم، مرتبط با حریم خصوصی)
- **شواهد:** `grep` روی `src/ config/ scripts/` ← تنها `src/ingestion/author_hash.py:38` متغیر `AUTHOR_HASH_SALT` را می‌خواند.
  **هیچ کدی `PROJECT_AUTHOR_SALT` را نمی‌خواند**، در حالی که `.env.example` هر دو را دارد و مشخصات v05 §5 فرمول را
  بر پایه‌ی `PROJECT_AUTHOR_SALT` توصیف می‌کند (خود docstring همان فایل هم همین را می‌نویسد).
- اگر Salt تنظیم نشود، `_FALLBACK_SALT` ثابتِ **عمومی** (`author_hash.py:31`) استفاده می‌شود و فقط **یک بار** پیام چاپ می‌شود.
  کسی که طبق مستندات v05 فقط `PROJECT_AUTHOR_SALT` را بگذارد، بی‌صدا با Salt عمومی hash می‌کند.
- **ریسک:** شناسه‌ی کانال YouTube عمومی است ← با Salt عمومی، `author_hash` قابل بازسازی/بازشناسایی است و ناشناس‌سازی
  عملاً بی‌اثر می‌شود. فایل‌های `data/raw_harmonized/*.parquet` (که `author_hash` دارند) در گیت ردیابی می‌شوند.
- **هنوز معلوم نیست** داده‌ی موجود با Salt واقعی ساخته شده یا fallback؛ شناسه‌ی خام ذخیره نشده تا بشود آزمود.
  ← در مرحله‌ی ۴ (حریم خصوصی) دنبال می‌شود؛ احتمالاً نیاز به سؤال از تیم.

### C-05 — `python-dotenv==1.0.1` آسیب‌پذیر (PYSEC-2026-2270، رفع در 1.2.2) (جزئی)
- مشکل فقط در `set_key()`/`unset_key()` (دنبال کردن symlink موقع بازنویسی `.env`) است. پروژه فقط `load_dotenv` را صدا می‌زند
  (`grep` روی `src/`) ← تأثیر عملی ندارد. ارتقا در مرحله‌ی ۶ با آزمون سازگاری.

### C-06 — `yfinance` در `requirements.txt` pin نشده (جزئی، تکرارپذیری)
- تنها بسته‌ی بدون نسخه (خط 11). `pip-audit -r requirements.txt` به همین دلیل خطا داد. در این محیط 1.8.0 نصب شد.
  خروجی داده‌ی مالی ممکن است با نسخه‌ی دیگر تغییر کند (داده‌ی مالی البته freeze شده است).

### C-07 — hygiene کد (جزئی)
- ruff: 12×F401 (import اضافه، از جمله `x_scraper.py:13,23`, `reddit_to_record.py:65`, `event_study.py:51`)، 4×F541 (f-string بی‌جایگزین)،
  2×F841 (`quality_grade.py:110 reasons`، `x_scraper.py:2724 closed_qw`)، 1×B904 (`x_scraper.py:2352` raise بدون `from`)، 1×F821.
- `F821 Groq` (`geo_tagger.py:70`) **false positive**: annotation رشته‌ای است و در اجرا خطا نمی‌دهد.
- vulture@60٪ (نمونه): `finance_market_extract.py:740 BASKET_MEMBERS` (global که نوشته می‌شود ولی هیچ‌جا خوانده نمی‌شود)،
  `drop_iran_friday` (جایگزین‌شده)، `x_scraper.py:2799 show_progress_once`, `3269 backfill_legacy_author_fields`، `3258 QUERY_PLAN_PREFLIGHT`،
  `youtube_extract.py rate_limit_events` (×4)، `apply_eligibility.py:368 _textless_role`. اعتماد ۶۰٪ یعنی ممکن است از notebook یا reflection استفاده شوند.
- `llm_client.py:197` `Groq(api_key=key)` بیرون از `try` است؛ خطای ساخت client به‌جای ثبت در `call_error` مستقیم بالا می‌رود (کم‌اهمیت).

## موارد بررسی‌شده و رد‌شده (false positive)
- mypy `llm_client.py:228 return None`: وقتی کلیدی هست حلقه همیشه `last_error` را پر می‌کند ← ایمن.
- mypy `build_dashboard.py:148-149 int(Series)`: `row` بعد از `iloc[0]` اسکالر است ← ایمن.
- mypy `finance_market_extract.py:740 BASKET_MEMBERS not defined`: تعریف با `global` داخل تابع (دیده نمی‌شود) ← فقط کد مرده.
- detect-secrets `profile_platform.py:676`: فقط نام کلید `"contains_secrets"`.
- regex کلیدها (Google `AIza`, Groq `gsk_`, OpenRouter `sk-or-`, `sk-`, AWS, GitHub, Slack, PEM) روی **همه‌ی** فایل‌های متنیِ ردیابی‌شده (شامل notebook/json/csv): 0 مورد.
  فقط `.env.example` ردیابی می‌شود. تنها literal مشکوک: `_FALLBACK_SALT` (C-04).

## محدودیت‌ها (صادقانه)
- mypy: فقط 13 از 144 مورد بررسی شد؛ 38×union-attr، 25×arg-type، 24×operator و غیره بدون بررسی ماندند (احتمال نویز بالا، ولی تضمین نیست).
- فایل‌های باینری (parquet/xlsx) در جستجوی رمز اسکن نشدند.
- ruff فقط قواعد باگ‌محور را اجرا کرد، نه سبک؛ تعداد کامل مشکلات سبکی گزارش نشد.
- هیچ‌کدام از کدها اجرا نشدند (مرحله‌ی ۲ ایستاست).
