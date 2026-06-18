from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.targeting.target_pipeline import run_target_pipeline


def smoke_test() -> None:
    payload = run_target_pipeline(mode="BTC_ACCUMULATION", top_n=3)

    assert set(payload.keys()) == {"timestamp", "mode", "source", "core", "ward", "hound"}

    core = payload["core"]
    ward = payload["ward"]
    hound = payload["hound"]

    assert core["engine"] == "CORE"
    assert ward["engine"] == "WARD"
    assert hound["engine"] == "HOUND"
    assert len({core["engine"], ward["engine"], hound["engine"]}) == 3

    assert core["focus_assets"]
    assert ward["risk_hint"] in {"NORMAL", "CAUTION"}
    assert hound["top_targets"]
    assert hound["priority_rank"]

    # Hound receives target candidates only. This pipeline has no Hound mutation handle.
    assert "detection_logic" not in hound
    assert "modify_hound" not in hound


if __name__ == "__main__":
    smoke_test()
    print("target intelligence pipeline smoke test ok")
