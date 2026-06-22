from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional


EVENT_SCHEMA_VERSION = "hellhound_event_v1"
DEFAULT_EVENT_GAP_HOURS = 24.0
EVENT_ID_NAMESPACE = uuid.UUID("856b21b2-22be-4ce2-8f20-3d4d2ce1f35e")


@dataclass(frozen=True)
class EventBuildResult:
    events: list[Dict[str, Any]]
    observations: list[Dict[str, Any]]
    duplicate_count: int
    input_count: int


def build_events_from_signals(
    signals: Iterable[Mapping[str, Any]],
    *,
    max_gap_hours: float = DEFAULT_EVENT_GAP_HOURS,
) -> EventBuildResult:
    """Build event timelines from shadow signals without deleting raw signals."""
    normalized = [_normalize_signal(signal) for signal in signals]
    normalized = [signal for signal in normalized if signal.get("symbol")]
    normalized.sort(key=lambda item: (item["symbol"], item["source_time_sort"], item["dedupe_key"]))

    deduped: list[Dict[str, Any]] = []
    seen = set()
    duplicate_count = 0
    for signal in normalized:
        key = signal["dedupe_key"]
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        deduped.append(signal)

    events: list[Dict[str, Any]] = []
    observations: list[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    current_last_dt: Optional[datetime] = None

    for signal in deduped:
        source_dt = signal["source_time_sort"]
        if (
            current is None
            or current["symbol"] != signal["symbol"]
            or _hours_between(current_last_dt, source_dt) > max_gap_hours
        ):
            if current is not None:
                events.append(_finalize_event(current))
            event_id = stable_event_id(signal["symbol"], signal["source_time"])
            current = {
                "event_schema_version": EVENT_SCHEMA_VERSION,
                "event_id": event_id,
                "symbol": signal["symbol"],
                "event_start_bucket": _event_start_bucket(source_dt),
                "max_gap_hours": max_gap_hours,
                "first_seen_time": signal["source_time"],
                "last_seen_time": signal["source_time"],
                "first_seen_dt": source_dt,
                "last_seen_dt": source_dt,
                "observation_times": [],
                "observation_count": 0,
                "hypotheses": set(),
                "shadow_actions": set(),
                "patterns": set(),
            }
        assert current is not None
        current["last_seen_time"] = signal["source_time"]
        current["last_seen_dt"] = source_dt
        current["observation_times"].append(source_dt)
        current["observation_count"] += 1
        current["hypotheses"].add(signal["hypothesis"])
        if signal.get("shadow_action"):
            current["shadow_actions"].add(signal["shadow_action"])
        if signal.get("pattern"):
            current["patterns"].add(signal["pattern"])
        observations.append(_event_observation(current["event_id"], signal))
        current_last_dt = source_dt

    if current is not None:
        events.append(_finalize_event(current))

    return EventBuildResult(
        events=events,
        observations=observations,
        duplicate_count=duplicate_count,
        input_count=len(normalized),
    )


def stable_event_id(symbol: str, first_seen_time: str) -> str:
    seed = f"hellhound:event:v1:{str(symbol).upper()}:{_canonical_time(first_seen_time)}"
    return str(uuid.uuid5(EVENT_ID_NAMESPACE, seed))


def signal_dedupe_key(signal: Mapping[str, Any]) -> str:
    normalized = _normalize_signal(signal)
    return normalized["dedupe_key"]


def _event_observation(event_id: str, signal: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": event_id,
        "shadow_signal_id": signal.get("id") or signal.get("shadow_signal_id"),
        "symbol": signal["symbol"],
        "source_time": signal["source_time"],
        "hypothesis": signal["hypothesis"],
        "dedupe_key": signal["dedupe_key"],
        "raw_signal": signal.get("raw_signal"),
    }


def _finalize_event(event: Mapping[str, Any]) -> Dict[str, Any]:
    first_seen = event["first_seen_dt"]
    last_seen = event["last_seen_dt"]
    return {
        "event_schema_version": EVENT_SCHEMA_VERSION,
        "event_id": event["event_id"],
        "symbol": event["symbol"],
        "event_start_bucket": event["event_start_bucket"],
        "max_gap_hours": event["max_gap_hours"],
        "first_seen_time": event["first_seen_time"],
        "last_seen_time": event["last_seen_time"],
        "event_age_hours": _hours_between(first_seen, last_seen),
        "observation_count": event["observation_count"],
        "observation_timeframe_hint": _observation_timeframe_hint(event["observation_times"]),
        "hypotheses": sorted(event["hypotheses"]),
        "shadow_actions": sorted(event["shadow_actions"]),
        "patterns": sorted(event["patterns"]),
        "event_state": _event_state(event["observation_count"], _hours_between(first_seen, last_seen)),
    }


def _event_state(observation_count: int, event_age_hours: float) -> str:
    if observation_count >= 20 and event_age_hours >= 12:
        return "extended_timeline"
    if observation_count >= 3:
        return "active"
    return "new"


def _event_start_bucket(value: datetime) -> str:
    return value.replace(minute=0, second=0, microsecond=0).isoformat()


def _observation_timeframe_hint(observation_times: list[datetime]) -> str:
    unique_times = sorted(set(observation_times))
    if len(unique_times) < 2:
        return "single_observation"
    gaps = [
        (current - previous).total_seconds() / 60.0
        for previous, current in zip(unique_times, unique_times[1:])
    ]
    median_gap = sorted(gaps)[len(gaps) // 2]
    if median_gap <= 1:
        return "1m"
    if median_gap <= 15:
        return "15m"
    if median_gap <= 60:
        return "1h"
    if median_gap <= 240:
        return "4h"
    if median_gap <= 1440:
        return "1d"
    return "1w"


def _normalize_signal(signal: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(signal.get("symbol") or "").upper()
    source_time = _source_time(signal)
    hypothesis = _hypothesis_name(signal)
    normalized = {
        "id": signal.get("id") or signal.get("shadow_signal_id"),
        "symbol": symbol,
        "source_time": source_time,
        "source_time_sort": _parse_time(source_time),
        "hypothesis": hypothesis,
        "shadow_action": _upper_or_none(signal.get("shadow_action")),
        "pattern": signal.get("pattern"),
        "raw_signal": dict(signal),
    }
    normalized["dedupe_key"] = _dedupe_key(
        symbol=normalized["symbol"],
        source_time=normalized["source_time"],
        hypothesis=normalized["hypothesis"],
    )
    return normalized


def _dedupe_key(*, symbol: str, source_time: str, hypothesis: str) -> str:
    text = f"{symbol}|{_canonical_time(source_time)}|{hypothesis}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_time(signal: Mapping[str, Any]) -> str:
    value = signal.get("source_time") or signal.get("created_at") or signal.get("timestamp")
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return _canonical_time(str(value))


def _canonical_time(value: str) -> str:
    parsed = _parse_time(value)
    return parsed.isoformat()


def _parse_time(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hypothesis_name(signal: Mapping[str, Any]) -> str:
    direct = signal.get("hypothesis_name") or signal.get("hypothesis")
    if isinstance(direct, Mapping):
        return str(direct.get("name") or direct.get("id") or "unknown")
    if direct:
        return str(direct)
    for key in ("execution_guidance", "lead_line_payload", "target_feed"):
        value = signal.get(key)
        if isinstance(value, Mapping):
            hypothesis = value.get("hypothesis")
            if isinstance(hypothesis, Mapping):
                return str(hypothesis.get("name") or hypothesis.get("id") or "unknown")
    return str(signal.get("pattern") or "unknown")


def _upper_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).upper()


def _hours_between(start: Optional[datetime], end: datetime) -> float:
    if start is None:
        return 0.0
    return max((end - start).total_seconds() / 3600.0, 0.0)
