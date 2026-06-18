from __future__ import annotations

from typing import Dict, List, Optional

from research.integration.state_schema import CoreState


def build_core_state(
    core_payload: Dict,
    focus_assets: Optional[List[str]] = None,
) -> CoreState:
    mode = str(core_payload["mode"])
    quote_asset = str(core_payload["quote_asset"])

    return CoreState(
        mode=mode,
        quote_asset=quote_asset,
        btc_accumulation=mode == "BTC_ACCUMULATION",
        focus_assets=focus_assets or [],
    )
