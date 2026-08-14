"""
score_relevance_audit.py — implements the reporting half of docs/checklist.md
§14 (Relevance Audit انسانی), scoring the human labels collected against
build_relevance_audit_sample.py's blinded CSVs.

Joins each docs/relevance_audit/relevance_audit_{platform}_labeled.csv back
onto data/audits/relevance_audit_answer_key.csv (on sample_id) to reveal what
apply_eligibility.py actually decided for each row, then reports, per §14:

  - Precision تصمیم Inclusion: of rows the system marked Included, what
    fraction did the human call relevant? (uncertain rows counted separately,
    not as a match either way -- see NOTE below)
  - نرخ Exclusion اشتباه: of rows the system marked Excluded, what fraction
    did the human call relevant (i.e. wrongly excluded)?
  - Breakdown by query_id and by platform, per §14's "بررسی خطا به تفکیک
    Query و Source".

NOTE on `uncertain`: neither counted as a hit nor a miss in the precision /
false-exclusion rates (those are computed over relevant+not_relevant rows
only) -- folding an admitted "can't tell" into either bucket would bias the
rate in an arbitrary direction. uncertain counts and rate are reported
separately per group so they aren't silently dropped from the record.

Usage:
    python src/preprocessing/score_relevance_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
LABELED_DIR = ROOT / "docs" / "relevance_audit"
ANSWER_KEY_PATH = ROOT / "data" / "audits" / "relevance_audit_answer_key.csv"
OUTPUT_PATH = ROOT / "data" / "audits" / "relevance_audit_scored.csv"
REPORT_PATH = ROOT / "data" / "audits" / "relevance_audit_report.md"

PLATFORMS = ["x", "reddit", "youtube"]
VALID_LABELS = {"relevant", "not_relevant", "uncertain"}


def _load_labeled(platform: str) -> pd.DataFrame:
    path = LABELED_DIR / f"relevance_audit_{platform}_labeled.csv"
    if not path.exists():
        raise SystemExit(f"missing {path} — not labeled yet")
    df = pd.read_csv(path)
    bad = set(df["human_relevance"].dropna().unique()) - VALID_LABELS
    if bad:
        raise SystemExit(f"{path}: unexpected human_relevance values {bad} (expected {VALID_LABELS})")
    missing = df["human_relevance"].isna().sum()
    if missing:
        print(f"  WARNING: {path} has {missing} unlabeled row(s) — excluded from scoring")
    return df[df["human_relevance"].notna()]


def load_scored() -> pd.DataFrame:
    if not ANSWER_KEY_PATH.exists():
        raise SystemExit(f"missing {ANSWER_KEY_PATH} — run build_relevance_audit_sample.py first")
    key = pd.read_csv(ANSWER_KEY_PATH)

    labeled = pd.concat([_load_labeled(p) for p in PLATFORMS], ignore_index=True)
    merged = labeled.merge(key, on=["sample_id", "platform"], how="left", validate="one_to_one")
    unmatched = merged["eligible"].isna()
    if unmatched.any():
        raise SystemExit(
            f"{unmatched.sum()} labeled row(s) have no matching sample_id in {ANSWER_KEY_PATH} "
            "-- labeled file and answer key are out of sync"
        )
    merged["eligible"] = merged["eligible"].astype(bool)
    return merged


def _group_metrics(df: pd.DataFrame) -> dict:
    decided = df[df["human_relevance"].isin(["relevant", "not_relevant"])]
    uncertain_n = int((df["human_relevance"] == "uncertain").sum())

    included = decided[decided["eligible"]]
    excluded = decided[~decided["eligible"]]

    inclusion_precision = (
        (included["human_relevance"] == "relevant").mean() if len(included) else float("nan")
    )
    false_exclusion_rate = (
        (excluded["human_relevance"] == "relevant").mean() if len(excluded) else float("nan")
    )

    return {
        "n": len(df),
        "n_included_reviewed": len(included),
        "n_excluded_reviewed": len(excluded),
        "n_uncertain": uncertain_n,
        "inclusion_precision": inclusion_precision,
        "false_exclusion_rate": false_exclusion_rate,
    }


def build_report(scored: pd.DataFrame) -> str:
    lines = ["# Relevance Audit Report (docs/checklist.md §14)", ""]

    lines.append("## Overall")
    overall = _group_metrics(scored)
    lines.append(_metrics_block(overall))

    lines.append("## By platform")
    for platform, sub in scored.groupby("platform"):
        m = _group_metrics(sub)
        lines.append(f"### {platform}")
        lines.append(_metrics_block(m))

    lines.append("## Excluded group, by primary_exclusion_reason")
    lines.append(
        "False exclusion rate above is computed over ALL system-Excluded rows "
        "(context_only + audit_only + quarantine, i.e. every eligibility gate combined). "
        "That mixes topic-relevance failures with other gates (date window, provenance, "
        "dedup, empty text) doing their job as designed -- a record correctly dropped for "
        "being outside the project window is not a Relevance-rule bug even if a human "
        "judges its text on-topic. §14/§7 of eligibility_rules_v03.md is specifically "
        "about the Topic-relevance stage (`out_of_scope`), so that row is the one that "
        "actually indicates a Relevance-rule problem; the rest are diagnostic context."
    )
    lines.append("")
    excluded_decided = scored[(~scored["eligible"]) & scored["human_relevance"].isin(["relevant", "not_relevant"])]
    for reason, sub in excluded_decided.groupby("primary_exclusion_reason", dropna=False):
        rate = (sub["human_relevance"] == "relevant").mean()
        lines.append(f"- `{reason}`: n={len(sub)}, human-judged-relevant-anyway={_fmt(rate)}")
    lines.append("")

    lines.append("## By query_id (خطا به تفکیک Query)")
    for query_id, sub in scored.groupby("query_id", dropna=False):
        m = _group_metrics(sub)
        if m["n_included_reviewed"] + m["n_excluded_reviewed"] == 0:
            continue
        lines.append(f"- `{query_id}`: n={m['n']}, "
                      f"inclusion_precision={_fmt(m['inclusion_precision'])} "
                      f"(n={m['n_included_reviewed']}), "
                      f"false_exclusion_rate={_fmt(m['false_exclusion_rate'])} "
                      f"(n={m['n_excluded_reviewed']}), uncertain={m['n_uncertain']}")

    lines.append("")
    lines.append("## By source_id (خطا به تفکیک Source)")
    for source_id, sub in scored.groupby("source_id", dropna=False):
        m = _group_metrics(sub)
        if m["n_included_reviewed"] + m["n_excluded_reviewed"] == 0:
            continue
        lines.append(f"- `{source_id}`: n={m['n']}, "
                      f"inclusion_precision={_fmt(m['inclusion_precision'])} "
                      f"(n={m['n_included_reviewed']}), "
                      f"false_exclusion_rate={_fmt(m['false_exclusion_rate'])} "
                      f"(n={m['n_excluded_reviewed']}), uncertain={m['n_uncertain']}")

    return "\n".join(lines)


def _fmt(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:.1%}"


def _metrics_block(m: dict) -> str:
    return (
        f"- n reviewed: {m['n']}\n"
        f"- Inclusion precision: {_fmt(m['inclusion_precision'])} "
        f"(n={m['n_included_reviewed']} system-Included rows reviewed)\n"
        f"- False exclusion rate: {_fmt(m['false_exclusion_rate'])} "
        f"(n={m['n_excluded_reviewed']} system-Excluded rows reviewed)\n"
        f"- Uncertain (excluded from both rates above): {m['n_uncertain']}\n"
    )


if __name__ == "__main__":
    print("Loading labeled files + answer key...")
    scored = load_scored()

    scored.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"  scored join ({len(scored)} rows) -> {OUTPUT_PATH}")

    report = build_report(scored)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"  report -> {REPORT_PATH}")
    print()
    print(report)
