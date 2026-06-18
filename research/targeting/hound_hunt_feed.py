from __future__ import annotations

from research.integration.state_schema import HoundState, LeadLineState
from research.targeting.target_schema import HoundHuntFeed


def build_hound_hunt_feed(
    hound_state: HoundState,
    lead_line_state: LeadLineState,
    top_n: int = 12,
) -> HoundHuntFeed:
    limit = max(int(top_n), 1)
    top_targets = list(hound_state.tracked_symbols[:limit])
    priority_rank = {
        symbol: int(hound_state.priority_rank.get(symbol, index))
        for index, symbol in enumerate(top_targets, start=1)
    }
    hunt_pressure = round(min(len(top_targets) / float(limit), 1.0), 4)

    return HoundHuntFeed(
        mode=lead_line_state.mode,
        top_targets=top_targets,
        priority_rank=priority_rank,
        hunt_pressure=hunt_pressure,
        confidence=hunt_pressure,
        source=lead_line_state.source,
    )
