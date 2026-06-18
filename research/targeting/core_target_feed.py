from __future__ import annotations

from research.integration.state_schema import CoreState, LeadLineState
from research.targeting.target_schema import CoreTargetFeed


def build_core_target_feed(
    core_state: CoreState,
    lead_line_state: LeadLineState,
) -> CoreTargetFeed:
    bias_by_mode = {
        "BTC_ACCUMULATION": 0.80,
        "BEAR_ESCAPE": 0.10,
        "OBSERVE_ONLY": 0.50,
    }
    bias = bias_by_mode.get(core_state.mode, 0.50)
    confidence = 0.80 if core_state.focus_assets else 0.30

    return CoreTargetFeed(
        mode=core_state.mode,
        quote_asset=core_state.quote_asset,
        btc_accumulation_bias=bias,
        focus_assets=list(core_state.focus_assets),
        confidence=confidence,
        source=lead_line_state.source,
    )
