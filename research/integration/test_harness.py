from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.integration.core_adapter import build_core_state
from research.integration.hound_adapter import build_hound_state
from research.integration.simulator_payload import build_simulator_payload
from research.integration.ward_adapter import build_ward_state
from research.whale_link_flow.lead_line_socket import (
    get_core_payload,
    get_current_lead_line,
    get_hound_universe,
    get_ward_context,
)


def smoke_test() -> None:
    mode = "BTC_ACCUMULATION"

    lead_line = get_current_lead_line(mode, top_n=3)
    assert lead_line["source"] == "whale_link_flow"
    assert lead_line["symbols"]

    core_state = build_core_state(get_core_payload(mode), focus_assets=lead_line["symbols"])
    assert core_state.mode == mode
    assert core_state.btc_accumulation is True

    ward_state = build_ward_state(get_ward_context(mode))
    assert ward_state.risk_level in {"NORMAL", "CAUTION"}

    hound_state = build_hound_state(get_hound_universe(mode, top_n=3))
    assert hound_state.target_count == 3

    simulator_payload = build_simulator_payload(mode, top_n=3)
    assert set(simulator_payload.keys()) == {"core", "ward", "hound", "lead_line"}


if __name__ == "__main__":
    smoke_test()
    print("integration harness smoke test ok")
