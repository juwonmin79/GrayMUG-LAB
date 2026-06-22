from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


EVENT_WRITER_SCHEMA_VERSION = "hellhound_event_writer_v1"
HELLHOUND_VERSION = "hellhound_shadow_advisor_v0.8"
ALLOWED_RECORD_TYPES = {
    "shadow_decision",
    "daily_open_alert_cluster",
    "real_feed_outcome",
}
DEFAULT_EVENT_LOG_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_event_layer.jsonl"
EVENT_ID_NAMESPACE = uuid.UUID("39155443-839f-46a1-99ea-e7eb49a923ba")


class EventValidationError(ValueError):
    pass


class EventWriter:
    def __init__(self, path: Union[Path, str] = DEFAULT_EVENT_LOG_PATH) -> None:
        self.path = Path(path)

    def append_event(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        validated = validate_event(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(validated, sort_keys=True) + "\n")
        return {
            "event_writer_schema_version": EVENT_WRITER_SCHEMA_VERSION,
            "path": str(self.path),
            "written_count": 1,
            "is_trade_command": False,
        }

    def append_events(self, records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        validated = [validate_event(record) for record in records]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            for record in validated:
                file.write(json.dumps(record, sort_keys=True) + "\n")
        return {
            "event_writer_schema_version": EVENT_WRITER_SCHEMA_VERSION,
            "path": str(self.path),
            "written_count": len(validated),
            "is_trade_command": False,
        }


def append_event(record: Mapping[str, Any], *, path: Union[Path, str] = DEFAULT_EVENT_LOG_PATH) -> Dict[str, Any]:
    return EventWriter(path).append_event(record)


def append_events(
    records: Sequence[Mapping[str, Any]], *, path: Union[Path, str] = DEFAULT_EVENT_LOG_PATH
) -> Dict[str, Any]:
    return EventWriter(path).append_events(records)


def validate_event(record: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, Mapping):
        raise EventValidationError("event record must be a mapping")
    normalized = dict(record)
    required = ("event_id", "event_time", "record_type", "source", "hellhound_version", "is_trade_command")
    missing = [field for field in required if field not in normalized]
    if missing:
        raise EventValidationError(f"event record missing required fields: {', '.join(missing)}")
    if normalized["record_type"] not in ALLOWED_RECORD_TYPES:
        raise EventValidationError(f"invalid record_type: {normalized['record_type']}")
    if normalized["is_trade_command"] is not False:
        raise EventValidationError("event record must have is_trade_command=false")
    if not normalized.get("event_id"):
        raise EventValidationError("event_id is required")
    if not normalized.get("event_time"):
        raise EventValidationError("event_time is required")
    if not normalized.get("source"):
        raise EventValidationError("source is required")
    if not normalized.get("hellhound_version"):
        raise EventValidationError("hellhound_version is required")
    normalized["event_writer_schema_version"] = EVENT_WRITER_SCHEMA_VERSION
    return normalized


def record_from_boundary_output(
    payload: Mapping[str, Any],
    *,
    record_type: Optional[str] = None,
    source: str = "hellhound_library_interface",
) -> Dict[str, Any]:
    inferred_type = record_type or _record_type_from_payload(payload)
    symbol = payload.get("symbol")
    event_time = (
        payload.get("signal_time")
        or payload.get("cluster_time")
        or payload.get("as_of_time")
        or _now_utc()
    )
    event_id = (
        payload.get("event_id")
        or payload.get("cluster_id")
        or _stable_event_id(inferred_type, event_time, symbol)
    )
    return validate_event(
        {
            "event_id": str(event_id),
            "event_time": str(event_time),
            "record_type": inferred_type,
            "source": source,
            "hellhound_version": HELLHOUND_VERSION,
            "symbol": str(symbol).upper() if symbol else None,
            "is_trade_command": False,
            "payload": dict(payload),
        }
    )


def records_from_boundary_output(payload: Mapping[str, Any]) -> list[Dict[str, Any]]:
    if payload.get("output_type") == "cluster":
        return [
            record_from_boundary_output(
                cluster,
                record_type="daily_open_alert_cluster",
                source="hellhound_cluster_boundary",
            )
            for cluster in payload.get("clusters", [])
            if isinstance(cluster, Mapping)
        ]
    return [record_from_boundary_output(payload)]


def _record_type_from_payload(payload: Mapping[str, Any]) -> str:
    if payload.get("record_type") == "daily_open_alert_cluster":
        return "daily_open_alert_cluster"
    if any(key in payload for key in ("actual_1h_outcome", "actual_4h_outcome", "actual_24h_outcome")):
        return "real_feed_outcome"
    return "shadow_decision"


def _stable_event_id(record_type: str, event_time: Any, symbol: Any) -> str:
    seed = f"hellhound:event-writer:v1:{record_type}:{symbol or ''}:{event_time}"
    return str(uuid.uuid5(EVENT_ID_NAMESPACE, seed))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
