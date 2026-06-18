from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from research.integration.core_adapter import build_core_state
from research.integration.hound_adapter import build_hound_state
from research.integration.state_schema import LeadLineState, SimulatorState
from research.integration.ward_adapter import build_ward_state
from research.whale_link_flow.lead_line_socket import (
    get_core_payload,
    get_current_lead_line,
    get_hound_universe,
    get_ward_context,
)


def build_simulator_payload(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 3,
    min_priority: float = 0.0,
) -> Dict:
    lead_line_payload = get_current_lead_line(
        mode=mode,
        top_n=top_n,
        min_priority=min_priority,
    )
    hound_universe = get_hound_universe(
        mode=mode,
        top_n=top_n,
        min_priority=min_priority,
    )

    priority_rank = {
        item["pair"]: int(item["rank"])
        for item in lead_line_payload.get("items", [])
    }

    lead_line_state = LeadLineState(
        timestamp=int(lead_line_payload["timestamp"]),
        mode=str(lead_line_payload["mode"]),
        quote_asset=str(lead_line_payload["quote_asset"]),
        symbols=list(lead_line_payload["symbols"]),
        source=str(lead_line_payload["source"]),
    )

    simulator_state = SimulatorState(
        core=build_core_state(
            get_core_payload(mode),
            focus_assets=list(lead_line_payload["symbols"]),
        ),
        ward=build_ward_state(get_ward_context(mode)),
        hound=build_hound_state(hound_universe, priority_rank=priority_rank),
        lead_line=lead_line_state,
    )

    return {
        "core": asdict(simulator_state.core),
        "ward": asdict(simulator_state.ward),
        "hound": asdict(simulator_state.hound),
        "lead_line": asdict(simulator_state.lead_line),
    }
