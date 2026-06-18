from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.calibration.calibration_policy import MAX_INFLUENCE
from research.calibration.engine_scope import ENGINE_SCOPES
from research.calibration.calibration_pipeline import run_calibration_pipeline


def smoke_test() -> None:
    payload = run_calibration_pipeline(mode="BTC_ACCUMULATION", top_n=3)
    signals = payload["signals"]
    engines = [signal["engine"] for signal in signals]

    assert sorted(engines) == ["CORE", "HOUND", "WARD"]
    assert len(set(engines)) == 3

    for signal in signals:
        engine = signal["engine"]
        assert signal["final_weight"] <= MAX_INFLUENCE[engine]
        assert signal["application_scope"] == ENGINE_SCOPES[engine].allowed_scope
        assert signal["application_scope"] != ENGINE_SCOPES[engine].forbidden

    assert [s for s in signals if s["engine"] == "CORE"][0]["final_weight"] <= 0.20
    assert [s for s in signals if s["engine"] == "WARD"][0]["final_weight"] <= 0.15
    assert [s for s in signals if s["engine"] == "HOUND"][0]["final_weight"] <= 0.30


if __name__ == "__main__":
    smoke_test()
    print("lab signal calibration pipeline smoke test ok")
