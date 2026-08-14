# Setup

راه‌اندازی محیط و اجرای پایپ‌لاین — تکمیل شود. راهنمای کار با گیت جدا توی [`GIT_WORKFLOW.md`](../GIT_WORKFLOW.md) هست.

## اجرای دستی استخراج YouTube

```bash
python src/ingestion/youtube_extract.py
```

این اسکریپت idempotent و incremental هست — هر بار اجرا فقط ویدیوی/کامنت **جدید**
(بر اساس watermark تاریخ ذخیره‌شده در `checkpoint.json`) رو می‌گیره، نه از اول. پس
اجرای دستی مکرر یا اجرای خودکار هفتگی (پایین) هر دو امن‌ان. خروجی‌ها (زیر
`data/raw/{topic_id}/`):
- `youtube_comments_v2.jsonl` — کامنت‌ها (فرمت `config/schema.py`)
- `youtube_raw_export.csv` — همون داده، فرمت export مطابق `docs/raw_schema_v03.md`
- `youtube_runs.csv` — manifest هر اجرا (به‌ازای هر query×هفته یک ردیف)
- `youtube_skipped_videos.csv` — لاگ ویدیوهایی که رد شدن (فیلتر ربط/quota)

قبل از اجرا مطمئن شو `.env` مقدار `YOUTUBE_API_KEY` و `AUTHOR_HASH_SALT` رو داره
(نمونه در `.env.example`).

**⚠️ هیچ‌وقت محتوای `.env` رو در اسکرین‌شات، چت، یا PR paste نکن** — اگه شک کردی
کلیدی جایی لو رفته، همون لحظه از کنسول همون Provider (Google/Groq/...) rotate‌ش کن.

## اجرای خودکار هفتگی (Windows Task Scheduler)

فایل `scripts/run_youtube_incremental_weekly.ps1` استخراج بالا رو با لاگ‌گیری در
`outputs/logs/` اجرا می‌کنه. برای ثبتش به‌عنوان یک Task هفتگی:

**از طریق GUI:**
1. `Task Scheduler` رو باز کن → `Create Task...`
2. تب General: یه اسم بذار (مثلاً `YouTube Incremental Collection`)، و
   «Run whether user is logged on or not» رو انتخاب کن.
3. تب Triggers → New → Weekly، روزی که می‌خوای (مثلاً هر شنبه)، ساعت دلخواه.
4. تب Actions → New → Program/script: `powershell.exe`؛ Arguments:
   ```
   -ExecutionPolicy Bypass -File "C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\scripts\run_youtube_incremental_weekly.ps1"
   ```
5. ذخیره کن؛ برای تست فوری، روی Task راست‌کلیک کن و `Run` رو بزن، بعد
   `outputs/logs/youtube_incremental_*.log` رو چک کن.

**از طریق PowerShell (به‌جای GUI، باید با دسترسی ادمین اجرا بشه):**
```powershell
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-ExecutionPolicy Bypass -File "C:\Users\user\OneDrive\Desktop\hamrahaval\final\media-sentiment-pipeline-starter\media-sentiment-pipeline-starter\scripts\run_youtube_incremental_weekly.ps1"'
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At 9am
Register-ScheduledTask -TaskName "YouTube Incremental Collection" -Action $Action -Trigger $Trigger -Description "Weekly incremental YouTube comment collection (media-sentiment-pipeline)"
```

اگه از virtualenv/conda استفاده می‌کنی، قبل از اجرا `$env:PYTHON_EXE` رو به مسیر
پایتون همون محیط ست کن (اسکریپت PowerShell این رو می‌خونه، وگرنه از `python` روی
PATH استفاده می‌کنه).
