from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.execution.execution_pipeline import run_execution_pipeline
from research.execution.execution_schema import PATTERN_NAMES


def smoke_test() -> None:
    payload = run_execution_pipeline(mode="BTC_ACCUMULATION", top_n=3)

    assert payload["target"]
    assert payload["pattern"]["pattern_name"] in PATTERN_NAMES
    assert payload["entry"]["entry_style"] in {"ALLOW", "WAIT_CONFIRMATION", "AVOID"}
    assert payload["tp_sl"]["tp_case"] in {"CASE A", "CASE B", "CASE C"}
    assert payload["tp_sl"]["sl_case"] in {"CASE A", "CASE B", "CASE C"}
    assert payload["exit"]["exit_triggers"]
    assert payload["source"] == "execution_guidance_api"

    assert "order" not in payload
    assert "position_size" not in payload
    assert "side" not in payload
    assert "BUY" not in payload["entry"]["entry_style"]
    assert "SELL" not in payload["entry"]["entry_style"]


if __name__ == "__main__":
    smoke_test()
    print("execution guidance pipeline smoke test ok")
