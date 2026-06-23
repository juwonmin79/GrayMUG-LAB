from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from .integration_stub import optional_hellhound_decision
    from .real_shadow_feed import build_real_shadow_decision, detect_daily_open_clusters
    from .shadow_advisor import run_shadow_evaluation_pipeline
except ImportError:
    from integration_stub import optional_hellhound_decision
    from real_shadow_feed import build_real_shadow_decision, detect_daily_open_clusters
    from shadow_advisor import run_shadow_evaluation_pipeline


HELLHOUND_INTERFACE_VERSION = "hellhound_library_interface_v1"
LOGGER = logging.getLogger("hellhound.library_interface")


def evaluate_signal_row(
    signal: Mapping[str, Any],
    *,
    shadow_signals: Optional[Sequence[Mapping[str, Any]]] = None,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
    decision_enabled: Optional[bool] = True,
) -> Dict[str, Any]:
    """Pure library boundary for a Hound/Hellhound signal row."""
    symbol = str(signal.get("symbol") or signal.get("market") or "").upper()
    if not symbol:
        return _interface_fail_safe("signal row is missing symbol")
    result = optional_hellhound_decision(
        symbol=symbol,
        signal=signal,
        shadow_signals=shadow_signals,
        candles_by_timeframe=candles_by_timeframe,
        historical_candles=historical_candles,
        event_history=event_history,
        decision_enabled=decision_enabled,
    )
    if _needs_signal_fallback(result):
        _log_fallback(
            "signal",
            symbol,
            result,
            candles_by_timeframe=candles_by_timeframe,
            historical_candles=historical_candles,
        )
        result = _fallback_signal_decision(symbol, signal, source_error=result.get("error"))
    return _with_boundary(
        result,
        input_type="signal",
        output_type="shadow_decision",
    )


def evaluate_event_row(
    event: Mapping[str, Any],
    *,
    signal: Optional[Mapping[str, Any]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    decision_enabled: Optional[bool] = True,
) -> Dict[str, Any]:
    """Pure library boundary for an event row. Persistence is intentionally out of scope."""
    symbol = str(event.get("symbol") or (signal or {}).get("symbol") or "").upper()
    if not symbol:
        return _interface_fail_safe("event row is missing symbol")
    input_signal = signal or {
        "id": event.get("event_id"),
        "symbol": symbol,
        "source_time": event.get("first_seen_time") or event.get("last_seen_time"),
        "hypothesis": {"name": "event-row"},
        "shadow_action": "WATCH",
        "pattern": event.get("event_state") or "EVENT_ROW",
    }
    result = optional_hellhound_decision(
        symbol=symbol,
        signal=input_signal,
        shadow_signals=[input_signal],
        historical_candles=historical_candles,
        event_history=[event],
        decision_enabled=decision_enabled,
    )
    return _with_boundary(
        result,
        input_type="event",
        output_type="advisor_result",
    )


def evaluate_snapshot_row(
    snapshot: Mapping[str, Any],
    *,
    signal: Optional[Mapping[str, Any]] = None,
    decision_enabled: Optional[bool] = True,
) -> Dict[str, Any]:
    """Pure library boundary for a snapshot row. Snapshot rows are advisory only."""
    symbol = str(snapshot.get("symbol") or (signal or {}).get("symbol") or "").upper()
    if not symbol:
        return _interface_fail_safe("snapshot row is missing symbol")
    input_signal = signal or {
        "id": snapshot.get("id"),
        "symbol": symbol,
        "source_time": snapshot.get("as_of_time") or snapshot.get("snapshot_time"),
        "hypothesis": {"name": "snapshot-row"},
        "shadow_action": "WATCH",
        "pattern": "SNAPSHOT_ROW",
    }
    candles_by_timeframe = _snapshot_candles_by_timeframe(snapshot)
    historical_candles = _snapshot_historical_candles(snapshot, candles_by_timeframe)
    pipeline = run_shadow_evaluation_pipeline(
        symbol=symbol,
        signal=input_signal,
        shadow_signals=[input_signal],
        candles_by_timeframe=candles_by_timeframe,
        historical_candles=historical_candles,
        log_path=None,
        decision_enabled=decision_enabled,
    )
    decision = dict(pipeline.get("hellhound_decision") or {})
    if _needs_signal_fallback(decision):
        _log_fallback(
            "snapshot",
            symbol,
            decision,
            candles_by_timeframe=candles_by_timeframe,
            historical_candles=historical_candles,
        )
    return _with_boundary(
        pipeline,
        input_type="snapshot",
        output_type="advisor_result",
    )


def detect_cluster_rows(
    signals: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    clusters = detect_daily_open_clusters(signals)
    return {
        "hellhound_interface_version": HELLHOUND_INTERFACE_VERSION,
        "input_type": "signal_batch",
        "output_type": "cluster",
        "clusters": clusters,
        "cluster_count": len(clusters),
        "is_trade_command": False,
    }


def evaluate_real_feed_row(
    signal: Mapping[str, Any],
    *,
    outcome_rows: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    result = build_real_shadow_decision(signal, outcome_rows=outcome_rows)
    return _with_boundary(
        result,
        input_type="signal",
        output_type="shadow_decision",
    )


def _with_boundary(
    payload: Mapping[str, Any],
    *,
    input_type: str,
    output_type: str,
) -> Dict[str, Any]:
    result = dict(payload)
    if "fallback_used" not in result:
        result["fallback_used"] = str(result.get("decision_source") or "").lower() in {"signal_fallback", "fail_safe"}
    result["hellhound_interface_version"] = HELLHOUND_INTERFACE_VERSION
    result["input_type"] = input_type
    result["output_type"] = output_type
    result["is_trade_command"] = False
    result["entry_bias"] = "neutral"
    return result


def _needs_signal_fallback(result: Mapping[str, Any]) -> bool:
    error = str(result.get("error") or "").lower()
    reasons = " ".join(str(reason) for reason in result.get("reasons") or []).lower()
    structure = str(result.get("structure_type") or "").upper()
    score = _to_float(result.get("hellhound_score"))
    if "optional decision import is disabled" in error:
        return True
    if "optional import failed" in error:
        return True
    if "fail-safe neutral" in reasons and structure in {"UNAVAILABLE", "UNKNOWN", ""} and score == 0.0:
        return True
    return False


def _log_fallback(
    input_type: str,
    symbol: str,
    result: Mapping[str, Any],
    *,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
) -> None:
    reasons = list(result.get("reasons") or [])
    source_error = result.get("error")
    score = _to_float(result.get("hellhound_score"))
    LOGGER.warning(
        "Hellhound fallback used input_type=%s symbol=%s score=%.4f source_error=%s reasons=%s candles_15m=%s historical_candles=%s decision_source=%s",
        input_type,
        str(symbol).upper(),
        score,
        source_error,
        reasons,
        len((candles_by_timeframe or {}).get("15m") or []),
        len(historical_candles or []),
        result.get("decision_source"),
    )


def _fallback_signal_decision(
    symbol: str,
    signal: Mapping[str, Any],
    *,
    source_error: Any = None,
) -> Dict[str, Any]:
    reasons = _reason_list(signal.get("reasons"))
    rsi = _to_float(signal.get("rsi"))
    volume_ratio = _to_float(signal.get("volume_ratio"))
    taker_buy_ratio = _to_float(signal.get("taker_buy_ratio"))
    rs_rising = _to_bool(signal.get("rs_rising"))
    passes_entry = _to_bool(signal.get("passes_entry"))
    is_whale = _to_bool(signal.get("is_whale"))
    volume_spike = _to_bool(signal.get("volume_spike"))

    score = 0.05
    score += min(volume_ratio, 4.0) / 4.0 * 0.25
    if rs_rising:
        score += 0.18
    if 40.0 <= rsi <= 70.0:
        score += 0.18
    elif rsi >= 70.0:
        score += 0.04
    if taker_buy_ratio >= 0.55:
        score += min(taker_buy_ratio - 0.5, 0.3) / 0.3 * 0.12
    if passes_entry:
        score += 0.17
    if is_whale:
        score += 0.12
    if volume_spike:
        score += 0.06

    negative_reason_count = sum(1 for reason in reasons if _is_negative_reason(reason))
    score -= min(negative_reason_count, 3) * 0.08
    score = _clamp(score)

    structure_type = _fallback_structure_type(
        rsi=rsi,
        volume_ratio=volume_ratio,
        rs_rising=rs_rising,
        passes_entry=passes_entry,
        is_whale=is_whale,
        reasons=reasons,
    )
    promotion_status = _promotion_status(score)

    fallback_reasons = [
        "signal fallback evaluation used because optional Hellhound decision was unavailable.",
        f"structure_type={structure_type} from signal fields.",
        f"hellhound_score={score:.4f} from volume/RS/RSI/taker/entry/whale factors.",
    ]
    if source_error:
        fallback_reasons.append(f"source_error={source_error}")
    fallback_reasons.extend(reasons)

    return {
        "symbol": str(symbol).upper(),
        "hellhound_score": score,
        "accumulation_score": 0.0,
        "repeat_activity_score": 0.0,
        "structure_type": structure_type,
        "setup_type": structure_type,
        "promotion_status": promotion_status,
        "advisory": _advisory(promotion_status),
        "distribution_risk": 0.0,
        "entry_bias": "neutral",
        "reasons": fallback_reasons,
        "event_id": signal.get("event_id"),
        "decision_source": "signal_fallback",
        "fallback_used": True,
        "is_trade_command": False,
    }


def _fallback_structure_type(
    *,
    rsi: float,
    volume_ratio: float,
    rs_rising: bool,
    passes_entry: bool,
    is_whale: bool,
    reasons: Sequence[str],
) -> str:
    reason_text = " ".join(reasons).lower()
    if rsi >= 70.0 or "candle_tail" in reason_text:
        return "ACT"
    if volume_ratio >= 2.0 and rs_rising and 40.0 <= rsi <= 70.0:
        return "BEL"
    if passes_entry and is_whale:
        return "ACE"
    if passes_entry or is_whale:
        return "BEL"
    if volume_ratio > 0.0 or rsi > 0.0:
        return "NIGHT"
    return "UNCLASSIFIED"


def _promotion_status(score: float) -> str:
    if score >= 0.65:
        return "PROMOTE"
    if score >= 0.35:
        return "WATCH"
    return "REJECT"


def _advisory(promotion_status: str) -> str:
    status = str(promotion_status or "WATCH").upper()
    if status == "PROMOTE":
        return "WATCH_STRONG"
    if status == "REJECT":
        return "AVOID"
    return "WATCH"


def _is_negative_reason(reason: str) -> bool:
    lowered = str(reason or "").lower()
    return any(token in lowered for token in ("reject", "avoid", "negative", "distribution", "weak", "risk"))


def _reason_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [str(item) for item in value if item is not None]
    return []


def _snapshot_candles_by_timeframe(
    snapshot: Mapping[str, Any],
) -> Optional[Dict[str, Sequence[Mapping[str, Any]]]]:
    if not isinstance(snapshot, Mapping):
        return None
    candidates = (
        snapshot.get("candles_by_timeframe"),
        snapshot.get("timeframes"),
    )
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            return _normalize_timeframe_keys(candidate)
    frames: Dict[str, Sequence[Mapping[str, Any]]] = {}
    for key, timeframe in (
        ("candles_1m", "1m"),
        ("candles_15m", "15m"),
        ("candles_1h", "1h"),
        ("candles_4h", "4h"),
        ("candles_1d", "1d"),
        ("candles_1w", "1w"),
    ):
        candles = snapshot.get(key)
        if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes, bytearray)):
            frames[timeframe] = candles
    return frames or None


def _snapshot_historical_candles(
    snapshot: Mapping[str, Any],
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]],
) -> Optional[Sequence[Mapping[str, Any]]]:
    candles = snapshot.get("historical_candles") if isinstance(snapshot, Mapping) else None
    if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes, bytearray)):
        return candles
    for timeframe in ("1d", "4h", "1h", "15m", "1m", "1w"):
        frame = (candles_by_timeframe or {}).get(timeframe)
        if frame:
            return frame
    return None


def _normalize_timeframe_keys(
    frames: Mapping[str, Any],
) -> Dict[str, Sequence[Mapping[str, Any]]]:
    aliases = {
        "1min": "1m",
        "15min": "15m",
        "60m": "1h",
        "1hour": "1h",
        "4hour": "4h",
        "1day": "1d",
        "1week": "1w",
    }
    normalized: Dict[str, Sequence[Mapping[str, Any]]] = {}
    for raw_key, value in frames.items():
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            continue
        key = str(raw_key).strip().lower()
        timeframe = aliases.get(key, key)
        normalized[timeframe] = value
    return normalized


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float) -> float:
    return round(min(max(float(value), 0.0), 1.0), 4)


def _interface_fail_safe(error: str) -> Dict[str, Any]:
    return {
        "hellhound_interface_version": HELLHOUND_INTERFACE_VERSION,
        "input_type": "unknown",
        "output_type": "fail_safe",
        "entry_bias": "neutral",
        "promotion_status": "WATCH",
        "reasons": ["Hellhound library interface returned fail-safe neutral."],
        "decision_source": "fail_safe",
        "fallback_used": True,
        "is_trade_command": False,
        "error": error,
    }
