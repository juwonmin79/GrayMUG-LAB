from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional


WINDOW_DURATIONS = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}


def compute_target_time(signal_created_at: Any, evaluation_window: Any) -> Optional[str]:
    created_at = parse_utc_datetime(signal_created_at)
    duration = WINDOW_DURATIONS.get(str(evaluation_window or ""))
    if created_at is None or duration is None:
        return None
    return (created_at + duration).isoformat()


def outcome_target_time(outcome: Mapping[str, Any]) -> Optional[str]:
    target_time = outcome.get("target_time")
    if target_time:
        return str(target_time)

    shadow_signal = outcome.get("shadow_signal")
    if isinstance(shadow_signal, Mapping):
        return compute_target_time(
            shadow_signal.get("created_at"),
            outcome.get("evaluation_window"),
        )
    return None


def is_outcome_due(outcome: Mapping[str, Any], now: Optional[datetime] = None) -> bool:
    target = parse_utc_datetime(outcome_target_time(outcome))
    if target is None:
        return False
    return (now or datetime.now(timezone.utc)) >= target


def parse_utc_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
