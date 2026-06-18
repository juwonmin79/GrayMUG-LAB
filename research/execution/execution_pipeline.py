from __future__ import annotations

import os
import sys
from typing import Dict


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.calibration.calibration_pipeline import run_calibration_pipeline
from research.execution.execution_builder import build_execution_guidance_payload
from research.execution.pattern_classifier import classify_pattern
from research.targeting.target_pipeline import run_target_pipeline


def run_execution_pipeline(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 3,
) -> Dict:
    target_payload = run_target_pipeline(mode=mode, top_n=top_n)
    calibration_payload = run_calibration_pipeline(mode=mode, top_n=top_n)
    hound_targets = target_payload["hound"]["top_targets"]
    target = hound_targets[0] if hound_targets else "NONE"
    pattern = classify_pattern(target_payload, calibration_payload)
    return build_execution_guidance_payload(target, pattern)


def main() -> None:
    payload = run_execution_pipeline(mode="BTC_ACCUMULATION", top_n=3)

    print("GRAYMUG EXECUTION GUIDANCE")
    print("TARGET")
    print(payload["target"])
    print("PATTERN")
    print(payload["pattern"]["pattern_name"])
    print("ENTRY")
    print(payload["entry"]["entry_style"])
    print("TP")
    print(payload["tp_sl"]["tp_case"])
    print("SL")
    print(payload["tp_sl"]["sl_case"])
    print("EXIT")
    for trigger in payload["exit"]["exit_triggers"]:
        print(trigger)


if __name__ == "__main__":
    main()
