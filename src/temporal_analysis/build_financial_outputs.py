"""Build the frozen, analysis-ready financial outputs.

The frozen collector outputs are inputs only. This module never edits them.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from config.config_loader import load_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_CONFIG = load_config(REPOSITORY_ROOT / "config" / "config.yaml")
STUDY_START = pd.Timestamp(PIPELINE_CONFIG.date_range.start)
STUDY_END = pd.Timestamp(PIPELINE_CONFIG.date_range.end.date())
SEED = 1405

ASSET_DECISIONS = [
    {
        "asset_id": "OIL_BRENT",
        "analysis_tier": "primary",
        "analysis_use": "main",
        "feature_column": "log_return__OIL_BRENT",
        "interpretation": "Energy and conflict-related market channel",
        "main_limitation": "Yahoo front-month futures; not identical to FRED Brent spot",
    },
    {
        "asset_id": "GOLD_USD",
        "analysis_tier": "primary",
        "analysis_use": "main",
        "feature_column": "log_return__GOLD_USD",
        "interpretation": "Global safe-haven market channel",
        "main_limitation": "Yahoo front-month gold futures rather than a cash spot fixing",
    },
    {
        "asset_id": "VIX",
        "analysis_tier": "primary",
        "analysis_use": "main",
        "feature_column": "log_change__VIX",
        "interpretation": "Expected U.S. equity-market volatility",
        "main_limitation": "A volatility index, not an investable asset return",
    },
    {
        "asset_id": "IRR_USD",
        "analysis_tier": "primary",
        "analysis_use": "main",
        "feature_column": "log_return__IRR_USD",
        "interpretation": "Iranian free-market exchange-rate channel",
        "main_limitation": "OTC archive; timestamp precision and market closure differ from exchanges",
    },
    {
        "asset_id": "SP500",
        "analysis_tier": "secondary",
        "analysis_use": "context",
        "feature_column": "log_return__SP500",
        "interpretation": "Broad U.S. equity-market context",
        "main_limitation": "Context indicator; not a direct Iran-specific measure",
    },
    {
        "asset_id": "OIL_WTI",
        "analysis_tier": "secondary",
        "analysis_use": "sensitivity",
        "feature_column": "log_return__OIL_WTI",
        "interpretation": "Alternative oil benchmark",
        "main_limitation": "Used to check whether an oil result is Brent-specific",
    },
    {
        "asset_id": "IRR_GOLD18",
        "analysis_tier": "secondary",
        "analysis_use": "sensitivity",
        "feature_column": "log_return__IRR_GOLD18",
        "interpretation": "Local Iranian gold-market sensitivity indicator",
        "main_limitation": "OTC/local-market series with different calendar and source conditions",
    },
    {
        "asset_id": "TEDPIX",
        "analysis_tier": "descriptive_only",
        "analysis_use": "not_in_main_tests",
        "feature_column": "log_return__TEDPIX",
        "interpretation": "Tehran equity-market context after valid data begin",
        "main_limitation": "Valid observations begin during the study; inadequate full-window coverage",
    },
]

PRIMARY_EVENTS = [
    {
        "event_id": "EV-016",
        "event_date": "2026-04-07",
        "project_week": "W06",
        "title_fa": "اعلام آتش‌بس دوهفته‌ای",
        "analysis_role": "primary_confirmatory",
    },
    {
        "event_id": "EV-025",
        "event_date": "2026-06-17",
        "project_week": "W16",
        "title_fa": "امضای تفاهم‌نامه اسلام‌آباد",
        "analysis_role": "primary_confirmatory",
    },
    {
        "event_id": "EV-031",
        "event_date": "2026-06-27",
        "project_week": "W18",
        "title_fa": "ازسرگیری حملات متقابل",
        "analysis_role": "primary_confirmatory",
    },
]


def project_root(start: Path | None = None) -> Path:
    """Find the repository root from a notebook, script, or repository cwd."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (
            (candidate / "config" / "config.yaml").exists()
            and (candidate / "data" / "interim" / "financial" / "frozen_inputs").exists()
        ):
            return candidate
    raise FileNotFoundError(
        "Repository root containing config/config.yaml and the frozen financial inputs was not found."
    )


def project_week(date: pd.Timestamp) -> str:
    if date < STUDY_START or date > STUDY_END:
        raise ValueError(f"Date {date.date()} lies outside the registered study window.")
    return f"W{((date - STUDY_START).days // 7) + 1:02d}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_input_inventory(input_dir: Path) -> pd.DataFrame:
    names = [
        "asset_registry.csv",
        "financial_raw.csv",
        "financial_calendar_panel.csv",
        "financial_cleaning_exclusions.csv",
        "financial_features.csv",
        "financial_source_crosscheck.csv",
        "report_crosscheck.csv",
        "report_stationarity.csv",
    ]
    rows = []
    root = input_dir.parents[3]
    for name in names:
        path = input_dir / name
        rows.append(
            {
                "input_file": str(path.relative_to(root)),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else np.nan,
                "sha256": sha256(path) if path.exists() else "",
                "analysis_treatment": "read_only_frozen_input",
            }
        )
    return pd.DataFrame(rows)


def build_asset_decisions(input_dir: Path) -> pd.DataFrame:
    decisions = pd.DataFrame(ASSET_DECISIONS)
    registry = pd.read_csv(input_dir / "asset_registry.csv")
    keep = [
        "asset_id",
        "name_fa",
        "category",
        "instrument_type",
        "unit",
        "currency",
        "transform",
        "market",
        "source",
        "source_series_id",
        "endpoint",
        "instrument_variant",
        "notes",
    ]
    return decisions.merge(registry[keep], on="asset_id", how="left", validate="one_to_one")


def build_daily_selected(input_dir: Path, decisions: pd.DataFrame) -> pd.DataFrame:
    features = pd.read_csv(input_dir / "financial_features.csv", parse_dates=["observation_date"])
    features = features.loc[features["observation_date"].between(STUDY_START, STUDY_END)].copy()
    rows = []
    for rec in decisions.itertuples(index=False):
        part = features[["observation_date", rec.feature_column]].rename(columns={rec.feature_column: "daily_log_change"})
        part["asset_id"] = rec.asset_id
        part["feature_column"] = rec.feature_column
        part["analysis_tier"] = rec.analysis_tier
        part["analysis_use"] = rec.analysis_use
        part["project_week"] = part["observation_date"].map(project_week)
        rows.append(part)
    daily = pd.concat(rows, ignore_index=True)
    return daily[[
        "observation_date",
        "project_week",
        "asset_id",
        "analysis_tier",
        "analysis_use",
        "feature_column",
        "daily_log_change",
    ]].sort_values(["asset_id", "observation_date"], ignore_index=True)


def build_weekly_returns(daily: pd.DataFrame) -> pd.DataFrame:
    observed = daily.dropna(subset=["daily_log_change"]).copy()
    weekly = (
        observed.groupby(
            ["project_week", "asset_id", "analysis_tier", "analysis_use", "feature_column"],
            as_index=False,
            observed=True,
        )
        .agg(
            week_first_return_date=("observation_date", "min"),
            week_last_return_date=("observation_date", "max"),
            n_return_obs=("daily_log_change", "size"),
            weekly_log_change=("daily_log_change", "sum"),
        )
    )
    weekly["weekly_simple_change"] = np.expm1(weekly["weekly_log_change"])
    weekly["week_number"] = weekly["project_week"].str[1:].astype(int)
    return weekly.sort_values(["week_number", "asset_id"], ignore_index=True).drop(columns="week_number")


def build_coverage(input_dir: Path, daily: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    calendar = pd.read_csv(input_dir / "financial_calendar_panel.csv", parse_dates=["observation_date"])
    selected = daily["asset_id"].drop_duplicates().tolist()
    calendar = calendar.loc[
        calendar["asset_id"].isin(selected) & calendar["observation_date"].between(STUDY_START, STUDY_END)
    ].copy()
    base = (
        calendar.groupby(["project_week", "asset_id"], as_index=False, observed=True)
        .agg(
            expected_market_open_days=("market_open", "sum"),
            source_observation_days=("has_observation", "sum"),
            calendar_confidence=("calendar_confidence", lambda x: "|".join(sorted(set(x.dropna().astype(str))))),
        )
    )
    return_count = weekly[["project_week", "asset_id", "n_return_obs"]]
    coverage = base.merge(return_count, on=["project_week", "asset_id"], how="left")
    coverage["n_return_obs"] = coverage["n_return_obs"].fillna(0).astype(int)
    coverage["return_coverage_ratio"] = np.where(
        coverage["expected_market_open_days"] > 0,
        coverage["n_return_obs"] / coverage["expected_market_open_days"],
        np.nan,
    )
    coverage["coverage_status"] = np.select(
        [
            coverage["expected_market_open_days"].eq(0),
            coverage["return_coverage_ratio"].ge(0.80),
            coverage["return_coverage_ratio"].ge(0.50),
        ],
        ["no_scheduled_market_day", "adequate", "limited"],
        default="insufficient",
    )
    coverage["week_is_partial_by_design"] = coverage["project_week"].eq("W21")
    coverage["week_number"] = coverage["project_week"].str[1:].astype(int)
    return coverage.sort_values(["week_number", "asset_id"], ignore_index=True).drop(columns="week_number")


def build_coverage_summary(daily: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    observed = (
        daily.groupby(["asset_id", "analysis_tier", "analysis_use"], as_index=False, observed=True)
        .agg(
            first_feature_date=("observation_date", lambda x: x[daily.loc[x.index, "daily_log_change"].notna()].min()),
            last_feature_date=("observation_date", lambda x: x[daily.loc[x.index, "daily_log_change"].notna()].max()),
            n_daily_return_obs=("daily_log_change", "count"),
        )
    )
    weekly_summary = (
        coverage.groupby("asset_id", as_index=False, observed=True)
        .agg(
            n_weeks_with_return=("n_return_obs", lambda x: int((x > 0).sum())),
            n_weeks_adequate=("coverage_status", lambda x: int((x == "adequate").sum())),
            minimum_weekly_coverage=("return_coverage_ratio", "min"),
            median_weekly_coverage=("return_coverage_ratio", "median"),
        )
    )
    out = observed.merge(weekly_summary, on="asset_id", how="left")
    out["main_test_eligible"] = (out["analysis_use"] == "main") & (out["n_weeks_with_return"] == 21)
    return out.sort_values(["analysis_tier", "asset_id"], ignore_index=True)


def cumulative_change(values: pd.Series) -> float:
    values = values.dropna().astype(float)
    return float(np.expm1(values.sum())) if len(values) else np.nan


def build_event_windows(daily: pd.DataFrame) -> pd.DataFrame:
    primary_assets = [x["asset_id"] for x in ASSET_DECISIONS if x["analysis_use"] == "main"]
    rows = []
    for event in PRIMARY_EVENTS:
        event_date = pd.Timestamp(event["event_date"])
        for asset_id in primary_assets:
            series = daily.loc[
                (daily["asset_id"] == asset_id) & daily["daily_log_change"].notna(),
                ["observation_date", "daily_log_change"],
            ].sort_values("observation_date", ignore_index=True)
            candidates = series.index[series["observation_date"] >= event_date]
            if not len(candidates):
                continue
            position = int(candidates[0])
            mapped_date = series.loc[position, "observation_date"]
            pre = series.iloc[max(0, position - 3):position]
            post = series.iloc[position:position + 3]
            rows.append(
                {
                    **event,
                    "asset_id": asset_id,
                    "mapped_first_observed_return_date": mapped_date,
                    "mapping_gap_calendar_days": int((mapped_date - event_date).days),
                    "pre_window_n_observed_returns": len(pre),
                    "post_window_n_observed_returns": len(post),
                    "pre_3_observed_returns_cumulative_change": cumulative_change(pre["daily_log_change"]),
                    "event_and_next_2_observed_returns_cumulative_change": cumulative_change(post["daily_log_change"]),
                    "interpretation_scope": "descriptive_temporal_alignment_not_causal",
                }
            )
    return pd.DataFrame(rows)


def build_quality_checks(
    inventory: pd.DataFrame,
    daily: pd.DataFrame,
    weekly: pd.DataFrame,
    coverage: pd.DataFrame,
    event_windows: pd.DataFrame,
) -> pd.DataFrame:
    primary_assets = {x["asset_id"] for x in ASSET_DECISIONS if x["analysis_use"] == "main"}
    primary_week_counts = weekly.loc[weekly["asset_id"].isin(primary_assets)].groupby("asset_id")["project_week"].nunique()
    checks = [
        ("all_frozen_inputs_exist", bool(inventory["exists"].all()), f"{int(inventory['exists'].sum())}/{len(inventory)}"),
        ("daily_key_is_unique", not daily.duplicated(["observation_date", "asset_id"]).any(), str(len(daily))),
        ("study_start_matches_contract", daily["observation_date"].min() == STUDY_START, str(daily["observation_date"].min().date())),
        ("study_end_matches_contract", daily["observation_date"].max() == STUDY_END, str(daily["observation_date"].max().date())),
        ("project_has_21_registered_weeks", daily["project_week"].nunique() == 21, str(daily["project_week"].nunique())),
        ("all_primary_assets_have_21_weekly_values", bool((primary_week_counts == 21).all()), primary_week_counts.to_dict()),
        ("w21_marked_partial_by_design", bool(coverage.loc[coverage["project_week"] == "W21", "week_is_partial_by_design"].all()), "W21=2026-07-18..2026-07-22"),
        ("three_primary_events_used", event_windows["event_id"].nunique() == 3, str(event_windows["event_id"].nunique())),
        ("event_output_has_four_primary_assets_each", bool((event_windows.groupby("event_id")["asset_id"].nunique() == 4).all()), event_windows.groupby("event_id")["asset_id"].nunique().to_dict()),
        ("no_level_series_used_for_weekly_statistics", weekly["feature_column"].str.startswith(("log_return__", "log_change__")).all(), "weekly sums of daily log changes"),
    ]
    return pd.DataFrame(checks, columns=["check_id", "passed", "observed_value"])


def social_input_template() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "platform",
            "project_week",
            "outcome_id",
            "target_id",
            "outcome_value",
            "n_records",
            "ci_low",
            "ci_high",
            "source_file",
            "source_version",
        ]
    )


def run(root: Path | None = None) -> dict[str, pd.DataFrame]:
    root = project_root(root)
    input_dir = root / "data" / "interim" / "financial" / "frozen_inputs"
    table_dir = root / "outputs" / "tables" / "financial"
    audit_dir = root / "outputs" / "audits" / "financial"
    table_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    inventory = build_input_inventory(input_dir)
    decisions = build_asset_decisions(input_dir)
    daily = build_daily_selected(input_dir, decisions)
    weekly = build_weekly_returns(daily)
    coverage = build_coverage(input_dir, daily, weekly)
    coverage_summary = build_coverage_summary(daily, coverage)
    event_windows = build_event_windows(daily)
    checks = build_quality_checks(inventory, daily, weekly, coverage, event_windows)
    social_template = social_input_template()
    alignment_status = pd.DataFrame(
        [
            {
                "component": "weekly_social_financial_alignment",
                "status": "pending_social_outcomes",
                "required_input": "data/processed/social_media/social_weekly_outcomes_v1.csv",
                "decision": "Do not calculate or report correlations until final eligible labels are available.",
                "planned_primary_method": "Spearman; lags 0, 1, 2 weeks; paired-week permutation p-value; BH-FDR",
                "planned_sensitivity": "Pearson; exclude partial W21; alternative OIL_WTI and IRR_GOLD18 indicators",
            }
        ]
    )

    table_outputs = {
        "financial_asset_decisions_v1.csv": decisions,
        "financial_daily_selected_v1.csv": daily,
        "financial_weekly_returns_v1.csv": weekly,
        "financial_coverage_summary_v1.csv": coverage_summary,
        "financial_primary_event_windows_v1.csv": event_windows,
    }
    audit_outputs = {
        "financial_input_inventory_v1.csv": inventory,
        "financial_weekly_coverage_v1.csv": coverage,
        "financial_quality_checks_v1.csv": checks,
        "financial_social_input_template_v1.csv": social_template,
        "financial_social_alignment_status_v1.csv": alignment_status,
    }
    outputs = {**table_outputs, **audit_outputs}
    for filename, frame in table_outputs.items():
        frame.to_csv(table_dir / filename, index=False)
    for filename, frame in audit_outputs.items():
        frame.to_csv(audit_dir / filename, index=False)
    return outputs


if __name__ == "__main__":
    built = run()
    for filename, frame in built.items():
        print(f"{filename}: {len(frame):,} rows")
