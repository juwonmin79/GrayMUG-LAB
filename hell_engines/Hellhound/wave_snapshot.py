from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence, Union


WAVE_SNAPSHOT_SCHEMA_VERSION = "hellhound_wave_snapshot_v0"
WAVE_LOG_SCHEMA_VERSION = "hellhound_wave_log_v0"
DEFAULT_WAVE_LOG_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_wave_log.jsonl"
WAVE_LOG_ID_NAMESPACE = uuid.UUID("4e62d0f7-6d4a-4a98-9c6c-f6ef44f3a902")
SNAPSHOT_KEYS = (
    "price_vs_ma20",
    "price_vs_ma99",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "rsi_15m",
    "macd_hist_15m",
    "btc_15m_trend",
    "btc_1h_trend",
    "btc_4h_trend",
    "btc_1d_trend",
    "btc_4h_weather",
    "signal_hour",
    "is_daily_open",
    "is_weekly_open",
    "is_monthly_open",
)


def _build_snapshot(
    symbol: str,
    timeframe: str,
    timestamp: Any,
    *,
    candles: Optional[Sequence[Mapping[str, Any]]] = None,
    btc_candles_by_timeframe: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Build a market state vector. It does not emit trade advice."""
    parsed_time = _parse_time(timestamp)
    normalized_candles = _normalized_candles(candles or [])
    closes = [row["close"] for row in normalized_candles]
    volumes = [row["volume"] for row in normalized_candles]
    last_close = closes[-1] if closes else None
    last_volume = volumes[-1] if volumes else None
    btc_candles_by_timeframe = btc_candles_by_timeframe or {}

    snapshot = {
        "wave_snapshot_schema_version": WAVE_SNAPSHOT_SCHEMA_VERSION,
        "symbol": str(symbol).upper(),
        "timeframe": str(timeframe),
        "timestamp": parsed_time.isoformat() if parsed_time else str(timestamp),
        "price_vs_ma20": _price_vs_ma(last_close, closes, 20),
        "price_vs_ma99": _price_vs_ma(last_close, closes, 99),
        "volume_ratio_ma5": _ratio_to_ma(last_volume, volumes, 5),
        "volume_ratio_ma20": _ratio_to_ma(last_volume, volumes, 20),
        "rsi_15m": _rsi(closes, 14),
        "macd_hist_15m": _macd_hist(closes),
        "btc_15m_trend": _btc_trend(btc_candles_by_timeframe.get("15m") or []),
        "btc_1h_trend": _btc_trend(btc_candles_by_timeframe.get("1h") or []),
        "btc_4h_trend": _btc_trend(btc_candles_by_timeframe.get("4h") or []),
        "btc_1d_trend": _btc_trend(btc_candles_by_timeframe.get("1d") or []),
        "btc_4h_weather": _btc_weather(_btc_trend(btc_candles_by_timeframe.get("4h") or [])),
        "signal_hour": parsed_time.hour if parsed_time else None,
        "is_daily_open": _is_daily_open(parsed_time),
        "is_weekly_open": _is_weekly_open(parsed_time),
        "is_monthly_open": _is_monthly_open(parsed_time),
        "is_trade_command": False,
    }
    return snapshot


def build_wave_features(
    *,
    signal_id: str,
    symbol: str,
    timeframe: str,
    timestamp_t2: Any,
    timestamp_t1: Any,
    timestamp_t0: Any,
    candles_t2: Sequence[Mapping[str, Any]],
    candles_t1: Sequence[Mapping[str, Any]],
    candles_t0: Sequence[Mapping[str, Any]],
    btc_candles_by_timeframe_t2: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    btc_candles_by_timeframe_t1: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    btc_candles_by_timeframe_t0: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
) -> Dict[str, Any]:
    snapshot_t2 = _build_snapshot(
        symbol,
        timeframe,
        timestamp_t2,
        candles=candles_t2,
        btc_candles_by_timeframe=btc_candles_by_timeframe_t2,
    )
    snapshot_t1 = _build_snapshot(
        symbol,
        timeframe,
        timestamp_t1,
        candles=candles_t1,
        btc_candles_by_timeframe=btc_candles_by_timeframe_t1,
    )
    snapshot_t0 = _build_snapshot(
        symbol,
        timeframe,
        timestamp_t0,
        candles=candles_t0,
        btc_candles_by_timeframe=btc_candles_by_timeframe_t0,
    )
    diff_a = diff_snapshots(snapshot_t1, snapshot_t2)
    diff_b = diff_snapshots(snapshot_t0, snapshot_t1)
    delta = diff_snapshots(diff_b, diff_a)
    created_at = _now_utc()
    return {
        "wave_log_schema_version": WAVE_LOG_SCHEMA_VERSION,
        "wave_log_id": _stable_wave_log_id(signal_id, symbol, timestamp_t0),
        "signal_id": str(signal_id),
        "symbol": str(symbol).upper(),
        "timeframe": str(timeframe),
        "snapshot_t2": snapshot_t2,
        "snapshot_t1": snapshot_t1,
        "snapshot_t0": snapshot_t0,
        "diff_a": diff_a,
        "diff_b": diff_b,
        "delta": delta,
        "created_at": created_at,
        "outcome_mfe_6h": None,
        "outcome_mae_6h": None,
        "outcome_time_to_peak_6h": None,
        "outcome_time_to_stop_6h": None,
        "outcome_mfe_24h": None,
        "outcome_mae_24h": None,
        "outcome_time_to_peak_24h": None,
        "outcome_time_to_stop_24h": None,
        "outcome_mfe_72h": None,
        "outcome_mae_72h": None,
        "outcome_time_to_peak_72h": None,
        "outcome_time_to_stop_72h": None,
        "is_trade_command": False,
    }


def diff_snapshots(current: Mapping[str, Any], previous: Mapping[str, Any]) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    for key in SNAPSHOT_KEYS:
        left = _numeric_value(current.get(key))
        right = _numeric_value(previous.get(key))
        diff[key] = round(left - right, 10) if left is not None and right is not None else None
    diff["is_trade_command"] = False
    return diff


def write_wave_log(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_WAVE_LOG_PATH,
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
        "wave_log_schema_version": WAVE_LOG_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def _normalized_candles(candles: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    rows = []
    for candle in candles:
        try:
            rows.append(
                {
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle.get("volume") or candle.get("quote_volume") or 0.0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def _price_vs_ma(price: Optional[float], closes: Sequence[float], lookback: int) -> Optional[float]:
    if price is None or len(closes) < lookback:
        return None
    baseline = mean(closes[-lookback:])
    if baseline == 0:
        return None
    return round((price / baseline) - 1.0, 10)


def _ratio_to_ma(value: Optional[float], values: Sequence[float], lookback: int) -> Optional[float]:
    if value is None or len(values) < lookback:
        return None
    baseline = mean(values[-lookback:])
    if baseline == 0:
        return None
    return round(value / baseline, 10)


def _rsi(closes: Sequence[float], period: int) -> Optional[float]:
    if len(closes) <= period:
        return None
    gains = []
    losses = []
    for previous, current in zip(closes[-period - 1 : -1], closes[-period:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 6)


def _macd_hist(closes: Sequence[float]) -> Optional[float]:
    if len(closes) < 35:
        return None
    macd_line = _ema(closes, 12) - _ema(closes, 26)
    macd_series = []
    for end in range(26, len(closes) + 1):
        window = closes[:end]
        macd_series.append(_ema(window, 12) - _ema(window, 26))
    signal = _ema(macd_series, 9)
    return round(macd_line - signal, 10)


def _ema(values: Sequence[float], period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    ema = float(values[0])
    for value in values[1:]:
        ema = float(value) * alpha + ema * (1.0 - alpha)
    return ema


def _btc_trend(candles: Sequence[Mapping[str, Any]], lookback: int = 5) -> Optional[float]:
    rows = _normalized_candles(candles)
    if len(rows) < 2:
        return None
    closes = [row["close"] for row in rows[-lookback:]]
    if len(closes) < 2 or closes[0] == 0:
        return None
    return round((closes[-1] / closes[0]) - 1.0, 10)


def _btc_weather(trend: Optional[float]) -> Optional[float]:
    if trend is None:
        return None
    if trend >= 0.015:
        return 1.0
    if trend <= -0.015:
        return -1.0
    return 0.0


def _numeric_value(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _is_daily_open(value: Optional[datetime]) -> bool:
    return bool(value and value.hour == 0)


def _is_weekly_open(value: Optional[datetime]) -> bool:
    return bool(value and value.weekday() == 0 and value.hour == 0)


def _is_monthly_open(value: Optional[datetime]) -> bool:
    return bool(value and value.day == 1 and value.hour == 0)


def _stable_wave_log_id(signal_id: str, symbol: str, timestamp: Any) -> str:
    seed = f"hellhound:wave-log:v0:{signal_id}:{str(symbol).upper()}:{timestamp}"
    return str(uuid.uuid5(WAVE_LOG_ID_NAMESPACE, seed))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
