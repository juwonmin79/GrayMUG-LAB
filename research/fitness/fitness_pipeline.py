from __future__ import annotations

import os
import sys
from dataclasses import asdict
from typing import Dict


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.fitness.core_fitness import evaluate_core_fitness
from research.fitness.fitness_registry import register_fitness_result
from research.fitness.fitness_schema import FitnessReport
from research.fitness.fitness_score import build_overall_fitness_score
from research.fitness.hound_fitness import evaluate_hound_fitness
from research.fitness.ward_fitness import evaluate_ward_fitness
from research.targeting.target_pipeline import run_target_pipeline
from research.targeting.target_schema import CoreTargetFeed, HoundHuntFeed, WardRiskFeed


def run_fitness_pipeline(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 3,
) -> Dict:
    target_payload = run_target_pipeline(mode=mode, top_n=top_n)

    core_feed = CoreTargetFeed(**target_payload["core"])
    ward_feed = WardRiskFeed(**target_payload["ward"])
    hound_feed = HoundHuntFeed(**target_payload["hound"])

    core_fitness = evaluate_core_fitness(core_feed)
    ward_fitness = evaluate_ward_fitness(ward_feed)
    hound_fitness = evaluate_hound_fitness(hound_feed)
    overall_score = build_overall_fitness_score(core_fitness, ward_fitness, hound_fitness)

    register_fitness_result(
        "whale_link_flow",
        core_fitness.score,
        ward_fitness.score,
        hound_fitness.score,
    )

    report = FitnessReport(
        timestamp=int(target_payload["timestamp"]),
        core=core_fitness,
        ward=ward_fitness,
        hound=hound_fitness,
        overall_score=overall_score,
    )
    return asdict(report)


def main() -> None:
    report = run_fitness_pipeline(mode="BTC_ACCUMULATION", top_n=3)

    print("GRAYMUG FITNESS REPORT")
    print("CORE")
    print(f"{report['core']['score']:.2f}")
    print("WARD")
    print(f"{report['ward']['score']:.2f}")
    print("HOUND")
    print(f"{report['hound']['score']:.2f}")
    print("OVERALL")
    print(f"{report['overall_score']:.2f}")


if __name__ == "__main__":
    main()
