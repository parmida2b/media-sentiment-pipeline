# Full Control Panel Overlay

این پوشه فقط لایه‌ی بیرونی کنترل و مانیتورینگ است. `../repo/` پایپ‌لاین اصلی گروه است و فایل‌های آن تغییر نمی‌کنند.

## مدل اتصال

- تنظیمات پنل در `monitoring/state/control_plane.db` ذخیره می‌شوند.
- credentialهایی که pipeline به‌صورت native از environment می‌خواند، فقط هنگام اجرای subprocess تزریق می‌شوند.
- تنظیماتی که در source اصلی environment variable ندارند، توسط `runtime_wrapper.py` بعد از import ماژول و قبل از `main()` فقط در حافظه همان process override می‌شوند.
- هیچ `config.yaml`، `query_registry.yaml` یا فایل Python داخل `repo/` توسط پنل نوشته نمی‌شود.

## صفحات

- `/` داشبورد و وضعیت collectorها
- `/data` خلاصه‌ی read-only خروجی‌های native
- `/scrapers/reddit` تنظیمات کامل Reddit + source/query registry runtime
- `/scrapers/youtube` API/quota/query/region/comment controls
- `/scrapers/x` accounts/worker/scroll/retry controls
- `/scrapers/finance` FRED + Asset Registry اصلی
- `/live` لاگ زنده
- `/integrity` کنترل SHA-256 پایپ‌لاین

## نکته درباره Query/Source override

برای Reddit، Source Registry و Query Registry اصلی از `reddit_parent_post_collector.py` خوانده می‌شوند. اگر در پنل ویرایش شوند، نسخه override فقط در Control DB ذخیره و هنگام اجرای همان process در RAM جایگزین می‌شود. دکمه Reset overrides همه چیز را به registry اصلی pipeline برمی‌گرداند.

برای X، query registry به دلیل preflight ثابت خود `x_scraper.py` فقط read-only نمایش داده می‌شود تا منطق pipeline شکسته نشود.
