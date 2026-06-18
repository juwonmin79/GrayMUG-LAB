from __future__ import annotations

from research.integration.state_schema import LeadLineState, WardState
from research.targeting.target_schema import WardRiskFeed


def build_ward_risk_feed(
    ward_state: WardState,
    lead_line_state: LeadLineState,
) -> WardRiskFeed:
    pressure_by_mode = {
        "BEAR_ESCAPE": 0.85,
        "BTC_ACCUMULATION": 0.10,
        "OBSERVE_ONLY": 0.50,
    }
    escape_pressure = pressure_by_mode.get(lead_line_state.mode, 0.50)

    if ward_state.warning_flags:
        risk_alignment = "CAUTION"
    elif lead_line_state.mode == "BEAR_ESCAPE":
        risk_alignment = "DEFENSIVE"
    else:
        risk_alignment = "ALIGNED"

    return WardRiskFeed(
        mode=lead_line_state.mode,
        risk_hint=ward_state.risk_level,
        escape_pressure=escape_pressure,
        risk_alignment=risk_alignment,
        warning_flags=list(ward_state.warning_flags),
        source=lead_line_state.source,
    )
