"""
sensitivity_analysis.py -- docs/checklist.md, Phase 15: تحلیل حساسیت
(حداقل شش مقایسه، قبلاً هیچ خروجی مستقلی نداشت).

Some of checklist Phase 15's list are already computed as a natural
byproduct of another script (Spearman vs Pearson: financial correlation;
Event window 1/2/3 weeks: event_study.py; per-platform vs Pooled:
descriptive_stats.py) -- this script does NOT recompute those, it reads
their existing outputs and re-presents a one-line summary in the SAME
table, so the "at least 6" deliverable genuinely lives in one place
(outputs/tables/sensitivity_analysis_results.csv) instead of being
scattered and easy to miss. The remaining comparisons are computed here
directly, on data/processed/annotated_dataset.parquet (annotation_status==
"ok" rows only, same rule every Pipeline B script uses).

Primary outcome metric for the comparisons computed here: share of
sentiment_label=="positive" among ok-labeled rows (a single, consistently
available metric -- checklist Phase 15 doesn't mandate one specific metric,
this project's own core outcome throughout is a label share). Each row
reports the metric under a baseline and an alternative condition side by
side, with the shift and n for both -- never just one number.

Comparisons (>= 6, checklist's minimum):
  1. with vs without Duplicate/Near-duplicate content
  2. Content-level vs Author-balanced (mean-per-author, one vote each)
  3. with vs without the single largest Source (source_container) per platform
  4. with vs without the single largest Parent (post_id) per platform
  5. All confidence vs high-confidence-only (confidence >= 0.7) labels
  6. Unweighted vs Engagement-weighted (log1p, capped at p99) -- YouTube
     only, the one platform with real engagement_score (see decision_log.md)
  7. [reference] Spearman vs Pearson -- financial_social_correlation_results_v1.csv
  8. [reference] Event window 1/2/3 weeks -- event_study_sensitivity_window.csv
  9. [reference] each platform separate vs Pooled observed

Usage:
    python -m src.temporal_analysis.sensitivity_analysis
    python -m src.temporal_analysis.sensitivity_analysis --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")  # Persian notes below

from src.temporal_analysis.common import (  # noqa: E402
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    PLATFORMS,
    load_annotated_dataset,
    wilson_confidence_interval,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIDENCE_THRESHOLD = 0.7
ENGAGEMENT_CAP_PERCENTILE = 99

RESULT_COLUMNS = [
    "comparison_id", "question", "platform",
    "n_baseline", "positive_share_baseline", "ci_low_baseline", "ci_high_baseline",
    "n_alternative", "positive_share_alternative", "ci_low_alternative", "ci_high_alternative",
    "shift", "note",
]


def positive_share(df: pd.DataFrame) -> tuple[int, float, float, float]:
    n = len(df)
    if n == 0:
        return 0, float("nan"), float("nan"), float("nan")
    k = int((df["sentiment_label"] == "positive").sum())
    lo, hi = wilson_confidence_interval(k, n)
    return n, k / n, lo, hi


def author_balanced_positive_share(df: pd.DataFrame) -> tuple[int, float]:
    """One vote per author_hash: mean(is_positive) within author, then mean
    across authors -- same "content-level vs author-balanced" logic
    composition_shift.py's sentiment_adjusted table already uses, applied
    here to the single share metric this script tracks."""
    d = df.dropna(subset=["author_hash"]).copy()
    if d.empty:
        return 0, float("nan")
    d["is_positive"] = (d["sentiment_label"] == "positive").astype(float)
    per_author = d.groupby("author_hash")["is_positive"].mean()
    return int(per_author.shape[0]), float(per_author.mean())


def row(comparison_id, question, platform, base, alt, note) -> dict:
    n_b, share_b, lo_b, hi_b = base
    n_a, share_a, lo_a, hi_a = alt
    return {
        "comparison_id": comparison_id, "question": question, "platform": platform,
        "n_baseline": n_b, "positive_share_baseline": share_b, "ci_low_baseline": lo_b, "ci_high_baseline": hi_b,
        "n_alternative": n_a, "positive_share_alternative": share_a, "ci_low_alternative": lo_a, "ci_high_alternative": hi_a,
        "shift": (share_a - share_b) if pd.notna(share_a) and pd.notna(share_b) else float("nan"),
        "note": note,
    }


def run(input_path: Path, output_dir: Path) -> pd.DataFrame:
    df = load_annotated_dataset(input_path)
    ok = df[df["annotation_status"] == "ok"].copy()
    results: list[dict] = []

    # 1. with vs without Duplicate/Near-duplicate
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        no_dup = sub[~(sub["is_exact_duplicate"].fillna(False) | sub["is_near_duplicate"].fillna(False))]
        results.append(row(
            "duplicate_inclusion", "با/بدون Duplicate و Near-duplicate", platform,
            positive_share(sub), positive_share(no_dup),
            f"حذف‌شده: {len(sub) - len(no_dup)} رکورد duplicate/near-duplicate",
        ))

    # 2. Content-level vs Author-balanced
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        n_b, share_b, lo_b, hi_b = positive_share(sub)
        n_a, share_a = author_balanced_positive_share(sub)
        results.append(row(
            "content_vs_author_balanced", "Content-level در برابر Author-balanced (هر کاربر یک رأی)", platform,
            (n_b, share_b, lo_b, hi_b), (n_a, share_a, float("nan"), float("nan")),
            "n_alternative = تعداد author_hash یکتا (مخرج Author-balanced)، نه تعداد رکورد",
        ))

    # 3. with vs without largest Source (source_container)
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        if sub["source_container"].notna().sum() == 0:
            results.append(row("largest_source_exclusion", "با/بدون بزرگ‌ترین Source", platform,
                                positive_share(sub), (0, float("nan"), float("nan"), float("nan")),
                                "source_container برای این پلتفرم خالی است -- قابل محاسبه نیست"))
            continue
        top_source = sub["source_container"].value_counts().idxmax()
        without_top = sub[sub["source_container"] != top_source]
        if without_top.empty:
            results.append(row(
                "largest_source_exclusion", "با/بدون بزرگ‌ترین Source", platform,
                positive_share(sub), (0, float("nan"), float("nan"), float("nan")),
                f"not_meaningful: source_container یک مقدار ثابت است ({top_source!r}، {sub['source_container'].nunique()} "
                "مقدار یکتا) -- این پلتفرم مفهوم Source/کانال واقعی ندارد (فقط Query-based Search)",
            ))
            continue
        results.append(row(
            "largest_source_exclusion", "با/بدون بزرگ‌ترین Source", platform,
            positive_share(sub), positive_share(without_top),
            f"بزرگ‌ترین Source حذف‌شده: {top_source!r} ({len(sub) - len(without_top)} رکورد)",
        ))

    # 4. with vs without largest Parent (post_id)
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        if sub["post_id"].notna().sum() == 0:
            results.append(row("largest_parent_exclusion", "با/بدون بزرگ‌ترین Parent", platform,
                                positive_share(sub), (0, float("nan"), float("nan"), float("nan")),
                                "post_id برای این پلتفرم خالی است -- قابل محاسبه نیست"))
            continue
        top_parent = sub["post_id"].value_counts().idxmax()
        without_top = sub[sub["post_id"] != top_parent]
        if without_top.empty:
            results.append(row(
                "largest_parent_exclusion", "با/بدون بزرگ‌ترین Parent", platform,
                positive_share(sub), (0, float("nan"), float("nan"), float("nan")),
                f"not_meaningful: post_id یک مقدار ثابت است ({top_parent!r}) -- این پلتفرم مفهوم Parent واقعی ندارد",
            ))
            continue
        results.append(row(
            "largest_parent_exclusion", "با/بدون بزرگ‌ترین Parent", platform,
            positive_share(sub), positive_share(without_top),
            f"بزرگ‌ترین Parent حذف‌شده: {top_parent!r} ({len(sub) - len(without_top)} رکورد)",
        ))

    # 5. All confidence vs high-confidence-only
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        high_conf = sub[sub["confidence"] >= CONFIDENCE_THRESHOLD]
        results.append(row(
            "confidence_threshold", f"همه Labelها در برابر Confidence>={CONFIDENCE_THRESHOLD}", platform,
            positive_share(sub), positive_share(high_conf),
            f"{len(sub) - len(high_conf)} رکورد زیر آستانه حذف‌شد",
        ))

    # 6. Unweighted vs Engagement-weighted (log1p, capped) -- YouTube only (see module docstring)
    yt = ok[(ok["platform"] == "youtube") & ok["engagement_score"].notna()]
    if len(yt) > 0:
        cap = np.percentile(yt["engagement_score"].clip(lower=0), ENGAGEMENT_CAP_PERCENTILE)
        w = np.log1p(yt["engagement_score"].clip(lower=0, upper=cap))
        is_pos = (yt["sentiment_label"] == "positive").astype(float)
        weighted_share = float(np.average(is_pos, weights=w)) if w.sum() > 0 else float("nan")
        results.append(row(
            "engagement_weighting", "Unweighted در برابر Engagement-weighted (log1p+Cap)", "youtube",
            positive_share(yt), (len(yt), weighted_share, float("nan"), float("nan")),
            f"Cap در صدک {ENGAGEMENT_CAP_PERCENTILE}={cap:.1f}؛ فقط youtube چون engagement_score فقط اونجا پرشده (decision_log.md)",
        ))
    else:
        results.append(row("engagement_weighting", "Unweighted در برابر Engagement-weighted (log1p+Cap)", "youtube",
                            (0, float("nan"), float("nan"), float("nan")), (0, float("nan"), float("nan"), float("nan")),
                            "engagement_score خالی است"))

    out = pd.DataFrame(results, columns=RESULT_COLUMNS)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "sensitivity_analysis_results.csv"
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} row(s) -> {out_path}")

    _write_reference_summary(output_dir)
    return out


def _write_reference_summary(output_dir: Path) -> None:
    """Comparisons 7-9 already exist as a byproduct of other scripts -- this
    writes one small pointer file (not a recomputation) so the "at least 6"
    Phase-15 deliverable is discoverable from a single place."""
    lines = [
        "# تحلیل حساسیت — مقایسه‌های موجود در جاهای دیگر (نه اینجا محاسبه‌شده)",
        "",
        "این‌ها به‌عنوان بخشی از اسکریپت‌های دیگر Pipeline B از قبل تولید شده‌اند؛ اینجا فقط رفرنس داده می‌شود.",
        "",
        "| مقایسه | فایل |",
        "|---|---|",
        "| Spearman در برابر Pearson (همبستگی مالی) | `outputs/tables/financial/financial_social_correlation_results_v1.csv` (ستون `method`) |",
        "| Event window ۱، ۲ و ۳ هفته‌ای | `outputs/tables/event_analysis/event_study_sensitivity_window.csv` |",
        "| هر پلتفرم جدا در برابر Pooled observed | `outputs/tables/descriptive_stats_by_platform_week.csv` در برابر `descriptive_stats_by_week_pooled_all_platforms.csv` |",
        "| با/بدون بزرگ‌ترین Source/Near-duplicate (رویداد) | `outputs/tables/event_analysis/event_study_sensitivity_robustness.csv` |",
    ]
    path = output_dir / "sensitivity_analysis_reference_index.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()
