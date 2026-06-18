from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from research.calibration.calibration_policy import get_max_influence, get_policy_reason
from research.calibration.calibration_schema import CalibratedSignalPayload, SignalCalibration
from research.calibration.engine_scope import get_engine_scope


def calibrate_signals(
    target_payload: Dict,
    fitness_report: Dict,
) -> Dict:
    timestamp = int(target_payload["timestamp"])
    signals = [
        _build_core_signal(target_payload["core"], fitness_report["core"]),
        _build_ward_signal(target_payload["ward"], fitness_report["ward"]),
        _build_hound_signal(target_payload["hound"], fitness_report["hound"]),
    ]
    payload = CalibratedSignalPayload(
        timestamp=timestamp,
        source="lab_signal_calibration_layer",
        signals=signals,
    )
    return asdict(payload)


def _build_core_signal(core_feed: Dict, core_fitness: Dict) -> SignalCalibration:
    return _build_signal(
        signal_name="core_btc_accumulation_reference",
        engine="CORE",
        signal_strength=float(core_feed["btc_accumulation_bias"]),
        confidence=float(core_fitness["score"]),
    )


def _build_ward_signal(ward_feed: Dict, ward_fitness: Dict) -> SignalCalibration:
    return _build_signal(
        signal_name="ward_risk_hint",
        engine="WARD",
        signal_strength=float(ward_fitness["score"]),
        confidence=float(ward_fitness["score"]),
    )


def _build_hound_signal(hound_feed: Dict, hound_fitness: Dict) -> SignalCalibration:
    return _build_signal(
        signal_name="hound_target_priority_boost",
        engine="HOUND",
        signal_strength=float(hound_feed["hunt_pressure"]),
        confidence=float(hound_fitness["score"]),
    )


def _build_signal(
    signal_name: str,
    engine: str,
    signal_strength: float,
    confidence: float,
) -> SignalCalibration:
    scope = get_engine_scope(engine)
    max_influence = get_max_influence(engine)
    final_weight = _clamp(signal_strength * confidence * max_influence)

    return SignalCalibration(
        signal_name=signal_name,
        engine=engine,
        signal_strength=_clamp(signal_strength),
        confidence=_clamp(confidence),
        application_scope=scope.allowed_scope,
        max_influence=max_influence,
        final_weight=final_weight,
        reason=get_policy_reason(engine),
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)
