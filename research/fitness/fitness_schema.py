from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class CoreFitness:
    score: float
    btc_accumulation_score: float
    btc_relative_alpha: float
    focus_assets: List[str]


@dataclass
class WardFitness:
    score: float
    survival_score: float
    drawdown_avoidance: float
    warning_accuracy: float


@dataclass
class HoundFitness:
    score: float
    hit_rate: float
    forward_return_score: float
    target_accuracy: float


@dataclass
class FitnessReport:
    timestamp: int
    core: CoreFitness
    ward: WardFitness
    hound: HoundFitness
    overall_score: float
