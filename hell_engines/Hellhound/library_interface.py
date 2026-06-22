from __future__ import annotations

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


def evaluate_signal_row(
    signal: Mapping[str, Any],
    *,
    shadow_signals: Optional[Sequence[Mapping[str, Any]]] = None,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
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
    )
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
    pipeline = run_shadow_evaluation_pipeline(
        symbol=symbol,
        signal=input_signal,
        shadow_signals=[input_signal],
        log_path=None,
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
    result["hellhound_interface_version"] = HELLHOUND_INTERFACE_VERSION
    result["input_type"] = input_type
    result["output_type"] = output_type
    result["is_trade_command"] = False
    return result


def _interface_fail_safe(error: str) -> Dict[str, Any]:
    return {
        "hellhound_interface_version": HELLHOUND_INTERFACE_VERSION,
        "input_type": "unknown",
        "output_type": "fail_safe",
        "entry_bias": "neutral",
        "promotion_status": "WATCH",
        "reasons": ["Hellhound library interface returned fail-safe neutral."],
        "is_trade_command": False,
        "error": error,
    }
