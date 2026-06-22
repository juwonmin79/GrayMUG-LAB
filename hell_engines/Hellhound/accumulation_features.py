from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence


ACCUMULATION_SCHEMA_VERSION = "hellhound_accumulation_features_v1"


def compute_accumulation_features(
    symbol: str,
    historical_candles: Sequence[Mapping[str, Any]],
    *,
    event_history: Optional[Sequence[Mapping[str, Any]]] = None,
    spike_return_threshold: float = 0.08,
    spike_volume_ratio: float = 1.8,
) -> Dict[str, Any]:
    """Compute long-horizon accumulation context from read-only historical candles."""
    try:
        candles = [_normalize_candle(candle) for candle in historical_candles]
        candles = [candle for candle in candles if candle is not None]
        if len(candles) < 30:
            return _empty_response(
                symbol,
                error="Need at least 30 historical candles for accumulation features.",
                input_candles=len(candles),
            )

        closes = [candle["close"] for candle in candles]
        highs = [candle["high"] for candle in candles]
        lows = [candle["low"] for candle in candles]
        volumes = [candle["volume"] for candle in candles]
        last_close = closes[-1]

        vol_7d_avg = _safe_mean(volumes[-7:])
        vol_14d_avg = _safe_mean(volumes[-14:])
        vol_30d_avg = _safe_mean(volumes[-30:])
        price_from_30d_high = _distance_from_level(last_close, max(highs[-30:]))
        price_from_52w_high = _distance_from_level(last_close, max(highs[-365:]))
        price_from_30d_low = _distance_from_level(last_close, min(lows[-30:]))
        price_from_52w_low = _distance_from_level(last_close, min(lows[-365:]))
        distance_ma200 = _distance_from_level(last_close, _safe_mean(closes[-200:])) if len(closes) >= 200 else None
        repeat = _repeat_activity(
            candles,
            event_history=event_history,
            spike_return_threshold=spike_return_threshold,
            spike_volume_ratio=spike_volume_ratio,
        )
        weekly_trend = _return_over(closes, 7)
        monthly_trend = _return_over(closes, 30)
        structure_type = _structure_type(
            last_close=last_close,
            price_from_52w_high=price_from_52w_high,
            price_from_52w_low=price_from_52w_low,
            distance_ma200=distance_ma200,
            weekly_trend=weekly_trend,
            monthly_trend=monthly_trend,
            vol_ratio_7d_vs_30d=_safe_ratio(vol_7d_avg, vol_30d_avg),
        )
        accumulation_score_raw = _accumulation_score_raw(
            vol_ratio_7d_vs_30d=_safe_ratio(vol_7d_avg, vol_30d_avg),
            vol_ratio_14d_vs_30d=_safe_ratio(vol_14d_avg, vol_30d_avg),
            price_from_52w_low=price_from_52w_low,
            price_from_52w_high=price_from_52w_high,
            monthly_trend=monthly_trend,
            repeat_activity_score=repeat["repeat_activity_score"],
            structure_type=structure_type,
        )
        structure_score = _structure_score(structure_type, distance_ma200, price_from_52w_low, price_from_52w_high)
        setup_type = _setup_type(structure_type, repeat["repeat_activity_score"], accumulation_score_raw)
        hellhound_score = _hellhound_score(
            accumulation_score_raw=accumulation_score_raw,
            repeat_activity_score=repeat["repeat_activity_score"],
            structure_score=structure_score,
        )

        return {
            "accumulation_schema_version": ACCUMULATION_SCHEMA_VERSION,
            "symbol": str(symbol).upper(),
            "input_candles": len(candles),
            "vol_7d_avg": round(vol_7d_avg, 6),
            "vol_14d_avg": round(vol_14d_avg, 6),
            "vol_30d_avg": round(vol_30d_avg, 6),
            "vol_ratio_7d_vs_30d": _round_or_none(_safe_ratio(vol_7d_avg, vol_30d_avg)),
            "vol_ratio_14d_vs_30d": _round_or_none(_safe_ratio(vol_14d_avg, vol_30d_avg)),
            "price_return_7d": _round_or_none(_return_over(closes, 7)),
            "price_return_14d": _round_or_none(_return_over(closes, 14)),
            "price_return_30d": _round_or_none(monthly_trend),
            "price_from_30d_high": _round_or_none(price_from_30d_high),
            "price_from_52w_high": _round_or_none(price_from_52w_high),
            "price_from_30d_low": _round_or_none(price_from_30d_low),
            "price_from_52w_low": _round_or_none(price_from_52w_low),
            "spike_count_7d": repeat["spike_count_7d"],
            "spike_count_14d": repeat["spike_count_14d"],
            "spike_count_30d": repeat["spike_count_30d"],
            "avg_spike_interval_days": repeat["avg_spike_interval_days"],
            "min_spike_interval_days": repeat["min_spike_interval_days"],
            "repeat_activity_score": repeat["repeat_activity_score"],
            "weekly_trend": _round_or_none(weekly_trend),
            "monthly_trend": _round_or_none(monthly_trend),
            "distance_ma200": _round_or_none(distance_ma200),
            "distance_52w_high": _round_or_none(price_from_52w_high),
            "distance_52w_low": _round_or_none(price_from_52w_low),
            "structure_type": structure_type,
            "setup_type": setup_type,
            "structure_score": structure_score,
            "accumulation_score_raw": accumulation_score_raw,
            "accumulation_score": accumulation_score_raw,
            "hellhound_score": hellhound_score,
            "distribution_risk": _distribution_risk(structure_type, price_from_52w_high, monthly_trend),
            "error": None,
        }
    except Exception as exc:
        return _empty_response(symbol, error=str(exc), input_candles=len(historical_candles))


def _repeat_activity(
    candles: Sequence[Mapping[str, Any]],
    *,
    event_history: Optional[Sequence[Mapping[str, Any]]],
    spike_return_threshold: float,
    spike_volume_ratio: float,
) -> Dict[str, Any]:
    if event_history:
        spike_indexes = _event_spike_indexes(candles, event_history)
    else:
        spike_indexes = _candle_spike_indexes(candles, spike_return_threshold, spike_volume_ratio)
    last_index = len(candles) - 1
    intervals = [b - a for a, b in zip(spike_indexes, spike_indexes[1:])]
    spike_count_7d = sum(1 for index in spike_indexes if last_index - index < 7)
    spike_count_14d = sum(1 for index in spike_indexes if last_index - index < 14)
    spike_count_30d = sum(1 for index in spike_indexes if last_index - index < 30)
    avg_interval = _safe_mean(intervals) if intervals else None
    min_interval = min(intervals) if intervals else None
    score = 0.0
    score += _score_above(spike_count_30d, 1, 5, weight=0.42)
    score += _score_above(spike_count_14d, 1, 3, weight=0.28)
    score += _score_below(avg_interval, 14, 3, weight=0.2)
    score += _score_below(min_interval, 10, 2, weight=0.1)
    return {
        "spike_count_7d": spike_count_7d,
        "spike_count_14d": spike_count_14d,
        "spike_count_30d": spike_count_30d,
        "avg_spike_interval_days": _round_or_none(avg_interval),
        "min_spike_interval_days": _round_or_none(min_interval),
        "repeat_activity_score": round(min(max(score, 0.0), 1.0), 4),
    }


def _candle_spike_indexes(
    candles: Sequence[Mapping[str, Any]], spike_return_threshold: float, spike_volume_ratio: float
) -> list[int]:
    indexes = []
    volumes = [candle["volume"] for candle in candles]
    for index in range(1, len(candles)):
        prev_close = candles[index - 1]["close"]
        if prev_close == 0:
            continue
        daily_return = (candles[index]["close"] - prev_close) / prev_close
        volume_baseline = _safe_mean(volumes[max(0, index - 20) : index])
        volume_ratio = _safe_ratio(candles[index]["volume"], volume_baseline)
        if daily_return >= spike_return_threshold or (volume_ratio is not None and volume_ratio >= spike_volume_ratio):
            indexes.append(index)
    return indexes


def _event_spike_indexes(candles: Sequence[Mapping[str, Any]], event_history: Sequence[Mapping[str, Any]]) -> list[int]:
    candle_times = [candle.get("time_dt") for candle in candles]
    indexes = []
    for event in event_history:
        raw_time = event.get("source_time") or event.get("first_seen_time") or event.get("created_at")
        event_time = _parse_time(raw_time) if raw_time else None
        if event_time is None:
            continue
        nearest = _nearest_index(candle_times, event_time)
        if nearest is not None:
            indexes.append(nearest)
    return sorted(set(indexes))


def _structure_type(
    *,
    last_close: float,
    price_from_52w_high: Optional[float],
    price_from_52w_low: Optional[float],
    distance_ma200: Optional[float],
    weekly_trend: Optional[float],
    monthly_trend: Optional[float],
    vol_ratio_7d_vs_30d: Optional[float],
) -> str:
    from_high = price_from_52w_high
    from_low = price_from_52w_low
    if from_high is None or from_low is None:
        return "UNKNOWN"
    if from_high > -0.18 and (monthly_trend or 0.0) <= 0 and (vol_ratio_7d_vs_30d or 0.0) < 0.95:
        return "DISTRIBUTION"
    if from_high <= -0.65 and (weekly_trend or 0.0) < -0.08 and (monthly_trend or 0.0) < -0.20:
        return "CAPITULATION"
    if from_high <= -0.30 and 0.03 <= from_low <= 0.60 and (vol_ratio_7d_vs_30d or 0.0) >= 1.05:
        return "ACCUMULATION_BASE"
    if distance_ma200 is not None and -0.25 <= distance_ma200 <= 0.35:
        return "MID_CYCLE"
    if last_close > 0:
        return "UNKNOWN"
    return "UNKNOWN"


def _setup_type(structure_type: str, repeat_activity_score: float, accumulation_score: float) -> str:
    if structure_type == "ACCUMULATION_BASE" and repeat_activity_score >= 0.25:
        return "BEL"
    if structure_type in {"DISTRIBUTION", "CAPITULATION"} and repeat_activity_score < 0.35:
        return "ACT"
    if structure_type == "DISTRIBUTION" and repeat_activity_score >= 0.35:
        return "ACE"
    if structure_type == "ACCUMULATION_BASE" and accumulation_score >= 0.55:
        return "MET"
    return "UNKNOWN"


def _accumulation_score_raw(
    *,
    vol_ratio_7d_vs_30d: Optional[float],
    vol_ratio_14d_vs_30d: Optional[float],
    price_from_52w_low: Optional[float],
    price_from_52w_high: Optional[float],
    monthly_trend: Optional[float],
    repeat_activity_score: float,
    structure_type: str,
) -> float:
    score = 0.0
    score += _score_above(vol_ratio_7d_vs_30d, 1.05, 2.4, weight=0.22)
    score += _score_above(vol_ratio_14d_vs_30d, 1.02, 1.8, weight=0.16)
    score += _score_below(price_from_52w_low, 0.75, 0.05, weight=0.18)
    score += _score_below(price_from_52w_high, -0.25, -0.75, weight=0.14)
    score += _score_between(monthly_trend, -0.08, 0.18, weight=0.12)
    score += repeat_activity_score * 0.12
    if structure_type == "ACCUMULATION_BASE":
        score += 0.28
    elif structure_type in {"DISTRIBUTION", "CAPITULATION"}:
        score -= 0.18
    return round(min(max(score, 0.0), 1.0), 4)


def _structure_score(
    structure_type: str,
    distance_ma200: Optional[float],
    price_from_52w_low: Optional[float],
    price_from_52w_high: Optional[float],
) -> float:
    base = {
        "ACCUMULATION_BASE": 0.78,
        "MID_CYCLE": 0.5,
        "CAPITULATION": 0.22,
        "DISTRIBUTION": 0.12,
        "UNKNOWN": 0.25,
    }.get(structure_type, 0.25)
    base += _score_between(distance_ma200, -0.2, 0.25, weight=0.1)
    base += _score_below(price_from_52w_low, 0.65, 0.05, weight=0.08)
    base += _score_below(price_from_52w_high, -0.3, -0.75, weight=0.04)
    return round(min(max(base, 0.0), 1.0), 4)


def _hellhound_score(
    *, accumulation_score_raw: float, repeat_activity_score: float, structure_score: float
) -> float:
    return round(
        min(max(accumulation_score_raw * 0.5 + repeat_activity_score * 0.25 + structure_score * 0.25, 0.0), 1.0),
        4,
    )


def _distribution_risk(
    structure_type: str, price_from_52w_high: Optional[float], monthly_trend: Optional[float]
) -> float:
    base = {
        "DISTRIBUTION": 0.82,
        "CAPITULATION": 0.62,
        "MID_CYCLE": 0.42,
        "ACCUMULATION_BASE": 0.22,
    }.get(structure_type, 0.5)
    if price_from_52w_high is not None and price_from_52w_high > -0.12:
        base += 0.12
    if monthly_trend is not None and monthly_trend < -0.18:
        base += 0.08
    return round(min(max(base, 0.0), 1.0), 4)


def _normalize_candle(candle: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        return {
            "time": candle.get("time") or candle.get("timestamp") or candle.get("open_time"),
            "time_dt": _parse_time(candle.get("time") or candle.get("timestamp") or candle.get("open_time")),
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
            "volume": float(candle.get("volume") or candle.get("quote_volume") or 0.0),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _empty_response(symbol: str, *, error: str, input_candles: int) -> Dict[str, Any]:
    return {
        "accumulation_schema_version": ACCUMULATION_SCHEMA_VERSION,
        "symbol": str(symbol).upper(),
        "input_candles": input_candles,
        "vol_7d_avg": None,
        "vol_14d_avg": None,
        "vol_30d_avg": None,
        "vol_ratio_7d_vs_30d": None,
        "vol_ratio_14d_vs_30d": None,
        "price_return_7d": None,
        "price_return_14d": None,
        "price_return_30d": None,
        "price_from_30d_high": None,
        "price_from_52w_high": None,
        "price_from_30d_low": None,
        "price_from_52w_low": None,
        "spike_count_7d": 0,
        "spike_count_14d": 0,
        "spike_count_30d": 0,
        "avg_spike_interval_days": None,
        "min_spike_interval_days": None,
        "repeat_activity_score": 0.0,
        "weekly_trend": None,
        "monthly_trend": None,
        "distance_ma200": None,
        "distance_52w_high": None,
        "distance_52w_low": None,
        "structure_type": "UNKNOWN",
        "setup_type": "UNKNOWN",
        "structure_score": 0.0,
        "accumulation_score_raw": 0.0,
        "accumulation_score": 0.0,
        "hellhound_score": 0.0,
        "distribution_risk": 0.0,
        "error": error,
    }


def _return_over(closes: Sequence[float], days: int) -> Optional[float]:
    if len(closes) <= days:
        return None
    base = closes[-days - 1]
    if base == 0:
        return None
    return (closes[-1] - base) / base


def _distance_from_level(price: float, level: float) -> Optional[float]:
    if level == 0:
        return None
    return (price - level) / level


def _safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def _round_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 6)


def _score_above(value: Any, low: float, high: float, *, weight: float) -> float:
    numeric = _optional_float(value)
    if numeric is None or numeric <= low:
        return 0.0
    if numeric >= high:
        return weight
    return ((numeric - low) / (high - low)) * weight


def _score_below(value: Any, high: float, low: float, *, weight: float) -> float:
    numeric = _optional_float(value)
    if numeric is None or numeric >= high:
        return 0.0
    if numeric <= low:
        return weight
    return ((high - numeric) / (high - low)) * weight


def _score_between(value: Any, low: float, high: float, *, weight: float) -> float:
    numeric = _optional_float(value)
    if numeric is None or numeric < low or numeric > high:
        return 0.0
    center = (low + high) / 2.0
    half_width = (high - low) / 2.0
    if half_width == 0:
        return weight
    return (1.0 - abs(numeric - center) / half_width) * weight


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _nearest_index(candle_times: Sequence[Optional[datetime]], event_time: datetime) -> Optional[int]:
    candidates = [
        (abs((time - event_time).total_seconds()), index)
        for index, time in enumerate(candle_times)
        if time is not None
    ]
    if not candidates:
        return None
    return min(candidates)[1]
