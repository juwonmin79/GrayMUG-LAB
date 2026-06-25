from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from .integration_stub import optional_hellhound_decision
    from .mirror_pattern_feature_discovery import (
        FOCUS_FEATURES,
        acceleration_summary,
        build_sequence_report,
        build_temporal_report,
        persistence_summary,
        segment_rows,
        slope,
    )
    from .wave_snapshot import _build_snapshot
except ImportError:
    from integration_stub import optional_hellhound_decision
    from mirror_pattern_feature_discovery import (
        FOCUS_FEATURES,
        acceleration_summary,
        build_sequence_report,
        build_temporal_report,
        persistence_summary,
        segment_rows,
        slope,
    )
    from wave_snapshot import _build_snapshot


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CONTRAST_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_dataset.json"
CONTRAST_REPORT_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_report.json"
FEATURE_VALIDATION_PATH = DEFAULT_OUTPUT_DIR / "mirror_feature_validation.json"
CONTRAST_MATRIX_PATH = DEFAULT_OUTPUT_DIR / "replay_contrast_matrix.json"
FEATURE_STABILITY_PATH = DEFAULT_OUTPUT_DIR / "mirror_feature_stability.json"
DEFAULT_CANDIDATE_SYMBOLS = (
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "SUIUSDT",
    "NEARUSDT",
    "WLDUSDT",
    "TAOUSDT",
    "ZECUSDT",
    "OPUSDT",
    "ARBUSDT",
)


def run_mirror_contrast_dataset(
    *,
    output_dir: Optional[Path | str] = None,
    symbols: Sequence[str] = DEFAULT_CANDIDATE_SYMBOLS,
    success_count: int = 2,
    failure_count: int = 2,
    candle_limit: int = 1000,
) -> Dict[str, Any]:
    btc_4h = fetch_binance_klines("BTCUSDT", "4h", limit=240)
    cases = select_contrast_cases(
        symbols=symbols,
        success_count=success_count,
        failure_count=failure_count,
        candle_limit=candle_limit,
    )
    replay_cases = []
    for case in cases:
        rows = build_case_replay_rows(case["candles_15m"], btc_4h, case["target"])
        analysis = analyze_case(rows, case["target"])
        replay_cases.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "symbol": case["symbol"],
                "target": _public_target(case["target"]),
                "rows": rows,
                "analysis": analysis,
                "is_trade_command": False,
            }
        )
    contrast_matrix = build_contrast_matrix(replay_cases)
    feature_validation = validate_mirror_candidates(replay_cases)
    feature_stability = build_feature_stability(replay_cases)
    report = build_contrast_report(replay_cases, contrast_matrix, feature_validation, feature_stability)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    dataset_path = base / CONTRAST_DATASET_PATH.name
    report_path = base / CONTRAST_REPORT_PATH.name
    validation_path = base / FEATURE_VALIDATION_PATH.name
    matrix_path = base / CONTRAST_MATRIX_PATH.name
    stability_path = base / FEATURE_STABILITY_PATH.name
    write_json({"mirror_contrast_dataset_schema_version": "mirror_contrast_dataset_v1", "cases": replay_cases, "is_trade_command": False}, dataset_path)
    write_json(report, report_path)
    write_json(feature_validation, validation_path)
    write_json(contrast_matrix, matrix_path)
    write_json(feature_stability, stability_path)
    return {
        "mirror_contrast_dataset_schema_version": "mirror_contrast_dataset_v1",
        "case_count": len(replay_cases),
        "success_count": sum(1 for case in replay_cases if case["case_type"] == "success"),
        "failure_count": sum(1 for case in replay_cases if case["case_type"] == "failure"),
        "dataset_path": str(dataset_path),
        "report_path": str(report_path),
        "feature_validation_path": str(validation_path),
        "contrast_matrix_path": str(matrix_path),
        "feature_stability_path": str(stability_path),
        "is_trade_command": False,
    }


def select_contrast_cases(
    *,
    symbols: Sequence[str],
    success_count: int,
    failure_count: int,
    candle_limit: int,
) -> list[Dict[str, Any]]:
    success_candidates = []
    failure_candidates = []
    for symbol in symbols:
        try:
            candles = fetch_binance_klines(symbol, "15m", limit=candle_limit)
        except Exception:
            continue
        if len(candles) < 220:
            continue
        success_target = select_success_target(symbol, candles)
        if success_target:
            success_candidates.append((success_target["selection_score"], symbol, candles, success_target))
        failure_target = select_failure_target(symbol, candles)
        if failure_target:
            failure_candidates.append((failure_target["selection_score"], symbol, candles, failure_target))
    success_candidates.sort(key=lambda item: item[0], reverse=True)
    failure_candidates.sort(key=lambda item: item[0], reverse=True)
    cases = []
    used_success_symbols = set()
    for _, symbol, candles, target in success_candidates:
        if len(cases) >= success_count:
            break
        if symbol in used_success_symbols:
            continue
        used_success_symbols.add(symbol)
        cases.append(_case("success", symbol, candles, target, len(cases) + 1))
    failure_cases = []
    used_failure_symbols = set()
    for _, symbol, candles, target in failure_candidates:
        if len(failure_cases) >= failure_count:
            break
        if symbol in used_failure_symbols:
            continue
        used_failure_symbols.add(symbol)
        failure_cases.append(_case("failure", symbol, candles, target, len(failure_cases) + 1))
    if len(cases) < success_count or len(failure_cases) < failure_count:
        raise ValueError("Unable to select enough success/failure replay cases from available symbols")
    return cases + failure_cases


def select_success_target(symbol: str, candles: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[tuple[float, int]] = None
    for index in range(96, len(candles) - 96):
        ret24 = _forward_return(candles, index, 96)
        if ret24 is None:
            continue
        if best is None or ret24 > best[0]:
            best = (ret24, index)
    if best is None or best[0] < 3.0:
        return None
    return _target_from_ignition(symbol, candles, best[1], case_type="success", selection_score=best[0])


def select_failure_target(symbol: str, candles: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[tuple[float, int, float, float]] = None
    for index in range(96, len(candles) - 96):
        ret4 = _forward_return(candles, index, 16)
        ret24 = _forward_return(candles, index, 96)
        if ret4 is None or ret24 is None:
            continue
        if ret4 < 1.5:
            continue
        failure_strength = ret4 - min(ret24, ret4)
        if ret24 <= 0:
            failure_strength += abs(ret24)
        elif ret24 < ret4 * 0.25:
            failure_strength += ret4 - ret24
        else:
            continue
        if best is None or failure_strength > best[0]:
            best = (failure_strength, index, ret4, ret24)
    if best is None:
        return None
    target = _target_from_ignition(symbol, candles, best[1], case_type="failure", selection_score=best[0])
    target["failure_return_4h"] = round(best[2], 6)
    target["failure_return_24h"] = round(best[3], 6)
    return target


def build_case_replay_rows(
    candles_15m: Sequence[Mapping[str, Any]],
    btc_4h: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    rows = []
    start = int(target["accumulation_start_index"])
    end = int(target["replay_end_index"])
    symbol = str(target["symbol"])
    for index in range(start, end + 1):
        current = candles_15m[index]
        history = candles_15m[: index + 1]
        timestamp = str(current["timestamp"])
        btc_history = [row for row in btc_4h if str(row.get("timestamp")) <= timestamp]
        snapshot = _build_snapshot(
            symbol,
            "15m",
            timestamp,
            candles=history,
            btc_candles_by_timeframe={"4h": btc_history},
        )
        signal = {
            "symbol": symbol,
            "source_time": timestamp,
            "shadow_action": "WATCH",
            "pattern": f"MIRROR_CONTRAST_{str(target['case_type']).upper()}",
        }
        decision = optional_hellhound_decision(
            symbol,
            signal=signal,
            shadow_signals=[signal],
            candles_by_timeframe={"15m": history},
            historical_candles=[],
            as_of_time=timestamp,
            decision_enabled=True,
        )
        row = {
            "timestamp": timestamp,
            "symbol": symbol,
            "case_type": target["case_type"],
            "close": current.get("close"),
            "hellhound_score": _number(decision.get("hellhound_score")),
            "rsi_15m": snapshot.get("rsi_15m"),
            "volume_ratio_ma20": snapshot.get("volume_ratio_ma20"),
            "promotion_status": decision.get("promotion_status"),
            "structure_type": decision.get("structure_type"),
            "return_4h": _forward_return(candles_15m, index, 16),
            "return_24h": _forward_return(candles_15m, index, 96),
            "mfe_pct": _mfe(candles_15m, index, 96),
            "mae_pct": _mae(candles_15m, index, 96),
            "is_trade_command": False,
        }
        rows.append(row)
    return rows


def analyze_case(rows: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> Dict[str, Any]:
    segmented = segment_rows(rows, target)
    temporal = build_temporal_report(segmented, target)
    sequence = build_sequence_report(segmented, target)
    return {
        "temporal": temporal,
        "sequence": sequence,
        "metrics": case_metrics(rows, temporal, sequence, target),
        "is_trade_command": False,
    }


def case_metrics(
    rows: Sequence[Mapping[str, Any]],
    temporal: Mapping[str, Any],
    sequence: Mapping[str, Any],
    target: Mapping[str, Any],
) -> Dict[str, Any]:
    features = temporal.get("features", {})
    relation = sequence.get("cross_feature_relation", {})
    return {
        "score_slope_4": _feature_slope(features, "hellhound_score", "4_candles"),
        "rsi_persistence": features.get("rsi_15m", {}).get("persistence", {}).get("max_increase_candles"),
        "volume_delay_after_score": relation.get("lead_lag_candles", {}).get("hellhound_score_to_volume_ratio_ma20"),
        "sequence": sequence.get("dominant_sequence"),
        "ignition_return_24h": target.get("ignition_return_24h"),
        "mfe_from_ignition": _mfe_from_ignition(rows, target),
        "mae_from_ignition": _mae_from_ignition(rows, target),
        "is_trade_command": False,
    }


def build_contrast_matrix(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for case in cases:
        metrics = case["analysis"]["metrics"]
        rows.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "symbol": case["symbol"],
                "score_slope_4": metrics.get("score_slope_4"),
                "rsi_persistence": metrics.get("rsi_persistence"),
                "volume_delay_after_score": metrics.get("volume_delay_after_score"),
                "sequence": metrics.get("sequence"),
                "ignition_return_24h": metrics.get("ignition_return_24h"),
                "mfe_from_ignition": metrics.get("mfe_from_ignition"),
                "mae_from_ignition": metrics.get("mae_from_ignition"),
                "is_trade_command": False,
            }
        )
    return {
        "replay_contrast_matrix_schema_version": "replay_contrast_matrix_v1",
        "rows": rows,
        "summary": {
            "success": _summary([row for row in rows if row["case_type"] == "success"]),
            "failure": _summary([row for row in rows if row["case_type"] == "failure"]),
        },
        "is_trade_command": False,
    }


def validate_mirror_candidates(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    validations = []
    for feature in FOCUS_FEATURES:
        success_cases = [case for case in cases if case["case_type"] == "success"]
        failure_cases = [case for case in cases if case["case_type"] == "failure"]
        success_hits = sum(1 for case in success_cases if _candidate_repeats(case, feature))
        failure_hits = sum(1 for case in failure_cases if _candidate_repeats(case, feature))
        validations.append(
            {
                "feature": feature,
                "success_repeat_count": success_hits,
                "failure_repeat_count": failure_hits,
                "success_case_count": len(success_cases),
                "failure_case_count": len(failure_cases),
                "breaks_in_failure": failure_hits < len(failure_cases),
                "validated": success_hits == len(success_cases) and failure_hits < len(failure_cases),
                "is_trade_command": False,
            }
        )
    return {
        "mirror_feature_validation_schema_version": "mirror_feature_validation_v1",
        "validations": validations,
        "is_trade_command": False,
    }


def build_feature_stability(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    stability = []
    for feature in FOCUS_FEATURES:
        success_values = [_case_feature_strength(case, feature) for case in cases if case["case_type"] == "success"]
        failure_values = [_case_feature_strength(case, feature) for case in cases if case["case_type"] == "failure"]
        stability.append(
            {
                "feature": feature,
                "success_average_strength": _average(success_values),
                "failure_average_strength": _average(failure_values),
                "contrast_delta": _delta(_average(success_values), _average(failure_values)),
                "is_trade_command": False,
            }
        )
    return {
        "mirror_feature_stability_schema_version": "mirror_feature_stability_v1",
        "features": stability,
        "is_trade_command": False,
    }


def build_contrast_report(
    cases: Sequence[Mapping[str, Any]],
    matrix: Mapping[str, Any],
    validation: Mapping[str, Any],
    stability: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "mirror_contrast_report_schema_version": "mirror_contrast_report_v1",
        "case_count": len(cases),
        "success_count": sum(1 for case in cases if case["case_type"] == "success"),
        "failure_count": sum(1 for case in cases if case["case_type"] == "failure"),
        "case_targets": [
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "symbol": case["symbol"],
                "target": case["target"],
                "is_trade_command": False,
            }
            for case in cases
        ],
        "contrast_matrix_summary": matrix.get("summary"),
        "feature_validation": validation.get("validations"),
        "feature_stability": stability.get("features"),
        "is_trade_command": False,
    }


def fetch_binance_klines(symbol: str, interval: str, *, limit: int) -> list[Dict[str, Any]]:
    params = urllib.parse.urlencode({"symbol": symbol.upper(), "interval": interval, "limit": int(limit)})
    req = urllib.request.Request(
        f"https://api.binance.com/api/v3/klines?{params}",
        method="GET",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [row for row in (_kline_to_candle(item) for item in payload if isinstance(payload, list)) if row is not None]


def _target_from_ignition(
    symbol: str,
    candles: Sequence[Mapping[str, Any]],
    ignition_idx: int,
    *,
    case_type: str,
    selection_score: float,
) -> Dict[str, Any]:
    start = min(range(max(0, ignition_idx - 96), ignition_idx + 1), key=lambda index: float(candles[index]["close"]))
    peak_end = min(len(candles), ignition_idx + 97)
    peak = max(range(ignition_idx, peak_end), key=lambda index: float(candles[index]["close"]))
    replay_end = min(len(candles) - 1, ignition_idx + 96)
    return {
        "symbol": symbol,
        "case_type": case_type,
        "selection_score": round(selection_score, 6),
        "accumulation_start": candles[start]["timestamp"],
        "ignition_time": candles[ignition_idx]["timestamp"],
        "local_peak_time": candles[peak]["timestamp"],
        "replay_end_time": candles[replay_end]["timestamp"],
        "accumulation_start_index": start,
        "ignition_index": ignition_idx,
        "local_peak_index": peak,
        "replay_end_index": replay_end,
        "ignition_return_24h": _forward_return(candles, ignition_idx, 96),
        "is_trade_command": False,
    }


def _case(case_type: str, symbol: str, candles: Sequence[Mapping[str, Any]], target: Mapping[str, Any], index: int) -> Dict[str, Any]:
    return {
        "case_id": f"{case_type}-{index}-{symbol}",
        "case_type": case_type,
        "symbol": symbol,
        "candles_15m": list(candles),
        "target": dict(target),
        "is_trade_command": False,
    }


def _public_target(target: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in target.items() if not str(key).endswith("_index")}


def _feature_slope(features: Mapping[str, Any], feature: str, window: str) -> Optional[float]:
    return features.get(feature, {}).get("slopes", {}).get(window)


def _candidate_repeats(case: Mapping[str, Any], feature: str) -> bool:
    data = case["analysis"]["temporal"]["features"].get(feature, {})
    persistence = int(data.get("persistence", {}).get("max_increase_candles") or 0)
    max_slope = max((abs(float(value or 0.0)) for value in data.get("slopes", {}).values()), default=0.0)
    return persistence >= 3 and max_slope > 0.0


def _case_feature_strength(case: Mapping[str, Any], feature: str) -> float:
    data = case["analysis"]["temporal"]["features"].get(feature, {})
    persistence = float(data.get("persistence", {}).get("max_increase_candles") or 0.0)
    max_slope = max((abs(float(value or 0.0)) for value in data.get("slopes", {}).values()), default=0.0)
    return round(persistence + max_slope, 6)


def _summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "count": len(rows),
        "average_score_slope_4": _average([row.get("score_slope_4") for row in rows]),
        "average_rsi_persistence": _average([row.get("rsi_persistence") for row in rows]),
        "average_volume_delay_after_score": _average([row.get("volume_delay_after_score") for row in rows]),
        "average_ignition_return_24h": _average([row.get("ignition_return_24h") for row in rows]),
    }


def _mfe_from_ignition(rows: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> Optional[float]:
    ignition = str(target.get("ignition_time"))
    match = next((row for row in rows if row.get("timestamp") == ignition), None)
    return _number(match.get("mfe_pct")) if match else None


def _mae_from_ignition(rows: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> Optional[float]:
    ignition = str(target.get("ignition_time"))
    match = next((row for row in rows if row.get("timestamp") == ignition), None)
    return _number(match.get("mae_pct")) if match else None


def _forward_return(candles: Sequence[Mapping[str, Any]], index: int, offset: int) -> Optional[float]:
    if index + offset >= len(candles):
        return None
    start = _number(candles[index].get("close"))
    end = _number(candles[index + offset].get("close"))
    if not start or end is None:
        return None
    return round((end / start - 1.0) * 100.0, 6)


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


def _kline_to_candle(row: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(row, list) or len(row) < 6:
        return None
    try:
        return {
            "timestamp": datetime.fromtimestamp(int(row[0]) / 1000.0, tz=timezone.utc).isoformat(),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
    except (TypeError, ValueError, OSError):
        return None


def _average(values: Sequence[Any]) -> Optional[float]:
    parsed = [_number(value) for value in values]
    parsed = [value for value in parsed if value is not None]
    return round(mean(parsed), 6) if parsed else None


def _delta(left: Optional[float], right: Optional[float]) -> Optional[float]:
    return round(left - right, 6) if left is not None and right is not None else None


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_contrast_dataset()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
