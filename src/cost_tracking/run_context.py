"""
run_context.py — run_id generation + output-snapshotting for versioned runs (Parmida)

outputs/model_evaluation/*.jsonl (sentiment_model_comparison.jsonl,
sentiment_accuracy_results.jsonl, sentiment_accuracy_summary.json, ...) live
at fixed paths that get overwritten every time run_model_comparison.py or
evaluate_sentiment_accuracy.py runs, so a pilot from last week is gone the
moment someone re-runs today. This module gives both scripts one shared way
to (a) build a sortable run_id and (b) additionally snapshot their output
file(s) under outputs/model_evaluation/runs/{run_id}/, so past runs stay
around for comparison. The original fixed-path file is still written as
before — this is additive, not a replacement.

Note: this run_id is unrelated to the per-call `run_id` string already
passed to llm_client.annotate() (e.g. "scouting_manual",
"gold_benchmark_manual"), which just tags rows in usage_log.jsonl. That
usage_log.jsonl stays append-only and untouched by this module.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def make_run_id(label: str | None = None) -> str:
    """Build a run_id like "2026-08-12_1430" or, with a label,
    "2026-08-12_1430_scouting". Minute-precision local timestamp — enough to
    tell apart separate manual runs without producing unreadable dir names."""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    return f"{ts}_{label}" if label else ts


def snapshot_outputs(run_id: str, *output_paths: Path, base_dir: Path) -> Path:
    """Copy each path in output_paths into base_dir/runs/{run_id}/, keeping
    the original filename. base_dir is normally outputs/model_evaluation/.
    Returns the run directory. Paths that don't exist are skipped (a route
    may have produced no accuracy summary yet, etc.)."""
    run_dir = base_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for path in output_paths:
        if path.exists():
            shutil.copy2(path, run_dir / path.name)
    return run_dir
