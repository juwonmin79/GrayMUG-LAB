from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.integration.simulator_payload import build_simulator_payload
from research.integration.state_schema import CoreState, HoundState, LeadLineState, WardState
from research.targeting.target_feed_builder import build_target_pipeline_payload


LATEST_TARGET_FEED_PATH = Path("outputs/targeting/latest_target_feed.json")


def run_target_pipeline(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 12,
) -> Dict:
    simulator_payload = build_simulator_payload(mode=mode, top_n=top_n)

    core_state = CoreState(**simulator_payload["core"])
    ward_state = WardState(**simulator_payload["ward"])
    hound_state = HoundState(**simulator_payload["hound"])
    lead_line_state = LeadLineState(**simulator_payload["lead_line"])

    payload = build_target_pipeline_payload(
        core_state=core_state,
        ward_state=ward_state,
        hound_state=hound_state,
        lead_line_state=lead_line_state,
        top_n=top_n,
    )
    _write_latest_target_feed(payload)
    return payload


def _write_latest_target_feed(payload: Dict) -> None:
    try:
        LATEST_TARGET_FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
        LATEST_TARGET_FEED_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # File export is a helper; the internal API contract is primary.
        return


def main() -> None:
    payload = run_target_pipeline(mode="BTC_ACCUMULATION", top_n=3)
    core = payload["core"]
    ward = payload["ward"]
    hound = payload["hound"]

    print("GRAYMUG TARGET INTELLIGENCE PIPELINE")
    print("MODE")
    print(payload["mode"])
    print("CORE FEED")
    print(f"BTC accumulation bias: {core['btc_accumulation_bias']:.2f}")
    print(f"Focus assets: {', '.join(core['focus_assets'])}")
    print("WARD FEED")
    print(f"Risk hint: {ward['risk_hint']}")
    print(f"Escape pressure: {ward['escape_pressure']:.2f}")
    print("HOUND FEED")
    print("Top targets:")
    for symbol in hound["top_targets"]:
        print(f"{hound['priority_rank'][symbol]} {symbol}")


if __name__ == "__main__":
    main()
