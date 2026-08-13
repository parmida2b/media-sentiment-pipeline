"""
estimate_full_run_cost.py — pre-Full-run cost/latency estimator (Parmida)

Pure ESTIMATION script for the "سقف هزینه و زمان اجرا" gate that
src/annotation/run_full_annotation.py refuses to run without (see that
file's docstring and docs/pre_analysis_decision_table_v1.md's row "سقف
هزینه و زمان اجرا": "پیش از Full run، سقف عددی هزینه و زمان بر اساس حجم
داده و Pilot در Decision Log تأیید می‌شود؛ تا آن زمان Full run مجاز
نیست"). This script makes NO real API calls — it counts records, estimates
token counts, and multiplies by the documented per-token prices in
src/annotation/model_routes.py's MODEL_ROUTES, producing one estimate PER
available route (not just one) so the team has real numbers to pick a cap
from instead of guessing.

What "eligible" means here
---------------------------
This reuses the same lightweight, already-established filter
run_model_comparison.load_sample() uses for its scouting sample — a
non-empty `text` field, on whichever data source is currently the best one
available — NOT the full 6-bucket decision made by
src/preprocessing/apply_eligibility.py (docs/eligibility_rules_v03.md),
which runs on a different, not-yet-fully-populated input
(data/raw_harmonized/{platform}/*.parquet) and produces
opinion_main/opinion_limited/opinion_untimed/context_only/audit_only/
quarantine. If/when that pipeline's output becomes the standing source of
truth for what actually gets annotated, point this script at
data/interim/opinion_main.parquet (+ opinion_limited/opinion_untimed)
instead — that swap is a follow-up, not done here. Until then, the
"eligible" count below is a same-order-of-magnitude estimate, not the
audited Eligible Sample count §12 of the doc requires for the real Gold
Sample / Full run.

Data source (same fallback order and, as of this change, the same raw_globs
list as run_model_comparison.load_sample — both now go through
src/common/jsonl_io.py's load_source_records() / DEFAULT_RAW_GLOBS so the
two scripts can't silently diverge on which population they're reading
again):
  1. data/interim/clean.jsonl, if it exists
  2. else data/raw/*/youtube_comments*.jsonl
     + data/raw/reddit/reddit_comments*.jsonl (per src/ingestion/
       reddit_to_record.py's fixed, non-topic-scoped output path — matches
       zero files today, picked up automatically once Reddit data lands
       there)

Token estimation
-----------------
- Per-call INPUT tokens = tokens of the actual prompt that would be sent —
  prompt_contract.build_prompt(text, target) — not just the raw comment,
  since the label-definition/instruction template is real billed input too.
- Uses `tiktoken` (cl100k_base) for a real BPE token count on a random
  sample of prompts if the library is installed; otherwise falls back to
  the simple 4-characters≈1-token heuristic the task specified.
- Per-call OUTPUT tokens: the REAL average `output_tokens` logged for that
  specific route in outputs/model_evaluation/usage_log.jsonl, if at least
  MIN_SAMPLES_FOR_ROUTE successful (call_error is None) calls with token
  counts exist for it; else the real average across ALL routes' successful
  calls (cross-route fallback — lower confidence, flagged in the output);
  else a fixed structural estimate from one example §22 JSON contract
  payload (lowest confidence, also flagged).

Latency estimation follows the same route → cross-route → structural
fallback chain, per the task's "بر اساس میانگین‌های واقعی ثبت‌شده در
usage_log.jsonl اگر داده کافی برای آن route وجود دارد". The total is
SEQUENTIAL wall-clock (no concurrency) — a worst-case upper bound, noted in
the output; a real run would likely batch/parallelize across routes/keys.

Output:
  - a route | est. cost | est. time table printed to the terminal
  - outputs/model_evaluation/full_run_cost_estimate.json (full detail)
  - a ready-to-paste docs/decision_log.md row (the team only has to pick and
    confirm one of the printed caps)

Usage:
    python src/cost_tracking/estimate_full_run_cost.py
"""

from __future__ import annotations

import glob
import json
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.annotation.model_routes import MODEL_ROUTES, estimate_cost_usd  # noqa: E402
from src.annotation.prompt_contract import build_prompt  # noqa: E402
from src.annotation.schema import TARGET_IDS  # noqa: E402
from src.common.jsonl_io import DEFAULT_RAW_GLOBS, load_source_records  # noqa: E402

CLEAN_PATH = ROOT / "data" / "interim" / "clean.jsonl"
# Same raw-fallback source list as run_model_comparison.py's RAW_GLOBS — see
# src/common/jsonl_io.py's DEFAULT_RAW_GLOBS docstring for why this includes
# both YouTube and Reddit rather than YouTube only, and why the Reddit
# pattern points at the fixed data/raw/reddit/ dir (not a topic-scoped one).
RAW_GLOBS = DEFAULT_RAW_GLOBS
USAGE_LOG_PATH = ROOT / "outputs" / "model_evaluation" / "usage_log.jsonl"
OUTPUT_PATH = ROOT / "outputs" / "model_evaluation" / "full_run_cost_estimate.json"

RANDOM_SEED = 42
TOKENIZER_SAMPLE_SIZE = 500  # prompts sampled to get a chars->token ratio
MIN_SAMPLES_FOR_ROUTE = 3  # usage_log rows needed before trusting a route's own average

# Structural fallback for output tokens when usage_log has nothing usable at
# all — one plausible, fully-filled §22 JSON contract payload.
_EXAMPLE_OUTPUT_JSON = (
    '{"sentiment": "negative", "stance": "oppose", "emotion": "anger", '
    '"content_type": "personal_opinion", "confidence": 0.82, '
    '"reason_code": "explicit_opposition_phrase"}'
)

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _ENCODING = None


def _count_tokens(text: str) -> int:
    """Real BPE token count via tiktoken if available, else the task's
    4-characters≈1-token heuristic."""
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    return max(1, len(text) // 4)


def tokenizer_label() -> str:
    return "tiktoken(cl100k_base)" if _ENCODING is not None else "heuristic_4_chars_per_token"


# --- step 1: load eligible records -------------------------------------------

def load_eligible_texts() -> tuple[list[str], dict]:
    """Returns (list of eligible texts, source-description dict). Mirrors
    run_model_comparison.load_sample()'s source selection and eligibility
    filter, but over the WHOLE dataset (no sampling) since this script needs
    a real count, not a scouting sample."""
    if CLEAN_PATH.exists():
        source_desc = {"type": "clean_jsonl", "files": [str(CLEAN_PATH)]}
    else:
        files = [fp for pattern in RAW_GLOBS for fp in sorted(glob.glob(pattern))]
        source_desc = {"type": "raw_glob", "files": files}

    records = load_source_records(CLEAN_PATH, RAW_GLOBS)
    texts = [text for r in records if (text := (r.get("text") or "").strip())]
    return texts, source_desc


# --- step 2: text/token length stats -----------------------------------------

def prompt_overhead_chars_avg() -> float:
    """Average length of the prompt TEMPLATE alone (no comment text), across
    all 5 Targets — the fixed per-call overhead every route pays regardless
    of comment length."""
    return mean(len(build_prompt("", target_id)) for target_id in TARGET_IDS)


def estimate_input_tokens_per_call(texts: list[str], overhead_chars: float) -> tuple[float, float]:
    """Returns (avg_input_tokens_per_call, avg_text_chars). Samples up to
    TOKENIZER_SAMPLE_SIZE real prompts to derive a chars->token ratio (real
    BPE if tiktoken is installed, else the fixed 4:1 heuristic), then applies
    that ratio to the true average prompt length computed over ALL eligible
    records (not just the sample)."""
    avg_text_chars = mean(len(t) for t in texts)
    avg_prompt_chars = overhead_chars + avg_text_chars

    rng = random.Random(RANDOM_SEED)
    sample = rng.sample(texts, min(TOKENIZER_SAMPLE_SIZE, len(texts)))
    sample_target = TARGET_IDS[0]
    sample_prompts = [build_prompt(t, sample_target) for t in sample]
    sample_chars = sum(len(p) for p in sample_prompts)
    sample_tokens = sum(_count_tokens(p) for p in sample_prompts)
    chars_per_token = sample_chars / sample_tokens if sample_tokens else 4.0

    avg_input_tokens = avg_prompt_chars / chars_per_token
    return avg_input_tokens, avg_text_chars


# --- step 3: real usage_log averages (output tokens + latency), with fallback

def load_usage_log() -> list[dict]:
    if not USAGE_LOG_PATH.exists():
        return []
    rows = []
    with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _successful_rows(rows: list[dict], route_name: str | None, field: str) -> list[dict]:
    return [
        r for r in rows
        if r.get("call_error") is None
        and r.get(field) is not None
        and (route_name is None or r.get("route_name") == route_name)
    ]


def route_avg_with_fallback(
    rows: list[dict], route_name: str, field: str, structural_default: float,
) -> tuple[float, str, int]:
    """Three-tier fallback: this route's own real average -> cross-route real
    average -> fixed structural default. Returns (value, source_label, n_used)."""
    own = _successful_rows(rows, route_name, field)
    if len(own) >= MIN_SAMPLES_FOR_ROUTE:
        return mean(r[field] for r in own), f"route_real_avg(n={len(own)})", len(own)

    cross = _successful_rows(rows, None, field)
    if len(cross) >= MIN_SAMPLES_FOR_ROUTE:
        return (
            mean(r[field] for r in cross),
            f"cross_route_fallback(n={len(cross)}, own_route_n={len(own)})",
            len(cross),
        )

    return structural_default, f"structural_estimate(own_route_n={len(own)}, cross_route_n={len(cross)})", 0


# --- reporting -----------------------------------------------------------------

def build_estimates(eligible_count: int, avg_input_tokens: float, usage_rows: list[dict]) -> list[dict]:
    structural_output_tokens = float(_count_tokens(_EXAMPLE_OUTPUT_JSON))
    results = []
    for route in MODEL_ROUTES:
        avg_output_tokens, output_source, _ = route_avg_with_fallback(
            usage_rows, route.route_name, "output_tokens", structural_output_tokens,
        )
        avg_latency_ms, latency_source, _ = route_avg_with_fallback(
            usage_rows, route.route_name, "latency_ms", 0.0,
        )

        total_input_tokens = round(eligible_count * avg_input_tokens)
        total_output_tokens = round(eligible_count * avg_output_tokens)
        total_cost_usd = estimate_cost_usd(route, total_input_tokens, total_output_tokens)
        cost_per_1000 = estimate_cost_usd(route, avg_input_tokens * 1000, avg_output_tokens * 1000)

        total_latency_hours = (
            (eligible_count * avg_latency_ms) / 1000 / 3600 if avg_latency_ms else None
        )

        results.append({
            "route_name": route.route_name,
            "model_name": route.model_name,
            "provider": route.provider,
            "avg_input_tokens_per_call": round(avg_input_tokens, 1),
            "avg_output_tokens_per_call": round(avg_output_tokens, 1),
            "output_tokens_source": output_source,
            "avg_latency_ms_per_call": round(avg_latency_ms, 1) if avg_latency_ms else None,
            "latency_source": latency_source,
            "estimated_total_cost_usd": round(total_cost_usd, 4),
            "estimated_cost_usd_per_1000_records": round(cost_per_1000, 4),
            "estimated_total_latency_hours_sequential": (
                round(total_latency_hours, 2) if total_latency_hours is not None else None
            ),
            "notes": route.notes,
        })
    return results


def print_table(estimates: list[dict]) -> None:
    ranked = sorted(estimates, key=lambda e: e["estimated_total_cost_usd"])
    print(f"{'route':28s} {'est. cost (USD)':>18s} {'est. time (sequential)':>26s}")
    print("-" * 74)
    for e in ranked:
        hours = e["estimated_total_latency_hours_sequential"]
        time_str = f"{hours:.1f}h" if hours is not None else "insufficient data"
        print(f"{e['route_name']:28s} {'$' + format(e['estimated_total_cost_usd'], ',.4f'):>18s} {time_str:>26s}")
    print()


def print_decision_log_row(estimates: list[dict], eligible_count: int, source_desc: dict) -> None:
    ranked = sorted(estimates, key=lambda e: e["estimated_total_cost_usd"])
    options = "؛ ".join(
        f"`{e['route_name']}` (~${e['estimated_total_cost_usd']:,.2f}"
        + (
            f"، ~{e['estimated_total_latency_hours_sequential']:.1f} ساعت sequential"
            if e["estimated_total_latency_hours_sequential"] is not None
            else "، زمان: داده کافی نیست"
        )
        + ")"
        for e in ranked
    )
    today = date.today().isoformat()
    decision_cell = (
        f"[تیم باید یکی از سقف‌های زیر را انتخاب/تأیید کند] بر اساس "
        f"`src/cost_tracking/estimate_full_run_cost.py` روی {eligible_count:,} رکورد واجد شرایط annotation "
        f"(منبع: {source_desc['type']}), تخمین هزینه/زمان کل Full run به ازای هر route: {options}."
    )
    why_cell = (
        "طبق `docs/pre_analysis_decision_table_v1.md` ردیف «سقف هزینه و زمان اجرا»، پیش از Full run باید "
        "سقف عددی هزینه و زمان بر اساس حجم داده تأیید و در Decision Log ثبت شود؛ این ردیف همان تأیید است "
        "(اعداد از تخمین صرف، بدون تماس واقعی API، محاسبه شده‌اند — نه اندازه‌گیری واقعی)."
    )
    print("Ready-to-paste row for docs/decision_log.md:\n")
    print(f"| {today} | {decision_cell} | {why_cell} |")
    print()


def main() -> None:
    print("Loading eligible records...")
    texts, source_desc = load_eligible_texts()
    eligible_count = len(texts)
    if eligible_count == 0:
        print(f"No eligible (non-empty text) records found via {source_desc} — nothing to estimate.")
        return
    print(f"  source: {source_desc['type']} ({len(source_desc['files'])} file(s))")
    print(f"  eligible records: {eligible_count:,}")

    overhead_chars = prompt_overhead_chars_avg()
    avg_input_tokens, avg_text_chars = estimate_input_tokens_per_call(texts, overhead_chars)
    print(f"  avg text length: {avg_text_chars:.1f} chars")
    print(f"  avg prompt length (template+text): {overhead_chars + avg_text_chars:.1f} chars "
          f"-> ~{avg_input_tokens:.1f} input tokens/call ({tokenizer_label()})")
    print()

    usage_rows = load_usage_log()
    print(f"usage_log.jsonl: {len(usage_rows)} logged calls "
          f"({USAGE_LOG_PATH if usage_rows else 'not found / empty'})\n")

    estimates = build_estimates(eligible_count, avg_input_tokens, usage_rows)

    print(f"Full-run estimate — {eligible_count:,} eligible records, {len(estimates)} routes:\n")
    print_table(estimates)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Pure estimate — no real API calls were made. See this script's module "
            "docstring for the eligibility-filter caveat and the input/output-token "
            "and latency fallback methodology."
        ),
        "data_source": source_desc,
        "eligible_record_count": eligible_count,
        "text_length_stats": {
            "avg_text_chars": round(avg_text_chars, 1),
            "prompt_overhead_chars_avg": round(overhead_chars, 1),
            "avg_input_tokens_per_call": round(avg_input_tokens, 1),
            "tokenizer": tokenizer_label(),
        },
        "usage_log_rows_used": len(usage_rows),
        "min_samples_for_route_avg": MIN_SAMPLES_FOR_ROUTE,
        "routes": estimates,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_doc, f, ensure_ascii=False, indent=2)
    print(f"Full detail written to {OUTPUT_PATH}\n")

    print_decision_log_row(estimates, eligible_count, source_desc)


if __name__ == "__main__":
    main()
