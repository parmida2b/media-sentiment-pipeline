"""
group_comparison.py -- docs/checklist.md, Phase 12 (item 24): مقایسه‌ی گروه‌ها

Implements the exact 4-test table checklist.md item 24 specifies -- no test
outside this table, no p<0.05-only reporting (every test reports n,
Estimate, CI, Effect size, p-value, assumptions, and the record-dependence
caveat, whether or not it's "significant"):

  question                                   | test          | effect size
  --------------------------------------------|---------------|------------------
  Stance distribution: platform / language    | Chi-square    | Cramer's V
  Small 2x2 table                              | Fisher Exact  | Odds Ratio (CI)
  Engagement difference, two groups            | Mann-Whitney U| rank-biserial r
  Mean difference, two independent groups      | Welch's t-test| Hedges' g

Reads data/processed/annotated_dataset.parquet (docs/pipeline_b_input_contract.md).
Stance-distribution tests use annotation_status=="ok" rows only (checklist
item 24's own label-exclusion rule, same as descriptive_stats.py/
weekly_trend.py). Engagement/text_length tests use the full population
(they don't depend on annotation succeeding).

CI method per test (documented per-row in the `assumptions` column too):
  - Odds Ratio: exact closed-form (statsmodels Table2x2), Fisher-consistent.
  - Hedges' g: analytic approximate CI (Hedges & Olkin 1985 SE formula) --
    closed-form, no resampling needed.
  - Cramer's V / rank-biserial r: no simple closed form exists -- percentile
    bootstrap (N_BOOT resamples). Continuous-variable groups (engagement/
    text_length) are capped at MAX_BOOTSTRAP_N per group before
    resampling, purely for runtime -- documented in `assumptions`, not
    silently applied.

Every comparison also reports a `dependency_note`: records from the same
author_hash/source_parent_id are not independent draws (checklist's
recurring caveat) -- these tests treat rows as independent, same
simplification descriptive_stats.py/weekly_trend.py already make; the
Author-balanced sensitivity check (composition_shift.py) is the intended
cross-check, not a substitute here.

Output: outputs/tables/group_comparison_results.csv (long format, one row
per test).

Usage:
    python -m src.temporal_analysis.group_comparison
    python -m src.temporal_analysis.group_comparison --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.contingency_tables import Table2x2

sys.stdout.reconfigure(encoding="utf-8")  # Persian notes/questions in print()/CSV below

from src.temporal_analysis.common import (  # noqa: E402
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    PLATFORMS,
    load_annotated_dataset,
)

RANDOM_SEED = 1405
N_BOOT = 1000
MAX_BOOTSTRAP_N = 5000  # per-group cap before bootstrapping a continuous-variable effect size, for runtime only

RESULT_COLUMNS = [
    "comparison_id", "question", "test", "effect_size_type", "groups",
    "n", "n_group_a", "n_group_b", "estimate", "ci_low", "ci_high",
    "effect_size", "effect_size_ci_low", "effect_size_ci_high",
    "p_value", "assumptions", "dependency_note",
]

DEPENDENCY_NOTE = (
    "رکوردها به‌عنوان مستقل فرض شده‌اند؛ چند رکورد از یک author_hash یا "
    "source_parent_id واقعاً مستقل نیستند (composition_shift.py's "
    "Author-balanced trend برای بررسی حساسیت این فرض است، نه جایگزین این آزمون)."
)


def _rng():
    return np.random.default_rng(RANDOM_SEED)


def cramers_v(chi2: float, n: int, r: int, k: int) -> float:
    if n <= 0 or min(r - 1, k - 1) <= 0:
        return float("nan")
    return float(np.sqrt((chi2 / n) / min(r - 1, k - 1)))


def bootstrap_cramers_v(table_df: pd.DataFrame, group_col: str, cat_col: str, n_boot: int = N_BOOT) -> tuple[float, float]:
    rng = _rng()
    df = table_df[[group_col, cat_col]].dropna()
    n = len(df)
    if n == 0:
        return float("nan"), float("nan")
    df = df.reset_index(drop=True)
    vs = []
    for _ in range(n_boot):
        sample = df.iloc[rng.integers(0, n, size=n)].reset_index(drop=True)
        ct = pd.crosstab(sample[group_col], sample[cat_col])
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            continue
        chi2, _, _, _ = stats.chi2_contingency(ct)
        vs.append(cramers_v(chi2, ct.values.sum(), *ct.shape))
    if not vs:
        return float("nan"), float("nan")
    return float(np.percentile(vs, 2.5)), float(np.percentile(vs, 97.5))


def rank_biserial_from_u(u: float, n1: int, n2: int) -> float:
    """r = 1 - 2U / (n1*n2); ranges [-1, 1], sign matches whichever group
    (a vs b, in call order) tends to rank higher."""
    if n1 == 0 or n2 == 0:
        return float("nan")
    return float(1 - (2 * u) / (n1 * n2))


def bootstrap_rank_biserial(a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT) -> tuple[float, float]:
    rng = _rng()
    vs = []
    for _ in range(n_boot):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        try:
            u, _ = stats.mannwhitneyu(sa, sb, alternative="two-sided")
        except ValueError:
            continue
        vs.append(rank_biserial_from_u(u, len(sa), len(sb)))
    if not vs:
        return float("nan"), float("nan")
    return float(np.percentile(vs, 2.5)), float(np.percentile(vs, 97.5))


def hedges_g(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Cohen's d (pooled SD), small-sample-corrected to Hedges' g, with the
    standard analytic approximate CI (Hedges & Olkin 1985): closed-form, no
    bootstrap needed."""
    n1, n2 = len(a), len(b)
    m1, m2 = np.mean(a), np.mean(b)
    v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled_sd = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return float("nan"), float("nan"), float("nan")
    d = (m1 - m2) / pooled_sd
    correction = 1 - 3 / (4 * (n1 + n2) - 9)  # Hedges' small-sample bias correction
    g = d * correction
    se_g = correction * np.sqrt((n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2 - 2)))
    return float(g), float(g - 1.959963984540054 * se_g), float(g + 1.959963984540054 * se_g)


def _cap(a: pd.Series, seed: int = RANDOM_SEED) -> np.ndarray:
    arr = a.dropna().to_numpy()
    if len(arr) > MAX_BOOTSTRAP_N:
        arr = np.random.default_rng(seed).choice(arr, size=MAX_BOOTSTRAP_N, replace=False)
    return arr


def chi_square_test(df: pd.DataFrame, group_col: str, comparison_id: str, question: str) -> dict:
    sub = df[["stance_label", group_col]].dropna()
    ct = pd.crosstab(sub[group_col], sub["stance_label"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    v = cramers_v(chi2, ct.values.sum(), *ct.shape)
    v_lo, v_hi = bootstrap_cramers_v(sub, group_col, "stance_label")
    return {
        "comparison_id": comparison_id, "question": question, "test": "chi_square",
        "effect_size_type": "cramers_v", "groups": f"stance_label x {group_col}",
        "n": int(ct.values.sum()), "n_group_a": None, "n_group_b": None,
        "estimate": None, "ci_low": None, "ci_high": None,
        "effect_size": v, "effect_size_ci_low": v_lo, "effect_size_ci_high": v_hi,
        "p_value": float(p),
        "assumptions": f"dof={dof}; Cramer's V CI از Bootstrap (n_boot={N_BOOT}) نه فرم بسته؛ annotation_status=='ok' فقط.",
        "dependency_note": DEPENDENCY_NOTE,
    }


def fisher_exact_test(df: pd.DataFrame, platform_a: str, platform_b: str) -> dict:
    """checklist item 24's "small 2x2 table" case: support vs oppose
    (other stance categories dropped), one platform pair at a time -- the
    natural 2x2 shape this test is meant for."""
    sub = df[df["platform"].isin([platform_a, platform_b]) & df["stance_label"].isin(["support", "oppose"])]
    ct = pd.crosstab(sub["platform"], sub["stance_label"]).reindex(
        index=[platform_a, platform_b], columns=["support", "oppose"], fill_value=0
    )
    odds_ratio, p = stats.fisher_exact(ct.values)
    table2x2 = Table2x2(ct.values)
    ci_low, ci_high = table2x2.oddsratio_confint()
    return {
        "comparison_id": f"fisher_{platform_a}_vs_{platform_b}",
        "question": f"support/oppose نسبت متفاوت بین {platform_a} و {platform_b}؟ (جدول ۲×۲)",
        "test": "fisher_exact", "effect_size_type": "odds_ratio",
        "groups": f"platform: {platform_a} vs {platform_b} (stance: support vs oppose)",
        "n": int(ct.values.sum()), "n_group_a": int(ct.loc[platform_a].sum()), "n_group_b": int(ct.loc[platform_b].sum()),
        "estimate": float(odds_ratio), "ci_low": float(ci_low), "ci_high": float(ci_high),
        "effect_size": float(odds_ratio), "effect_size_ci_low": float(ci_low), "effect_size_ci_high": float(ci_high),
        "p_value": float(p),
        "assumptions": f"جدول: {ct.values.tolist()}; annotation_status=='ok' فقط؛ CI دقیق (statsmodels Table2x2).",
        "dependency_note": DEPENDENCY_NOTE,
    }


def engagement_not_applicable_row(platform_a: str, platform_b: str, reason: str) -> dict:
    """engagement_score is entirely null for x/reddit in the current
    annotated_dataset.parquet (docs/pipeline_b_input_contract.md lists it,
    but neither collector's Record populates it -- see x_to_record.py's
    module docstring, same gap for Reddit) -- an honest "not computable"
    row instead of a silent NaN/empty-sample result."""
    return {
        "comparison_id": f"mannwhitney_engagement_{platform_a}_vs_{platform_b}",
        "question": f"Engagement متفاوت بین {platform_a} و {platform_b}؟",
        "test": "mann_whitney_u", "effect_size_type": "rank_biserial_r",
        "groups": f"platform: {platform_a} vs {platform_b} (engagement_score)",
        "n": 0, "n_group_a": 0, "n_group_b": 0,
        "estimate": None, "ci_low": None, "ci_high": None,
        "effect_size": None, "effect_size_ci_low": None, "effect_size_ci_high": None,
        "p_value": None,
        "assumptions": f"not_applicable: {reason}",
        "dependency_note": DEPENDENCY_NOTE,
    }


def mann_whitney_test(a_full: pd.Series, b_full: pd.Series, comparison_id: str, question: str, groups: str) -> dict:
    a, b = _cap(a_full), _cap(b_full)
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    r = rank_biserial_from_u(u, len(a), len(b))
    r_lo, r_hi = bootstrap_rank_biserial(a, b)
    capped_note = f" (نمونه برای Bootstrap به {MAX_BOOTSTRAP_N} در هر گروه Cap شد، فقط برای زمان اجرا)" if (
        len(a_full) > MAX_BOOTSTRAP_N or len(b_full) > MAX_BOOTSTRAP_N
    ) else ""
    return {
        "comparison_id": comparison_id, "question": question,
        "test": "mann_whitney_u", "effect_size_type": "rank_biserial_r", "groups": groups,
        "n": int(len(a_full) + len(b_full)), "n_group_a": int(len(a_full)), "n_group_b": int(len(b_full)),
        "estimate": float(np.median(a) - np.median(b)), "ci_low": None, "ci_high": None,
        "effect_size": r, "effect_size_ci_low": r_lo, "effect_size_ci_high": r_hi,
        "p_value": float(p),
        "assumptions": f"Engagement به‌شدت چوله است؛ median/IQR نه Mean؛ rank-biserial CI از Bootstrap.{capped_note}",
        "dependency_note": DEPENDENCY_NOTE,
    }


def welch_t_test(df: pd.DataFrame, platform_a: str, platform_b: str) -> dict:
    # pipeline_b_input_contract.md has no text_length column -- derived here
    # from text_raw (same "count chars" definition normalize_text.py uses
    # upstream, on data/interim/*.parquet -- not part of this file's contract).
    text_length = df["text_raw"].fillna("").str.len()
    a_full = text_length[df["platform"] == platform_a].dropna()
    b_full = text_length[df["platform"] == platform_b].dropna()
    t, p = stats.ttest_ind(a_full, b_full, equal_var=False)
    g, g_lo, g_hi = hedges_g(a_full.to_numpy(), b_full.to_numpy())
    return {
        "comparison_id": f"welch_text_length_{platform_a}_vs_{platform_b}",
        "question": f"میانگین طول متن متفاوت بین {platform_a} و {platform_b}؟",
        "test": "welch_t_test", "effect_size_type": "hedges_g",
        "groups": f"platform: {platform_a} vs {platform_b} (text_length)",
        "n": int(len(a_full) + len(b_full)), "n_group_a": int(len(a_full)), "n_group_b": int(len(b_full)),
        "estimate": float(a_full.mean() - b_full.mean()), "ci_low": None, "ci_high": None,
        "effect_size": g, "effect_size_ci_low": g_lo, "effect_size_ci_high": g_hi,
        "p_value": float(p),
        "assumptions": "Welch's t (واریانس نابرابر فرض)؛ CI تحلیلی Hedges & Olkin 1985 (فرم بسته، بدون Bootstrap).",
        "dependency_note": DEPENDENCY_NOTE,
    }


def run(input_path: Path, output_dir: Path) -> pd.DataFrame:
    df = load_annotated_dataset(input_path)
    ok = df[df["annotation_status"] == "ok"].copy()

    results = []
    results.append(chi_square_test(ok, "platform", "chi_square_stance_platform", "توزیع Stance بین پلتفرم‌ها متفاوت است؟"))
    results.append(chi_square_test(ok, "language_detected", "chi_square_stance_language", "توزیع Stance بین زبان‌ها متفاوت است؟"))

    engagement_by_platform = df.groupby("platform")["engagement_score"].apply(lambda s: int(s.notna().sum()))
    for a, b in itertools.combinations(PLATFORMS, 2):
        results.append(fisher_exact_test(ok, a, b))
        if engagement_by_platform.get(a, 0) == 0 or engagement_by_platform.get(b, 0) == 0:
            missing = [p for p in (a, b) if engagement_by_platform.get(p, 0) == 0]
            results.append(engagement_not_applicable_row(
                a, b, f"engagement_score برای {'/'.join(missing)} در annotated_dataset.parquet کاملاً خالی است "
                      "(هیچ Collector این فیلد را برای این پلتفرم پر نمی‌کند -- x_to_record.py/reddit_to_record.py's "
                      "module docstring)."
            ))
        else:
            results.append(mann_whitney_test(
                df.loc[df["platform"] == a, "engagement_score"].dropna(),
                df.loc[df["platform"] == b, "engagement_score"].dropna(),
                f"mannwhitney_engagement_{a}_vs_{b}", f"Engagement متفاوت بین {a} و {b}؟",
                f"platform: {a} vs {b} (engagement_score)",
            ))
        results.append(welch_t_test(df, a, b))

    # Cross-platform engagement comparison isn't possible (only YouTube has
    # engagement_score at all) -- a within-YouTube comparison by sentiment
    # is still a real, computable "Engagement difference, two groups" test.
    ok_yt = ok[ok["platform"] == "youtube"]
    pos = ok_yt.loc[ok_yt["sentiment_label"] == "positive", "engagement_score"].dropna()
    neg = ok_yt.loc[ok_yt["sentiment_label"] == "negative", "engagement_score"].dropna()
    if len(pos) > 0 and len(neg) > 0:
        results.append(mann_whitney_test(
            pos, neg, "mannwhitney_engagement_youtube_positive_vs_negative",
            "Engagement بین کامنت‌های مثبت و منفی یوتیوب متفاوت است؟",
            "youtube, sentiment_label: positive vs negative (engagement_score)",
        ))

    out = pd.DataFrame(results, columns=RESULT_COLUMNS)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "group_comparison_results.csv"
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} row(s) -> {out_path}")
    n_sig = int((out["p_value"] < 0.05).sum())
    print(f"({n_sig}/{len(out)} tests have p<0.05 -- every test is reported regardless, per checklist item 24)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()
