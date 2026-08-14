# X config runtime fallback — v9

Pipeline اصلی گروه دست‌نخورده باقی مانده است.

در `repo/config/config.yaml` فعلی، block مربوط به X به‌صورت `youtube.x` قرار گرفته، در حالی که `config_loader.PipelineConfig` انتظار `x` در سطح اصلی YAML را دارد. به همین دلیل `x_scraper.py` هنگام import مقدار `PIPELINE_CONFIG.x` را خالی دریافت می‌کرد و با خطای زیر متوقف می‌شد:

```text
ValueError: X configuration is missing from config.yaml.
```

Overlay v9 قبل از import کردن `src.ingestion.x_scraper` فقط در حافظه این fallback را اعمال می‌کند:

```text
اگر PipelineConfig.x موجود بود
    -> همان native config استفاده می‌شود
اگر PipelineConfig.x خالی بود و PipelineConfig.youtube["x"] وجود داشت
    -> همان dict فقط در RAM به PipelineConfig.x داده می‌شود
```

هیچ فایلی در `repo/` نوشته یا patch نمی‌شود.
