# T05: استحکام annotation: آخرین تلاش، سقف هزینه‌ی تجمعی، cache، خطاها
- موج 1 | مهم | یافته‌ها: C-10، C-19، C-20، C-21 | مدل: Opus / medium | وابستگی: T01 | نیاز به کاربر: خیر
- فایل‌ها: `src/annotation/build_annotated_dataset.py` (فقط `load_annotations`)، `src/annotation/run_full_annotation.py`، `src/annotation/llm_client.py`،
  `tests/test_annotation_runner.py` (جدید)

## مسئله
1. C-10: `load_annotations` (خط 150 و 151) با `sort_values` ناپایدار و `keep="last"`؛ در شبیه‌سازی ۲۰٪ مواقع تلاش قدیمی‌تر برنده شد. «آخرین» = ترتیب فایل، نه زمان.
2. C-19: `state["cost_usd"]` در هر session از صفر (خطوط 367 و 404 تا 414). resume و shardهای موازی هرکدام سقف ۱۰۰ دلاری جدا دارند.
   `load_done_keys` فقط فایل shard خودش را می‌خواند؛ تغییر `--num-shards` همه را دوباره annotate می‌کند.
3. C-20: نتیجه‌ی cache همان `cost_usd` تماس اصلی را برمی‌گرداند (`llm_client.py:353-354`) و جمع زده می‌شود.
4. C-21: `for _ in as_completed(futures): pass` (خطوط 432 تا 438) هرگز `future.result()` نمی‌خواند؛ exceptionها بی‌صدا گم می‌شوند.
   `Groq(api_key=key)` بیرون از `try` است (`llm_client.py:187`). `cache.save()` هم‌زمان با `cache.set()` از thread دیگر ممکن است «dictionary changed size» بدهد.

## تغییر
1. `sort_values(["_ok_rank", "annotated_at_utc"], kind="stable")`.
2. قبل از شروع، هزینه‌ی واقعی قبلی از همه‌ی `outputs/full_annotation/shard_*.jsonl` جمع شود (فقط ردیف‌های غیر cache) و سقف تجمعی باشد. `done_keys` از همه‌ی فایل‌های shard.
3. نتیجه‌ی cache با `cost_usd = 0.0` (هزینه‌ی اصلی در فیلد جدا اگر لازم است).
4. `future.result()` در try؛ شمارش و چاپ خطاها در خلاصه. ساخت client داخل try. قفل مشترک برای set و save، یا save روی کپی snapshot.
5. پیام‌ها و docstringها که «hard cap» می‌گویند با رفتار جدید هماهنگ شوند (`run_pipeline.py`، `docs/architecture.md`).

## تست
دو تلاش ok با زمان متفاوت ← جدیدتر؛ fixture دو فایل shard با هزینه ← سقف تجمعی؛ برخورد cache ← هزینه 0؛ worker که exception می‌دهد ← در خلاصه شمرده شود. بدون تماس شبکه (mock).
