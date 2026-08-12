# outputs/model_evaluation/runs/

`outputs/model_evaluation/*.jsonl` and `*.json` (e.g.
`sentiment_model_comparison.jsonl`, `sentiment_accuracy_results.jsonl`,
`sentiment_accuracy_summary.json`) are fixed paths — every run of
`run_model_comparison.py` or `evaluate_sentiment_accuracy.py` overwrites
them, and other scripts read those fixed paths, so they have to stay that
way. That means the *last* run is always available, but a pilot from last
week is gone the moment someone re-runs today.

This folder is where past runs are kept instead of lost. Each run gets its
own subfolder named by `run_id` (built by
[`src/cost_tracking/run_context.py`](../../../src/cost_tracking/run_context.py)):

```
runs/
  2026-08-12_1430_scouting_manual/
    sentiment_model_comparison.jsonl
  2026-08-13_0915_gold_benchmark_manual/
    sentiment_accuracy_results.jsonl
    sentiment_accuracy_summary.json
```

`{timestamp}_{label}` — timestamp is minute-precision local time, label is
`scouting_<COMPARISON_RUN_TAG>` for `run_model_comparison.py` or
`gold_benchmark_<EVAL_RUN_TAG>` for `evaluate_sentiment_accuracy.py` (default
tag is `manual` if the env var isn't set).

## What this is for

Comparing pilots **over time** — which route was tried on which day, and
what it scored — not just looking at the latest run. Before this existed,
re-running either script silently destroyed the previous run's numbers, so
there was no way to answer "did switching routes on the 12th actually help?"
without having saved a copy by hand.

Each subfolder is a self-contained snapshot of that run's output file(s), so
you can diff, `jq` over, or load any two run folders side by side.

## What this is *not*

- Not a replacement for the fixed-path files at `outputs/model_evaluation/*`
  — those are still written on every run and are what other scripts/notebooks
  should keep reading.
- Not where `usage_log.jsonl` lives — that file is already append-only
  (every call is appended, never overwritten), so it already has full
  history across all runs and doesn't need per-run copies here.
- Not automatically pruned. If this grows large, it's safe to delete old
  run folders you no longer need — nothing reads from `runs/` except a human
  doing a comparison.
