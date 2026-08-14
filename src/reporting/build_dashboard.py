"""Build a self-contained HTML dashboard from the pipeline's outputs/tables/*.csv.

Usage
-----
    python -m src.reporting.build_dashboard
    python -m src.reporting.build_dashboard --data-status real --out outputs/dashboard/index.html

This script does NOT talk to any API and does not require the outputs to be
"final" — it simply reads whatever is currently under ``outputs/tables/`` and
``outputs/model_evaluation/`` and renders a dashboard from it. That means:

  * Today, with mock/placeholder data flowing through the pipeline, running
    this script produces a dashboard over the mock numbers (and the
    dashboard visibly says so — see ``--data-status``).
  * Once the real collected + annotated data replaces the mock data and the
    same analysis scripts (src/preprocessing, src/temporal_analysis,
    src/event_analysis, ...) regenerate outputs/tables/*.csv, re-running this
    *same* script regenerates the dashboard over the real numbers. Nothing
    about the dashboard is hand-authored per run.

The output is a single HTML file with the data inlined as JSON and a small
vanilla-JS chart layer (no external CDN, so it also works opened directly
from disk with no server / no internet).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]


def _num(x) -> float | None:
    """Cast to float, mapping NaN/inf to None (JSON has no NaN/Infinity literal).

    With sparse real annotation coverage, before/after-event windows can have
    zero eligible records, which makes pandas produce NaN for derived shares
    and CIs. ``json.dumps`` happily emits a bare ``NaN`` token for that by
    default, which is invalid JSON and makes the browser's ``JSON.parse``
    throw — silently breaking every chart on the page, not just the one with
    missing data. Route every float through here before it reaches the
    payload so that can't happen again.
    """
    v = float(x)
    return v if math.isfinite(v) else None


def _sanitize(obj):
    """Recursively replace any stray NaN/inf float with None (defense in depth)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

# Fixed platform order used everywhere in the dashboard so a given platform
# always gets the same categorical color slot (blue / orange / aqua).
PLATFORM_ORDER = ["x", "reddit", "youtube"]

TREND_DIMENSIONS = {
    "sentiment": "outputs/tables/weekly_trend_sentiment_by_platform.csv",
    "emotion": "outputs/tables/weekly_trend_emotion_by_platform.csv",
    "stance": "outputs/tables/weekly_trend_stance_by_platform.csv",
}

# Fixed, meaningful class order per dimension (rather than alphabetical) so
# the default class shown on load is the most narratively useful one.
CLASS_ORDER = {
    "sentiment": ["positive", "negative", "neutral", "mixed", "unclear"],
    "emotion": ["hope", "anger", "fear", "sadness", "joy", "disgust", "surprise", "none_or_unclear"],
    "stance": ["support", "oppose", "neutral_or_balanced", "unrelated", "unclear"],
}

CATEGORY_SHARE_DIMENSIONS = {
    "language_detected": "زبان محتوا",
    "label:content_type": "نوع محتوا",
}


def _sort_by_order(values, order):
    order_index = {v: i for i, v in enumerate(order)}
    return sorted(values, key=lambda v: order_index.get(v, len(order)))


def load_kpis(tables_dir: Path, model_eval_dir: Path) -> dict:
    overall = pd.read_csv(tables_dir / "descriptive_stats_overall.csv").iloc[0]
    coverage = pd.read_csv(tables_dir / "descriptive_stats_annotation_coverage.csv")
    weekly = pd.read_csv(tables_dir / "weekly_trend_sentiment_by_platform.csv")

    overall_coverage = coverage[coverage["group_level"] == "overall"].iloc[0]

    kpi = {
        "n_total": int(overall["n_total"]),
        "n_annotation_ok": int(overall["n_annotation_ok"]),
        "pct_annotation_non_ok": float(overall["pct_annotation_non_ok"]),
        "n_platforms": int(weekly["platform"].nunique()),
        "n_weeks": int(weekly["project_week"].nunique()),
        "n_low_confidence": int(overall_coverage["n_low_confidence"]),
        "n_json_parse_failure": int(overall_coverage["n_json_parse_failure"]),
        "n_api_failure": int(overall_coverage["n_api_failure"]),
    }

    # LLM route KPIs — best-effort; the dashboard still renders without them.
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from src.annotation.model_routes import LOCKED_ROUTE_NAME  # type: ignore

        route_name = LOCKED_ROUTE_NAME or "groq_cheap_fast"
    except Exception:
        route_name = "groq_cheap_fast"

    summary_path = model_eval_dir / "sentiment_accuracy_summary.json"
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
        route = summary.get("routes", {}).get(route_name)
        if route:
            kpi["llm_route"] = route_name
            kpi["llm_n_gold"] = summary.get("n_gold_rows")
            kpi["llm_accuracy"] = route["sentiment"]["accuracy"]
            kpi["llm_macro_f1"] = route["sentiment"]["macro_f1"]
            kpi["llm_cost_per_1000"] = route.get("cost_per_1000_records_usd")

    return kpi


def load_coverage_by_platform(tables_dir: Path) -> list[dict]:
    coverage = pd.read_csv(tables_dir / "descriptive_stats_annotation_coverage.csv")
    by_platform = coverage[coverage["group_level"] == "platform"]
    rows = []
    for platform in PLATFORM_ORDER:
        row = by_platform[by_platform["platform"] == platform]
        if row.empty:
            continue
        row = row.iloc[0]
        rows.append(
            {
                "platform": platform,
                "n_total": int(row["n_total"]),
                "n_ok": int(row["n_ok"]),
                "pct_non_ok": float(row["pct_non_ok"]),
            }
        )
    return rows


def load_missing_rates(tables_dir: Path, top_n: int = 8) -> list[dict]:
    df = pd.read_csv(tables_dir / "descriptive_stats_missing_rates.csv")
    overall = df[df["group_level"] == "overall"].sort_values("missing_rate", ascending=False)
    return [
        {"column": r["column"], "missing_rate": float(r["missing_rate"])}
        for _, r in overall.head(top_n).iterrows()
    ]


def load_category_shares(tables_dir: Path) -> dict:
    df = pd.read_csv(tables_dir / "descriptive_stats_category_shares.csv")
    result = {}
    for dim in CATEGORY_SHARE_DIMENSIONS:
        sub = df[(df["dimension"] == dim) & (df["group_level"] == "platform")]
        by_platform = {}
        for platform in PLATFORM_ORDER:
            rows = sub[sub["platform"] == platform].sort_values("proportion", ascending=False)
            by_platform[platform] = [
                {"category": r["category"], "proportion": float(r["proportion"])}
                for _, r in rows.iterrows()
            ]
        result[dim] = by_platform
    return result


def load_weekly_trends(tables_dir: Path) -> dict:
    result = {}
    for dim, rel_path in TREND_DIMENSIONS.items():
        df = pd.read_csv(REPO_ROOT / rel_path)
        weeks = sorted(df["project_week"].unique().tolist())
        classes = _sort_by_order(df["class_label"].unique().tolist(), CLASS_ORDER[dim])

        series = {}
        for platform in PLATFORM_ORDER:
            series[platform] = {}
            for cls in classes:
                rows = df[(df["platform"] == platform) & (df["class_label"] == cls)]
                by_week = {r["project_week"]: r for _, r in rows.iterrows()}
                points = []
                for week in weeks:
                    r = by_week.get(week)
                    if r is None:
                        points.append(None)
                        continue
                    points.append(
                        {
                            "week": week,
                            "n": int(r["n"]),
                            "proportion": float(r["class_proportion"]),
                            "ci_low": float(r["wilson_ci_low"]),
                            "ci_high": float(r["wilson_ci_high"]),
                            "is_low_sample": bool(r["is_low_sample"]),
                            "is_partial_week": bool(r["is_partial_week"]),
                            "is_data_gap": bool(r["is_data_gap"]),
                        }
                    )
                series[platform][cls] = points

        result[dim] = {"weeks": weeks, "classes": classes, "series": series}

    return result


def load_event_study(tables_dir: Path) -> list[dict]:
    path = REPO_ROOT / "outputs/tables/event_analysis/event_study_main.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df = df[df["is_placebo"] == False]  # noqa: E712 — pandas boolean column
    events = []
    for _, r in df.iterrows():
        events.append(
            {
                "event_id": r["event_id"],
                "title_fa": r["title_fa"],
                "platform": r["platform"],
                "expected_direction_fa": r["expected_direction_fa"],
                "window_days": int(r["window_days"]),
                "p_before": _num(r["p_before"]),
                "p_after": _num(r["p_after"]),
                "share_diff": _num(r["share_diff"]),
                "ci_low": _num(r["ci_low"]),
                "ci_high": _num(r["ci_high"]),
                "n_before_target": int(r["n_before_target"]),
                "n_after_target": int(r["n_after_target"]),
            }
        )
    # Events with no eligible before/after records (share_diff is None, e.g.
    # a sparsely-annotated window) sort last rather than crashing the compare.
    events.sort(key=lambda e: (e["share_diff"] is None, e["share_diff"] or 0))
    return events


def load_financial_correlation(tables_dir: Path, top_n: int = 8) -> dict:
    path = REPO_ROOT / "outputs/tables/financial/financial_social_correlation_results_v1.csv"
    if not path.exists():
        return {"n_tested": 0, "n_significant_fdr": 0, "top": []}
    df = pd.read_csv(path)
    n_tested = len(df)
    n_significant = int((df["p_value_bh_fdr"] < 0.05).sum())
    top = df.reindex(df["p_value_raw"].sort_values().index).head(top_n)
    rows = [
        {
            "platform": r["platform"],
            "outcome_id": r["outcome_id"],
            "asset_id": r["asset_id"],
            "method": r["method"],
            "coefficient": float(r["coefficient"]),
            "p_value_raw": float(r["p_value_raw"]),
            "p_value_bh_fdr": float(r["p_value_bh_fdr"]),
            "n_paired_weeks": int(r["n_paired_weeks"]),
        }
        for _, r in top.iterrows()
    ]
    return {"n_tested": n_tested, "n_significant_fdr": n_significant, "top": rows}


def build_payload(tables_dir: Path, model_eval_dir: Path, data_status: str) -> dict:
    weekly_trends = load_weekly_trends(tables_dir)
    weekly_flat = pd.concat(
        [pd.read_csv(REPO_ROOT / p) for p in TREND_DIMENSIONS.values()], ignore_index=True
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_status": data_status,
        "platforms": PLATFORM_ORDER,
        "kpi": load_kpis(tables_dir, model_eval_dir),
        "coverage_by_platform": load_coverage_by_platform(tables_dir),
        "missing_rates": load_missing_rates(tables_dir),
        "category_shares": load_category_shares(tables_dir),
        "category_share_labels": CATEGORY_SHARE_DIMENSIONS,
        "weekly_trends": weekly_trends,
        "event_study": load_event_study(tables_dir),
        "financial_correlation": load_financial_correlation(tables_dir),
        "data_quality_flags": {
            "n_data_gap_weeks": int(weekly_flat["is_data_gap"].sum()),
            "n_low_sample_weeks": int(weekly_flat["is_low_sample"].sum()),
            "n_partial_weeks": int(weekly_flat["is_partial_week"].sum()),
        },
    }


def render(payload: dict, template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    payload = _sanitize(payload)
    # allow_nan=False: fail loudly at build time if a NaN/inf slipped through
    # _sanitize, instead of shipping a page whose embedded JSON.parse throws
    # in the browser (which silently kills every chart, not just the bad one).
    data_json = json.dumps(payload, ensure_ascii=False, indent=None, allow_nan=False)
    # Guard against a stray "</script>" inside string data breaking the
    # inline <script> block the JSON is embedded in.
    data_json = data_json.replace("</script", "<\\/script")
    return template.replace("__DASHBOARD_DATA_JSON__", data_json)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables-dir", default=str(REPO_ROOT / "outputs/tables"))
    parser.add_argument("--model-eval-dir", default=str(REPO_ROOT / "outputs/model_evaluation"))
    parser.add_argument("--template", default=str(Path(__file__).parent / "dashboard_template.html"))
    parser.add_argument("--out", default=str(REPO_ROOT / "outputs/dashboard/index.html"))
    parser.add_argument(
        "--data-status",
        choices=["mock", "real"],
        default="mock",
        help="Stamped in the dashboard banner so nobody mistakes placeholder numbers for real ones.",
    )
    args = parser.parse_args()

    tables_dir = Path(args.tables_dir)
    model_eval_dir = Path(args.model_eval_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_payload(tables_dir, model_eval_dir, args.data_status)
    html = render(payload, Path(args.template))
    out_path.write_text(html, encoding="utf-8")

    print(f"Dashboard written to {out_path} ({len(html):,} bytes, data_status={args.data_status})")


if __name__ == "__main__":
    main()
