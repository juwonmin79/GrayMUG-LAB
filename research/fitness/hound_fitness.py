from __future__ import annotations

from research.fitness.fitness_schema import HoundFitness
from research.targeting.target_schema import HoundHuntFeed


def evaluate_hound_fitness(hound_feed: HoundHuntFeed) -> HoundFitness:
    target_presence = 1.0 if hound_feed.top_targets else 0.0
    hit_rate = _clip((target_presence * 0.50) + (hound_feed.confidence * 0.50))
    forward_return_score = _clip(hound_feed.hunt_pressure)
    target_accuracy = _clip(min(len(hound_feed.priority_rank) / 3.0, 1.0))
    score = _clip((hit_rate * 0.40) + (forward_return_score * 0.30) + (target_accuracy * 0.30))

    return HoundFitness(
        score=score,
        hit_rate=hit_rate,
        forward_return_score=forward_return_score,
        target_accuracy=target_accuracy,
    )


def _clip(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)
