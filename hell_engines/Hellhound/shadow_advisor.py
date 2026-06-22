from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


SHADOW_ADVISOR_SCHEMA_VERSION = "hellhound_shadow_advisor_v1"
DEFAULT_SHADOW_LOG_PATH = Path(__file__).resolve().parent / "shadow_decision_log.jsonl"


def run_shadow_evaluation_pipeline(
    *,
    symbol: str,
    signal: Mapping[str, Any],
    shadow_signals: Optional[Sequence[Mapping[str, Any]]] = None,
    historical_candles: Optional[Sequence[Mapping[str, Any]]] = None,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
    log_path: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Hound Signal -> Hellhound Evaluate -> Shadow Decision -> file log only."""
    try:
        try:
            from .integration_stub import optional_hellhound_decision
        except ImportError:
            from integration_stub import optional_hellhound_decision

        decision = optional_hellhound_decision(
            symbol=symbol,
            signal=signal,
            shadow_signals=shadow_signals,
            historical_candles=historical_candles,
            event_history=event_history,
        )
        audit = audit_decision(
            symbol=symbol,
            signal_time=str(signal.get("source_time") or signal.get("created_at") or _now_utc()),
            event_id=decision.get("event_id"),
            hellhound_score=float(decision.get("hellhound_score") or 0.0),
            promotion_status=str(decision.get("promotion_status") or "WATCH"),
            entry_bias=str(decision.get("entry_bias") or "neutral"),
        )
        if log_path is not None:
            write_shadow_decision_log(audit, log_path=log_path)
        return {
            "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
            "pipeline": "Hound Signal -> Hellhound Evaluate -> Shadow Decision -> Log Only",
            "symbol": str(symbol).upper(),
            "hound_signal": dict(signal),
            "hellhound_decision": decision,
            "audit": audit,
            "is_trade_command": False,
        }
    except Exception as exc:
        return {
            "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
            "symbol": str(symbol).upper(),
            "hellhound_decision": _neutral_advice(symbol, str(exc)),
            "is_trade_command": False,
            "error": str(exc),
        }


def audit_decision(
    *,
    symbol: str,
    signal_time: str,
    event_id: Optional[str],
    hellhound_score: float,
    promotion_status: str,
    entry_bias: str,
    actual_1h_outcome: Optional[str] = None,
    actual_4h_outcome: Optional[str] = None,
    actual_24h_outcome: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
        "symbol": str(symbol).upper(),
        "signal_time": signal_time,
        "event_id": event_id,
        "hellhound_score": round(min(max(float(hellhound_score), 0.0), 1.0), 4),
        "promotion_status": str(promotion_status or "WATCH").upper(),
        "entry_bias": str(entry_bias or "neutral"),
        "actual_1h_outcome": actual_1h_outcome,
        "actual_4h_outcome": actual_4h_outcome,
        "actual_24h_outcome": actual_24h_outcome,
        "is_trade_command": False,
    }


def write_shadow_decision_log(
    audit_row: Mapping[str, Any],
    *,
    log_path: Union[Path, str] = DEFAULT_SHADOW_LOG_PATH,
) -> Dict[str, Any]:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(dict(audit_row), sort_keys=True) + "\n")
    return {
        "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
        "log_path": str(path),
        "written": True,
        "is_trade_command": False,
    }


def replay_validation(cases: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    rows = []
    for case in cases:
        hound_signal = dict(case.get("hound_signal") or {})
        decision = dict(case.get("hellhound_decision") or {})
        outcome = dict(case.get("actual_outcome") or {})
        rows.append(
            {
                "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
                "symbol": str(case.get("symbol") or hound_signal.get("symbol") or decision.get("symbol") or "").upper(),
                "setup_type": decision.get("setup_type"),
                "hound_signal": hound_signal,
                "hellhound_decision": decision,
                "actual_outcome": outcome,
                "comparison": _compare_decision_to_outcome(decision, outcome),
                "is_trade_command": False,
            }
        )
    return rows


def analyze_false_positives(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    failure_reasons: Counter[str] = Counter()
    success_reasons: Counter[str] = Counter()
    false_positive_count = 0
    false_negative_count = 0
    for row in rows:
        decision = row.get("hellhound_decision") or row
        outcome = row.get("actual_outcome") or row
        promotion = str(decision.get("promotion_status") or "").upper()
        success = _is_success_outcome(outcome)
        reasons = [str(reason) for reason in decision.get("reasons") or ["unknown"]]
        if promotion == "PROMOTE" and success is False:
            false_positive_count += 1
            failure_reasons.update(reasons)
        elif promotion == "REJECT" and success is True:
            false_negative_count += 1
            success_reasons.update(reasons)
    return {
        "shadow_advisor_schema_version": SHADOW_ADVISOR_SCHEMA_VERSION,
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "top_failure_reasons": _counter_rows(failure_reasons),
        "top_success_reasons": _counter_rows(success_reasons),
        "is_trade_command": False,
    }


def _compare_decision_to_outcome(
    decision: Mapping[str, Any], outcome: Mapping[str, Any]
) -> str:
    promotion = str(decision.get("promotion_status") or "").upper()
    success = _is_success_outcome(outcome)
    if success is None:
        return "PENDING"
    if promotion == "PROMOTE" and success:
        return "PROMOTE_SUCCESS"
    if promotion == "PROMOTE" and not success:
        return "PROMOTE_FAIL"
    if promotion == "REJECT" and success:
        return "REJECT_SUCCESS_FALSE_NEGATIVE"
    if promotion == "REJECT" and not success:
        return "REJECT_FAIL_AVOIDED"
    return "WATCH_OBSERVED"


def _is_success_outcome(outcome: Mapping[str, Any]) -> Optional[bool]:
    values = [
        outcome.get("actual_1h_outcome"),
        outcome.get("actual_4h_outcome"),
        outcome.get("actual_24h_outcome"),
        outcome.get("result"),
    ]
    normalized = [str(value).upper() for value in values if value is not None]
    if not normalized:
        return None
    if "SUCCESS" in normalized:
        return True
    if "FAIL" in normalized:
        return False
    return None


def _counter_rows(counter: Counter[str]) -> list[Dict[str, Any]]:
    return [
        {"reason": reason, "count": count}
        for reason, count in counter.most_common(5)
    ]


def _neutral_advice(symbol: str, error: str) -> Dict[str, Any]:
    return {
        "symbol": str(symbol).upper(),
        "hellhound_score": 0.0,
        "accumulation_score": 0.0,
        "repeat_activity_score": 0.0,
        "structure_type": "UNAVAILABLE",
        "setup_type": None,
        "promotion_status": "WATCH",
        "distribution_risk": 0.0,
        "entry_bias": "neutral",
        "reasons": ["Hellhound Shadow Advisor returned fail-safe neutral."],
        "is_trade_command": False,
        "error": error,
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
