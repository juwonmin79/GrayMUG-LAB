from __future__ import annotations

from research.fitness.fitness_schema import WardFitness
from research.targeting.target_schema import WardRiskFeed


def evaluate_ward_fitness(ward_feed: WardRiskFeed) -> WardFitness:
    if ward_feed.mode == "BEAR_ESCAPE":
        survival_score = max(ward_feed.escape_pressure, 0.75)
    elif ward_feed.mode == "BTC_ACCUMULATION":
        survival_score = 0.75 if ward_feed.risk_hint == "NORMAL" else 0.60
    else:
        survival_score = 0.55

    drawdown_avoidance = _clip((ward_feed.escape_pressure * 0.50) + (survival_score * 0.50))
    warning_accuracy = 0.70 if ward_feed.warning_flags else 0.60
    score = _clip((survival_score * 0.50) + (drawdown_avoidance * 0.30) + (warning_accuracy * 0.20))

    return WardFitness(
        score=score,
        survival_score=_clip(survival_score),
        drawdown_avoidance=drawdown_avoidance,
        warning_accuracy=warning_accuracy,
    )


def _clip(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)
