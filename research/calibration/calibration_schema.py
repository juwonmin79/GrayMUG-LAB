from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class SignalCalibration:
    signal_name: str
    engine: str
    signal_strength: float
    confidence: float
    application_scope: str
    max_influence: float
    final_weight: float
    reason: str


@dataclass
class EngineCalibrationScope:
    engine: str
    allowed_scope: str
    forbidden: str


@dataclass
class CalibratedSignalPayload:
    timestamp: int
    source: str
    signals: List[SignalCalibration]
