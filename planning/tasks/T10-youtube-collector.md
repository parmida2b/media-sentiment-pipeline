# T10: اصلاح collector یوتیوب
- موج 3 | مهم | یافته‌ها: C-22، C-23، C-24 | مدل: Opus / high | وابستگی: T06 | نیاز به کاربر: خیر (کد با mock، بدون تماس واقعی)
- فایل‌ها: `src/ingestion/youtube_extract.py`، `src/ingestion/incremental_state.py`، `tests/test_youtube_collector.py` (جدید)

## مسئله
1. C-22: پاسخ‌ها فقط از `item["replies"]["comments"]` در `commentThreads.list` (خطوط 367 تا 445)؛ `comments().list(parentId=...)` هیچ‌جا نیست.
   روی داده: حداکثر ۵ پاسخ برای هر رشته؛ ۱,۱۰۳ کامنت با `reply_count > 5`؛ دست‌کم ۱۰,۳۷۱ پاسخ (۳۵.۶٪ پاسخ‌های اعلام‌شده) دست‌نیافتنی.
2. C-23: pool = ۱۵۰۰ کامنت جدیدتر (`COMMENT_POOL_CAP`، خط 139)؛ watermark = جدیدترینِ pool (خطوط 1195 و 1196). اگر بین دو اجرا بیش از ۱۵۰۰ کامنت تازه بیاید،
   بقیه هرگز واکشی نمی‌شوند و هیچ شمارنده‌ای ثبتشان نمی‌کند.
3. C-24: `author_id_status` در خروجی collector زنده null است. `rate_limit_events` شمرده می‌شود ولی ثبت نمی‌شود.

## تغییر
1. برای رشته‌هایی که `totalReplyCount` بیشتر از پاسخ‌های برگشته است: `comments().list(parentId=..., maxResults=100)` با صفحه‌بندی، `since_dt` و حساب quota (`checkpoint.QUOTA_COSTS`).
2. وقتی pool به سقف رسید، watermark جلو نرود؛ یک cursor برای بازه‌ی جانمانده ذخیره شود و اجرای بعد اول آن را کامل کند. تعداد جانمانده‌ها در run log.
3. `author_id_status`: `available` اگر `author_hash` هست، وگرنه `not_provided`. `rate_limit_events` در run log.

## تست
client جعلی (mock) برای `commentThreads().list` و `comments().list`: رشته‌ی ۱۲ پاسخی ← ۱۲ پاسخ؛ ویدیو با ۲۰۰۰ کامنت تازه و سقف ۱۵۰۰ ← اجرای دوم بقیه را می‌گیرد؛ quota درست کم می‌شود.

## خارج از محدوده
اجرای واقعی (T11).
