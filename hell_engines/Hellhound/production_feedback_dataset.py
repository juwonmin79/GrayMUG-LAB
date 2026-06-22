from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Union


FEEDBACK_DATASET_SCHEMA_VERSION = "hellhound_feedback_dataset_v1"
DEFAULT_PRODUCTION_SHADOW_PATH = Path(__file__).resolve().parents[2] / "production_hellhound_shadow.jsonl"
DEFAULT_FEEDBACK_DATASET_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_feedback_dataset.jsonl"
FEEDBACK_ID_NAMESPACE = uuid.UUID("86fc62c0-30f2-4cdf-a278-01f462f13eea")


def create_feedback_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(row.get("symbol") or _payload_value(row, "symbol") or "").upper()
    signal_time = row.get("signal_time") or row.get("event_time") or _payload_value(row, "signal_time")
    return {
        "feedback_dataset_schema_version": FEEDBACK_DATASET_SCHEMA_VERSION,
        "feedback_id": _stable_feedback_id(symbol, signal_time, row.get("event_id") or row.get("case_id")),
        "source": "production_shadow_pipeline",
        "symbol": symbol or None,
        "signal_time": signal_time,
        "event_id": row.get("event_id"),
        "case_id": row.get("case_id"),
        "hellhound_score": row.get("hellhound_score") or _payload_value(row, "hellhound_score"),
        "promotion_status": row.get("promotion_status") or _payload_value(row, "promotion_status"),
        "structure_type": row.get("structure_type") or _payload_value(row, "structure_type") or _payload_value(row, "setup_type"),
        "entry_bias": row.get("entry_bias") or _payload_value(row, "entry_bias"),
        "raw_shadow_row": dict(row),
        "is_trade_command": False,
    }


def load_jsonl_rows(path: Union[Path, str] = DEFAULT_PRODUCTION_SHADOW_PATH) -> list[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def build_feedback_dataset(
    *,
    input_path: Union[Path, str] = DEFAULT_PRODUCTION_SHADOW_PATH,
    output_path: Union[Path, str] = DEFAULT_FEEDBACK_DATASET_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    rows = [create_feedback_record(row) for row in load_jsonl_rows(input_path)]
    write_feedback_dataset(rows, output_path=output_path, append=append)
    return {
        "feedback_dataset_schema_version": FEEDBACK_DATASET_SCHEMA_VERSION,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "written_count": len(rows),
        "is_trade_command": False,
    }


def write_feedback_dataset(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_FEEDBACK_DATASET_PATH,
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
        "feedback_dataset_schema_version": FEEDBACK_DATASET_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def _payload_value(row: Mapping[str, Any], key: str) -> Any:
    payload = row.get("payload")
    if isinstance(payload, Mapping):
        return payload.get(key)
    return None


def _stable_feedback_id(symbol: str, signal_time: Any, row_id: Any) -> str:
    seed = f"hellhound:feedback:v1:{symbol}:{signal_time or ''}:{row_id or ''}"
    return str(uuid.uuid5(FEEDBACK_ID_NAMESPACE, seed))
