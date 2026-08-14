"""
model_routes.py — cost-aware model registry (Parmida)

Implements §21 of the assignment doc ("معماری Cost-aware پیشنهادی"): a
documented, versioned list of model routes with real per-token pricing, so
model choice is an explicit, auditable decision instead of a hardcoded model
name buried in a prompt-calling script.

Pricing was pulled 2026-08-07 from each provider's own pricing page/API and
converted to USD per 1,000,000 tokens:
  - Groq:       console.groq.com/docs/models
  - OpenRouter: GET https://openrouter.ai/api/v1/models (live `pricing` field,
                which is USD per single token)
  - DeepSeek:   api-docs.deepseek.com/quick_start/pricing (cache-miss input
                rate used, since our comments are not expected to repeat
                verbatim across calls)
Re-check these before relying on them for a real budget number — providers
change pricing without notice (see the doc's own warning in §21).

GEMINI_API_KEY in .env is currently invalid for the native `google-generativeai`
SDK (403 — wrong key format, verified 2026-08-07; a proper AI-Studio key
starting with "AIzaSy..." is still needed from
https://aistudio.google.com/apikey). Until that's fixed, Gemini models are
reached indirectly through the OpenRouter route below — same underlying
model, extra hop, slightly different price.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.annotation.decision_gate import require_decision_log_gate

ROOT = Path(__file__).resolve().parent.parent.parent
DECISION_LOG_PATH = ROOT / "docs" / "decision_log.md"


@dataclass(frozen=True)
class ModelRoute:
    """A documented route for cost-aware text annotation."""

    route_name: str
    model_name: str
    provider: str  # "groq" | "openrouter" | "deepseek"
    max_batch_size: int
    confidence_threshold: float
    estimated_input_cost_per_million_tokens: float
    estimated_output_cost_per_million_tokens: float
    notes: str = ""


MODEL_ROUTES: list[ModelRoute] = [
    ModelRoute(
        route_name="groq_cheap_fast",
        model_name="llama-3.1-8b-instant",
        provider="groq",
        max_batch_size=1,
        confidence_threshold=0.60,
        estimated_input_cost_per_million_tokens=0.05,
        estimated_output_cost_per_million_tokens=0.08,
        notes="Cheapest/fastest route — first pass / high-volume tier per §21 step 3.",
    ),
    ModelRoute(
        route_name="groq_default",
        model_name="llama-3.3-70b-versatile",
        provider="groq",
        max_batch_size=1,
        confidence_threshold=0.55,
        estimated_input_cost_per_million_tokens=0.59,
        estimated_output_cost_per_million_tokens=0.79,
        notes="Current default in compare_llm_sentiment.py / evaluate_sentiment_accuracy.py.",
    ),
    ModelRoute(
        route_name="deepseek_flash_direct",
        model_name="deepseek-v4-flash",
        provider="deepseek",
        max_batch_size=1,
        confidence_threshold=0.60,
        estimated_input_cost_per_million_tokens=0.14,  # cache-miss rate
        estimated_output_cost_per_million_tokens=0.28,
        notes="Direct DeepSeek API, no OpenRouter hop.",
    ),
    ModelRoute(
        route_name="openrouter_deepseek_flash",
        model_name="deepseek/deepseek-v4-flash",
        provider="openrouter",
        max_batch_size=1,
        confidence_threshold=0.60,
        estimated_input_cost_per_million_tokens=0.14,
        estimated_output_cost_per_million_tokens=0.28,
        notes="Same model as deepseek_flash_direct, routed through OpenRouter — kept "
        "for A/B-ing whether the extra hop changes latency/reliability.",
    ),
    ModelRoute(
        route_name="openrouter_gemini_flash_lite",
        model_name="google/gemini-2.5-flash-lite",
        provider="openrouter",
        max_batch_size=1,
        confidence_threshold=0.55,
        estimated_input_cost_per_million_tokens=0.10,
        estimated_output_cost_per_million_tokens=0.40,
        notes="Stand-in for a native Gemini route until a valid GEMINI_API_KEY is set "
        "(see module docstring). §21 escalation-tier candidate given Gemini's "
        "reputation on multilingual (fa/ar) text.",
    ),
    ModelRoute(
        route_name="ollama_llama3_local",
        model_name="llama3:latest",
        provider="ollama",
        max_batch_size=1,
        confidence_threshold=0.55,  # same default as the other 8B-class route (groq_cheap_fast) until Gold-evaluated
        estimated_input_cost_per_million_tokens=0.0,
        estimated_output_cost_per_million_tokens=0.0,
        notes="2026-08-14 — local Ollama server (localhost:11434), NOT a cloud "
        "provider: zero cost, no rate limit, but throughput is capped by local "
        "hardware (~0.6-0.7 req/s observed at 4-8 concurrent workers, not "
        "scaling much past that — see docs/decision_log.md). NOT YET "
        "Gold-evaluated (evaluate_sentiment_accuracy.py hasn't scored it) and "
        "NOT the locked route — added so it CAN be evaluated/used, added "
        "deliberately without touching any existing route's config or "
        "LOCKED_ROUTE_NAME (still groq_cheap_fast, unchanged by this entry).",
    ),
]

PROVIDERS_REQUIRING_ENV_KEY = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    # No real secret needed (local, unauthenticated server) — mapped to a
    # var that every caller's api_keys dict can default to a non-empty
    # value (OLLAMA_BASE_URL, default "http://localhost:11434") so the
    # existing "route has a usable key" filter in run_model_comparison.py/
    # evaluate_sentiment_accuracy.py/run_full_annotation.py works unchanged
    # instead of needing a special case for this one provider.
    "ollama": "OLLAMA_BASE_URL",
}


def estimate_cost_usd(route: ModelRoute, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for one call on `route` given token counts."""
    return (
        input_tokens * route.estimated_input_cost_per_million_tokens
        + output_tokens * route.estimated_output_cost_per_million_tokens
    ) / 1_000_000


def get_route(route_name: str) -> ModelRoute:
    for route in MODEL_ROUTES:
        if route.route_name == route_name:
            return route
    raise KeyError(f"Unknown route_name {route_name!r}. Known routes: "
                    f"{[r.route_name for r in MODEL_ROUTES]}")


# --- Model lock (Gate per docs/pre_analysis_decision_table_v1.md) ---------

LOCKED_ROUTE_NAME: str | None = "groq_cheap_fast"
# Originally locked 2026-08-14 to "openrouter_gemini_flash_lite" (best F1 of
# the 3 evaluated routes — see decision_log.md's model-lock entry). Switched
# same day, mid Full-run, to "groq_cheap_fast": the OpenRouter account backing
# that route ran out of real credit ("HTTP 402: Insufficient credits. This
# account never purchased credits") ~7,000 rows into shard_0of2, an 84%
# failure rate. See docs/decision_log.md's dated entry for the full
# reasoning — this is a forced fallback due to a real payment/account
# problem, not a quality-driven re-pick.
"""route_name (from MODEL_ROUTES above) locked in for the Full run — or None.

This MUST stay None until:
  1. src/validation/evaluate_sentiment_accuracy.py has been run on the full,
     hand-labeled Gold Sample (not a scouting subset — see that script's own
     docstring / run_model_comparison.py for the qualitative-only pass that
     comes before it), and
  2. the resulting choice (with its Macro-F1, failure rate, cost and latency
     numbers) has been written down as a dated entry in docs/decision_log.md.

This is the explicit Gate from docs/pre_analysis_decision_table_v1.md, row
"مدل و Provider LLM": "... انتخاب مدل پس از Pilot روی ۱۰۰ رکورد و پیش از
Full run قفل می‌شود" — model choice is locked *after* the Pilot and *before*
the Full run, not before. Do not set this to a route_name to "just try it" —
that defeats the point of the Gate (endless model-hopping without a written,
falsifiable reason is explicitly forbidden by the same doc row: "مقایسه
بی‌پایان مدل ممنوع"). Once you do set it, record the route_name and the
decision_log.md entry date in a comment next to the assignment.
"""


def get_locked_route() -> ModelRoute:
    """Return the ModelRoute locked in for the Full run.

    Raises RuntimeError if no route has been locked yet (LOCKED_ROUTE_NAME is
    still None) — this is intentional: it is the safety check that stops
    anyone from running annotation over the whole dataset before the model
    choice is actually decided and logged. Also prints a (non-fatal) warning
    if LOCKED_ROUTE_NAME, once set, can't actually be found anywhere in
    docs/decision_log.md — see decision_gate.require_decision_log_gate.
    """
    require_decision_log_gate(
        LOCKED_ROUTE_NAME,
        gate_name="LOCKED_ROUTE_NAME",
        decision_log_path=DECISION_LOG_PATH,
        missing_message=(
            "هنوز مدلی برای Full run قفل نشده — اول evaluate_sentiment_accuracy.py "
            "را اجرا کن و نتیجه را در LOCKED_ROUTE_NAME ثبت کن"
        ),
    )
    return get_route(LOCKED_ROUTE_NAME)
