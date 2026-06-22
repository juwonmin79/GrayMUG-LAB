from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

try:
    from .library_interface import evaluate_signal_row
except ImportError:
    from library_interface import evaluate_signal_row


PRODUCTION_INTERFACE_VERSION = "hellhound_production_interface_v1"
SHADOW_MODE = "shadow"


def validate_production_interface_input(payload: Mapping[str, Any]) -> Dict[str, Any]:
    errors = []
    if payload.get("interface_version") != PRODUCTION_INTERFACE_VERSION:
        errors.append("interface_version must be hellhound_production_interface_v1.")
    if str(payload.get("mode") or "").lower() != SHADOW_MODE:
        errors.append("mode must be shadow.")
    cases = payload.get("cases")
    if cases is None:
        errors.append("cases is required.")
    elif not isinstance(cases, list):
        errors.append("cases must be a list.")
    return {
        "interface_version": PRODUCTION_INTERFACE_VERSION,
        "valid": not errors,
        "errors": errors,
        "is_trade_command": False,
    }


def evaluate_case(case: Mapping[str, Any]) -> Dict[str, Any]:
    case_errors = _validate_case(case)
    if case_errors:
        return _case_fail_safe(case, "; ".join(case_errors))

    case_id = str(case.get("case_id"))
    symbol = str(case.get("symbol")).upper()
    signal = dict(case.get("signal") or {})
    signal.setdefault("symbol", symbol)

    decision = evaluate_signal_row(
        signal,
        shadow_signals=case.get("shadow_signals") or [signal],
        candles_by_timeframe=_candles_by_timeframe(case),
        historical_candles=case.get("historical_candles"),
        event_history=case.get("event_history"),
        decision_enabled=case.get("decision_enabled", True),
    )
    result = {
        "case_id": case_id,
        "symbol": symbol,
        "structure_type": decision.get("setup_type") or decision.get("structure_type") or "UNKNOWN",
        "promotion_status": str(decision.get("promotion_status") or "WATCH").upper(),
        "hellhound_score": _clamp(decision.get("hellhound_score")),
        "entry_bias": "neutral",
        "advisory": _advisory(promotion_status=str(decision.get("promotion_status") or "WATCH")),
        "risk_note": "shadow_only",
        "reasons": list(decision.get("reasons") or []),
        "event_id": decision.get("event_id"),
        "source_interface_version": decision.get("hellhound_interface_version"),
        "is_trade_command": False,
    }
    if decision.get("error"):
        result["error"] = decision["error"]
    return enforce_non_trade_output(result)


def evaluate_cases(cases: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    return [evaluate_case(case) for case in cases]


def build_production_interface_response(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return enforce_non_trade_output(
        {
            "interface_version": PRODUCTION_INTERFACE_VERSION,
            "mode": SHADOW_MODE,
            "is_trade_command": False,
            "results": [dict(result) for result in results],
        }
    )


def enforce_non_trade_output(payload: Any) -> Any:
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            sanitized[key] = enforce_non_trade_output(value)
        sanitized["is_trade_command"] = False
        if "entry_bias" in sanitized:
            sanitized["entry_bias"] = "neutral"
        return sanitized
    if isinstance(payload, list):
        return [enforce_non_trade_output(item) for item in payload]
    return payload


def evaluate_production_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    validation = validate_production_interface_input(payload)
    if not validation["valid"]:
        return build_production_interface_response(
            [
                _case_fail_safe(
                    {"case_id": None, "symbol": None},
                    "; ".join(validation["errors"]),
                )
            ]
        )
    return build_production_interface_response(evaluate_cases(payload.get("cases") or []))


def _validate_case(case: Any) -> list[str]:
    if not isinstance(case, Mapping):
        return ["case must be an object."]
    errors = []
    if not case.get("case_id"):
        errors.append("case_id is required.")
    if not case.get("symbol"):
        errors.append("symbol is required.")
    signal = case.get("signal")
    if signal is not None and not isinstance(signal, Mapping):
        errors.append("signal must be an object when provided.")
    snapshot = case.get("snapshot")
    if snapshot is not None and not isinstance(snapshot, Mapping):
        errors.append("snapshot must be an object when provided.")
    return errors


def _case_fail_safe(case: Mapping[str, Any], error: str) -> Dict[str, Any]:
    symbol = str(case.get("symbol") or "").upper() or None
    case_id = case.get("case_id")
    return {
        "case_id": str(case_id) if case_id is not None else None,
        "symbol": symbol,
        "structure_type": "UNKNOWN",
        "promotion_status": "WATCH",
        "hellhound_score": 0.0,
        "entry_bias": "neutral",
        "advisory": "WATCH_NEUTRAL",
        "risk_note": "shadow_only",
        "reasons": ["Hellhound production interface returned fail-safe neutral."],
        "event_id": None,
        "error": error,
        "is_trade_command": False,
    }


def _candles_by_timeframe(case: Mapping[str, Any]) -> Any:
    if case.get("candles_by_timeframe"):
        return case.get("candles_by_timeframe")
    snapshot = case.get("snapshot") or {}
    if not isinstance(snapshot, Mapping):
        return None
    if snapshot.get("candles_by_timeframe"):
        return snapshot.get("candles_by_timeframe")
    if snapshot.get("timeframes"):
        return snapshot.get("timeframes")
    return None


def _advisory(*, promotion_status: str) -> str:
    status = str(promotion_status or "WATCH").upper()
    if status == "PROMOTE":
        return "WATCH_STRONG"
    if status == "REJECT":
        return "AVOID"
    return "WATCH"


def _clamp(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(max(numeric, 0.0), 1.0), 4)
