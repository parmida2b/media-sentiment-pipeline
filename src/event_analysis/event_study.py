"""
event_study.py — docs/checklist.md §25/فاز سیزدهم: Event Analysis (Parmida)

Reads the one file Pipeline B may depend on (docs/pipeline_b_input_contract.md
via src.temporal_analysis.common.load_annotated_dataset — same synthetic
fallback while Pipeline A's real annotated_dataset.parquet isn't ready yet).

For each `primary_confirmatory` event in event_registry.py (pre-registered,
see that file's docstring — NOT chosen after looking at the data):

  - before/after share of the event's registered outcome (stance==support or
    stance==oppose against the event's target_id, whichever the outcome text
    says), using the registered main_window, computed PER PLATFORM separately
    (§25: "تحلیل جداگانه هر پلتفرم") — never pooled across platforms as the
    primary number.
  - difference in share (after - before) with a 95% CI for the difference of
    two independent proportions (normal-approximation on the difference,
    documented in `diff_of_proportions_ci` — no scipy/statsmodels dependency,
    matching src/temporal_analysis/common.py's own no-scipy rule).
  - content volume and composition (platform's own share of all-platform
    volume, top-source share) in the same before/after window, so a share
    change can be checked against a possible composition shift, not just
    read as attitude change.
  - sensitivity re-run at the registered sensitivity_window (narrower).
  - sensitivity re-run with the largest single source_container and all
    is_near_duplicate rows excluded (§25: "حذف بزرگ‌ترین Parent/Near-duplicate
    به‌عنوان حساسیت").
  - a PLACEBO comparison (event_registry.placebo_event_for) at a date
    nothing happened, same window width — explicitly labeled PLACEBO
    everywhere, never presented as a real effect.

EV-001 (study_anchor, no main_window) is reported separately, descriptively
only (volume + label composition in the days right after it) — see
`describe_study_anchor`.

Every number here is a "temporal association", never worded as a causal
effect (docs/checklist.md §29's own rule) — column names avoid "effect"/
"impact" on purpose (e.g. `share_diff`, not `event_effect`).

Usage:
    python -m src.event_analysis.event_study
    python -m src.event_analysis.event_study --input data/processed/annotated_dataset.parquet
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.event_analysis.event_registry import (  # noqa: E402
    EVENTS, PRIMARY_CONFIRMATORY_EVENTS, RegisteredEvent, placebo_event_for,
)
from src.temporal_analysis.common import (  # noqa: E402
    DEFAULT_INPUT_PATH, PLATFORMS, load_annotated_dataset,
)

DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "tables" / "event_analysis"

# Which stance direction each event's registered outcome text refers to —
# transcribed by hand from event_registry.py's primary_outcome_fa (support
# vs. oppose share), not inferred at runtime, so the choice is auditable.
_OUTCOME_STANCE = {
    "EV-016": "support",  # "سهم حمایت از دیپلماسی"
    "EV-025": "support",  # "سهم حمایت از دیپلماسی"
    "EV-031": "oppose",   # "سهم مخالفت با تشدید نظامی"
}


def _parse_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def diff_of_proportions_ci(count_a: int, n_a: int, count_b: int, n_b: int, confidence: float = 0.95) -> dict:
    """95% CI for (p_b - p_a), normal approximation on the difference of two
    independent-sample proportions (textbook closed form — no scipy, same
    convention as common.py's Wilson CI). Returns NaNs when either n is 0."""
    z = {0.90: 1.6448536269514722, 0.95: 1.959963984540054, 0.99: 2.5758293035489004}[confidence]
    if n_a <= 0 or n_b <= 0:
        return {"p_before": float("nan"), "p_after": float("nan"), "share_diff": float("nan"),
                "ci_low": float("nan"), "ci_high": float("nan")}
    p_a, p_b = count_a / n_a, count_b / n_b
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    diff = p_b - p_a
    return {
        "p_before": p_a, "p_after": p_b, "share_diff": diff,
        "ci_low": diff - z * se, "ci_high": diff + z * se,
    }


def _window(event_date: date, window_days: int) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    center = pd.Timestamp(event_date, tz="UTC")
    return center - timedelta(days=window_days), center, center + timedelta(days=window_days)


def _score_window(
    df: pd.DataFrame, platform: str, target_id: str, stance_direction: str,
    start: pd.Timestamp, center: pd.Timestamp, end: pd.Timestamp,
    exclude_near_dup: bool = False, exclude_top_source: bool = False,
) -> dict:
    sub = df[(df["platform"] == platform) & (df["annotation_status"] == "ok")]
    if exclude_near_dup and "is_near_duplicate" in sub.columns:
        sub = sub[~sub["is_near_duplicate"].fillna(False)]
    if exclude_top_source and "source_container" in sub.columns and sub["source_container"].notna().any():
        top_source = sub["source_container"].value_counts().idxmax()
        sub = sub[sub["source_container"] != top_source]

    before = sub[(sub["_dt"] >= start) & (sub["_dt"] < center)]
    after = sub[(sub["_dt"] >= center) & (sub["_dt"] < end)]

    target_before = before[before["target"] == target_id]
    target_after = after[after["target"] == target_id]

    result = diff_of_proportions_ci(
        count_a=int((target_before["stance_label"] == stance_direction).sum()), n_a=len(target_before),
        count_b=int((target_after["stance_label"] == stance_direction).sum()), n_b=len(target_after),
    )
    result.update({
        "n_before_all_records": len(before),
        "n_after_all_records": len(after),
        "n_before_target": len(target_before),
        "n_after_target": len(target_after),
    })
    return result


def run_event(df: pd.DataFrame, event: RegisteredEvent, window_days: int, label: str,
              exclude_near_dup: bool = False, exclude_top_source: bool = False) -> list[dict]:
    stance_direction = _OUTCOME_STANCE.get(event.event_id.replace("PLACEBO-", ""))
    if stance_direction is None or window_days is None:
        return []
    start, center, end = _window(event.event_date, window_days)
    rows = []
    for platform in PLATFORMS:
        scored = _score_window(
            df, platform, event.target_id, stance_direction, start, center, end,
            exclude_near_dup=exclude_near_dup, exclude_top_source=exclude_top_source,
        )
        rows.append({
            "event_id": event.event_id,
            "is_placebo": event.event_id.startswith("PLACEBO-"),
            "title_fa": event.title_fa,
            "platform": platform,
            "target_id": event.target_id,
            "outcome_stance_direction": stance_direction,
            "window_label": label,
            "window_days": window_days,
            "window_start_utc": start.isoformat(),
            "window_end_utc": end.isoformat(),
            "expected_direction_fa": event.expected_direction_fa,
            **scored,
        })
    return rows


def build_composition_table(df: pd.DataFrame, event: RegisteredEvent, window_days: int) -> list[dict]:
    """Volume + composition (per-platform share of total cross-platform
    volume, and share by language) in the same before/after window — so a
    share change found above can be sanity-checked against a possible
    composition shift instead of assumed to be attitude change (§25)."""
    if window_days is None:
        return []
    start, center, end = _window(event.event_date, window_days)
    ok = df[df["annotation_status"] == "ok"]
    before = ok[(ok["_dt"] >= start) & (ok["_dt"] < center)]
    after = ok[(ok["_dt"] >= center) & (ok["_dt"] < end)]

    rows = []
    for label, chunk, other in (("before", before, after), ("after", after, before)):
        total = len(chunk)
        for platform in PLATFORMS:
            n_platform = int((chunk["platform"] == platform).sum())
            rows.append({
                "event_id": event.event_id,
                "window_label": label,
                "platform": platform,
                "n_records": n_platform,
                "platform_share_of_window": n_platform / total if total else float("nan"),
                "total_records_in_window": total,
            })
    return rows


def describe_study_anchor(df: pd.DataFrame, event: RegisteredEvent, days_after: int = 14) -> pd.DataFrame:
    """EV-001 has no pre-war baseline in-window (analysis_role=study_anchor)
    — reported descriptively only: daily volume and label composition for
    the `days_after` days following it, per platform."""
    start = pd.Timestamp(event.event_date, tz="UTC")
    end = start + timedelta(days=days_after)
    ok = df[(df["annotation_status"] == "ok") & (df["_dt"] >= start) & (df["_dt"] < end)]
    rows = []
    for platform in PLATFORMS:
        sub = ok[ok["platform"] == platform]
        n = len(sub)
        rows.append({
            "event_id": event.event_id,
            "platform": platform,
            "days_after": days_after,
            "n_records": n,
            "negative_sentiment_share": (sub["sentiment_label"] == "negative").mean() if n else float("nan"),
            "anger_share": (sub["emotion_label"] == "anger").mean() if n else float("nan"),
            "fear_share": (sub["emotion_label"] == "fear").mean() if n else float("nan"),
        })
    return pd.DataFrame(rows)


def build_all(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = df.copy()
    df["_dt"] = _parse_dt(df["created_at_utc"])

    main_rows, sens_rows, robust_rows, placebo_rows, comp_rows = [], [], [], [], []
    for event in PRIMARY_CONFIRMATORY_EVENTS:
        main_rows += run_event(df, event, event.main_window_days, "main")
        sens_rows += run_event(df, event, event.sensitivity_window_days, "sensitivity_narrow_window")
        robust_rows += run_event(df, event, event.main_window_days, "sensitivity_excl_near_dup", exclude_near_dup=True)
        robust_rows += run_event(df, event, event.main_window_days, "sensitivity_excl_top_source", exclude_top_source=True)
        comp_rows += build_composition_table(df, event, event.main_window_days)

        placebo = placebo_event_for(event)
        placebo_rows += run_event(df, placebo, placebo.main_window_days, "placebo")

    anchor = next(e for e in EVENTS if e.analysis_role == "study_anchor")

    return {
        "event_study_main": pd.DataFrame(main_rows),
        "event_study_sensitivity_window": pd.DataFrame(sens_rows),
        "event_study_sensitivity_robustness": pd.DataFrame(robust_rows),
        "event_study_placebo": pd.DataFrame(placebo_rows),
        "event_study_composition": pd.DataFrame(comp_rows),
        "event_study_anchor_descriptive": describe_study_anchor(df, anchor),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    df = load_annotated_dataset(args.input)
    tables = build_all(df)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        out_path = args.output_dir / f"{name}.csv"
        table.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(table)} row(s) to {out_path}")

    print(f"\n{len(PRIMARY_CONFIRMATORY_EVENTS)} primary_confirmatory event(s) scored "
          f"(+1 study_anchor descriptive, +{len(PRIMARY_CONFIRMATORY_EVENTS)} placebo comparison(s)). "
          "Reminder: results are temporal associations, not causal effects (docs/checklist.md §29).")


if __name__ == "__main__":
    main()
