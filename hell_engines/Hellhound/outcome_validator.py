from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union

try:
    from .lead_line_dataset import DEFAULT_DATASET_PATH
except ImportError:
    from lead_line_dataset import DEFAULT_DATASET_PATH


VALIDATION_DATASET_SCHEMA_VERSION = "hellhound_outcome_validation_v1"
DEFAULT_VALIDATION_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_validation_dataset.jsonl"
VALIDATION_ID_NAMESPACE = uuid.UUID("08cad4d8-8d2f-4f50-b322-53e399076d0e")
VALIDATION_STATUSES = {"VALIDATED", "DELAYED", "INCONCLUSIVE", "REJECTED"}


def validate_lead_line(
    lead_line_rows: Sequence[Mapping[str, Any]],
    *,
    validation_windows: Sequence[int] = (24, 48, 72),
    output_path: Optional[Union[Path, str]] = DEFAULT_VALIDATION_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    records = []
    for row in lead_line_rows:
        for window in validation_windows:
            records.append(validate_outcome_window(row, validation_window_hours=window))
    write_result = None
    if output_path is not None:
        write_result = write_validation_dataset(records, output_path=output_path, append=append)
    return {
        "validation_dataset_schema_version": VALIDATION_DATASET_SCHEMA_VERSION,
        "input_count": len(lead_line_rows),
        "validation_count": len(records),
        "validation_windows": list(validation_windows),
        "output_path": str(output_path) if output_path is not None else None,
        "write_result": write_result,
        "records": records,
        "is_trade_command": False,
    }


def validate_outcome_window(
    lead_line_row: Mapping[str, Any],
    *,
    validation_window_hours: int,
) -> Dict[str, Any]:
    status = _validation_status(lead_line_row, validation_window_hours)
    return create_validation_record(
        lead_line_row=lead_line_row,
        validation_window_hours=validation_window_hours,
        validation_status=status,
    )


def create_validation_record(
    *,
    lead_line_row: Mapping[str, Any],
    validation_window_hours: int,
    validation_status: str,
) -> Dict[str, Any]:
    status = validation_status if validation_status in VALIDATION_STATUSES else "INCONCLUSIVE"
    lead_line_id = str(lead_line_row.get("lead_line_id") or "")
    symbol = lead_line_row.get("symbol")
    hours_before = _optional_int(lead_line_row.get("hours_before_outcome"))
    validation_score = _validation_score(
        status=status,
        hours_before_outcome=hours_before,
        validation_window_hours=validation_window_hours,
        saw_daily_open_cluster=bool(lead_line_row.get("saw_daily_open_cluster")),
        promotion_status=str(lead_line_row.get("promotion_status") or ""),
        event_count=_optional_int(lead_line_row.get("event_count")) or 0,
    )
    return {
        "validation_dataset_schema_version": VALIDATION_DATASET_SCHEMA_VERSION,
        "validation_id": _stable_validation_id(lead_line_id, validation_window_hours),
        "lead_line_id": lead_line_id or None,
        "symbol": str(symbol).upper() if symbol else None,
        "validation_status": status,
        "validation_window_hours": validation_window_hours,
        "hours_before_outcome": hours_before,
        "saw_daily_open_cluster": bool(lead_line_row.get("saw_daily_open_cluster")),
        "promotion_status": lead_line_row.get("promotion_status"),
        "structure_type": lead_line_row.get("structure_type"),
        "daily_open_cluster": bool(lead_line_row.get("daily_open_cluster")),
        "alert_count": _optional_int(lead_line_row.get("alert_count")),
        "event_count": _optional_int(lead_line_row.get("event_count")),
        "validation_score": validation_score,
        "is_trade_command": False,
    }


def write_validation_dataset(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_VALIDATION_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(dict(row), sort_keys=True) + "\n")
    return {
        "validation_dataset_schema_version": VALIDATION_DATASET_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def load_lead_line_rows(path: Union[Path, str] = DEFAULT_DATASET_PATH) -> list[Dict[str, Any]]:
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
        if _is_usable_lead_line_row(row):
            rows.append(row)
    return rows


def _validation_status(row: Mapping[str, Any], validation_window_hours: int) -> str:
    if not _is_usable_lead_line_row(row):
        return "INCONCLUSIVE"
    if _has_success_outcome(row):
        hours_before = _optional_int(row.get("hours_before_outcome"))
        if hours_before is None:
            return "INCONCLUSIVE"
        return "VALIDATED" if hours_before <= validation_window_hours else "DELAYED"
    if _has_fail_outcome(row):
        return "REJECTED"
    return "INCONCLUSIVE"


def _validation_score(
    *,
    status: str,
    hours_before_outcome: Optional[int],
    validation_window_hours: int,
    saw_daily_open_cluster: bool,
    promotion_status: str,
    event_count: int,
) -> float:
    if status == "REJECTED":
        return 0.0
    base = {
        "VALIDATED": 0.62,
        "DELAYED": 0.38,
        "INCONCLUSIVE": 0.18,
        "REJECTED": 0.0,
    }.get(status, 0.0)
    if status == "VALIDATED" and hours_before_outcome is not None and validation_window_hours > 0:
        lead_bonus = max(0.0, min((validation_window_hours - hours_before_outcome) / validation_window_hours, 1.0)) * 0.18
        base += lead_bonus
    if saw_daily_open_cluster:
        base += 0.08
    if promotion_status.upper() == "PROMOTE":
        base += 0.08
    base += min(event_count, 10) * 0.004
    return round(min(max(base, 0.0), 1.0), 4)


def _is_usable_lead_line_row(row: Mapping[str, Any]) -> bool:
    if row.get("is_trade_command") is not False:
        return False
    return bool(row.get("lead_line_id") and row.get("symbol"))


def _has_success_outcome(row: Mapping[str, Any]) -> bool:
    values = [
        row.get("actual_1h_outcome"),
        row.get("actual_4h_outcome"),
        row.get("actual_24h_outcome"),
        row.get("outcome_result"),
        row.get("result"),
    ]
    if row.get("outcome_time"):
        values.append("SUCCESS")
    return any(str(value).upper() == "SUCCESS" for value in values if value is not None)


def _has_fail_outcome(row: Mapping[str, Any]) -> bool:
    values = [
        row.get("actual_1h_outcome"),
        row.get("actual_4h_outcome"),
        row.get("actual_24h_outcome"),
        row.get("outcome_result"),
        row.get("result"),
    ]
    return any(str(value).upper() == "FAIL" for value in values if value is not None)


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_validation_id(lead_line_id: str, validation_window_hours: int) -> str:
    seed = f"hellhound:validation:v1:{lead_line_id}:{validation_window_hours}"
    return str(uuid.uuid5(VALIDATION_ID_NAMESPACE, seed))
