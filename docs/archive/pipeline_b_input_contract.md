# قرارداد ورودی Pipeline B (تحلیل و گزارش)

**نسخه:** 1.0 — ۲۰۲۶-۰۸-۱۳
**وضعیت:** قفل‌شده — تغییرش نیاز به هماهنگی هر دو تیم (A و B) و ثبت در `decision_log.md` داره.

## چرا این سند

پروژه به دو Pipeline مستقل تقسیم شد (`docs/decision_log.md` ۲۰۲۶-۰۸-۱۳):

- **Pipeline A (داده + Annotation):** جمع‌آوری → Harmonization → Eligibility → Gold Sample →
  ارزیابی مدل → Full Annotation
- **Pipeline B (تحلیل + گزارش):** آمار توصیفی → روند زمانی → Composition Shift →
  مقایسه‌ی گروه‌ها → رویداد → مالی → حساسیت → گزارش‌ها

این دو تا فقط از طریق **یک فایل** با هم حرف می‌زنن:

```
data/processed/annotated_dataset.parquet
```

Pipeline B **هیچ‌وقت** نباید مستقیم به `data/raw/`، `data/interim/`، یا هر خروجی annotation
دیگه‌ای رجوع کنه — فقط همین یک فایل. این یعنی B رو می‌شه صد بار دوباره اجرا کرد (مثلاً یه
Sensitivity Analysis جدید) بدون این‌که annotation یک‌بار دیگه تکرار بشه.

## چه‌کسی این فایل رو می‌سازه

Pipeline A، بعد از `run_full_annotation.py` — با join کردن خروجی
`apply_eligibility.py`'s `opinion_main`/`opinion_limited`/`opinion_untimed` با خروجی
annotation (بر اساس `content_id`). تا وقتی این آماده نشده، Pipeline B باید روی یه نسخه‌ی
**مصنوعی** با همین دقیقاً schema کار کنه (پایین توضیح داده شده).

## Schema (هر ستون اجباریه، حتی اگه مقدارش null باشه)

### هویت و Provenance
| ستون | نوع | توضیح |
|---|---|---|
| `content_id` | str | یکتا. از `platform_content_id` |
| `platform` | str | `x` \| `reddit` \| `youtube` |
| `parent_id` | str, nullable | |
| `post_id` | str, nullable | شناسه‌ی thread/video/submission (`source_parent_id`) |
| `dataset_target` | str | `opinion_main` \| `opinion_limited` \| `opinion_untimed` — خروجی `apply_eligibility.py`. **`opinion_untimed` باید از هر تحلیل روند زمانی حذف بشه ولی در آمار توصیفی کلی بمونه** (`docs/checklist.md` فاز نهم/دهم) |
| `provenance_quality` | str | `full` \| `partial` \| `unknown` |

### زمان
| ستون | نوع | توضیح |
|---|---|---|
| `created_at_utc` | str (ISO 8601) | |
| `project_week` | str | `"W01"`..`"W21"` یا `"OUT"` |
| `in_window` | bool | |
| `is_partial_week` | bool | فقط W21 طبق سند فعلی |

### متن (فقط برای Spot-check/نقل‌قول در گزارش — هیچ تحلیل آماری نباید بهش نیاز داشته باشه)
| ستون | نوع |
|---|---|
| `text_raw` | str |

### منبع
| ستون | نوع |
|---|---|
| `source_id` | str, nullable |
| `source_container` | str, nullable |
| `query_id` | str, nullable |
| `query_version` | str, nullable |

### زبان و جغرافیا
| ستون | نوع |
|---|---|
| `language_detected` | str (`fa`\|`en`\|`ar`\|`other`) |
| `language_confidence` | float, nullable |
| `country_or_region` | str, nullable |
| `geo_confidence` | str, nullable (`high`\|`medium`\|`low`) |

### Engagement
| ستون | نوع |
|---|---|
| `engagement_score` | int |
| `engagement_replies` | int |
| `engagement_shares` | int |
| `engagement_views` | int |

### نویسنده و ریسک
| ستون | نوع | توضیح |
|---|---|---|
| `author_hash` | str, nullable | برای Author-balanced trend (فاز پانزدهم) |
| `automation_risk_score_user` | float, nullable | از `join_and_clean.py`'s Tier B |
| `is_flagged_bot_suspect` | bool | |

### Dedup/Repost (برای Sensitivity Analysis — «با/بدون Duplicate»)
| ستون | نوع |
|---|---|
| `is_exact_duplicate` | bool |
| `is_near_duplicate` | bool |
| `near_duplicate_cluster_id` | str, nullable |

### Annotation (خروجی اصلی Pipeline A — بخش §22 سند مشاور)
| ستون | نوع | توضیح |
|---|---|---|
| `target` | str, nullable | `T01`-`T06`. Null فقط اگه `stance_label=unrelated` |
| `sentiment_label` | str | `positive`\|`negative`\|`neutral`\|`mixed`\|`unclear` |
| `stance_label` | str | `support`\|`oppose`\|`neutral_or_balanced`\|`unrelated`\|`unclear` |
| `emotion_label` | str | |
| `content_type_label` | str | |
| `confidence` | float [0,1] | Confidence خودِ مدل — طبق §24 سند، معیار کافی صحت نیست، فقط برای Coverage threshold استفاده بشه |
| `reason_code` | str | |
| `annotation_status` | str | `ok`\|`low_confidence`\|`json_parse_failure`\|`api_failure` — رکوردهای غیر`ok` باید طبق §24 از تحلیل اصلی کنار گذاشته و در Coverage گزارش بشن |
| `model_version` | str | |
| `prompt_version` | str | |
| `annotated_at_utc` | str | |

## داده‌ی مصنوعی برای شروع زودهنگام Pipeline B

تا وقتی annotation واقعی آماده بشه، از یه فایل ساختگی با همین schema استفاده کنید:
`data/processed/annotated_dataset.sample.parquet` — پرامپت جداگانه‌ی ساخت این فایل در
ادامه‌ی همین گفتگو داده شده. **این فایل هیچ‌وقت نباید به‌عنوان داده‌ی واقعی در گزارش یا
ادعای آماری استفاده بشه** — فقط برای توسعه و تست کد Pipeline B است.
