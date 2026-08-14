"""
run_pipeline.py -- single entry point for BOTH pipelines (docs/how_to_run_
pipeline_fa.md's Pipeline A and Pipeline B), matching GIT_WORKFLOW.md
section 7's ask for a scripted, config-driven pipeline runner instead of
every step being typed by hand.

This file does not contain any pipeline LOGIC of its own -- it only runs the
existing, already-reviewed scripts in the right order, the same way you'd
type each command yourself. Nothing about those scripts is changed by this
file existing or running.

Runs, in order, everything from "raw data already on disk under data/raw/"
through Pipeline A's bridge, then straight into Pipeline B's analysis
scripts on the file that bridge just produced
(data/processed/annotated_dataset.parquet) -- the two pipelines are chained,
not just each individually runnable:

  Pipeline A:
    [optional, --with-ingestion] youtube_extract.py (live collector) +
                                      handoff_csv_to_record.py for reddit and
                                      x (--reddit-handoff-file/--x-handoff-file
                                      override which delivered file to read;
                                      default to the files currently on disk)
    backfill_raw_harmonized_v05.py   raw_harmonized layer, all 3 platforms
    apply_eligibility.py             filter/dedup/provenance -> data/interim/*
    normalize_text.py                text_normalized + PII masking, in place
    duplicate_analysis.py            near-duplicate clustering, in place
    [optional, --with-profiling] profile_platform.py x3 + quality_grade.py
                                      + sync_query_execution_audit.py x3
    [optional, --with-financial] finance_market_extract.py + build_financial_outputs.py
                                      (financial market data -- hits FRED/Yahoo)
    [optional, --with-annotation] run_full_annotation.py -- real LLM API
                                      cost, hard-capped at $100 (must match
                                      docs/decision_log.md's approved cap,
                                      enforced by the script itself, not by
                                      this orchestrator); --annotation-targets/
                                      --annotation-limit/--annotation-stratify-cap/
                                      --annotation-workers pass through
    build_annotated_dataset.py       Pipeline A -> B bridge (does NOT require
                                      annotation to be done first -- rows not
                                      yet annotated get
                                      annotation_status="pending_annotation",
                                      see that script's own docstring)

  Pipeline B (always runs after the bridge, on the file it just wrote):
    descriptive_stats.py, weekly_trend.py, composition_shift.py,
    group_comparison.py, sensitivity_analysis.py, event_study.py,
    build_social_weekly_outcomes.py -- all pure local computation on
    annotated_dataset.parquet, no external API, so no gate needed.
    [optional, --with-notebooks] re-executes the financial-alignment
    notebook and the three demo/presentation notebooks (05/06/07) via
    nbconvert -- off by default because nbconvert is slower and rewrites
    the .ipynb files in place (more invasive than a plain script run).

Deliberately NOT included here at all, gated or otherwise:
  - Gold Sample labeling (build_labeling_sample.py + two humans labeling by
    hand + compute_annotator_agreement.py/evaluate_sentiment_accuracy.py) --
    needs actual people, not a script.

x/reddit handoff ingestion (handoff_csv_to_record.py) and full LLM annotation
(run_full_annotation.py) ARE included, both behind their own gate
(--with-ingestion and --with-annotation respectively) since they can't run
themselves -- ingestion needs an explicit file path (defaulted to whichever
handoff file is currently on disk, override with --x-handoff-file/
--reddit-handoff-file when a new one arrives) and annotation spends real
money (hard-capped at $100, matching docs/decision_log.md's approved cap;
run_full_annotation.py itself refuses to run if that cap isn't also logged
there, independent of anything this script does).

Financial market data (finance_market_extract.py + build_financial_outputs.py)
is intentionally NOT mentioned in docs/how_to_run_pipeline_fa.md at all --
per docs/decision_log.md 2026-08-13, it's designed to be collected once and
frozen (data/interim/financial/frozen_inputs/) specifically so routine
pipeline runs don't have to re-hit FRED/Yahoo every time. It's included
here behind its own gate (--with-financial, off by default) for the times
you DO want to refresh it.

Each step below is a subprocess: exactly the same command docs/how_to_run_
pipeline_fa.md lists, run with the current Python interpreter and the
project root as the working directory. The run stops at the first failing
step (fail-fast) -- every step consumes the previous step's output, so
continuing past a failure would just process broken/partial data -- and
prints a clear summary of what ran, what was skipped, and where it stopped.

Usage:
    python src/pipeline/run_pipeline.py
    python src/pipeline/run_pipeline.py --with-ingestion    # also runs the
                                                             # live YouTube
                                                             # collector
    python src/pipeline/run_pipeline.py --with-profiling    # also rebuilds
                                                             # Inventory/
                                                             # Coverage docs
    python src/pipeline/run_pipeline.py --with-financial    # also refreshes
                                                             # financial data
                                                             # (FRED/Yahoo)
    python src/pipeline/run_pipeline.py --with-notebooks    # also re-executes
                                                             # the analysis/demo
                                                             # notebooks
    python src/pipeline/run_pipeline.py --with-annotation   # also runs real
                                                             # LLM annotation
                                                             # (real $, capped)
    python src/pipeline/run_pipeline.py --with-annotation --annotation-limit 10
                                                             # cheap smoke test
    python src/pipeline/run_pipeline.py --skip normalize_text,duplicate_analysis
    python src/pipeline/run_pipeline.py --list               # show the plan,
                                                               # run nothing
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Defaults matching docs/how_to_run_pipeline_fa.md's documented handoff
# commands -- these are the actual files currently on disk. --x-handoff-file/
# --reddit-handoff-file override them for whenever a NEW handoff file with a
# different name arrives; there's no way to auto-detect "the latest one" so
# a stale-but-explicit default beats guessing.
DEFAULT_X_HANDOFF = "data/raw_original/x/records/X_Scraper_v4_7_Target20K_Current.xlsx"
DEFAULT_REDDIT_HANDOFF = "data/raw_original/reddit/records/reddit_raw_schema.csv"

# Must match run_full_annotation.py's own APPROVED_COST_CAP_USD, which that
# script cross-checks against a dated docs/decision_log.md entry itself --
# this constant doesn't grant any trust on its own, it just has to agree
# with the number typed there (docs/decision_log.md 2026-08-14: $100).
APPROVED_ANNOTATION_COST_CAP_USD = 100.0


@dataclass
class Step:
    name: str  # short id, used with --skip
    description: str
    # Either a fixed argv list, or a function of the parsed args (for steps
    # whose command depends on a CLI flag, e.g. which handoff file to read) --
    # argv[0] is always sys.executable.
    argv: list[str] | Callable[[argparse.Namespace], list[str]]
    gate: str | None = None  # None = always runs; else the --with-* flag name that must be set


def _resolve_argv(step: Step, args: argparse.Namespace) -> list[str]:
    return step.argv(args) if callable(step.argv) else step.argv


def _step_argv(script_relpath: str, extra: list[str] | None = None) -> list[str]:
    return [sys.executable, script_relpath, *(extra or [])]


def _module_argv(module_path: str, extra: list[str] | None = None) -> list[str]:
    """For scripts meant to run as `python -m pkg.module` (no sys.path
    trickery of their own -- e.g. build_financial_outputs.py, unlike the
    src/ingestion/*.py scripts above which do their own sys.path.insert and
    are invoked as plain file paths instead)."""
    return [sys.executable, "-m", module_path, *(extra or [])]


def _notebook_argv(notebook_relpath: str) -> list[str]:
    """Matches docs/how_to_run_pipeline_fa.md's nbconvert invocation exactly:
    executes the notebook and writes the outputs back into the same file
    (--inplace) -- this is why notebook steps live behind --with-notebooks
    rather than always running, unlike the plain-script Pipeline B steps."""
    return [sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace", notebook_relpath]


def _reddit_ingestion_argv(args: argparse.Namespace) -> list[str]:
    return _step_argv("src/ingestion/handoff_csv_to_record.py", [
        "--input", args.reddit_handoff_file, "--platform", "reddit",
    ])


def _x_ingestion_argv(args: argparse.Namespace) -> list[str]:
    return _step_argv("src/ingestion/handoff_csv_to_record.py", [
        "--input", args.x_handoff_file, "--sheet", args.x_handoff_sheet, "--platform", "x",
    ])


def _annotation_argv(args: argparse.Namespace) -> list[str]:
    argv = [
        "--confirm-cost-cap", str(APPROVED_ANNOTATION_COST_CAP_USD),
        "--targets", args.annotation_targets,
        "--workers", str(args.annotation_workers),
    ]
    if args.annotation_limit is not None:
        argv += ["--limit", str(args.annotation_limit)]
    if args.annotation_stratify_cap is not None:
        argv += ["--stratify-cap", str(args.annotation_stratify_cap)]
    return _step_argv("src/annotation/run_full_annotation.py", argv)


ANNOTATED_DATASET = "data/processed/annotated_dataset.parquet"


STEPS: list[Step] = [
    Step(
        "youtube_ingestion",
        "Live YouTube collector (youtube_extract.py) -- consumes real API quota",
        _step_argv("src/ingestion/youtube_extract.py"),
        gate="with_ingestion",
    ),
    Step(
        "reddit_ingestion",
        "Convert the Reddit handoff file to Record shape (handoff_csv_to_record.py --platform reddit)",
        _reddit_ingestion_argv,
        gate="with_ingestion",
    ),
    Step(
        "x_ingestion",
        "Convert the X handoff file to Record shape (handoff_csv_to_record.py --platform x)",
        _x_ingestion_argv,
        gate="with_ingestion",
    ),
    Step(
        "harmonize",
        "Build raw_harmonized layer for all 3 platforms (backfill_raw_harmonized_v05.py)",
        _step_argv("src/ingestion/backfill_raw_harmonized_v05.py"),
    ),
    Step(
        "eligibility",
        "Filter/dedup/provenance -> data/interim/{opinion_main,opinion_limited,...}.parquet (apply_eligibility.py)",
        _step_argv("src/preprocessing/apply_eligibility.py"),
    ),
    Step(
        "normalize_text",
        "Text normalization + URL/hashtag/emoji extraction + PII masking, in place (normalize_text.py)",
        _step_argv("src/preprocessing/normalize_text.py"),
    ),
    Step(
        "duplicate_analysis",
        "Near-duplicate text clustering, in place (duplicate_analysis.py)",
        _step_argv("src/preprocessing/duplicate_analysis.py"),
    ),
    Step(
        "profile_x",
        "Rebuild X inventory/coverage (profile_platform.py --platform x)",
        _step_argv("src/intake/profile_platform.py", ["--platform", "x"]),
        gate="with_profiling",
    ),
    Step(
        "profile_reddit",
        "Rebuild Reddit inventory/coverage (profile_platform.py --platform reddit)",
        _step_argv("src/intake/profile_platform.py", ["--platform", "reddit"]),
        gate="with_profiling",
    ),
    Step(
        "profile_youtube",
        "Rebuild YouTube inventory/coverage (profile_platform.py --platform youtube)",
        _step_argv("src/intake/profile_platform.py", ["--platform", "youtube"]),
        gate="with_profiling",
    ),
    Step(
        "quality_grade",
        "Recompute docs/collection_coverage.csv quality grades (quality_grade.py --apply)",
        _step_argv("src/intake/quality_grade.py", ["--apply"]),
        gate="with_profiling",
    ),
    Step(
        "finance_extract",
        "Collect/refresh financial market data (finance_market_extract.py) -- hits FRED/Yahoo APIs",
        _module_argv("src.ingestion.finance_market_extract"),
        gate="with_financial",
    ),
    Step(
        "finance_build_outputs",
        "Build frozen, analysis-ready financial tables (build_financial_outputs.py)",
        _module_argv("src.temporal_analysis.build_financial_outputs"),
        gate="with_financial",
    ),
    Step(
        "annotation",
        "Full-dataset LLM annotation (run_full_annotation.py) -- real API cost, capped at "
        f"${APPROVED_ANNOTATION_COST_CAP_USD} per docs/decision_log.md 2026-08-14",
        _annotation_argv,
        gate="with_annotation",
    ),
    Step(
        "bridge",
        "Join eligibility output with annotation output -> data/processed/annotated_dataset.parquet (build_annotated_dataset.py)",
        _step_argv("src/annotation/build_annotated_dataset.py"),
    ),

    # --- Pipeline B (docs/how_to_run_pipeline_fa.md's Pipeline B section) ---
    # All of these are pure local computation over ANNOTATED_DATASET -- no
    # external API, nothing paid, nothing that needs a human -- so unlike
    # Pipeline A's optional steps above, none of these are gated.
    Step(
        "descriptive_stats",
        "Descriptive statistics (descriptive_stats.py)",
        _module_argv("src.temporal_analysis.descriptive_stats", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "weekly_trend",
        "Weekly sentiment trend (weekly_trend.py)",
        _module_argv("src.temporal_analysis.weekly_trend", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "composition_shift",
        "Composition shift analysis (composition_shift.py)",
        _module_argv("src.temporal_analysis.composition_shift", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "group_comparison",
        "Group comparison analysis (group_comparison.py)",
        _module_argv("src.temporal_analysis.group_comparison", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "sensitivity_analysis",
        "Sensitivity analysis, min. 6 comparisons (sensitivity_analysis.py)",
        _module_argv("src.temporal_analysis.sensitivity_analysis", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "event_study",
        "Event study on event_registry.py's pre-registered events (event_study.py)",
        _module_argv("src.event_analysis.event_study", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "social_weekly_outcomes",
        "Weekly social-sentiment outcomes table for financial alignment (build_social_weekly_outcomes.py)",
        _module_argv("src.temporal_analysis.build_social_weekly_outcomes", ["--input", ANNOTATED_DATASET]),
    ),
    Step(
        "notebook_financial_alignment",
        "Re-execute the financial/social alignment notebook (needs frozen financial inputs on disk already)",
        _notebook_argv("notebooks/financial/02_financial_social_alignment.ipynb"),
        gate="with_notebooks",
    ),
    Step(
        "notebook_05",
        "Re-execute notebooks/05_descriptive_and_temporal_analysis.ipynb (demo/presentation)",
        _notebook_argv("notebooks/05_descriptive_and_temporal_analysis.ipynb"),
        gate="with_notebooks",
    ),
    Step(
        "notebook_06",
        "Re-execute notebooks/06_event_and_financial_analysis.ipynb (demo/presentation)",
        _notebook_argv("notebooks/06_event_and_financial_analysis.ipynb"),
        gate="with_notebooks",
    ),
    Step(
        "notebook_07",
        "Re-execute notebooks/07_sensitivity_and_final_claims.ipynb (demo/presentation)",
        _notebook_argv("notebooks/07_sensitivity_and_final_claims.ipynb"),
        gate="with_notebooks",
    ),
]


def _print_plan(steps: list[Step], args: argparse.Namespace) -> None:
    print("Pipeline A + Pipeline B plan (docs/how_to_run_pipeline_fa.md):")
    for i, step in enumerate(steps, start=1):
        gated = step.gate is not None
        will_run = (not gated) or getattr(args, step.gate)
        skipped_by_flag = step.name in args.skip
        status = "RUN" if (will_run and not skipped_by_flag) else "skip"
        reason = ""
        if skipped_by_flag:
            reason = " (--skip)"
        elif gated and not will_run:
            reason = f" (needs --{step.gate.replace('_', '-')})"
        print(f"  {i:>2}. [{status:<4}] {step.name:<18} {step.description}{reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--with-ingestion", action="store_true",
        help="Also run the live YouTube collector first. Off by default: it calls a real API with a "
             "daily quota budget, so it should only run when you actually mean to collect new data.",
    )
    parser.add_argument(
        "--with-profiling", action="store_true",
        help="Also rebuild per-platform inventory/coverage docs (docs/collection_coverage.csv and friends). "
             "Off by default per docs/how_to_run_pipeline_fa.md: only needed when new raw data arrived.",
    )
    parser.add_argument(
        "--with-financial", action="store_true",
        help="Also refresh financial market data (finance_market_extract.py + build_financial_outputs.py). "
             "Off by default: it's designed to be collected once and frozen "
             "(data/interim/financial/frozen_inputs/, docs/decision_log.md 2026-08-13), "
             "and hits FRED/Yahoo when it does run.",
    )
    parser.add_argument(
        "--with-notebooks", action="store_true",
        help="Also re-execute the financial-alignment notebook and the 3 demo/presentation notebooks "
             "(05/06/07) via nbconvert. Off by default: slower, and rewrites the .ipynb files in place.",
    )
    parser.add_argument(
        "--with-annotation", action="store_true",
        help="Also run real LLM annotation (run_full_annotation.py) before the bridge step. Off by "
             f"default: real API cost, hard-capped at ${APPROVED_ANNOTATION_COST_CAP_USD} "
             "(docs/decision_log.md 2026-08-14) -- the underlying script enforces this cap itself.",
    )
    parser.add_argument(
        "--x-handoff-file", default=DEFAULT_X_HANDOFF, metavar="PATH",
        help=f"X handoff file for --with-ingestion's x_ingestion step (default: {DEFAULT_X_HANDOFF}).",
    )
    parser.add_argument(
        "--x-handoff-sheet", default="Raw_Tweets", metavar="SHEET",
        help="Worksheet name within --x-handoff-file (default: Raw_Tweets).",
    )
    parser.add_argument(
        "--reddit-handoff-file", default=DEFAULT_REDDIT_HANDOFF, metavar="PATH",
        help=f"Reddit handoff file for --with-ingestion's reddit_ingestion step (default: {DEFAULT_REDDIT_HANDOFF}).",
    )
    parser.add_argument(
        "--annotation-targets", default="T01", metavar="T01[,T02,T03]",
        help="Passed through to run_full_annotation.py --targets. Default T01 (cheapest); "
             "T01,T02,T03 is full primary-Target coverage at ~3x the cost.",
    )
    parser.add_argument(
        "--annotation-limit", type=int, default=None, metavar="N",
        help="Passed through to run_full_annotation.py --limit -- only process the first N tasks "
             "(cheap smoke-testing, e.g. --annotation-limit 10). Omit for the full eligible set.",
    )
    parser.add_argument(
        "--annotation-stratify-cap", type=int, default=None, metavar="N",
        help="Passed through to run_full_annotation.py --stratify-cap (cap per platform/week cell).",
    )
    parser.add_argument(
        "--annotation-workers", type=int, default=20, metavar="N",
        help="Passed through to run_full_annotation.py --workers (concurrent threads). Default 20.",
    )
    parser.add_argument(
        "--skip", default="", metavar="NAME[,NAME...]",
        help="Comma-separated step names to skip even if their gate flag is on (see --list for names).",
    )
    parser.add_argument("--list", action="store_true", help="Print the plan and exit; run nothing.")
    args = parser.parse_args(argv)
    args.skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    unknown_skip = args.skip - {s.name for s in STEPS}
    if unknown_skip:
        parser.error(f"--skip: unknown step name(s): {', '.join(sorted(unknown_skip))}")

    _print_plan(STEPS, args)
    if args.list:
        return 0

    print()
    results: list[tuple[Step, str, float]] = []  # (step, status, seconds)
    overall_start = time.monotonic()

    for step in STEPS:
        if step.gate is not None and not getattr(args, step.gate):
            results.append((step, "skipped (gate off)", 0.0))
            continue
        if step.name in args.skip:
            results.append((step, "skipped (--skip)", 0.0))
            continue

        argv = _resolve_argv(step, args)
        print("=" * 72)
        print(f"Step: {step.name} -- {step.description}")
        print(f"$ {' '.join(argv)}")
        print("=" * 72)
        start = time.monotonic()
        proc = subprocess.run(argv, cwd=PROJECT_ROOT)
        elapsed = time.monotonic() - start

        if proc.returncode != 0:
            results.append((step, f"FAILED (exit {proc.returncode})", elapsed))
            _print_summary(results, time.monotonic() - overall_start)
            print(f"\nStopping: step '{step.name}' failed. Fix it and re-run "
                  f"(re-running the whole pipeline is safe -- every step is idempotent).")
            return 1

        results.append((step, "ok", elapsed))
        print(f"-- {step.name} done in {elapsed:.1f}s\n")

    _print_summary(results, time.monotonic() - overall_start)
    print("\nPipeline A + Pipeline B complete. Outputs are in outputs/tables/ "
          "(and outputs/tables/event_analysis/, outputs/tables/financial/), "
          "as described in docs/handoff_notes_fa.md.")
    return 0


def _print_summary(results: list[tuple[Step, str, float]], total_elapsed: float) -> None:
    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    for step, status, elapsed in results:
        time_str = f"{elapsed:.1f}s" if elapsed else "-"
        print(f"  {step.name:<18} {status:<24} {time_str}")
    print(f"  total: {total_elapsed:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
