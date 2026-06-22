from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Mapping, Optional, Sequence, Union

try:
    from .lead_line_dataset import DEFAULT_DATASET_PATH
except ImportError:
    from lead_line_dataset import DEFAULT_DATASET_PATH


DETECTION_DELAY_SCHEMA_VERSION = "hellhound_detection_delay_report_v1"
DEFAULT_DETECTION_DELAY_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_detection_delay_report.jsonl"


def create_detection_delay_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    signal_time = _signal_time(row)
    outcome_time = _parse_time(row.get("outcome_time"))
    delay_hours = None
    if signal_time is not None and outcome_time is not None:
        delay_hours = round((outcome_time - signal_time).total_seconds() / 3600.0, 6)
    return {
        "detection_delay_schema_version": DETECTION_DELAY_SCHEMA_VERSION,
        "lead_line_id": row.get("lead_line_id"),
        "symbol": str(row.get("symbol") or "").upper() or None,
        "signal_time": signal_time.isoformat() if signal_time else None,
        "outcome_time": outcome_time.isoformat() if outcome_time else row.get("outcome_time"),
        "delay_hours": delay_hours,
        "promotion_status": row.get("promotion_status"),
        "structure_type": row.get("structure_type"),
        "is_trade_command": False,
    }


def summarize_detection_delays(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    records = [create_detection_delay_record(row) for row in rows if row.get("is_trade_command") is False]
    values = [float(row["delay_hours"]) for row in records if row.get("delay_hours") is not None]
    return {
        "detection_delay_schema_version": DETECTION_DELAY_SCHEMA_VERSION,
        "count": len(values),
        "average_delay_hours": round(mean(values), 6) if values else None,
        "median_delay_hours": round(median(values), 6) if values else None,
        "min_delay_hours": round(min(values), 6) if values else None,
        "max_delay_hours": round(max(values), 6) if values else None,
        "records": records,
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
        if row.get("is_trade_command") is False:
            rows.append(row)
    return rows


def build_detection_delay_report(
    *,
    input_path: Union[Path, str] = DEFAULT_DATASET_PATH,
    output_path: Union[Path, str] = DEFAULT_DETECTION_DELAY_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    rows = load_lead_line_rows(input_path)
    summary = summarize_detection_delays(rows)
    write_detection_delay_report([_summary_row(summary), *summary["records"]], output_path=output_path, append=append)
    return {
        "detection_delay_schema_version": DETECTION_DELAY_SCHEMA_VERSION,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "record_count": len(summary["records"]),
        "summary": _summary_row(summary),
        "is_trade_command": False,
    }


def write_detection_delay_report(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_DETECTION_DELAY_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            normalized = dict(row)
            normalized["detection_delay_schema_version"] = DETECTION_DELAY_SCHEMA_VERSION
            normalized["is_trade_command"] = False
            file.write(json.dumps(normalized, sort_keys=True) + "\n")
    return {
        "detection_delay_schema_version": DETECTION_DELAY_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def _summary_row(summary: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "record_type": "detection_delay_summary",
        "count": summary.get("count"),
        "average_delay_hours": summary.get("average_delay_hours"),
        "median_delay_hours": summary.get("median_delay_hours"),
        "min_delay_hours": summary.get("min_delay_hours"),
        "max_delay_hours": summary.get("max_delay_hours"),
        "is_trade_command": False,
    }


def _signal_time(row: Mapping[str, Any]) -> Optional[datetime]:
    value = row.get("signal_time")
    if value:
        return _parse_time(value)
    outcome_time = _parse_time(row.get("outcome_time"))
    hours_before_outcome = _optional_float(row.get("hours_before_outcome"))
    if outcome_time is None or hours_before_outcome is None:
        return None
    return outcome_time - timedelta(hours=hours_before_outcome)


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
