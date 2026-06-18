from __future__ import annotations

from typing import Dict

from research.execution.execution_schema import PatternHint


def classify_pattern(
    target_payload: Dict,
    calibration_payload: Dict,
) -> PatternHint:
    signals = {signal["engine"]: signal for signal in calibration_payload["signals"]}
    hound_weight = float(signals["HOUND"]["final_weight"])
    hound_strength = float(signals["HOUND"]["signal_strength"])
    ward_weight = float(signals["WARD"]["final_weight"])
    core_weight = float(signals["CORE"]["final_weight"])

    if ward_weight >= 0.10:
        return PatternHint(
            pattern_name="DISTRIBUTION_RISK",
            confidence=ward_weight,
            description="Ward risk calibration is elevated; distribution risk should be watched.",
        )
    if hound_strength >= 0.80 and hound_weight >= 0.20:
        return PatternHint(
            pattern_name="CHAIN_ROTATION",
            confidence=hound_weight,
            description="Hound target pressure and calibrated Lead Line strength are high.",
        )
    if core_weight >= 0.15:
        return PatternHint(
            pattern_name="BTC_HIDE",
            confidence=core_weight,
            description="Core BTC accumulation reference is dominant; avoid overreading alt pressure.",
        )
    if hound_strength >= 0.50:
        return PatternHint(
            pattern_name="SLOW_CREEP",
            confidence=hound_weight,
            description="Target pressure exists but requires confirmation.",
        )
    return PatternHint(
        pattern_name="SHOCK_PUMP",
        confidence=max(hound_weight, ward_weight, core_weight),
        description="Abrupt target pressure without enough calibrated confirmation.",
    )
