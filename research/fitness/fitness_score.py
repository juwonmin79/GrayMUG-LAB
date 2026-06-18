from __future__ import annotations

from research.fitness.fitness_schema import CoreFitness, HoundFitness, WardFitness


def build_overall_fitness_score(
    core: CoreFitness,
    ward: WardFitness,
    hound: HoundFitness,
) -> float:
    return round(
        (core.score * 0.40) +
        (ward.score * 0.30) +
        (hound.score * 0.30),
        4,
    )
