from __future__ import annotations

from typing import Dict, List

from research.integration.state_schema import WardState


def build_ward_state(ward_context: Dict) -> WardState:
    mode = str(ward_context["mode"])
    risk_context = ward_context.get("risk_context", {})
    max_priority = float(risk_context.get("max_priority_score", 0.0))

    warning_flags: List[str] = []
    if mode == "BEAR_ESCAPE":
        warning_flags.append("BEAR_ESCAPE_MODE")
    if max_priority >= 0.8:
        warning_flags.append("HIGH_PRIORITY_CLUSTER")

    return WardState(
        regime=mode,
        risk_level="NORMAL" if not warning_flags else "CAUTION",
        warning_flags=warning_flags,
    )
