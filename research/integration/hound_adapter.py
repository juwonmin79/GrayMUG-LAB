from __future__ import annotations

from typing import Dict, List, Optional

from research.integration.state_schema import HoundState


def build_hound_state(
    hound_universe: List[str],
    priority_rank: Optional[Dict[str, int]] = None,
) -> HoundState:
    ranks = priority_rank or {symbol: rank for rank, symbol in enumerate(hound_universe, start=1)}

    return HoundState(
        tracked_symbols=list(hound_universe),
        priority_rank=ranks,
        target_count=len(hound_universe),
    )
