from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional, Sequence


def optional_hellhound_decision(
    symbol: str,
    signal: Optional[Mapping[str, Any]] = None,
    shadow_signals: Optional[Sequence[Mapping[str, Any]]] = None,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
    as_of_time: Optional[str] = None,
    decision_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Example-only Hound integration point. Production Hound is not modified here."""
    if not _decision_enabled(decision_enabled):
        return _neutral_shadow_advice(symbol, "Hellhound optional decision import is disabled.")

    try:
        try:
            from .decision_api import evaluate_symbol
            from .promotion_candidate import build_shadow_decision
        except ImportError:
            from decision_api import evaluate_symbol
            from promotion_candidate import build_shadow_decision
    except Exception as exc:
        return _neutral_shadow_advice(symbol, f"Hellhound optional import failed: {exc}")

    try:
        signals = list(shadow_signals or [])
        if signal and not signals:
            signals = [signal]
        evaluation = evaluate_symbol(
            symbol,
            as_of_time=as_of_time,
            shadow_signals=signals,
            candles_by_timeframe=candles_by_timeframe,
            historical_candles=historical_candles,
            event_history=event_history,
            decision_enabled=decision_enabled,
        )
        if evaluation.get("error"):
            return _neutral_shadow_advice(symbol, str(evaluation["error"]))
        promotion = build_shadow_decision(
            symbol=symbol,
            setup_type=str(evaluation.get("setup_type") or "UNKNOWN"),
            structure_type=str(evaluation.get("structure_type") or "UNKNOWN"),
            hellhound_score=float(evaluation.get("hellhound_score") or 0.0),
            accumulation_score=float(evaluation.get("accumulation_score") or 0.0),
            repeat_activity_score=float(evaluation.get("repeat_activity_score") or 0.0),
            distribution_risk=float(evaluation.get("distribution_risk") or 0.0),
        )
        return {
            "symbol": str(symbol).upper(),
            "hellhound_score": evaluation.get("hellhound_score", 0.0),
            "accumulation_score": evaluation.get("accumulation_score", 0.0),
            "repeat_activity_score": evaluation.get("repeat_activity_score", 0.0),
            "structure_type": evaluation.get("structure_type", "UNKNOWN"),
            "setup_type": evaluation.get("setup_type"),
            "promotion_status": promotion["promotion_status"],
            "advisory": _advisory(promotion["promotion_status"]),
            "distribution_risk": evaluation.get("distribution_risk", 0.0),
            "entry_bias": "neutral",
            "reasons": list(evaluation.get("reasons") or []) + promotion["reasons"],
            "event_id": evaluation.get("event_id"),
            "decision_source": "decision_api",
            "is_trade_command": False,
        }
    except Exception as exc:
        return _neutral_shadow_advice(symbol, str(exc))


def _neutral_shadow_advice(symbol: str, error: str) -> Dict[str, Any]:
    return {
        "symbol": str(symbol).upper(),
        "hellhound_score": 0.0,
        "accumulation_score": 0.0,
        "repeat_activity_score": 0.0,
        "structure_type": "UNAVAILABLE",
        "setup_type": None,
        "promotion_status": "WATCH",
        "advisory": "WATCH_NEUTRAL",
        "distribution_risk": 0.0,
        "entry_bias": "neutral",
        "reasons": ["Hellhound Shadow Advisor returned fail-safe neutral."],
        "event_id": None,
        "decision_source": "fail_safe",
        "is_trade_command": False,
        "error": error,
    }


def _decision_enabled(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return explicit
    return os.environ.get("HELLHOUND_DECISION_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _advisory(promotion_status: Any) -> str:
    status = str(promotion_status or "WATCH").upper()
    if status == "PROMOTE":
        return "WATCH_STRONG"
    if status == "REJECT":
        return "AVOID"
    return "WATCH"
