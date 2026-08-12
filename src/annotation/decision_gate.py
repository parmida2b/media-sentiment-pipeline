"""
decision_gate.py — shared "None until logged in decision_log.md" gate (Parmida)

model_routes.py's LOCKED_ROUTE_NAME/get_locked_route() and
run_full_annotation.py's APPROVED_COST_CAP_USD/--confirm-cost-cap were two
separate implementations of the same idea: a None-default constant that must
only be set *after* a dated decision has been written down in
docs/decision_log.md, with a check that fails loudly while it's still None.
Neither had any automated check that such a row actually exists in
decision_log.md — this module adds that (as a best-effort *warning*, not a
hard fail: decision_log.md's "تصمیم" column is free-text Persian prose, not a
machine format, so a miss here is a signal to double-check, not proof the
entry is missing).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def require_decision_log_gate(
    value: Any,
    gate_name: str,
    decision_log_path: Path,
    *,
    missing_message: str,
) -> None:
    """Enforce a "must be set from a dated docs/decision_log.md entry" gate.

    - If value is None (the un-set default), raises RuntimeError(missing_message)
      — this is the hard fail that stops an unset gate from silently letting a
      caller proceed. The wording stays caller-specific on purpose: each gate
      names its own doc row and its own next step, and that context is more
      useful inline than a generic message here.
    - If value IS set, best-effort checks that decision_log.md actually
      mentions gate_name or str(value) somewhere, and prints a warning to
      stderr if neither is found. This does not raise — a miss can be a false
      positive (free-text log, differently-formatted number, etc.), so it's a
      signal for a human to double-check, not something to fail the run on.
    """
    if value is None:
        raise RuntimeError(missing_message)

    try:
        log_text = decision_log_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"[decision_gate] WARNING: could not read {decision_log_path} to verify "
            f"the {gate_name!r} gate (value={value!r}) is backed by a logged decision: "
            f"{exc}",
            file=sys.stderr,
        )
        return

    needle_candidates = (gate_name, str(value))
    if not any(needle in log_text for needle in needle_candidates):
        print(
            f"[decision_gate] WARNING: neither {gate_name!r} nor {value!r} was found "
            f"anywhere in {decision_log_path} — double-check that this value is "
            f"actually backed by a dated entry there. (The log's format is free text, "
            f"so this check can miss a real entry that's phrased differently; it is a "
            f"signal, not proof the entry is missing.)",
            file=sys.stderr,
        )
