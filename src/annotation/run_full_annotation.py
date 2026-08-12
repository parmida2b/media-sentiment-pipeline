"""
run_full_annotation.py — SKELETON: Full-dataset annotation run (Parmida)

NOT YET IMPLEMENTED. This file only exists to hold the two safety checks the
Gate in docs/pre_analysis_decision_table_v1.md requires before anyone runs
annotation over the whole dataset (~155k records across youtube + reddit as
of this writing — recount before relying on that number, it is not read from
disk here):

  1. Model lock — row "مدل و Provider LLM": "... انتخاب مدل پس از Pilot روی
     ۱۰۰ رکورد و پیش از Full run قفل می‌شود". Enforced by calling
     get_locked_route() (src/annotation/model_routes.py), which raises
     RuntimeError until someone has run
     src/validation/evaluate_sentiment_accuracy.py on the full Gold Sample
     and set MODEL_ROUTES.LOCKED_ROUTE_NAME accordingly.
  2. Cost cap — row "سقف هزینه و زمان اجرا": "پیش از Full run، سقف عددی
     هزینه و زمان بر اساس حجم داده و Pilot در Decision Log تأیید می‌شود؛ تا
     آن زمان Full run مجاز نیست". Enforced by requiring --confirm-cost-cap,
     which must equal APPROVED_COST_CAP_USD below — a constant that itself
     must be filled in from a dated docs/decision_log.md entry before this
     script can do anything. This is deliberately a *second*, independent
     gate from the model lock: locking a model does not by itself authorize
     spending money on the full dataset.

Both gates fail loudly and early (before any data is touched) rather than
silently defaulting to "proceed" — the whole point is that nobody should be
able to trigger a full, real-money run by accident.

The actual annotation logic (reading the full clean dataset, batching calls
through llm_client.annotate() with the locked route, writing results,
resumability/checkpointing for a ~155k-record run, retry/failure handling,
progress + running-cost reporting against the confirmed cap) is intentionally
NOT implemented yet. That comes only after LOCKED_ROUTE_NAME is actually set
and a real cost cap has been approved and logged.

Usage (once both gates above are actually satisfied):
    python src/annotation/run_full_annotation.py --confirm-cost-cap 42.00
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.annotation.decision_gate import require_decision_log_gate  # noqa: E402
from src.annotation.model_routes import get_locked_route  # noqa: E402

DECISION_LOG_PATH = ROOT / "docs" / "decision_log.md"

# Approved cost cap (USD) for the Full run, per docs/pre_analysis_decision_table_v1.md
# row "سقف هزینه و زمان اجرا". Must stay None — and this script must keep
# refusing to run — until a numeric cap has been decided from Pilot data and
# written down as a dated entry in docs/decision_log.md. When that happens,
# set this to the approved number and reference the decision_log.md date in a
# comment here, the same way LOCKED_ROUTE_NAME is documented in model_routes.py.
APPROVED_COST_CAP_USD: float | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run LLM annotation over the FULL dataset using the locked model route. "
            "Refuses to run unless a model is locked (model_routes.LOCKED_ROUTE_NAME) "
            "and the caller explicitly confirms the cost cap approved in "
            "docs/decision_log.md."
        )
    )
    parser.add_argument(
        "--confirm-cost-cap",
        type=float,
        required=True,
        metavar="USD",
        help=(
            "The USD cost cap approved for this Full run, as written in a dated "
            "docs/decision_log.md entry. Must match APPROVED_COST_CAP_USD exactly "
            "in this script — this is a deliberate 'type it out' confirmation so a "
            "full, real-money run can't be triggered by accident (e.g. by a default "
            "flag value, or by copy-pasting a command without reading it)."
        ),
    )
    return parser.parse_args()


def check_cost_cap(confirmed_cap: float) -> None:
    """Second Gate: refuse to run unless the caller's --confirm-cost-cap
    matches the cap actually approved and logged in docs/decision_log.md.
    Also prints a (non-fatal) warning if APPROVED_COST_CAP_USD, once set,
    can't actually be found anywhere in docs/decision_log.md — see
    decision_gate.require_decision_log_gate.
    """
    require_decision_log_gate(
        APPROVED_COST_CAP_USD,
        gate_name="APPROVED_COST_CAP_USD",
        decision_log_path=DECISION_LOG_PATH,
        missing_message=(
            "هنوز سقف هزینه‌ای برای Full run تأیید نشده — طبق "
            "docs/pre_analysis_decision_table_v1.md ('سقف هزینه و زمان اجرا'), "
            "اول باید سقف عددی بر اساس Pilot در docs/decision_log.md ثبت شود، "
            "بعد APPROVED_COST_CAP_USD در این فایل مقداردهی شود."
        ),
    )
    if confirmed_cap != APPROVED_COST_CAP_USD:
        raise ValueError(
            f"--confirm-cost-cap={confirmed_cap} با سقف تأییدشده "
            f"(APPROVED_COST_CAP_USD={APPROVED_COST_CAP_USD}) مطابقت ندارد — "
            "برای جلوگیری از اجرای تصادفی روی کل دیتاست، این دو باید دقیقاً برابر باشند."
        )


def main() -> None:
    args = parse_args()

    # Gate 1: model must be locked (raises RuntimeError otherwise).
    route = get_locked_route()

    # Gate 2: cost cap must be explicitly confirmed and match decision_log.md.
    check_cost_cap(args.confirm_cost_cap)

    print(f"[skeleton] Both gates passed — route={route.route_name!r}, "
          f"confirmed cost cap=${args.confirm_cost_cap}")

    # TODO (after the model is actually locked and the cap actually approved):
    #   - load the full clean dataset (data/interim/clean.jsonl + raw jsonl fallback,
    #     same pattern as run_model_comparison.load_sample, but without sampling)
    #   - resumability/checkpointing so a ~155k-record run can be interrupted and
    #     resumed without re-annotating (re-use src.annotation.llm_client.AnnotationCache)
    #   - batch calls through llm_client.annotate() using `route`
    #   - track running cost against args.confirm_cost_cap and stop if exceeded
    #   - write results to outputs/ (path TBD) with the same §22 structured contract
    #     used by run_model_comparison.py / evaluate_sentiment_accuracy.py
    #   - progress reporting (this is a long-running job)
    raise NotImplementedError(
        "run_full_annotation.py is still a skeleton — the actual annotation loop "
        "is not implemented yet. Both safety gates above ran successfully; the "
        "TODOs in main() are what's left."
    )


if __name__ == "__main__":
    main()
