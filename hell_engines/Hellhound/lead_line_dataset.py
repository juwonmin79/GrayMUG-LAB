from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union

try:
    from .event_writer import DEFAULT_EVENT_LOG_PATH
except ImportError:
    from event_writer import DEFAULT_EVENT_LOG_PATH


LEAD_LINE_DATASET_SCHEMA_VERSION = "hellhound_lead_line_dataset_v1"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_lead_line_dataset.jsonl"
LEAD_LINE_ID_NAMESPACE = uuid.UUID("6e3ae9a5-f58f-4674-b0b9-0e17dc90e1a2")


def build_lead_line_dataset(
    *,
    event_log_path: Union[Path, str] = DEFAULT_EVENT_LOG_PATH,
    output_path: Optional[Union[Path, str]] = DEFAULT_DATASET_PATH,
    windows_hours: Sequence[int] = (24, 48, 72),
    append: bool = True,
) -> Dict[str, Any]:
    events = load_event_records(event_log_path)
    rows = []
    for outcome in _outcome_events(events):
        for hours in windows_hours:
            pre_events = collect_pre_outcome_events(
                events,
                outcome_event=outcome,
                hours_before_outcome=hours,
            )
            rows.append(
                create_lead_line_record(
                    outcome_event=outcome,
                    pre_events=pre_events,
                    hours_before_outcome=hours,
                )
            )
    write_result = None
    if output_path is not None:
        write_result = write_lead_line_dataset(rows, output_path=output_path, append=append)
    return {
        "lead_line_dataset_schema_version": LEAD_LINE_DATASET_SCHEMA_VERSION,
        "event_count": len(events),
        "outcome_count": len(_outcome_events(events)),
        "dataset_count": len(rows),
        "windows_hours": list(windows_hours),
        "output_path": str(output_path) if output_path is not None else None,
        "write_result": write_result,
        "rows": rows,
        "is_trade_command": False,
    }


def collect_pre_outcome_events(
    events: Sequence[Mapping[str, Any]],
    *,
    outcome_event: Mapping[str, Any],
    hours_before_outcome: int,
) -> list[Dict[str, Any]]:
    outcome_time = _parse_time(outcome_event.get("event_time"))
    if outcome_time is None:
        return []
    symbol = str(outcome_event.get("symbol") or "").upper()
    window_start = outcome_time - timedelta(hours=hours_before_outcome)
    collected = []
    for event in events:
        if event is outcome_event:
            continue
        event_time = _parse_time(event.get("event_time"))
        if event_time is None:
            continue
        event_symbol = str(event.get("symbol") or "").upper()
        if symbol and event_symbol and event_symbol != symbol:
            continue
        if window_start <= event_time < outcome_time:
            collected.append(dict(event))
    return sorted(collected, key=lambda row: str(row.get("event_time") or ""))


def create_lead_line_record(
    *,
    outcome_event: Mapping[str, Any],
    pre_events: Sequence[Mapping[str, Any]],
    hours_before_outcome: int,
) -> Dict[str, Any]:
    outcome_time = str(outcome_event.get("event_time") or "")
    symbol = str(outcome_event.get("symbol") or _symbol_from_payload(outcome_event) or "").upper()
    shadow_events = [event for event in pre_events if event.get("record_type") in {"shadow_decision", "real_feed_outcome"}]
    cluster_events = [event for event in pre_events if event.get("record_type") == "daily_open_alert_cluster"]
    selected_shadow = _latest_event(shadow_events)
    selected_cluster = _latest_event(cluster_events)
    signal_hour = _signal_hour(selected_shadow or outcome_event)
    lead_line_id = _stable_lead_line_id(symbol, outcome_time, hours_before_outcome)
    return {
        "lead_line_dataset_schema_version": LEAD_LINE_DATASET_SCHEMA_VERSION,
        "lead_line_id": lead_line_id,
        "symbol": symbol or None,
        "outcome_time": outcome_time,
        "outcome_event_id": outcome_event.get("event_id"),
        "hours_before_outcome": hours_before_outcome,
        "saw_shadow_decision": bool(shadow_events),
        "saw_daily_open_cluster": bool(cluster_events),
        "promotion_status": _payload_value(selected_shadow, "promotion_status"),
        "structure_type": _payload_value(selected_shadow, "structure_type") or _payload_value(selected_shadow, "setup_type"),
        "hellhound_score": _payload_value(selected_shadow, "hellhound_score"),
        "entry_bias": _payload_value(selected_shadow, "entry_bias"),
        "signal_hour": signal_hour,
        "daily_open_cluster": bool(cluster_events),
        "alert_count": _payload_value(selected_cluster, "alert_count"),
        "event_count": len(pre_events),
        "record_types": sorted({str(event.get("record_type")) for event in pre_events}),
        "is_trade_command": False,
    }


def load_event_records(path: Union[Path, str]) -> list[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _is_usable_event(row):
            records.append(row)
    return records


def write_lead_line_dataset(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_DATASET_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(dict(row), sort_keys=True) + "\n")
    return {
        "lead_line_dataset_schema_version": LEAD_LINE_DATASET_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def _outcome_events(events: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    return [
        dict(event)
        for event in events
        if event.get("record_type") == "real_feed_outcome"
    ]


def _is_usable_event(row: Mapping[str, Any]) -> bool:
    if row.get("is_trade_command") is not False:
        return False
    if not row.get("event_id") or not row.get("event_time") or not row.get("record_type"):
        return False
    return row.get("record_type") in {"shadow_decision", "daily_open_alert_cluster", "real_feed_outcome"}


def _latest_event(events: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    if not events:
        return None
    return sorted(events, key=lambda row: str(row.get("event_time") or ""))[-1]


def _payload_value(event: Optional[Mapping[str, Any]], key: str) -> Any:
    if not event:
        return None
    payload = event.get("payload")
    if isinstance(payload, Mapping) and key in payload:
        return payload.get(key)
    return event.get(key)


def _symbol_from_payload(event: Mapping[str, Any]) -> Optional[str]:
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        value = payload.get("symbol")
        if value:
            return str(value)
    return None


def _signal_hour(event: Optional[Mapping[str, Any]]) -> Optional[int]:
    if not event:
        return None
    event_time = _parse_time(event.get("event_time"))
    return event_time.hour if event_time is not None else None


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


def _stable_lead_line_id(symbol: str, outcome_time: str, hours_before_outcome: int) -> str:
    seed = f"hellhound:lead-line:v1:{symbol}:{outcome_time}:{hours_before_outcome}"
    return str(uuid.uuid5(LEAD_LINE_ID_NAMESPACE, seed))
