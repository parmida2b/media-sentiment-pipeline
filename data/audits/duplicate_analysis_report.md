# Duplicate Analysis Report

تاریخ: 2026-08-14 -- منبع: src/preprocessing/duplicate_analysis.py (checklist.md فاز پنجم، آیتم ۱۲)

## آمار کلی

- تعداد Exact-ID duplicate (حذف‌شده در apply_eligibility.py's stage_dedup، قبل از این مرحله): 0
- تعداد رکورد کل (kept: opinion_main+opinion_limited+opinion_untimed+context_only): 233,006
- متن یکسان با ID متفاوت (case 2): 5,087 رکورد (2.18%)
- Unique text rate: 97.82%
- Near-duplicate (case 3): 4,712 رکورد در 1,631 Cluster (بزرگ‌ترین Cluster: 41 رکورد)
- رکوردهای زیر آستانه‌ی طول متن (MIN_TEXT_LEN_FOR_DUP_CHECK=10، بررسی Duplicate روی آن‌ها انجام نشد چون تطابق تصادفی متن کوتاه معنادار نیست): 5,721

## تفکیک هفته/پلتفرم (Near-duplicate)

| platform | project_week | n | near_dup_clusters | near_dup_rows |
|---|---|---:|---:|---:|
| reddit | W01 | 6548 | 18 | 74 |
| reddit | W02 | 9781 | 28 | 115 |
| reddit | W03 | 8509 | 30 | 140 |
| reddit | W04 | 11315 | 39 | 127 |
| reddit | W05 | 10631 | 28 | 119 |
| reddit | W06 | 13086 | 33 | 145 |
| reddit | W07 | 9835 | 31 | 113 |
| reddit | W08 | 7398 | 31 | 128 |
| reddit | W09 | 6276 | 27 | 82 |
| reddit | W10 | 7609 | 28 | 80 |
| reddit | W11 | 4878 | 12 | 47 |
| reddit | W12 | 5028 | 15 | 66 |
| reddit | W13 | 4639 | 13 | 60 |
| reddit | W14 | 4272 | 15 | 48 |
| reddit | W15 | 5901 | 21 | 71 |
| reddit | W16 | 8588 | 42 | 143 |
| reddit | W17 | 6246 | 25 | 79 |
| reddit | W18 | 4082 | 13 | 44 |
| reddit | W19 | 4008 | 11 | 31 |
| reddit | W20 | 7004 | 25 | 111 |
| reddit | W21 | 5013 | 19 | 80 |
| x | W01 | 471 | 8 | 21 |
| x | W02 | 726 | 9 | 20 |
| x | W03 | 1002 | 17 | 41 |
| x | W04 | 963 | 16 | 36 |
| x | W05 | 455 | 9 | 28 |
| x | W06 | 316 | 2 | 4 |
| x | W07 | 202 | 4 | 10 |
| x | W08 | 370 | 7 | 32 |
| x | W09 | 1470 | 25 | 60 |
| x | W10 | 746 | 19 | 39 |
| x | W11 | 864 | 25 | 54 |
| x | W12 | 713 | 20 | 42 |
| x | W13 | 259 | 2 | 5 |
| x | W14 | 320 | 6 | 13 |
| x | W15 | 1050 | 22 | 44 |
| x | W16 | 1399 | 26 | 56 |
| x | W17 | 902 | 22 | 53 |
| x | W18 | 671 | 6 | 13 |
| x | W19 | 456 | 10 | 22 |
| x | W20 | 1269 | 23 | 53 |
| x | W21 | 1162 | 16 | 33 |
| youtube | W01 | 1342 | 5 | 17 |
| youtube | W02 | 297 | 2 | 4 |
| youtube | W03 | 99 | 1 | 2 |
| youtube | W04 | 99 | 0 | 0 |
| youtube | W05 | 290 | 4 | 10 |
| youtube | W06 | 201 | 2 | 4 |
| youtube | W07 | 43 | 0 | 0 |
| youtube | W08 | 269 | 1 | 2 |
| youtube | W09 | 192 | 2 | 5 |
| youtube | W10 | 150 | 0 | 0 |
| youtube | W11 | 393 | 7 | 26 |
| youtube | W12 | 198 | 1 | 3 |
| youtube | W13 | 324 | 3 | 6 |
| youtube | W14 | 832 | 19 | 54 |
| youtube | W15 | 564 | 8 | 20 |
| youtube | W16 | 167 | 0 | 0 |
| youtube | W17 | 875 | 16 | 39 |
| youtube | W18 | 724 | 14 | 30 |
| youtube | W19 | 2374 | 20 | 58 |
| youtube | W20 | 12952 | 141 | 332 |
| youtube | W21 | 44182 | 587 | 1518 |

## روش

- Case 2 (متن یکسان، ID متفاوت): هش SHA-1 روی `text_normalized.strip().lower()`.
- Case 3 (Near-duplicate): MinHash (num_perm=64) روی Shingleهای 3-کلمه‌ای `text_normalized.lower()`، LSH با threshold=0.8 (تخمین Jaccard similarity)، به‌ازای هر سلول (platform, project_week) جداگانه (برای مقیاس‌پذیری روی ~۲۳۳K رکورد؛ opinion_untimed چون project_week ندارد از این تحلیل کنار گذاشته شده، فقط ۶ رکورد).