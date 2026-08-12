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
    """Build a run_id like "2026-08-12_143012" or, with a label,
    "2026-08-12_143012_scouting". Second-precision local timestamp — enough
    to tell apart separate manual runs without producing unreadable dir
    names (these run_ids are for manual pilots, not high-volume parallel
    runs, so second precision is sufficient)."""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{ts}_{label}" if label else ts


def snapshot_outputs(run_id: str, *output_paths: Path, base_dir: Path) -> Path:
    """Copy each path in output_paths into base_dir/runs/{run_id}/, keeping
    the original filename. base_dir is normally outputs/model_evaluation/.
    Returns the run directory. Paths that don't exist are skipped (a route
    may have produced no accuracy summary yet, etc.).

    If base_dir/runs/{run_id}/ already exists and is non-empty, a numeric
    suffix is appended (run_id_2, run_id_3, ...) so a colliding run_id never
    silently overwrites a previous snapshot via shutil.copy2."""
    runs_dir = base_dir / "runs"
    run_dir = runs_dir / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        suffix = 2
        while (candidate := runs_dir / f"{run_id}_{suffix}").exists() and any(candidate.iterdir()):
            suffix += 1
        run_dir = candidate
    run_dir.mkdir(parents=True, exist_ok=True)
    for path in output_paths:
        if path.exists():
            shutil.copy2(path, run_dir / path.name)
    return run_dir
