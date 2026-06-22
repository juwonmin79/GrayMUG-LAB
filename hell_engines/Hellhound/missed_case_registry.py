from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


MISSED_CASE_SCHEMA_VERSION = "hellhound_missed_case_registry_v1"
DEFAULT_MISSED_CASE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_missed_cases.jsonl"
MISSED_CASE_ID_NAMESPACE = uuid.UUID("5e5167e1-f3f4-46c6-a503-a97f3ec65256")


def create_missed_case_record(
    *,
    symbol: str,
    outcome_time: Any,
    case_name: str,
    hound_scan: Optional[Mapping[str, Any]] = None,
    shadow_result: Optional[Mapping[str, Any]] = None,
    hellhound_score: Any = None,
    promotion_status: Any = None,
    structure_classification: Any = None,
    notes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    normalized_symbol = str(symbol or "").upper()
    normalized_outcome_time = str(outcome_time or "")
    return {
        "missed_case_schema_version": MISSED_CASE_SCHEMA_VERSION,
        "missed_case_id": _stable_missed_case_id(normalized_symbol, normalized_outcome_time, case_name),
        "case_name": case_name,
        "symbol": normalized_symbol or None,
        "outcome_time": normalized_outcome_time or None,
        "registered_at": _now_utc(),
        "case_type": "MISSED",
        "hound_scan": dict(hound_scan or {}),
        "shadow_result": dict(shadow_result or {}),
        "hellhound_score": _value_or_shadow(shadow_result, hellhound_score, "hellhound_score"),
        "promotion_status": _value_or_shadow(shadow_result, promotion_status, "promotion_status"),
        "structure_classification": _value_or_shadow(
            shadow_result,
            structure_classification,
            "structure_type",
        )
        or _value_or_shadow(shadow_result, structure_classification, "setup_type"),
        "review_questions": [
            "What did Hellhound see before the move?",
            "What did Hellhound miss before the move?",
        ],
        "notes": list(notes or []),
        "is_trade_command": False,
    }


def write_missed_cases(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_MISSED_CASE_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(_enforce_non_trade(row), sort_keys=True) + "\n")
    return {
        "missed_case_schema_version": MISSED_CASE_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def register_missed_case(
    *,
    symbol: str,
    outcome_time: Any,
    case_name: str,
    output_path: Union[Path, str] = DEFAULT_MISSED_CASE_PATH,
    **kwargs: Any,
) -> Dict[str, Any]:
    record = create_missed_case_record(symbol=symbol, outcome_time=outcome_time, case_name=case_name, **kwargs)
    write_missed_cases([record], output_path=output_path, append=True)
    return record


def _value_or_shadow(shadow_result: Optional[Mapping[str, Any]], explicit: Any, key: str) -> Any:
    if explicit is not None:
        return explicit
    if isinstance(shadow_result, Mapping):
        return shadow_result.get(key)
    return None


def _enforce_non_trade(row: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    normalized["is_trade_command"] = False
    return normalized


def _stable_missed_case_id(symbol: str, outcome_time: str, case_name: str) -> str:
    seed = f"hellhound:missed-case:v1:{symbol}:{outcome_time}:{case_name}"
    return str(uuid.uuid5(MISSED_CASE_ID_NAMESPACE, seed))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
