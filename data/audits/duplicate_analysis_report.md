# Duplicate Analysis Report

تاریخ: 2026-08-14 -- منبع: src/preprocessing/duplicate_analysis.py (checklist.md فاز پنجم، آیتم ۱۲)

## آمار کلی

- تعداد Exact-ID duplicate (حذف‌شده در apply_eligibility.py's stage_dedup، قبل از این مرحله): 0
- تعداد رکورد کل (kept: opinion_main+opinion_limited+opinion_untimed+context_only): 287,868
- متن یکسان با ID متفاوت (case 2): 20,580 رکورد (7.15%)
- Unique text rate: 92.85%
- Near-duplicate (case 3): 19,967 رکورد در 8,939 Cluster (بزرگ‌ترین Cluster: 41 رکورد)
- رکوردهای زیر آستانه‌ی طول متن (MIN_TEXT_LEN_FOR_DUP_CHECK=10، بررسی Duplicate روی آن‌ها انجام نشد چون تطابق تصادفی متن کوتاه معنادار نیست): 7,930

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
| youtube | W01 | 6575 | 260 | 534 |
| youtube | W02 | 3774 | 78 | 170 |
| youtube | W03 | 2531 | 23 | 46 |
| youtube | W04 | 3287 | 18 | 42 |
| youtube | W05 | 3251 | 29 | 60 |
| youtube | W06 | 2492 | 14 | 41 |
| youtube | W07 | 1346 | 9 | 23 |
| youtube | W08 | 1103 | 35 | 70 |
| youtube | W09 | 634 | 8 | 42 |
| youtube | W10 | 373 | 1 | 2 |
| youtube | W11 | 603 | 7 | 26 |
| youtube | W12 | 659 | 20 | 45 |
| youtube | W13 | 1072 | 16 | 34 |
| youtube | W14 | 1455 | 55 | 136 |
| youtube | W15 | 2075 | 189 | 389 |
| youtube | W16 | 1129 | 49 | 98 |
| youtube | W17 | 2567 | 33 | 73 |
| youtube | W18 | 1596 | 24 | 50 |
| youtube | W19 | 4929 | 763 | 1590 |
| youtube | W20 | 18848 | 1680 | 3503 |
| youtube | W21 | 61130 | 4830 | 10411 |

## روش

- Case 2 (متن یکسان، ID متفاوت): هش SHA-1 روی `text_normalized.strip().lower()`.
- Case 3 (Near-duplicate): MinHash (num_perm=64) روی Shingleهای 3-کلمه‌ای `text_normalized.lower()`، LSH با threshold=0.8 (تخمین Jaccard similarity)، به‌ازای هر سلول (platform, project_week) جداگانه (برای مقیاس‌پذیری روی ~۲۳۳K رکورد؛ opinion_untimed چون project_week ندارد از این تحلیل کنار گذاشته شده، فقط ۶ رکورد).