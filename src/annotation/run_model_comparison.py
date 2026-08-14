"""
run_model_comparison.py — multi-provider, multi-label model scouting (Parmida)

Replaces compare_llm_sentiment.py. Runs a small sample of comments through
every configured ModelRoute (src/annotation/model_routes.py) side by side,
using the full §22 structured-output contract (sentiment + stance + emotion +
content_type, not just sentiment), so the team can eyeball which
model/provider handles Persian/English annotation better — and see cost and
latency per route — before committing to a route for the real Gold Sample
benchmark (evaluate_sentiment_accuracy.py).

This is still a QUALITATIVE scouting pass (no human ground truth here). For
the actual accuracy benchmark, hand-label the Gold Sample CSV first, then run
evaluate_sentiment_accuracy.py.

Usage:
    python src/annotation/run_model_comparison.py
    python src/annotation/run_model_comparison.py --sample-size 30
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.annotation.llm_client import AnnotationCache, annotate  # noqa: E402
from src.annotation.model_routes import MODEL_ROUTES, PROVIDERS_REQUIRING_ENV_KEY  # noqa: E402
from src.annotation.schema import TARGET_IDS  # noqa: E402
from src.common.jsonl_io import DEFAULT_RAW_GLOBS, load_source_records  # noqa: E402
from src.cost_tracking.run_context import make_run_id, snapshot_outputs  # noqa: E402

CLEAN_PATH = ROOT / "data" / "interim" / "clean.jsonl"
# Same raw-fallback source list as estimate_full_run_cost.py's RAW_GLOBS —
# see src/common/jsonl_io.py's DEFAULT_RAW_GLOBS docstring for why this
# includes both YouTube and Reddit rather than YouTube only.
RAW_GLOBS = DEFAULT_RAW_GLOBS
OUTPUT_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_model_comparison.jsonl"

DEFAULT_SAMPLE_SIZE = 20
RANDOM_SEED = 42
RUN_ID = "scouting_" + os.environ.get("COMPARISON_RUN_TAG", "manual")


def load_sample(n: int) -> list[dict]:
    records = load_source_records(CLEAN_PATH, RAW_GLOBS)
    records = [r for r in records if (r.get("text") or "").strip()]
    random.seed(RANDOM_SEED)
    fa = [r for r in records if r.get("language") == "fa"]
    en = [r for r in records if r.get("language") == "en"]
    random.shuffle(fa)
    random.shuffle(en)
    half = n // 2
    sample = fa[:half] + en[:n - half]
    random.shuffle(sample)
    return sample


def available_routes(api_keys: dict[str, str]) -> list:
    routes = []
    for route in MODEL_ROUTES:
        env_var = PROVIDERS_REQUIRING_ENV_KEY[route.provider]
        if not api_keys.get(env_var):
            print(f"Skipping route {route.route_name!r} ({route.provider}) — {env_var} is empty in .env.")
            continue
        routes.append(route)
    return routes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    args = parser.parse_args()

    api_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }
    routes = available_routes(api_keys)
    if not routes:
        print("No model routes have a usable API key in .env — nothing to compare.")
        return

    sample = load_sample(args.sample_size)
    if not sample:
        print(f"No records found in {CLEAN_PATH} or {RAW_GLOBS} — run extraction first.")
        return

    print(f"Comparing {len(routes)} routes on {len(sample)} comments: "
          f"{[r.route_name for r in routes]}\n")

    cache = AnnotationCache()
    results = []
    sentiment_agreement_counter = Counter()

    for i, record in enumerate(sample, 1):
        text = record["text"]
        lang = record.get("language")
        content_id = record.get("content_id") or f"scouting:{i}"
        target_id = TARGET_IDS[i % len(TARGET_IDS)]  # rotate targets for coverage variety

        print(f"[{i}/{len(sample)}] ({lang}, target={target_id}) {text[:70]!r}")
        per_route = {}
        for route in routes:
            result = annotate(
                text=text, target_id=target_id, route=route, api_keys=api_keys,
                cache=cache, run_id=RUN_ID, content_id=content_id,
            )
            per_route[route.route_name] = result
            if result.ok:
                p = result.payload
                cost_str = f"${result.cost_usd:.6f}" if result.cost_usd is not None else "cost=?"
                print(f"   {route.route_name:28s} sentiment={p['sentiment']:9s} stance={p['stance']:20s} "
                      f"emotion={p['emotion']:9s} type={p['content_type']:17s} conf={p['confidence']:.2f} "
                      f"{result.latency_ms:6.0f}ms {cost_str}"
                      + (" [cache]" if result.from_cache else ""))
            else:
                reason = result.call_error or result.parse_error or result.validation_error
                print(f"   {route.route_name:28s} FAILED — {reason}")

        sentiments = [r.payload["sentiment"] for r in per_route.values() if r.ok]
        if len(set(sentiments)) == 1 and sentiments:
            sentiment_agreement_counter["all_agree"] += 1
        elif sentiments:
            sentiment_agreement_counter["disagree"] += 1
        print()

        results.append({
            "content_id": content_id,
            "text": text,
            "language": lang,
            "target": target_id,
            "routes": {
                name: {
                    "payload": r.payload,
                    "latency_ms": r.latency_ms,
                    "cost_usd": r.cost_usd,
                    "from_cache": r.from_cache,
                    "call_error": r.call_error,
                    "parse_error": r.parse_error,
                    "validation_error": r.validation_error,
                }
                for name, r in per_route.items()
            },
        })

    cache.save()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Keep this pilot's results around under runs/{run_id}/ — OUTPUT_PATH
    # above is still overwritten each run (other scripts read that fixed
    # path), this is an additive, timestamped copy for comparing pilots.
    run_id = make_run_id("scouting_" + os.environ.get("COMPARISON_RUN_TAG", "manual"))
    run_dir = snapshot_outputs(run_id, OUTPUT_PATH, base_dir=OUTPUT_PATH.parent)

    total_compared = sum(sentiment_agreement_counter.values())
    if total_compared:
        agree_rate = sentiment_agreement_counter["all_agree"] / total_compared
        print(f"All-route sentiment agreement: {agree_rate:.0%} ({sentiment_agreement_counter['all_agree']}/{total_compared})")
    print(f"Full results written to {OUTPUT_PATH}")
    print(f"Versioned copy: {run_dir / OUTPUT_PATH.name}")
    print(f"Usage/cost log: outputs/model_evaluation/usage_log.jsonl")
    print("\nThis is a scouting pass, not accuracy — it has no human ground truth. "
          "Run evaluate_sentiment_accuracy.py against the hand-labeled Gold Sample for real accuracy numbers.")


if __name__ == "__main__":
    main()
