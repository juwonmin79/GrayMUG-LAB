from __future__ import annotations

from research.fitness.fitness_schema import CoreFitness
from research.targeting.target_schema import CoreTargetFeed


def evaluate_core_fitness(core_feed: CoreTargetFeed) -> CoreFitness:
    mode_bonus = {
        "BTC_ACCUMULATION": 0.80,
        "OBSERVE_ONLY": 0.50,
        "BEAR_ESCAPE": 0.25,
    }.get(core_feed.mode, 0.50)

    focus_score = min(len(core_feed.focus_assets) / 3.0, 1.0)
    btc_accumulation_score = _clip((core_feed.btc_accumulation_bias * 0.70) + (focus_score * 0.30))
    btc_relative_alpha = _clip((core_feed.confidence * 0.60) + (mode_bonus * 0.40))
    score = _clip((btc_accumulation_score * 0.60) + (btc_relative_alpha * 0.40))

    return CoreFitness(
        score=score,
        btc_accumulation_score=btc_accumulation_score,
        btc_relative_alpha=btc_relative_alpha,
        focus_assets=list(core_feed.focus_assets),
    )


def _clip(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)
