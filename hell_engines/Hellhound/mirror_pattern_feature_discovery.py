from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence


FOCUS_FEATURES = ("hellhound_score", "rsi_15m", "volume_ratio_ma20")
SLOPE_WINDOWS = (2, 4, 8, 16)
DEFAULT_REPLAY_DATASET_PATH = Path(__file__).resolve().parents[2] / "outputs" / "btc_replay_dataset.jsonl"
DEFAULT_REPLAY_REPORT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "btc_replay_report.json"
DEFAULT_CANDIDATES_PATH = Path(__file__).resolve().parents[2] / "outputs" / "mirror_pattern_feature_candidates.json"
DEFAULT_SEQUENCE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "mirror_pattern_sequence_report.json"
DEFAULT_TEMPORAL_PATH = Path(__file__).resolve().parents[2] / "outputs" / "pre_ignition_temporal_report.json"
DEFAULT_TRANSITION_PATH = Path(__file__).resolve().parents[2] / "outputs" / "feature_transition_matrix.json"


def run_mirror_pattern_feature_discovery(
    *,
    replay_dataset_path: Path | str = DEFAULT_REPLAY_DATASET_PATH,
    replay_report_path: Path | str = DEFAULT_REPLAY_REPORT_PATH,
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    rows = load_jsonl(replay_dataset_path)
    replay_report = load_json(replay_report_path)
    target = dict(replay_report.get("target") or {})
    segmented = segment_rows(rows, target)
    temporal_report = build_temporal_report(segmented, target)
    sequence_report = build_sequence_report(segmented, target)
    transition_matrix = build_transition_matrix(segmented)
    feature_candidates = build_feature_candidates(temporal_report, sequence_report, transition_matrix)

    base_dir = Path(output_dir) if output_dir is not None else DEFAULT_CANDIDATES_PATH.parent
    candidates_path = base_dir / DEFAULT_CANDIDATES_PATH.name
    sequence_path = base_dir / DEFAULT_SEQUENCE_PATH.name
    temporal_path = base_dir / DEFAULT_TEMPORAL_PATH.name
    transition_path = base_dir / DEFAULT_TRANSITION_PATH.name
    write_json(feature_candidates, candidates_path)
    write_json(sequence_report, sequence_path)
    write_json(temporal_report, temporal_path)
    write_json(transition_matrix, transition_path)
    return {
        "mirror_pattern_feature_discovery_schema_version": "mirror_pattern_feature_discovery_v1",
        "row_count": len(rows),
        "candidates_path": str(candidates_path),
        "sequence_path": str(sequence_path),
        "temporal_path": str(temporal_path),
        "transition_path": str(transition_path),
        "top_candidates": feature_candidates["candidates"][:10],
        "dominant_sequence": sequence_report["dominant_sequence"],
        "is_trade_command": False,
    }


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, Mapping) and row.get("is_trade_command") is False:
            rows.append(dict(row))
    return rows


def load_json(path: Path | str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def segment_rows(rows: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> Dict[str, list[Dict[str, Any]]]:
    ignition_time = str(target.get("ignition_time") or "")
    peak_time = str(target.get("local_peak_time") or "")
    pre = [dict(row) for row in rows if str(row.get("timestamp") or "") < ignition_time]
    ignition = [dict(row) for row in rows if str(row.get("timestamp") or "") == ignition_time]
    post = [
        dict(row)
        for row in rows
        if ignition_time < str(row.get("timestamp") or "") <= peak_time
    ]
    return {"pre_ignition": pre, "ignition": ignition, "post_ignition": post, "all": [dict(row) for row in rows]}


def build_temporal_report(segmented: Mapping[str, Sequence[Mapping[str, Any]]], target: Mapping[str, Any]) -> Dict[str, Any]:
    pre_rows = list(segmented.get("pre_ignition") or [])
    all_rows = list(segmented.get("all") or [])
    report = {
        "mirror_temporal_schema_version": "pre_ignition_temporal_report_v1",
        "target": dict(target),
        "focus_features": list(FOCUS_FEATURES),
        "row_counts": {name: len(rows) for name, rows in segmented.items()},
        "features": {},
        "success_vs_missed": success_vs_missed(all_rows),
        "is_trade_command": False,
    }
    for feature in FOCUS_FEATURES:
        series = [_number(row.get(feature)) for row in pre_rows]
        series = [value for value in series if value is not None]
        all_series = [_number(row.get(feature)) for row in all_rows]
        all_series = [value for value in all_series if value is not None]
        report["features"][feature] = {
            "absolute_value": {
                "pre_ignition_first": _round(series[0]) if series else None,
                "pre_ignition_last": _round(series[-1]) if series else None,
                "pre_ignition_min": _round(min(series)) if series else None,
                "pre_ignition_max": _round(max(series)) if series else None,
                "replay_min": _round(min(all_series)) if all_series else None,
                "replay_max": _round(max(all_series)) if all_series else None,
            },
            "slopes": {f"{window}_candles": slope(series, window) for window in SLOPE_WINDOWS},
            "acceleration": acceleration_summary(series),
            "persistence": persistence_summary(series),
        }
    return report


def build_sequence_report(segmented: Mapping[str, Sequence[Mapping[str, Any]]], target: Mapping[str, Any]) -> Dict[str, Any]:
    pre_rows = list(segmented.get("pre_ignition") or [])
    events = []
    for feature in FOCUS_FEATURES:
        rows = feature_rise_events(pre_rows, feature)
        if rows:
            first = rows[0]
            events.append(
                {
                    "feature": feature,
                    "first_rise_timestamp": first["timestamp"],
                    "first_rise_index": first["index"],
                    "event_count": len(rows),
                    "is_trade_command": False,
                }
            )
    events.sort(key=lambda row: row["first_rise_index"])
    sequence = [row["feature"] for row in events]
    relation = cross_feature_relation(events)
    return {
        "mirror_sequence_schema_version": "mirror_pattern_sequence_report_v1",
        "target": dict(target),
        "focus_features": list(FOCUS_FEATURES),
        "dominant_sequence": " -> ".join(sequence) if sequence else None,
        "sequence_features": sequence,
        "events": events,
        "cross_feature_relation": relation,
        "is_trade_command": False,
    }


def build_transition_matrix(segmented: Mapping[str, Sequence[Mapping[str, Any]]]) -> Dict[str, Any]:
    rows = list(segmented.get("pre_ignition") or [])
    matrix: Dict[str, Dict[str, int]] = {}
    for previous, current in zip(rows, rows[1:]):
        state = transition_state(previous, current)
        for left in FOCUS_FEATURES:
            matrix.setdefault(left, {})
            for right in FOCUS_FEATURES:
                if left == right:
                    continue
                key = f"{state[left]}->{state[right]}"
                matrix[left][key] = matrix[left].get(key, 0) + 1
    return {
        "feature_transition_matrix_schema_version": "feature_transition_matrix_v1",
        "focus_features": list(FOCUS_FEATURES),
        "matrix": matrix,
        "is_trade_command": False,
    }


def build_feature_candidates(
    temporal_report: Mapping[str, Any],
    sequence_report: Mapping[str, Any],
    transition_matrix: Mapping[str, Any],
) -> Dict[str, Any]:
    candidates = []
    sequence = list(sequence_report.get("sequence_features") or [])
    for feature in FOCUS_FEATURES:
        data = temporal_report.get("features", {}).get(feature, {})
        slopes = data.get("slopes", {})
        persistence = data.get("persistence", {})
        acceleration = data.get("acceleration", {})
        max_slope = max((abs(float(value or 0.0)) for value in slopes.values()), default=0.0)
        persistence_score = float(persistence.get("max_increase_candles") or 0.0) / max(len(temporal_report.get("features", {})), 1)
        acceleration_score = abs(float(acceleration.get("last_acceleration") or 0.0))
        sequence_bonus = (len(FOCUS_FEATURES) - sequence.index(feature)) if feature in sequence else 0
        evidence_score = round(max_slope + persistence_score + acceleration_score + sequence_bonus, 6)
        candidates.append(
            {
                "rank": 0,
                "feature": feature,
                "candidate_type": "temporal_line_feature",
                "evidence_score": evidence_score,
                "max_abs_slope": _round(max_slope),
                "max_increase_persistence": persistence.get("max_increase_candles"),
                "last_acceleration": acceleration.get("last_acceleration"),
                "sequence_position": sequence.index(feature) + 1 if feature in sequence else None,
                "definition": candidate_definition(feature),
                "is_trade_command": False,
            }
        )
    candidates.sort(key=lambda row: row["evidence_score"], reverse=True)
    for index, row in enumerate(candidates, start=1):
        row["rank"] = index
    return {
        "mirror_pattern_feature_candidate_schema_version": "mirror_pattern_feature_candidates_v1",
        "source": "Sprint 12M BTC replay evidence",
        "focus_features": list(FOCUS_FEATURES),
        "candidates": candidates,
        "transition_matrix_summary": transition_matrix.get("matrix", {}),
        "is_trade_command": False,
    }


def success_vs_missed(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    high = [row for row in rows if (_number(row.get("mfe_pct")) or 0.0) >= 2.0]
    loss = [row for row in rows if (_number(row.get("mfe_pct")) or 0.0) <= 0.0]
    return {
        "high_mfe_count": len(high),
        "loss_count": len(loss),
        "high_mfe": group_temporal_summary(high),
        "loss": group_temporal_summary(loss),
        "delta_high_minus_loss": {
            feature: _delta_average(high, loss, feature) for feature in FOCUS_FEATURES
        },
    }


def group_temporal_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        feature: {
            "average_value": _average(rows, feature),
            "average_4_candle_slope": average_window_slope(rows, feature, 4),
            "max_increase_persistence": persistence_summary([_number(row.get(feature)) for row in rows])["max_increase_candles"],
        }
        for feature in FOCUS_FEATURES
    }


def slope(values: Sequence[float], window: int) -> Optional[float]:
    if len(values) <= window:
        return None
    return _round((values[-1] - values[-window - 1]) / float(window))


def average_window_slope(rows: Sequence[Mapping[str, Any]], feature: str, window: int) -> Optional[float]:
    values = [_number(row.get(feature)) for row in rows]
    values = [value for value in values if value is not None]
    if len(values) <= window:
        return None
    slopes = [(values[index] - values[index - window]) / float(window) for index in range(window, len(values))]
    return _round(mean(slopes)) if slopes else None


def acceleration_summary(values: Sequence[Optional[float]]) -> Dict[str, Any]:
    series = [value for value in values if value is not None]
    if len(series) < 3:
        return {"last_acceleration": None, "inflection_count": 0, "direction": None}
    deltas = [current - previous for previous, current in zip(series, series[1:])]
    accelerations = [current - previous for previous, current in zip(deltas, deltas[1:])]
    inflections = sum(1 for previous, current in zip(deltas, deltas[1:]) if (previous < 0 <= current) or (previous > 0 >= current))
    last = accelerations[-1] if accelerations else None
    direction = "increasing" if last and last > 0 else "decreasing" if last and last < 0 else "flat"
    return {
        "last_acceleration": _round(last),
        "average_acceleration": _round(mean(accelerations)) if accelerations else None,
        "inflection_count": inflections,
        "direction": direction,
    }


def persistence_summary(values: Sequence[Optional[float]]) -> Dict[str, Any]:
    series = [value for value in values if value is not None]
    max_up = max_down = current_up = current_down = 0
    for previous, current in zip(series, series[1:]):
        if current > previous:
            current_up += 1
            current_down = 0
        elif current < previous:
            current_down += 1
            current_up = 0
        else:
            current_up = current_down = 0
        max_up = max(max_up, current_up)
        max_down = max(max_down, current_down)
    return {
        "max_increase_candles": max_up,
        "max_decrease_candles": max_down,
        "last_direction": last_direction(series),
    }


def feature_rise_events(rows: Sequence[Mapping[str, Any]], feature: str) -> list[Dict[str, Any]]:
    values = [_number(row.get(feature)) for row in rows]
    events = []
    for index in range(1, len(values)):
        if values[index] is None or values[index - 1] is None:
            continue
        if values[index] > values[index - 1]:
            events.append({"index": index, "timestamp": rows[index].get("timestamp")})
    return events


def cross_feature_relation(events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    positions = {row["feature"]: int(row["first_rise_index"]) for row in events}
    pairs = {}
    for left in FOCUS_FEATURES:
        for right in FOCUS_FEATURES:
            if left == right:
                continue
            if left in positions and right in positions:
                pairs[f"{left}_to_{right}"] = positions[right] - positions[left]
    simultaneous = [
        f"{left}+{right}"
        for left in FOCUS_FEATURES
        for right in FOCUS_FEATURES
        if left < right and positions.get(left) is not None and positions.get(left) == positions.get(right)
    ]
    return {
        "first_rise_positions": positions,
        "lead_lag_candles": pairs,
        "simultaneous_first_rise": simultaneous,
    }


def transition_state(previous: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, str]:
    state = {}
    for feature in FOCUS_FEATURES:
        left = _number(previous.get(feature))
        right = _number(current.get(feature))
        if left is None or right is None:
            state[feature] = "missing"
        elif right > left:
            state[feature] = "up"
        elif right < left:
            state[feature] = "down"
        else:
            state[feature] = "flat"
    return state


def candidate_definition(feature: str) -> str:
    return {
        "hellhound_score": "Score line slope, acceleration, and persistence before ignition.",
        "rsi_15m": "RSI line slope, inflection, and persistence before ignition.",
        "volume_ratio_ma20": "MA20 volume ratio line slope, acceleration, and persistence before ignition.",
    }[feature]


def last_direction(values: Sequence[float]) -> Optional[str]:
    if len(values) < 2:
        return None
    if values[-1] > values[-2]:
        return "up"
    if values[-1] < values[-2]:
        return "down"
    return "flat"


def _average(rows: Sequence[Mapping[str, Any]], feature: str) -> Optional[float]:
    values = [_number(row.get(feature)) for row in rows]
    values = [value for value in values if value is not None]
    return _round(mean(values)) if values else None


def _delta_average(left_rows: Sequence[Mapping[str, Any]], right_rows: Sequence[Mapping[str, Any]], feature: str) -> Optional[float]:
    left = _average(left_rows, feature)
    right = _average(right_rows, feature)
    return _round(left - right) if left is not None and right is not None else None


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float]) -> Optional[float]:
    return round(float(value), 6) if value is not None else None


def main() -> int:
    result = run_mirror_pattern_feature_discovery()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
