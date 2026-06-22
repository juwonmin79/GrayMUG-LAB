from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


SUCCESS_CASE_SCHEMA_VERSION = "hellhound_success_case_registry_v1"
DEFAULT_SUCCESS_CASE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_success_cases.jsonl"
SUCCESS_CASE_ID_NAMESPACE = uuid.UUID("37fe36aa-7d2e-4d82-9f2c-d0262169d328")


def create_success_case_record(
    *,
    symbol: str,
    signal_time: Any,
    outcome_time: Any,
    case_name: str,
    shadow_result: Optional[Mapping[str, Any]] = None,
    hellhound_score: Any = None,
    promotion_status: Any = None,
    structure_classification: Any = None,
    mfe_pct: Any = None,
    mae_pct: Any = None,
    notes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    normalized_symbol = str(symbol or "").upper()
    normalized_signal_time = str(signal_time or "")
    normalized_outcome_time = str(outcome_time or "")
    return {
        "success_case_schema_version": SUCCESS_CASE_SCHEMA_VERSION,
        "success_case_id": _stable_success_case_id(normalized_symbol, normalized_signal_time, normalized_outcome_time),
        "case_name": case_name,
        "symbol": normalized_symbol or None,
        "signal_time": normalized_signal_time or None,
        "outcome_time": normalized_outcome_time or None,
        "registered_at": _now_utc(),
        "case_type": "SUCCESS",
        "shadow_result": dict(shadow_result or {}),
        "hellhound_score": _value_or_shadow(shadow_result, hellhound_score, "hellhound_score"),
        "promotion_status": _value_or_shadow(shadow_result, promotion_status, "promotion_status"),
        "structure_classification": _value_or_shadow(
            shadow_result,
            structure_classification,
            "structure_type",
        )
        or _value_or_shadow(shadow_result, structure_classification, "setup_type"),
        "mfe_pct": mfe_pct,
        "mae_pct": mae_pct,
        "notes": list(notes or []),
        "is_trade_command": False,
    }


def write_success_cases(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_SUCCESS_CASE_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            normalized = dict(row)
            normalized["is_trade_command"] = False
            file.write(json.dumps(normalized, sort_keys=True) + "\n")
    return {
        "success_case_schema_version": SUCCESS_CASE_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def register_success_case(
    *,
    symbol: str,
    signal_time: Any,
    outcome_time: Any,
    case_name: str,
    output_path: Union[Path, str] = DEFAULT_SUCCESS_CASE_PATH,
    **kwargs: Any,
) -> Dict[str, Any]:
    record = create_success_case_record(
        symbol=symbol,
        signal_time=signal_time,
        outcome_time=outcome_time,
        case_name=case_name,
        **kwargs,
    )
    write_success_cases([record], output_path=output_path, append=True)
    return record


def _value_or_shadow(shadow_result: Optional[Mapping[str, Any]], explicit: Any, key: str) -> Any:
    if explicit is not None:
        return explicit
    if isinstance(shadow_result, Mapping):
        return shadow_result.get(key)
    return None


def _stable_success_case_id(symbol: str, signal_time: str, outcome_time: str) -> str:
    seed = f"hellhound:success-case:v1:{symbol}:{signal_time}:{outcome_time}"
    return str(uuid.uuid5(SUCCESS_CASE_ID_NAMESPACE, seed))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
