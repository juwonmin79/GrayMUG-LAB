from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence


FEATURE_SCHEMA_VERSION = "hellhound_pre_spike_features_v1"
DEFAULT_LOOKBACK = 20


def build_multitimeframe_snapshot(
    symbol: str,
    candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
) -> Dict[str, Any]:
    candles_by_timeframe = candles_by_timeframe or {}
    timeframes = ("1m", "15m", "1h", "4h", "1d", "1w")
    return {
        "snapshot_schema_version": "hellhound_mtf_snapshot_v1",
        "symbol": str(symbol).upper(),
        "timeframes": {
            timeframe: _timeframe_state(candles_by_timeframe.get(timeframe) or [])
            for timeframe in timeframes
        },
    }


def compute_pre_spike_features(
    candles: Sequence[Mapping[str, Any]],
    *,
    lookback: int = DEFAULT_LOOKBACK,
    spike_threshold_pct: float = 0.08,
    watchlist_age_hours: Optional[float] = None,
) -> Dict[str, Any]:
    window = [_normalize_candle(candle) for candle in candles[-lookback:]]
    window = [candle for candle in window if candle is not None]
    features: Dict[str, Any] = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "lookback": lookback,
        "input_candles": len(window),
        "watchlist_age": watchlist_age_hours,
        "todos": [],
    }
    if len(window) < 6:
        features.update(
            {
                "micro_vol_rise": None,
                "volume_acceleration": None,
                "vol_ma_acceleration": None,
                "price_compression": None,
                "rs_slope": None,
                "candle_body_expansion": None,
                "volatility_contraction": None,
                "spike_count_7d": None,
                "spike_interval": None,
            }
        )
        features["todos"].append("Need at least 6 candles for stable pre-spike features.")
        return features

    volumes = [candle["volume"] for candle in window]
    closes = [candle["close"] for candle in window]
    highs = [candle["high"] for candle in window]
    lows = [candle["low"] for candle in window]
    bodies = [abs(candle["close"] - candle["open"]) for candle in window]

    first_half_vol = _safe_mean(volumes[: len(volumes) // 2])
    second_half_vol = _safe_mean(volumes[len(volumes) // 2 :])
    short_vol = _safe_mean(volumes[-3:])
    base_vol = _safe_mean(volumes[:-3])
    volume_acceleration = _safe_ratio(second_half_vol, first_half_vol)

    features["micro_vol_rise"] = _safe_ratio(short_vol, base_vol)
    features["volume_acceleration"] = (
        round(volume_acceleration - 1.0, 6) if volume_acceleration is not None else None
    )
    features["vol_ma_acceleration"] = features["volume_acceleration"]
    features["price_compression"] = _compression_score(highs, lows, closes)
    features["rs_slope"] = _relative_strength_slope(window)
    features["candle_body_expansion"] = _safe_ratio(_safe_mean(bodies[-3:]), _safe_mean(bodies[:-3]))
    features["volatility_contraction"] = _volatility_contraction(window)
    features["spike_count_7d"] = _spike_count(closes, spike_threshold_pct)
    features["spike_interval"] = _last_spike_interval(closes, spike_threshold_pct)
    if features["rs_slope"] is None:
        features["todos"].append("rs_slope requires btc_close or benchmark_close on candles.")
    if watchlist_age_hours is None:
        features["todos"].append("watchlist_age requires Hound/Hellhound watchlist first_seen integration.")
    return features


def pre_spike_score(features: Mapping[str, Any]) -> float:
    score = 0.0
    score += _score_above(features.get("micro_vol_rise"), 1.15, 1.8, weight=0.22)
    score += _score_above(_first_present(features, "volume_acceleration", "vol_ma_acceleration"), 0.05, 0.7, weight=0.18)
    score += _score_above(features.get("price_compression"), 0.45, 0.9, weight=0.18)
    score += _score_above(features.get("rs_slope"), 0.0, 0.04, weight=0.14)
    score += _score_above(features.get("candle_body_expansion"), 1.1, 2.0, weight=0.14)
    score += _score_above(features.get("volatility_contraction"), 0.25, 0.75, weight=0.08)
    score += _score_above(features.get("spike_count_7d"), 1, 4, weight=0.08)
    score += _score_below(features.get("spike_interval"), 30, 5, weight=0.04)
    return round(min(max(score, 0.0), 1.0), 4)


def _timeframe_state(candles: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized = [_normalize_candle(candle) for candle in candles]
    normalized = [candle for candle in normalized if candle is not None]
    if not normalized:
        return {
            "status": "empty",
            "candle_count": 0,
            "last_close": None,
            "last_volume": None,
            "range_pct": None,
            "volume_ma_ratio": None,
        }
    last = normalized[-1]
    return {
        "status": "ready",
        "candle_count": len(normalized),
        "last_time": last.get("time"),
        "last_close": last["close"],
        "last_volume": last["volume"],
        "range_pct": _range_pct(normalized),
        "volume_ma_ratio": _volume_ma_ratio(normalized),
        "pre_spike_features": compute_pre_spike_features(normalized),
    }


def _normalize_candle(candle: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        return {
            "time": candle.get("time") or candle.get("timestamp") or candle.get("open_time"),
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
            "volume": float(candle.get("volume") or candle.get("quote_volume") or 0.0),
            "btc_close": _optional_float(candle.get("btc_close") or candle.get("benchmark_close")),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _compression_score(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> Optional[float]:
    if not highs or not lows or not closes:
        return None
    last_close = closes[-1]
    if last_close == 0:
        return None
    recent_range = (max(highs[-5:]) - min(lows[-5:])) / abs(last_close)
    full_range = (max(highs) - min(lows)) / abs(last_close)
    if full_range == 0:
        return 1.0
    return round(max(0.0, min(1.0, 1.0 - (recent_range / full_range))), 4)


def _volatility_contraction(candles: Sequence[Mapping[str, Any]]) -> Optional[float]:
    if len(candles) < 6:
        return None
    ranges = [
        (candle["high"] - candle["low"]) / abs(candle["close"])
        for candle in candles
        if candle["close"] != 0
    ]
    if len(ranges) < 6:
        return None
    recent = _safe_mean(ranges[-3:])
    baseline = _safe_mean(ranges[:-3])
    if baseline == 0:
        return None
    return round(max(0.0, min(1.0, 1.0 - (recent / baseline))), 4)


def _range_pct(candles: Sequence[Mapping[str, Any]]) -> Optional[float]:
    if not candles:
        return None
    last_close = candles[-1]["close"]
    if last_close == 0:
        return None
    return round((max(candle["high"] for candle in candles) - min(candle["low"] for candle in candles)) / abs(last_close), 6)


def _volume_ma_ratio(candles: Sequence[Mapping[str, Any]], lookback: int = 20) -> Optional[float]:
    if not candles:
        return None
    volumes = [candle["volume"] for candle in candles[-lookback:]]
    baseline = _safe_mean(volumes[:-1]) if len(volumes) > 1 else _safe_mean(volumes)
    return _safe_ratio(volumes[-1], baseline)


def _relative_strength_slope(candles: Sequence[Mapping[str, Any]]) -> Optional[float]:
    ratios = []
    for candle in candles:
        btc_close = candle.get("btc_close")
        if btc_close in (None, 0):
            return None
        ratios.append(candle["close"] / btc_close)
    if len(ratios) < 2:
        return None
    return round((ratios[-1] - ratios[0]) / ratios[0], 6) if ratios[0] else None


def _spike_count(closes: Sequence[float], threshold_pct: float) -> int:
    count = 0
    for prev, current in zip(closes, closes[1:]):
        if prev and (current - prev) / prev >= threshold_pct:
            count += 1
    return count


def _last_spike_interval(closes: Sequence[float], threshold_pct: float) -> Optional[int]:
    intervals = [
        len(closes) - index - 1
        for index, (prev, current) in enumerate(zip(closes, closes[1:]), start=1)
        if prev and (current - prev) / prev >= threshold_pct
    ]
    return min(intervals) if intervals else None


def _safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(values: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = values.get(key)
        if value is not None:
            return value
    return None


def _score_above(value: Any, low: float, high: float, *, weight: float) -> float:
    numeric = _optional_float(value)
    if numeric is None:
        return 0.0
    if numeric <= low:
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
