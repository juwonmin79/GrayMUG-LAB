from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from .accumulation_features import compute_accumulation_features
    from .event_classifier import classify_event, decision_bias
    from .event_layer import build_events_from_signals
    from .pre_spike_features import build_multitimeframe_snapshot, compute_pre_spike_features
except ImportError:
    from accumulation_features import compute_accumulation_features
    from event_classifier import classify_event, decision_bias
    from event_layer import build_events_from_signals
    from pre_spike_features import build_multitimeframe_snapshot, compute_pre_spike_features


HELLHOUND_LIB_VERSION = "0.1.0-event-layer"
DECISION_SCHEMA_VERSION = "hellhound_decision_v1"


def evaluate_symbol(
    symbol: str,
    as_of_time: Optional[str] = None,
    *,
    shadow_signals: Optional[Sequence[Mapping[str, Any]]] = None,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Optional Hound-facing decision API. Default is OFF and fail-safe."""
    try:
        if not _decision_enabled():
            return _neutral_response(
                symbol,
                as_of_time=as_of_time,
                error="HELLHOUND_DECISION_ENABLED is false; decision API is fail-safe OFF.",
            )
        normalized_symbol = str(symbol).upper()
        signals = [
            signal
            for signal in (shadow_signals or [])
            if str(signal.get("symbol") or "").upper() == normalized_symbol
        ]
        if not signals:
            return _neutral_response(
                normalized_symbol,
                as_of_time=as_of_time,
                error="No Hellhound shadow signals were provided for event evaluation.",
            )

        event_result = build_events_from_signals(signals)
        events = event_result.events
        if not events:
            return _neutral_response(
                normalized_symbol,
                as_of_time=as_of_time,
                error="No Hellhound event could be built from provided signals.",
            )
        event = events[-1]
        primary_candles = _primary_candles(candles_by_timeframe or {})
        features = compute_pre_spike_features(primary_candles) if primary_candles else {}
        snapshot = build_multitimeframe_snapshot(normalized_symbol, candles_by_timeframe)
        classification = classify_event(event, features)
        accumulation = (
            compute_accumulation_features(
                normalized_symbol,
                historical_candles,
                event_history=event_history,
            )
            if historical_candles
            else {}
        )
        accumulation_score = accumulation.get("accumulation_score", classification["accumulation_score"])
        repeat_activity_score = accumulation.get("repeat_activity_score", 0.0)
        structure_score = accumulation.get("structure_score", 0.0)
        hellhound_score = accumulation.get(
            "hellhound_score",
            round(
                min(
                    max(
                        float(accumulation_score) * 0.5
                        + classification["pre_spike_score"] * 0.3
                        + float(structure_score) * 0.2,
                        0.0,
                    ),
                    1.0,
                ),
                4,
            ),
        )
        bias = decision_bias(classification)
        reasons = list(classification["reasons"])
        if event_result.duplicate_count:
            reasons.append(f"Deduped {event_result.duplicate_count} duplicate shadow signals for event analysis.")
        if not primary_candles:
            reasons.append("Pre-spike features are placeholders because no candle snapshot was provided.")

        return {
            "hellhound_lib_version": HELLHOUND_LIB_VERSION,
            "decision_schema_version": DECISION_SCHEMA_VERSION,
            "symbol": normalized_symbol,
            "as_of_time": as_of_time or _now_utc(),
            "event_id": event["event_id"],
            "event_state": event["event_state"],
            "accumulation_score": accumulation_score,
            "pre_spike_score": classification["pre_spike_score"],
            "repeat_activity_score": repeat_activity_score,
            "structure_score": structure_score,
            "hellhound_score": hellhound_score,
            "structure_type": accumulation.get("structure_type", classification["structure_type"]),
            "setup_type": accumulation.get("setup_type"),
            "distribution_risk": accumulation.get("distribution_risk", classification["distribution_risk"]),
            "entry_bias": bias["entry_bias"],
            "recommended_tp": bias["recommended_tp"],
            "recommended_sl": bias["recommended_sl"],
            "confidence": bias["confidence"],
            "reasons": reasons,
            "event": event,
            "mtf_snapshot": snapshot,
            "accumulation_context": accumulation or None,
        }
    except Exception as exc:  # Defensive API boundary for future Production Hound imports.
        return _neutral_response(symbol, as_of_time=as_of_time, error=str(exc))


def _neutral_response(symbol: str, *, as_of_time: Optional[str], error: str) -> Dict[str, Any]:
    return {
        "hellhound_lib_version": HELLHOUND_LIB_VERSION,
        "decision_schema_version": DECISION_SCHEMA_VERSION,
        "symbol": str(symbol).upper(),
        "as_of_time": as_of_time or _now_utc(),
        "event_id": None,
        "event_state": "unavailable",
        "accumulation_score": 0.0,
        "pre_spike_score": 0.0,
        "repeat_activity_score": 0.0,
        "structure_score": 0.0,
        "hellhound_score": 0.0,
        "structure_type": "UNAVAILABLE",
        "setup_type": None,
        "distribution_risk": 0.0,
        "entry_bias": "neutral",
        "recommended_tp": "none",
        "recommended_sl": "none",
        "confidence": 0,
        "reasons": ["Hellhound decision API returned fail-safe neutral."],
        "error": error,
    }


def _decision_enabled() -> bool:
    raw = os.environ.get("HELLHOUND_DECISION_ENABLED", "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _primary_candles(
    candles_by_timeframe: Mapping[str, Sequence[Mapping[str, Any]]]
) -> Sequence[Mapping[str, Any]]:
    for timeframe in ("15m", "1h", "4h", "1m", "1d", "1w"):
        candles = candles_by_timeframe.get(timeframe)
        if candles:
            return candles
    return []


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
