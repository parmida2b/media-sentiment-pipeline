"""
composition_shift.py — docs/checklist.md فاز یازدهم (§23): بررسی تغییر ترکیب نمونه

هدف: تشخیص این‌که آیا تغییر روند خام سنتیمنت هفتگی ناشی از تغییر نگرش واقعی
است یا تغییر ترکیب داده (پلتفرم، منبع، زبان، کاربران پرتکرار، محتوای تکراری
یا پرریسک). پاسخ به این سوال پیش‌شرط هر نتیجه‌گیری علّی از روند زمانی است.

─────────────────────────────────────────────
روش انتخاب‌شده برای Adjusted Trend: Author-balanced trend
─────────────────────────────────────────────
از چهار روش پیشنهادی checklist (Stratified / Author-balanced /
Parent-balanced sensitivity / Shared-period comparison)، «Author-balanced trend»
انتخاب شد به دلایل زیر:

۱. مشکل اصلی کشف‌شده: سهم کاربران پرتکرار می‌تواند بازه‌های زمانی خاصی را
   تحت‌سلطه قرار دهد — یک کاربر با ۵۰ توییت در یک هفته همان وزن سنتیمنتی
   را دارد که ۵۰ کاربر منحصر‌به‌فرد دارند. این bias مستقیماً از ستون‌های
   composition (n_unique_author_hash در مقابل n_total) قابل اندازه‌گیری است.

۲. قابلیت مقایسه‌ی مستقیم: Author-balanced فقط وزن‌دهی مجدد می‌کند
   (هر author_hash یک رأی)، و نتیجه همچنان یک نرخ سنتیمنت در همان مقیاس
   [0,1] است که مستقیماً با روند خام قابل مقایسه است.

۳. سازگاری با داده: author_hash در pipeline_b_input_contract.md صراحتاً
   برای همین هدف (Author-balanced trend) ذکر شده، و در fixture مصنوعی موجود
   است. برخلاف Parent-balanced که نیاز به parent_id کامل دارد (در داده‌ی
   synthetic اغلب null)، author_hash coverage بهتری دارد.

۴. سادگی تفسیر: «یک نظر به‌ازای هر کاربر در هر هفته» برای خواننده‌ی
   غیرتخصصی گزارش نهایی شهودی‌تر از Stratification یا Shared-period است.

۵. رد Stratified: نیاز به تعریف صریح stratum (پلتفرم × هفته) دارد که دقیقاً
   همان کاری است که weekly_trend.py قبلاً کرده؛ مقایسه‌ی دو خروجی آن ماژول
   افزوده‌ی تحلیلی جدیدی ندارد. Author-balanced بُعد جدیدی می‌افزاید.

۶. رد Shared-period: مناسب‌ترین است وقتی دو cohort مستقل وجود دارد و
   می‌خواهیم در دوره‌ی مشترک مقایسه کنیم — اما این پروژه یک stream پیوسته
   است، نه دو cohort.

─────────────────────────────────────────────
خروجی‌ها (outputs/tables/)
─────────────────────────────────────────────
composition_shift_platform_share.csv
    — سهم هر پلتفرم از کل رکوردها، به تفکیک هفته
composition_shift_source_share.csv
    — سهم top-N source_id (source_container) به تفکیک پلتفرم × هفته
composition_shift_language_share.csv
    — سهم language_detected به تفکیک پلتفرم × هفته
composition_shift_content_type_share.csv
    — سهم news_or_report در برابر personal_opinion (content_type_label)
    فقط روی annotation_status=="ok" — همان قانون §24
composition_shift_query_share.csv
    — سهم هر query_id × query_version به تفکیک پلتفرم × هفته
composition_shift_duplicate_share.csv
    — سهم is_exact_duplicate، is_near_duplicate به تفکیک پلتفرم × هفته
composition_shift_author_concentration.csv
    — n_total، n_unique_authors، top_author_share (بزرگ‌ترین کاربر چند درصد
    از هفته را در اختیار دارد) به تفکیک پلتفرم × هفته
composition_shift_risk_share.csv
    — سهم is_flagged_bot_suspect + automation_risk bucket به تفکیک پلتفرم × هفته
composition_shift_parent_concentration.csv
    — سهم بزرگ‌ترین parent_id / source_container به تفکیک پلتفرم × هفته
composition_shift_sentiment_adjusted.csv
    — روند خام positive_rate در کنار author-balanced positive_rate
    (هر author_hash یک رأی به‌ازای هر هفته × پلتفرم) با is_low_sample /
    is_partial_week / is_data_gap

Usage:
    python -m src.temporal_analysis.composition_shift
    python -m src.temporal_analysis.composition_shift --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")  # Persian notes/arrows in print() below

from src.temporal_analysis.common import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    LOW_SAMPLE_THRESHOLD,
    PARTIAL_WEEK,
    PLATFORMS,
    WEEKS,
    load_annotated_dataset,
    wilson_confidence_interval,
)

# top-N source_id entries per (platform, week) برای خوانایی جدول
TOP_N_SOURCES = 5

# automation risk buckets — همان سطح‌بندی descriptive_stats.py
_RISK_HIGH = 0.6
_RISK_MED = 0.3


def _risk_bucket(score: float | None) -> str:
    if pd.isna(score):
        return "unknown"
    if score < _RISK_MED:
        return "low"
    if score < _RISK_HIGH:
        return "medium"
    return "high"


def _week_flags(week: str, n: int) -> dict:
    return {
        "is_data_gap": n == 0,
        "is_low_sample": 0 < n < LOW_SAMPLE_THRESHOLD,
        "is_partial_week": week == PARTIAL_WEEK,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. سهم پلتفرم — pooled across weeks برای مشاهده‌ی shift کلی
# ─────────────────────────────────────────────────────────────────────────────

def build_platform_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم هر پلتفرم از کل رکوردهای annotation_status=="ok" به تفکیک هفته.

    Pooled across platforms (نه per-platform) چون سوال «چه کسری از این هفته
    از X/Reddit/YouTube آمده» است، نه «X در این هفته چقدر داشت»."""
    eligible = df[df["annotation_status"] == "ok"]
    rows: list[dict] = []
    for week in WEEKS:
        week_df = eligible[eligible["project_week"] == week]
        n_total = len(week_df)
        flags = _week_flags(week, n_total)
        for platform in PLATFORMS:
            n_platform = int((week_df["platform"] == platform).sum())
            proportion = round(n_platform / n_total, 4) if n_total else float("nan")
            rows.append({
                "project_week": week,
                "platform": platform,
                "n_platform": n_platform,
                "n_total_week": n_total,
                "platform_share": proportion,
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 2. سهم Source
# ─────────────────────────────────────────────────────────────────────────────

def build_source_share(df: pd.DataFrame) -> pd.DataFrame:
    """Top-N source_id به تفکیک پلتفرم × هفته + سهم «سایرین».

    از source_container (channel/subreddit/account) استفاده می‌شود، نه source_id
    خام، چون source_container سطح تجمیع معنادارتری برای تشخیص چرخش منبع دارد.
    اگه null بود، «(unknown)» می‌شود."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            src_col = week_df["source_container"].fillna("(unknown)")
            counts = src_col.value_counts()
            top = counts.head(TOP_N_SOURCES)
            for rank, (src, cnt) in enumerate(top.items(), start=1):
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "source_container": src,
                    "rank": rank,
                    "n_source": int(cnt),
                    "n_week": n,
                    "source_share": round(cnt / n, 4) if n else float("nan"),
                    **flags,
                })
            # سایرین
            n_top = int(top.sum())
            n_other = n - n_top
            rows.append({
                "platform": platform,
                "project_week": week,
                "source_container": "(others)",
                "rank": TOP_N_SOURCES + 1,
                "n_source": n_other,
                "n_week": n,
                "source_share": round(n_other / n, 4) if n else float("nan"),
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 3. سهم زبان
# ─────────────────────────────────────────────────────────────────────────────

def build_language_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم language_detected به تفکیک پلتفرم × هفته.

    همه‌ی رکوردها (نه فقط ok) چون language یک ویژگی محتواست، نه annotation."""
    canonical_langs = ["fa", "en", "ar", "other"]
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            counts = week_df["language_detected"].value_counts() if n else {}
            for lang in canonical_langs:
                cnt = int(counts.get(lang, 0))
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "language": lang,
                    "n_lang": cnt,
                    "n_week": n,
                    "lang_share": round(cnt / n, 4) if n else float("nan"),
                    **flags,
                })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 4. سهم News در برابر Personal opinion
# ─────────────────────────────────────────────────────────────────────────────

def build_content_type_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم news_or_report در برابر personal_opinion از content_type_label.

    فقط annotation_status=="ok" — همان قانون §24."""
    eligible = df[df["annotation_status"] == "ok"]
    tracked = ["news_or_report", "personal_opinion"]
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = eligible[eligible["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            counts = week_df["content_type_label"].value_counts() if n else {}
            for ct in tracked:
                cnt = int(counts.get(ct, 0))
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "content_type": ct,
                    "n_type": cnt,
                    "n_ok_week": n,
                    "type_share": round(cnt / n, 4) if n else float("nan"),
                    **flags,
                })
            # سایر برچسب‌های content_type
            n_tracked = sum(int(counts.get(ct, 0)) for ct in tracked)
            n_other = n - n_tracked
            rows.append({
                "platform": platform,
                "project_week": week,
                "content_type": "(other_types)",
                "n_type": n_other,
                "n_ok_week": n,
                "type_share": round(n_other / n, 4) if n else float("nan"),
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 5. سهم Query و Query version
# ─────────────────────────────────────────────────────────────────────────────

def build_query_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم هر query_id × query_version به تفکیک پلتفرم × هفته."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            if n == 0:
                rows.append({
                    "platform": platform, "project_week": week,
                    "query_id": float("nan"), "query_version": float("nan"),
                    "n_query": 0, "n_week": 0, "query_share": float("nan"),
                    **flags,
                })
                continue
            combo = (
                week_df[["query_id", "query_version"]]
                .fillna("(unknown)")
                .apply(tuple, axis=1)
                .value_counts()
            )
            for (qid, qver), cnt in combo.items():
                rows.append({
                    "platform": platform,
                    "project_week": week,
                    "query_id": qid,
                    "query_version": qver,
                    "n_query": int(cnt),
                    "n_week": n,
                    "query_share": round(cnt / n, 4),
                    **flags,
                })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 6. سهم Duplicate
# ─────────────────────────────────────────────────────────────────────────────

def build_duplicate_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم is_exact_duplicate و is_near_duplicate به تفکیک پلتفرم × هفته."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            n_exact = int(week_df["is_exact_duplicate"].sum()) if n else 0
            n_near = int(week_df["is_near_duplicate"].sum()) if n else 0
            rows.append({
                "platform": platform,
                "project_week": week,
                "n_total": n,
                "n_exact_duplicate": n_exact,
                "n_near_duplicate": n_near,
                "exact_duplicate_share": round(n_exact / n, 4) if n else float("nan"),
                "near_duplicate_share": round(n_near / n, 4) if n else float("nan"),
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 7. تمرکز کاربران پرتکرار
# ─────────────────────────────────────────────────────────────────────────────

def build_author_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """n_unique_authors و سهم پرتکرارترین کاربر به تفکیک پلتفرم × هفته.

    top_author_share بالا یعنی یک کاربر روند هفته را می‌تواند تعیین کند —
    این مستقیماً دلیل انتخاب Author-balanced trend است."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            known_authors = week_df["author_hash"].dropna()
            n_unique = int(known_authors.nunique())
            if n and not known_authors.empty:
                top_count = int(known_authors.value_counts().iloc[0])
                top_share = round(top_count / n, 4)
            else:
                top_count = 0
                top_share = float("nan")
            rows.append({
                "platform": platform,
                "project_week": week,
                "n_total": n,
                "n_unique_authors": n_unique,
                "n_missing_author_hash": int(week_df["author_hash"].isna().sum()),
                "top_author_n": top_count,
                "top_author_share": top_share,
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 8. سهم محتوای پرریسک
# ─────────────────────────────────────────────────────────────────────────────

def build_risk_share(df: pd.DataFrame) -> pd.DataFrame:
    """سهم is_flagged_bot_suspect و automation_risk bucket به تفکیک پلتفرم × هفته."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)
            n_bot = int(week_df["is_flagged_bot_suspect"].sum()) if n else 0
            buckets = week_df["automation_risk_score_user"].apply(_risk_bucket)
            bucket_counts = buckets.value_counts() if n else {}
            rows.append({
                "platform": platform,
                "project_week": week,
                "n_total": n,
                "n_flagged_bot": n_bot,
                "bot_suspect_share": round(n_bot / n, 4) if n else float("nan"),
                "n_risk_high": int(bucket_counts.get("high", 0)),
                "n_risk_medium": int(bucket_counts.get("medium", 0)),
                "n_risk_low": int(bucket_counts.get("low", 0)),
                "n_risk_unknown": int(bucket_counts.get("unknown", 0)),
                "risk_high_share": round(bucket_counts.get("high", 0) / n, 4) if n else float("nan"),
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 9. تمرکز Parent
# ─────────────────────────────────────────────────────────────────────────────

def build_parent_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """سهم بزرگ‌ترین parent_id / source_container به تفکیک پلتفرم × هفته.

    بزرگ‌ترین parent بودن یعنی یک thread/video/submission سهم بالایی از
    کل رکوردهای هفته را دارد — bias محتوایی معین."""
    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = df[df["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)

            parent_counts = week_df["parent_id"].dropna().value_counts()
            if n and not parent_counts.empty:
                top_parent = str(parent_counts.index[0])
                top_parent_n = int(parent_counts.iloc[0])
                top_parent_share = round(top_parent_n / n, 4)
            else:
                top_parent = float("nan")
                top_parent_n = 0
                top_parent_share = float("nan")

            container_counts = week_df["source_container"].dropna().value_counts()
            if n and not container_counts.empty:
                top_container = str(container_counts.index[0])
                top_container_n = int(container_counts.iloc[0])
                top_container_share = round(top_container_n / n, 4)
            else:
                top_container = float("nan")
                top_container_n = 0
                top_container_share = float("nan")

            rows.append({
                "platform": platform,
                "project_week": week,
                "n_total": n,
                "top_parent_id": top_parent,
                "top_parent_n": top_parent_n,
                "top_parent_share": top_parent_share,
                "top_container": top_container,
                "top_container_n": top_container_n,
                "top_container_share": top_container_share,
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 10. روند خام + Author-balanced trend سنتیمنت
# ─────────────────────────────────────────────────────────────────────────────

def build_sentiment_adjusted(df: pd.DataFrame) -> pd.DataFrame:
    """روند خام positive_rate در کنار author-balanced positive_rate.

    Author-balanced: برای هر (author_hash, platform, project_week)، اول
    میانگین positive می‌گیریم (اگر کاربری ۱۰ توییت positive + ۱۰ توییت neutral
    داشته، positive_rate او 0.5 است)، سپس میانگین کاربران. این وزن «یک کاربر
    یک رأی» را اعمال می‌کند بدون این‌که کاربران پرتکرار روند را تعیین کنند.

    کاربرانی که author_hash=null دارند در Author-balanced شرکت نمی‌کنند و
    این محدودیت صریحاً در ستون n_authors_in_balanced گزارش می‌شود."""
    eligible = df[(df["annotation_status"] == "ok")]
    positive_label = "positive"

    rows: list[dict] = []
    for platform in PLATFORMS:
        plat_df = eligible[eligible["platform"] == platform]
        for week in WEEKS:
            week_df = plat_df[plat_df["project_week"] == week]
            n = len(week_df)
            flags = _week_flags(week, n)

            # روند خام
            if n:
                n_pos_raw = int((week_df["sentiment_label"] == positive_label).sum())
                raw_rate = round(n_pos_raw / n, 4)
                ci_low_raw, ci_high_raw = wilson_confidence_interval(n_pos_raw, n)
                ci_low_raw = round(ci_low_raw, 4)
                ci_high_raw = round(ci_high_raw, 4)
            else:
                n_pos_raw = 0
                raw_rate = float("nan")
                ci_low_raw = ci_high_raw = float("nan")

            # Author-balanced trend
            known = week_df.dropna(subset=["author_hash"])
            n_authors = int(known["author_hash"].nunique())
            if n_authors > 0:
                author_means = (
                    known.assign(_is_pos=(known["sentiment_label"] == positive_label).astype(float))
                    .groupby("author_hash")["_is_pos"]
                    .mean()
                )
                balanced_rate = round(float(author_means.mean()), 4)
                # Wilson CI روی n_authors با count معادل
                n_pos_balanced = round(balanced_rate * n_authors)
                ci_low_bal, ci_high_bal = wilson_confidence_interval(int(n_pos_balanced), n_authors)
                ci_low_bal = round(ci_low_bal, 4)
                ci_high_bal = round(ci_high_bal, 4)
            else:
                balanced_rate = float("nan")
                ci_low_bal = ci_high_bal = float("nan")

            rows.append({
                "platform": platform,
                "project_week": week,
                "n": n,
                "n_authors_in_balanced": n_authors,
                "n_positive_raw": n_pos_raw,
                "raw_positive_rate": raw_rate,
                "raw_ci_low": ci_low_raw,
                "raw_ci_high": ci_high_raw,
                "balanced_positive_rate": balanced_rate,
                "balanced_ci_low": ci_low_bal,
                "balanced_ci_high": ci_high_bal,
                "rate_delta": (
                    round(balanced_rate - raw_rate, 4)
                    if not (pd.isna(balanced_rate) or pd.isna(raw_rate))
                    else float("nan")
                ),
                **flags,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# orchestration
# ─────────────────────────────────────────────────────────────────────────────

def build_all_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "composition_shift_platform_share":    build_platform_share(df),
        "composition_shift_source_share":      build_source_share(df),
        "composition_shift_language_share":    build_language_share(df),
        "composition_shift_content_type_share": build_content_type_share(df),
        "composition_shift_query_share":       build_query_share(df),
        "composition_shift_duplicate_share":   build_duplicate_share(df),
        "composition_shift_author_concentration": build_author_concentration(df),
        "composition_shift_risk_share":        build_risk_share(df),
        "composition_shift_parent_concentration": build_parent_concentration(df),
        "composition_shift_sentiment_adjusted": build_sentiment_adjusted(df),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    df = load_annotated_dataset(args.input)
    tables = build_all_tables(df)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        out_path = args.output_dir / f"{name}.csv"
        table.to_csv(out_path, index=False, encoding="utf-8-sig")
        n_gap = int(table.get("is_data_gap", pd.Series(dtype=bool)).sum()) if "is_data_gap" in table.columns else 0
        print(f"Wrote {len(table):>6} rows → {out_path.name}  ({n_gap} data-gap rows)")


if __name__ == "__main__":
    main()
