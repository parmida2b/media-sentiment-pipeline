# T08: CI، وابستگی‌ها و hygiene
- موج 2 | جزئی | یافته‌ها: C-02، C-05، C-06، C-07 | مدل: Sonnet / medium | وابستگی: موج 1 merged | نیاز به کاربر: خیر

## تغییر
1. `.github/workflows/ci.yml`: Python 3.13، نصب وابستگی‌ها، `ruff check` با قواعد `F,E9,PLE,B006,B008,B015,B018,B023,B904`، `pytest`. پیکربندی ruff در `pyproject.toml`.
2. `requirements.txt`: `python-dotenv>=1.2.2` (PYSEC-2026-2270)؛ `yfinance==1.8.0` (نسخه‌ای که در این محیط نصب شد). در صورت نیاز `requirements-dev.txt` برای pytest/ruff.
   اجرای `pip-audit -r requirements.txt` باید بدون آسیب‌پذیری تمام شود.
3. ruff: ۱۲ import اضافه، ۴ f-string بدون placeholder، `quality_grade.py:110 reasons`، `x_scraper.py:2724 closed_qw`، `x_scraper.py:2352` (`raise ... from`).
4. کد مرده (vulture، اطمینان ۶۰٪): قبل از حذف در notebookها هم grep کن. نمونه‌ها: `finance_market_extract.py:740 BASKET_MEMBERS`، `drop_iran_friday`،
   `x_scraper.py` (`show_progress_once`، `backfill_legacy_author_fields`، `QUERY_PLAN_PREFLIGHT`)، `apply_eligibility.py:368 _textless_role`.
5. C-02: `backfill_raw_harmonized_v05.py:264-268` وقتی هیچ رکوردی نیست، پیام روشن «no input records found» بدهد و `[PASS]` چاپ نکند.

## معیار پذیرش
CI سبز روی برنچ؛ `ruff` بدون خطا؛ `pytest` سبز؛ `pip-audit` تمیز.
