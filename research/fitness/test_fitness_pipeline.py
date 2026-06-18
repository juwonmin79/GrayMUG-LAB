from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.fitness.fitness_pipeline import run_fitness_pipeline


def smoke_test() -> None:
    report = run_fitness_pipeline(mode="BTC_ACCUMULATION", top_n=3)

    assert set(report.keys()) == {"timestamp", "core", "ward", "hound", "overall_score"}
    assert 0.0 <= report["core"]["score"] <= 1.0
    assert 0.0 <= report["ward"]["score"] <= 1.0
    assert 0.0 <= report["hound"]["score"] <= 1.0
    assert 0.0 <= report["overall_score"] <= 1.0

    assert report["core"]["focus_assets"]
    assert "survival_score" in report["ward"]
    assert "target_accuracy" in report["hound"]


if __name__ == "__main__":
    smoke_test()
    print("engine fitness pipeline smoke test ok")
