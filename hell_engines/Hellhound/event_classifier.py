from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

try:
    from .pre_spike_features import pre_spike_score
except ImportError:
    from pre_spike_features import pre_spike_score


CLASSIFIER_SCHEMA_VERSION = "hellhound_event_classifier_v1"


def classify_event(
    event: Mapping[str, Any],
    features: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    features = features or {}
    observation_count = int(event.get("observation_count") or 0)
    event_age_hours = float(event.get("event_age_hours") or 0.0)
    spike_score = pre_spike_score(features)
    compression = _float_or_zero(features.get("price_compression"))
    vol_rise = _float_or_zero(features.get("micro_vol_rise"))
    rs_slope = _float_or_zero(features.get("rs_slope"))
    spike_count = int(features.get("spike_count_7d") or 0)

    reasons = []
    if event_age_hours >= 24 and observation_count >= 20 and spike_score < 0.35:
        structure_type = "ACT"
        confidence = 0.58
        reasons.append("Long event age with many observations but weak pre-spike score.")
    elif spike_count >= 2 and observation_count >= 10:
        structure_type = "NIGHT"
        confidence = 0.56
        reasons.append("Repeated recent spike behavior with sustained observation timeline.")
    elif spike_score >= 0.62 and observation_count <= 4:
        structure_type = "ACE"
        confidence = 0.52
        reasons.append("Strong spike features with short observation history; late detection risk.")
    elif compression >= 0.45 and vol_rise >= 1.1 and rs_slope >= 0:
        structure_type = "BEL"
        confidence = 0.6
        reasons.append("Compression, volume lift, and non-negative relative strength align.")
    else:
        structure_type = "UNCLASSIFIED"
        confidence = 0.35
        reasons.append("Event does not meet initial BEL/ACT/ACE/NIGHT rules.")

    distribution_risk = _distribution_risk(structure_type, event_age_hours, spike_count, spike_score)
    accumulation_score = _accumulation_score(structure_type, spike_score, compression, vol_rise)
    return {
        "classifier_schema_version": CLASSIFIER_SCHEMA_VERSION,
        "structure_type": structure_type,
        "confidence": round(confidence, 4),
        "accumulation_score": accumulation_score,
        "pre_spike_score": spike_score,
        "distribution_risk": distribution_risk,
        "reasons": reasons,
    }


def decision_bias(classification: Mapping[str, Any]) -> Dict[str, Any]:
    structure_type = classification.get("structure_type")
    confidence = _float_or_zero(classification.get("confidence"))
    pre_spike = _float_or_zero(classification.get("pre_spike_score"))
    distribution = _float_or_zero(classification.get("distribution_risk"))

    if structure_type == "BEL" and pre_spike >= 0.45 and distribution < 0.55:
        entry_bias = "watch"
        tp = "shadow_tp_expansion_case"
        sl = "shadow_sl_structure_break_case"
    elif structure_type == "NIGHT" and distribution < 0.65:
        entry_bias = "wait_confirmation"
        tp = "shadow_tp_reaccumulation_case"
        sl = "shadow_sl_failed_reclaim_case"
    elif structure_type in {"ACT", "ACE"} or distribution >= 0.65:
        entry_bias = "avoid"
        tp = "none"
        sl = "none"
    else:
        entry_bias = "neutral"
        tp = "none"
        sl = "none"

    return {
        "entry_bias": entry_bias,
        "recommended_tp": tp,
        "recommended_sl": sl,
        "confidence": round(min(confidence, 0.75), 4),
    }


def _accumulation_score(structure_type: str, spike_score: float, compression: float, vol_rise: float) -> float:
    base = {
        "BEL": 0.42,
        "NIGHT": 0.34,
        "ACE": 0.18,
        "ACT": 0.12,
    }.get(structure_type, 0.2)
    return round(min(base + spike_score * 0.35 + compression * 0.15 + min(vol_rise, 2.0) * 0.04, 1.0), 4)


def _distribution_risk(structure_type: str, event_age_hours: float, spike_count: int, spike_score: float) -> float:
    base = {
        "ACT": 0.72,
        "ACE": 0.62,
        "NIGHT": 0.45,
        "BEL": 0.28,
    }.get(structure_type, 0.5)
    age_risk = min(event_age_hours / 168.0, 0.2)
    spike_risk = min(spike_count * 0.04, 0.16)
    offset = spike_score * 0.08 if structure_type == "BEL" else 0.0
    return round(min(max(base + age_risk + spike_risk - offset, 0.0), 1.0), 4)


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
