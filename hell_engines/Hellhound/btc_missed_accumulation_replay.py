from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from .integration_stub import optional_hellhound_decision
    from .wave_snapshot import _build_snapshot
except ImportError:
    from integration_stub import optional_hellhound_decision
    from wave_snapshot import _build_snapshot


SYMBOL = "BTCUSDT"
INTERVAL = "15m"
BTC_REPLAY_DATASET_PATH = Path(__file__).resolve().parents[2] / "outputs" / "btc_replay_dataset.jsonl"
BTC_REPLAY_REPORT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "btc_replay_report.json"
LEADLINE_REPORT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "leadline_candidate_report.json"
VERDICT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "detectability_verdict.json"
FEATURE_FIELDS = (
    "hellhound_score",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "rsi_15m",
    "macd_hist_15m",
    "btc_weather",
    "signal_hour",
)


def run_btc_replay(
    *,
    candle_limit: int = 1000,
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    candles_15m = fetch_binance_klines(SYMBOL, INTERVAL, limit=candle_limit)
    candles_4h = fetch_binance_klines(SYMBOL, "4h", limit=240)
    target = select_replay_target(candles_15m)
    rows = build_replay_rows(candles_15m, candles_4h, target)
    missed_summary = summarize_missed_reasons(rows)
    candidates = rank_leadline_candidates(candles_15m, candles_4h, rows, target)
    verdict = detectability_verdict(rows, target, candidates)
    report = build_replay_report(rows, target, missed_summary, verdict)

    base_dir = Path(output_dir) if output_dir is not None else BTC_REPLAY_DATASET_PATH.parent
    dataset_path = base_dir / BTC_REPLAY_DATASET_PATH.name
    replay_report_path = base_dir / BTC_REPLAY_REPORT_PATH.name
    leadline_path = base_dir / LEADLINE_REPORT_PATH.name
    verdict_path = base_dir / VERDICT_PATH.name
    write_jsonl(rows, dataset_path)
    write_json(report, replay_report_path)
    write_json(candidates, leadline_path)
    write_json(verdict, verdict_path)
    return {
        "dataset_path": str(dataset_path),
        "replay_report_path": str(replay_report_path),
        "leadline_report_path": str(leadline_path),
        "verdict_path": str(verdict_path),
        "row_count": len(rows),
        "target": target,
        "missed_summary": missed_summary,
        "detectability_verdict": verdict,
        "leadline_top10": candidates["candidates"][:10],
        "is_trade_command": False,
    }


def fetch_binance_klines(symbol: str, interval: str, *, limit: int) -> list[Dict[str, Any]]:
    params = urllib.parse.urlencode(
        {"symbol": symbol.upper(), "interval": interval, "limit": int(limit)}
    )
    endpoint = f"https://api.binance.com/api/v3/klines?{params}"
    request = urllib.request.Request(endpoint, method="GET", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Binance kline response was not a list")
    candles = [_kline_to_candle(row) for row in payload]
    return [row for row in candles if row is not None]


def select_replay_target(candles: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if len(candles) < 220:
        raise ValueError("Need at least 220 15m candles for replay target selection")
    returns_24h = []
    for index in range(60, len(candles) - 96):
        close = _number(candles[index].get("close"))
        future = _number(candles[index + 96].get("close"))
        if close and future:
            returns_24h.append((round((future / close - 1.0) * 100.0, 6), index))
    if not returns_24h:
        raise ValueError("No usable 24h forward returns for replay target selection")
    _, ignition_idx = max(returns_24h, key=lambda item: item[0])
    lookback_start = max(0, ignition_idx - 96)
    accumulation_idx = min(
        range(lookback_start, ignition_idx + 1),
        key=lambda item: float(candles[item]["close"]),
    )
    peak_end = min(len(candles), ignition_idx + 97)
    peak_idx = max(
        range(ignition_idx, peak_end),
        key=lambda item: float(candles[item]["close"]),
    )
    return {
        "symbol": SYMBOL,
        "selection_method": "max_24h_forward_return_latest_1000_15m",
        "accumulation_start": candles[accumulation_idx]["timestamp"],
        "ignition_time": candles[ignition_idx]["timestamp"],
        "local_peak_time": candles[peak_idx]["timestamp"],
        "accumulation_start_index": accumulation_idx,
        "ignition_index": ignition_idx,
        "local_peak_index": peak_idx,
        "ignition_return_24h": _forward_return(candles, ignition_idx, 96),
        "peak_return_from_ignition": _return_between(candles, ignition_idx, peak_idx),
        "is_trade_command": False,
    }


def build_replay_rows(
    candles_15m: Sequence[Mapping[str, Any]],
    candles_4h: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    start = int(target["accumulation_start_index"])
    end = int(target["local_peak_index"])
    rows = []
    for index in range(start, end + 1):
        current = candles_15m[index]
        history = candles_15m[: index + 1]
        timestamp = str(current["timestamp"])
        btc_4h_history = [
            row for row in candles_4h if str(row.get("timestamp")) <= timestamp
        ]
        snapshot = _build_snapshot(
            SYMBOL,
            INTERVAL,
            timestamp,
            candles=history,
            btc_candles_by_timeframe={"4h": btc_4h_history},
        )
        signal = {
            "symbol": SYMBOL,
            "source_time": timestamp,
            "shadow_action": "WATCH",
            "pattern": "BTC_REPLAY",
        }
        decision = optional_hellhound_decision(
            SYMBOL,
            signal=signal,
            shadow_signals=[signal],
            candles_by_timeframe={"15m": history},
            historical_candles=[],
            as_of_time=timestamp,
            decision_enabled=True,
        )
        row = {
            "timestamp": timestamp,
            "symbol": SYMBOL,
            "close": current.get("close"),
            "structure_type": decision.get("structure_type"),
            "promotion_status": decision.get("promotion_status"),
            "hellhound_score": _number(decision.get("hellhound_score")),
            "decision_source": decision.get("decision_source"),
            "volume_ratio_ma5": snapshot.get("volume_ratio_ma5"),
            "volume_ratio_ma20": snapshot.get("volume_ratio_ma20"),
            "rsi_15m": snapshot.get("rsi_15m"),
            "macd_hist_15m": snapshot.get("macd_hist_15m"),
            "btc_weather": snapshot.get("btc_4h_weather"),
            "signal_hour": snapshot.get("signal_hour"),
            "signal_day_of_week": _weekday(timestamp),
            "return_1h": _forward_return(candles_15m, index, 4),
            "return_4h": _forward_return(candles_15m, index, 16),
            "return_24h": _forward_return(candles_15m, index, 96),
            "mfe_pct": _mfe(candles_15m, index, 96),
            "mae_pct": _mae(candles_15m, index, 96),
            "is_trade_command": False,
        }
        row["missed_reason"] = classify_missed_reason(row)
        rows.append(row)
    return rows


def classify_missed_reason(row: Mapping[str, Any]) -> str:
    required = ("volume_ratio_ma5", "volume_ratio_ma20", "rsi_15m", "macd_hist_15m", "btc_weather")
    if any(row.get(key) is None for key in required):
        return "C_FEATURE_MISSING"
    score = _number(row.get("hellhound_score")) or 0.0
    status = str(row.get("promotion_status") or "").upper()
    btc_weather = _number(row.get("btc_weather"))
    if btc_weather is not None and btc_weather < 0:
        return "D_MARKET_ENVIRONMENT_BLOCK"
    if status != "PROMOTE" and score >= 0.60:
        return "A_GATE_BLOCKED"
    if status != "PROMOTE" and score >= 0.40:
        return "B_THRESHOLD_INSUFFICIENT"
    return "E_NOT_DETECTABLE_CURRENT_PIPELINE"


def summarize_missed_reasons(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    pre_ignition = [row for row in rows if row.get("missed_reason")]
    for row in pre_ignition:
        key = str(row["missed_reason"])
        counts[key] = counts.get(key, 0) + 1
    return {
        "total_rows": len(rows),
        "counts": counts,
        "dominant_reason": max(counts, key=counts.get) if counts else None,
        "is_trade_command": False,
    }


def rank_leadline_candidates(
    candles_15m: Sequence[Mapping[str, Any]],
    candles_4h: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> Dict[str, Any]:
    start = int(target["accumulation_start_index"])
    ignition = int(target["ignition_index"])
    lead_count = max(1, ignition - start + 1)
    baseline_start = max(0, start - lead_count)
    baseline_rows = build_baseline_rows(candles_15m, candles_4h, baseline_start, start)
    lead_rows = [row for row in rows if str(row.get("timestamp")) <= str(target["ignition_time"])]
    candidates = []
    for feature in FEATURE_FIELDS:
        baseline_values = [_number(row.get(feature)) for row in baseline_rows]
        lead_values = [_number(row.get(feature)) for row in lead_rows]
        baseline_values = [value for value in baseline_values if value is not None]
        lead_values = [value for value in lead_values if value is not None]
        if not lead_values:
            strength = 0.0
            confidence = "LOW"
            observation_count = 0
        else:
            baseline_avg = mean(baseline_values) if baseline_values else 0.0
            lead_avg = mean(lead_values)
            scale = pstdev(baseline_values) if len(baseline_values) > 1 else abs(baseline_avg) or 1.0
            strength = round(abs(lead_avg - baseline_avg) / (scale or 1.0), 6)
            observation_count = len(lead_values)
            confidence = _confidence(strength, observation_count)
        candidates.append(
            {
                "rank": 0,
                "feature": feature,
                "lead_strength": strength,
                "confidence": confidence,
                "observation_count": observation_count,
                "is_trade_command": False,
            }
        )
    candidates.sort(key=lambda row: (row["lead_strength"], row["observation_count"]), reverse=True)
    for rank, row in enumerate(candidates, start=1):
        row["rank"] = rank
    return {
        "symbol": SYMBOL,
        "candidate_schema_version": "btc_leadline_candidate_report_v1",
        "candidates": candidates,
        "is_trade_command": False,
    }


def build_baseline_rows(
    candles_15m: Sequence[Mapping[str, Any]],
    candles_4h: Sequence[Mapping[str, Any]],
    start: int,
    end: int,
) -> list[Dict[str, Any]]:
    if end <= start:
        return []
    synthetic_target = {
        "accumulation_start_index": start,
        "local_peak_index": end - 1,
    }
    return build_replay_rows(candles_15m, candles_4h, synthetic_target)


def detectability_verdict(
    rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    candidates: Mapping[str, Any],
) -> Dict[str, Any]:
    ignition_time = str(target["ignition_time"])
    pre_ignition = [row for row in rows if str(row.get("timestamp")) <= ignition_time]
    promoted = [row for row in pre_ignition if str(row.get("promotion_status") or "").upper() == "PROMOTE"]
    max_score = max((_number(row.get("hellhound_score")) or 0.0 for row in pre_ignition), default=0.0)
    feature_complete = sum(
        1
        for row in pre_ignition
        if all(row.get(field) is not None for field in ("volume_ratio_ma5", "volume_ratio_ma20", "rsi_15m", "macd_hist_15m", "btc_weather"))
    )
    feature_coverage = round(feature_complete / len(pre_ignition), 6) if pre_ignition else 0.0
    top_strength = max((row.get("lead_strength") or 0.0 for row in candidates.get("candidates", [])), default=0.0)
    if promoted:
        verdict = "DETECTABLE_NOW"
        reason = "At least one pre-ignition row reached current PROMOTE gate."
    elif feature_coverage >= 0.8 and max_score >= 0.40:
        verdict = "DETECTABLE_AFTER_THRESHOLD_TUNING"
        reason = "Pre-ignition features are present and score reached watchable range without promotion."
    elif feature_coverage >= 0.8 and top_strength >= 1.0:
        verdict = "DETECTABLE_AFTER_THRESHOLD_TUNING"
        reason = "Existing features moved before ignition, but current score/gate did not promote."
    else:
        verdict = "NOT_DETECTABLE_YET"
        reason = "Current features and score did not provide a pre-ignition detectable signal."
    return {
        "symbol": SYMBOL,
        "detectability_verdict": verdict,
        "reason": reason,
        "max_pre_ignition_score": round(max_score, 6),
        "pre_ignition_feature_coverage": feature_coverage,
        "pre_ignition_promote_count": len(promoted),
        "top_lead_strength": top_strength,
        "accumulation_start": target.get("accumulation_start"),
        "ignition_time": target.get("ignition_time"),
        "local_peak_time": target.get("local_peak_time"),
        "is_trade_command": False,
    }


def build_replay_report(
    rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    missed_summary: Mapping[str, Any],
    verdict: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "btc_replay_report_schema_version": "btc_missed_accumulation_replay_v1",
        "target": dict(target),
        "row_count": len(rows),
        "score_summary": {
            "min": _aggregate(rows, "hellhound_score", min),
            "max": _aggregate(rows, "hellhound_score", max),
            "average": _aggregate(rows, "hellhound_score", mean),
        },
        "missed_reason_summary": dict(missed_summary),
        "detectability_verdict": dict(verdict),
        "is_trade_command": False,
    }


def write_jsonl(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(dict(row), sort_keys=True) + "\n")


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _kline_to_candle(row: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(row, list) or len(row) < 6:
        return None
    try:
        open_time_ms = int(row[0])
        return {
            "timestamp": datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc).isoformat(),
            "open_time": open_time_ms,
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
    except (TypeError, ValueError, OSError):
        return None


def _forward_return(candles: Sequence[Mapping[str, Any]], index: int, offset: int) -> Optional[float]:
    if index + offset >= len(candles):
        return None
    return _return_between(candles, index, index + offset)


def _return_between(candles: Sequence[Mapping[str, Any]], start: int, end: int) -> Optional[float]:
    entry = _number(candles[start].get("close"))
    exit_price = _number(candles[end].get("close"))
    if not entry or exit_price is None:
        return None
    return round((exit_price / entry - 1.0) * 100.0, 6)


def _mfe(candles: Sequence[Mapping[str, Any]], index: int, offset: int) -> Optional[float]:
    entry = _number(candles[index].get("close"))
    if not entry:
        return None
    window = candles[index : min(len(candles), index + offset + 1)]
    highs = [_number(row.get("high")) for row in window]
    highs = [value for value in highs if value is not None]
    return round((max(highs) / entry - 1.0) * 100.0, 6) if highs else None


def _mae(candles: Sequence[Mapping[str, Any]], index: int, offset: int) -> Optional[float]:
    entry = _number(candles[index].get("close"))
    if not entry:
        return None
    window = candles[index : min(len(candles), index + offset + 1)]
    lows = [_number(row.get("low")) for row in window]
    lows = [value for value in lows if value is not None]
    return round((min(lows) / entry - 1.0) * 100.0, 6) if lows else None


def _weekday(timestamp: str) -> Optional[int]:
    try:
        return datetime.fromisoformat(timestamp).weekday()
    except ValueError:
        return None


def _aggregate(rows: Sequence[Mapping[str, Any]], field: str, func: Any) -> Optional[float]:
    values = [_number(row.get(field)) for row in rows]
    values = [value for value in values if value is not None]
    return round(float(func(values)), 6) if values else None


def _confidence(strength: float, count: int) -> str:
    if count >= 12 and strength >= 1.0:
        return "HIGH"
    if count >= 6 and strength >= 0.5:
        return "MEDIUM"
    return "LOW"


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    limit = int(os.environ.get("BTC_REPLAY_CANDLE_LIMIT", "1000"))
    result = run_btc_replay(candle_limit=limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
