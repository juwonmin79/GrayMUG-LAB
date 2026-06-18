from __future__ import annotations

from research.calibration.calibration_schema import EngineCalibrationScope


ENGINE_SCOPES = {
    "CORE": EngineCalibrationScope(
        engine="CORE",
        allowed_scope="BTC_ACCUMULATION_REFERENCE",
        forbidden="FINAL_STRATEGY_DECISION",
    ),
    "WARD": EngineCalibrationScope(
        engine="WARD",
        allowed_scope="RISK_HINT",
        forbidden="FINAL_DEFENSE_DECISION",
    ),
    "HOUND": EngineCalibrationScope(
        engine="HOUND",
        allowed_scope="TARGET_PRIORITY_BOOST",
        forbidden="DETECTION_LOGIC_REPLACEMENT",
    ),
}


def get_engine_scope(engine: str) -> EngineCalibrationScope:
    normalized = str(engine).upper()
    if normalized not in ENGINE_SCOPES:
        raise ValueError(f"unsupported engine for calibration: {engine}")
    return ENGINE_SCOPES[normalized]
