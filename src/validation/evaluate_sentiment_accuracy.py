"""
evaluate_sentiment_accuracy.py — Model Evaluation benchmark (Parmida)

Implements §23 of the assignment doc. Reads the hand-labeled Gold Sample CSV
(built by src/annotation/build_labeling_sample.py) and scores every
available model route (src/annotation/model_routes.py) against those human
labels, using the same structured §22 contract as run_model_comparison.py
(via src/annotation/llm_client.py) so the numbers here are directly
comparable to that scouting pass.

Metrics per route (§23's "حداقل Metrics" list):
  - accuracy (secondary indicator only, per the doc)
  - precision / recall / F1 per class + F1 macro          — sentiment AND stance
  - confusion matrix                                        — sentiment AND stance
  - coverage after each route's own confidence_threshold (model_routes.py)
  - cost per 1,000 records, latency per 1,000 records
  - failure rate (API/call failures), JSON parsing failure rate
  - accuracy breakdown by: language, text length bucket, human content_type,
    Stance target, and satire/quotation subset (§23's "ÙØªÙ Ø¯Ø§Ø±Ø§Û Sarcasm ÛØ§
    Quote"). NOTE: no time-window breakdown — the Gold Sample CSV (§19's
    column list) carries no timestamp; this is a known limitation, not an
    oversight, and is reported as such in the summary.

Usage:
    python src/validation/evaluate_sentiment_accuracy.py
    python src/validation/evaluate_sentiment_accuracy.py --routes groq_cheap_fast,openrouter_gemini_flash_lite

    # Cache-warming pass (no gold labels needed yet): annotate() every row of
    # the Gold Sample CSV, including still-unlabeled ones, so AnnotationCache
    # is pre-populated before human labeling finishes. No metrics are
    # computed (there's no ground truth to score against yet) — just
    # annotate success/failure counts, total cost, and latency.
    python src/validation/evaluate_sentiment_accuracy.py --warm-cache-only --routes groq_cheap_fast,groq_default
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.annotation.llm_client import AnnotationCache, annotate  # noqa: E402
from src.annotation.model_routes import MODEL_ROUTES, PROVIDERS_REQUIRING_ENV_KEY  # noqa: E402
from src.annotation.schema import SENTIMENT_LABELS, STANCE_LABELS, TARGET_IDS  # noqa: E402
from src.cost_tracking.run_context import make_run_id, snapshot_outputs  # noqa: E402

INPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
RESULTS_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_accuracy_results.jsonl"
SUMMARY_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_accuracy_summary.json"
WARM_CACHE_SUMMARY_PATH = ROOT / "outputs" / "model_evaluation" / "warm_cache_summary.json"
RUN_ID = "gold_benchmark_" + os.environ.get("EVAL_RUN_TAG", "manual")

SENTIMENT_ALIASES = {  # accept a few obvious Persian/short-hand transcription variants
    "positive": "positive", "pos": "positive", "مثبت": "positive",
    "negative": "negative", "neg": "negative", "منفی": "negative",
    "neutral": "neutral", "neu": "neutral", "خنثی": "neutral", "خنثي": "neutral",
    "mixed": "mixed", "آمیخته": "mixed",
    "unclear": "unclear", "نامشخص": "unclear",
}

TEXT_LENGTH_BUCKETS = [("short(<50)", 0, 50), ("medium(50-150)", 50, 150), ("long(>150)", 150, float("inf"))]


def normalize_sentiment(raw: str) -> str | None:
    return SENTIMENT_ALIASES.get((raw or "").strip().lower())


def load_gold_rows() -> list[dict]:
    rows = []
    skipped_no_target = 0
    with open(INPUT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sentiment = normalize_sentiment(row.get("sentiment_label", ""))
            stance = (row.get("stance_label") or "").strip().lower()
            target = (row.get("target") or "").strip()
            if not sentiment and stance not in STANCE_LABELS:
                continue  # row has neither axis labeled — nothing to score
            if stance in STANCE_LABELS and target not in TARGET_IDS:
                skipped_no_target += 1
                stance = None  # can't score stance without knowing which Target it's against
            row["_sentiment_gold"] = sentiment
            row["_stance_gold"] = stance if stance in STANCE_LABELS else None
            row["_target"] = target if target in TARGET_IDS else None
            rows.append(row)
    print(f"Loaded {len(rows)} hand-labeled rows "
          f"({skipped_no_target} had a stance_label but no valid target — stance not scored for those).")
    return rows


def load_all_rows() -> list[dict]:
    """Like load_gold_rows(), but keeps every row of the Gold Sample CSV —
    including ones with neither sentiment_label nor stance_label filled in
    yet. Used by --warm-cache-only to pre-populate AnnotationCache ahead of
    human labeling finishing, so the labeling wait isn't also an LLM-call
    wait. _sentiment_gold / _stance_gold / _target are still attached (None
    where absent) so the rest of the pipeline (annotate() call, row dict
    shape) doesn't need a separate code path."""
    rows = []
    with open(INPUT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sentiment = normalize_sentiment(row.get("sentiment_label", ""))
            stance = (row.get("stance_label") or "").strip().lower()
            target = (row.get("target") or "").strip()
            row["_sentiment_gold"] = sentiment
            row["_stance_gold"] = stance if stance in STANCE_LABELS else None
            row["_target"] = target if target in TARGET_IDS else None
            rows.append(row)
    n_labeled = sum(1 for r in rows if r["_sentiment_gold"] or r["_stance_gold"])
    print(f"Loaded {len(rows)} rows ({n_labeled} already hand-labeled, "
          f"{len(rows) - n_labeled} still unlabeled — warm-cache-only skips the label filter).")
    return rows


def text_length_bucket(text: str) -> str:
    n = len(text)
    for name, lo, hi in TEXT_LENGTH_BUCKETS:
        if lo <= n < hi:
            return name
    return TEXT_LENGTH_BUCKETS[-1][0]


# --- classification metrics (no sklearn dependency, per requirements.txt) ---

def compute_classification_metrics(pairs: list[tuple[str, str]], labels: list[str]) -> dict:
    """pairs = [(true_label, predicted_label), ...]. macro_f1 averages F1 over
    only the labels that actually appear in the gold set (labels with zero
    support are excluded, matching common practice for small unbalanced
    samples — with n~90 most label sets won't cover every category)."""
    tp, fp, fn, confusion = Counter(), Counter(), Counter(), Counter()
    for true, pred in pairs:
        confusion[(true, pred)] += 1
        if true == pred:
            tp[true] += 1
        else:
            fn[true] += 1
            fp[pred] += 1

    per_class, f1s = {}, []
    for label in labels:
        support = tp[label] + fn[label]
        precision = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) else 0.0
        recall = tp[label] / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        if support > 0:
            f1s.append(f1)

    n = len(pairs)
    return {
        "n": n,
        "accuracy": sum(tp.values()) / n if n else 0.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        "per_class": per_class,
        "confusion_matrix": {f"true={t}|pred={p}": c for (t, p), c in confusion.items()},
    }


def breakdown_accuracy(pairs_with_key: list[tuple[str, str, str]]) -> dict:
    """pairs_with_key = [(true, pred, group_key), ...] -> per-group accuracy."""
    by_group = defaultdict(lambda: {"correct": 0, "total": 0})
    for true, pred, key in pairs_with_key:
        by_group[key]["total"] += 1
        by_group[key]["correct"] += int(true == pred)
    return {
        key: {"accuracy": v["correct"] / v["total"] if v["total"] else 0.0, **v}
        for key, v in sorted(by_group.items())
    }


def score_route(rows: list[dict], route_name: str) -> dict:
    sentiment_pairs, stance_pairs = [], []
    sentiment_by_lang, sentiment_by_len, sentiment_by_ctype, sentiment_by_sarcasm = [], [], [], []
    stance_by_target = []

    n_calls = n_call_failures = n_parse_failures = n_covered = 0
    total_cost_usd, total_latency_ms, n_cost_known = 0.0, 0.0, 0

    threshold = next(r.confidence_threshold for r in MODEL_ROUTES if r.route_name == route_name)

    for row in rows:
        pred = row["_predictions"].get(route_name)
        if pred is None:
            continue
        n_calls += 1
        total_latency_ms += pred.latency_ms
        if pred.cost_usd is not None:
            total_cost_usd += pred.cost_usd
            n_cost_known += 1
        if pred.call_error is not None:
            n_call_failures += 1
            continue
        if pred.parse_error is not None or pred.validation_error is not None:
            n_parse_failures += 1
            continue

        payload = pred.payload
        is_covered = pred.confidence is not None and pred.confidence >= threshold
        n_covered += int(is_covered)

        gold_sentiment = row["_sentiment_gold"]
        if gold_sentiment and is_covered:
            sentiment_pairs.append((gold_sentiment, payload["sentiment"]))
            lang = row.get("language") or "unknown"
            sentiment_by_lang.append((gold_sentiment, payload["sentiment"], lang))
            sentiment_by_len.append((gold_sentiment, payload["sentiment"], text_length_bucket(row.get("text", ""))))
            ctype = (row.get("content_type_label") or "unknown").strip().lower()
            sentiment_by_ctype.append((gold_sentiment, payload["sentiment"], ctype or "unknown"))
            is_sarcasm_or_quote = ctype in ("satire", "quotation")
            sentiment_by_sarcasm.append((gold_sentiment, payload["sentiment"], "sarcasm_or_quote" if is_sarcasm_or_quote else "other"))

        gold_stance = row["_stance_gold"]
        if gold_stance and row["_target"] and is_covered:
            stance_pairs.append((gold_stance, payload["stance"]))
            stance_by_target.append((gold_stance, payload["stance"], row["_target"]))

    n_labeled_sentiment = sum(1 for r in rows if r["_sentiment_gold"])
    n_labeled_stance = sum(1 for r in rows if r["_stance_gold"] and r["_target"])

    return {
        "route_name": route_name,
        "confidence_threshold": threshold,
        "n_calls": n_calls,
        "failure_rate": n_call_failures / n_calls if n_calls else float("nan"),
        "json_parse_failure_rate": n_parse_failures / n_calls if n_calls else float("nan"),
        "coverage": n_covered / n_calls if n_calls else float("nan"),
        "cost_per_1000_records_usd": (total_cost_usd / n_cost_known * 1000) if n_cost_known else None,
        "latency_ms_per_1000_records": (total_latency_ms / n_calls * 1000) if n_calls else None,
        "sentiment": {
            "n_gold_labeled": n_labeled_sentiment,
            "n_scored_after_coverage": len(sentiment_pairs),
            **compute_classification_metrics(sentiment_pairs, SENTIMENT_LABELS),
            "by_language": breakdown_accuracy(sentiment_by_lang),
            "by_text_length": breakdown_accuracy(sentiment_by_len),
            "by_content_type": breakdown_accuracy(sentiment_by_ctype),
            "by_sarcasm_or_quote": breakdown_accuracy(sentiment_by_sarcasm),
        },
        "stance": {
            "n_gold_labeled": n_labeled_stance,
            "n_scored_after_coverage": len(stance_pairs),
            **compute_classification_metrics(stance_pairs, STANCE_LABELS),
            "by_target": breakdown_accuracy(stance_by_target),
        },
    }


def warm_cache_route_summary(rows: list[dict], route_name: str) -> dict:
    """Like score_route(), but with no ground truth to score against yet:
    just annotate() success/failure counts, total cost, and latency for one
    route, over whatever rows actually got a prediction attached."""
    n_calls = n_success = n_call_failures = n_parse_failures = 0
    total_cost_usd = total_latency_ms = 0.0
    n_cost_known = 0

    for row in rows:
        pred = row["_predictions"].get(route_name)
        if pred is None:
            continue
        n_calls += 1
        total_latency_ms += pred.latency_ms
        if pred.cost_usd is not None:
            total_cost_usd += pred.cost_usd
            n_cost_known += 1
        if pred.call_error is not None:
            n_call_failures += 1
            continue
        if pred.parse_error is not None or pred.validation_error is not None:
            n_parse_failures += 1
            continue
        n_success += 1

    return {
        "route_name": route_name,
        "n_calls": n_calls,
        "n_success": n_success,
        "n_call_failures": n_call_failures,
        "n_parse_failures": n_parse_failures,
        "total_cost_usd": total_cost_usd,
        "cost_per_1000_records_usd": (total_cost_usd / n_cost_known * 1000) if n_cost_known else None,
        "total_latency_ms": total_latency_ms,
        "latency_ms_per_1000_records": (total_latency_ms / n_calls * 1000) if n_calls else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", type=str, default=None,
                         help="comma-separated route_names to evaluate (default: all with a usable API key)")
    parser.add_argument("--warm-cache-only", action="store_true",
                         help="Annotate every row of the Gold Sample CSV (labeled or not) against each "
                              "selected route to pre-populate AnnotationCache, without waiting for human "
                              "labeling to finish. Skips precision/recall/F1/confusion-matrix computation "
                              "(no ground truth yet) — reports annotate success/failure counts, total "
                              "cost, and latency only. Normal (no-flag) behavior is unchanged.")
    args = parser.parse_args()

    if not INPUT_PATH.exists():
        print(f"{INPUT_PATH} not found — run src/annotation/build_labeling_sample.py first.")
        return

    if args.warm_cache_only:
        rows = load_all_rows()
    else:
        rows = load_gold_rows()
        if not rows:
            print("No labeled rows to evaluate. Fill in sentiment_label/stance_label (+ target) and re-run.")
            return

    api_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }
    wanted = set(args.routes.split(",")) if args.routes else None
    routes = []
    for route in MODEL_ROUTES:
        if wanted and route.route_name not in wanted:
            continue
        env_var = PROVIDERS_REQUIRING_ENV_KEY[route.provider]
        if not api_keys.get(env_var):
            print(f"Skipping route {route.route_name!r} ({route.provider}) — {env_var} is empty in .env.")
            continue
        routes.append(route)
    if not routes:
        print("No model routes available to evaluate.")
        return

    if args.warm_cache_only:
        print(f"[--warm-cache-only] Warming cache with {len(routes)} routes on all {len(rows)} rows "
              f"(labeled or not): {[r.route_name for r in routes]}\n")
    else:
        print(f"Evaluating {len(routes)} routes on {len(rows)} gold-labeled rows: {[r.route_name for r in routes]}\n")

    cache = AnnotationCache()
    CACHE_SAVE_EVERY = 10  # periodic flush so a crash/interrupt mid-run (e.g. a route
    # exhausting its daily quota partway through, or the process getting killed) doesn't
    # throw away every already-paid-for annotate() call — AnnotationCache used to only
    # save once at the very end of the whole loop.
    for i, row in enumerate(rows, 1):
        row["_predictions"] = {}
        target_id = row["_target"] or TARGET_IDS[0]  # rows with no valid target still get scored on sentiment
        content_id = row.get("content_id") or f"gold:{row.get('sample_id', i)}"
        for route in routes:
            row["_predictions"][route.route_name] = annotate(
                text=row["text"], target_id=target_id, route=route, api_keys=api_keys,
                cache=cache, run_id=RUN_ID, content_id=content_id,
            )
        print(f"[{i}/{len(rows)}] scored against {len(routes)} routes")
        if i % CACHE_SAVE_EVERY == 0:
            cache.save()
    cache.save()

    if args.warm_cache_only:
        warm_summary = {
            "n_rows": len(rows),
            "prompt_version": next(iter(rows[0]["_predictions"].values())).prompt_version,
            "routes": {route.route_name: warm_cache_route_summary(rows, route.route_name) for route in routes},
            "note": "Cache-warming pass only — precision/recall/F1/confusion matrix were NOT computed "
                    "(most rows have no sentiment_label/stance_label yet). Re-run without "
                    "--warm-cache-only once labeling is done to get real accuracy metrics "
                    "(cached calls made here will be reused, at no extra cost).",
        }
        WARM_CACHE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(WARM_CACHE_SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(warm_summary, f, ensure_ascii=False, indent=2)

        print(f"\n=== Cache warm-up results (n={len(rows)} rows) ===")
        total_cost = total_success = total_calls = 0.0
        for route_name, r in warm_summary["routes"].items():
            print(f"\n{route_name}:")
            print(f"  n_calls={r['n_calls']}  n_success={r['n_success']}  "
                  f"n_call_failures={r['n_call_failures']}  n_parse_failures={r['n_parse_failures']}")
            if r["cost_per_1000_records_usd"] is not None:
                print(f"  total_cost={r['total_cost_usd']:.4f} USD  cost/1000={r['cost_per_1000_records_usd']:.4f} USD  "
                      f"latency/1000={r['latency_ms_per_1000_records']/1000:.1f}s")
            total_cost += r["total_cost_usd"]
            total_success += r["n_success"]
            total_calls += r["n_calls"]
        print(f"\nTotal across {len(routes)} routes: {int(total_calls)} annotate calls, "
              f"{int(total_success)} succeeded, total_cost={total_cost:.4f} USD")
        print(f"\nWarm-cache summary: {WARM_CACHE_SUMMARY_PATH}")
        print(f"AnnotationCache updated: {cache.path}")
        return

    summary = {
        "n_gold_rows": len(rows),
        "prompt_version": next(iter(rows[0]["_predictions"].values())).prompt_version,
        "routes": {route.route_name: score_route(rows, route.route_name) for route in routes},
        "limitations": [
            "No time-window breakdown: the Gold Sample CSV carries no timestamp column (§19 schema).",
            "Small n (typically ~90 rows split across languages) — per-class and per-breakdown "
            "cells with few examples are noisy; treat splits below ~10 examples as indicative only.",
        ],
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            out = {k: v for k, v in row.items() if not k.startswith("_") or k in ("_sentiment_gold", "_stance_gold", "_target")}
            out["predictions"] = {
                name: {
                    "payload": p.payload, "confidence": p.confidence, "latency_ms": p.latency_ms,
                    "cost_usd": p.cost_usd, "call_error": p.call_error, "parse_error": p.parse_error,
                    "validation_error": p.validation_error,
                }
                for name, p in row["_predictions"].items()
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Keep this benchmark's results around under runs/{run_id}/ — RESULTS_PATH
    # and SUMMARY_PATH above are still overwritten each run (other scripts
    # read those fixed paths), this is an additive, timestamped copy for
    # comparing benchmark runs over time.
    run_id = make_run_id("gold_benchmark_" + os.environ.get("EVAL_RUN_TAG", "manual"))
    run_dir = snapshot_outputs(run_id, RESULTS_PATH, SUMMARY_PATH, base_dir=RESULTS_PATH.parent)

    print(f"\n=== Results (n={len(rows)} gold rows) ===")
    for route_name, r in summary["routes"].items():
        print(f"\n{route_name}:")
        print(f"  failure_rate={r['failure_rate']:.1%}  json_parse_failure_rate={r['json_parse_failure_rate']:.1%}  "
              f"coverage={r['coverage']:.1%} (threshold={r['confidence_threshold']})")
        if r["cost_per_1000_records_usd"] is not None:
            print(f"  cost/1000={r['cost_per_1000_records_usd']:.4f} USD  latency/1000={r['latency_ms_per_1000_records']/1000:.1f}s")
        s = r["sentiment"]
        print(f"  sentiment: accuracy={s['accuracy']:.1%} macro_f1={s['macro_f1']:.3f} "
              f"(n_scored={s['n_scored_after_coverage']}/{s['n_gold_labeled']} labeled)")
        for lang, v in s["by_language"].items():
            print(f"     by_language[{lang}]: {v['accuracy']:.1%} ({v['correct']}/{v['total']})")
        t = r["stance"]
        if t["n_gold_labeled"]:
            print(f"  stance: accuracy={t['accuracy']:.1%} macro_f1={t['macro_f1']:.3f} "
                  f"(n_scored={t['n_scored_after_coverage']}/{t['n_gold_labeled']} labeled)")
        else:
            print("  stance: no gold-labeled rows with a valid target yet.")

    print(f"\nDetailed per-row results: {RESULTS_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    print(f"Versioned copies: {run_dir}")


if __name__ == "__main__":
    main()
