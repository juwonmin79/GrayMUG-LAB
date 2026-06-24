from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Mapping, Sequence, Union

try:
    from .mfe_mae_engine import DEFAULT_MFE_MAE_PATH
except ImportError:
    from mfe_mae_engine import DEFAULT_MFE_MAE_PATH


MFE_MAE_REPORT_SCHEMA_VERSION = "hellhound_mfe_mae_dataset_report_v1"
DEFAULT_MFE_MAE_REPORT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_mfe_mae_report.json"
TRACKED_STRUCTURES = ("BEL", "ACT", "ACE", "MET", "NIGHT")
QUANTILES = (0.25, 0.5, 0.75, 0.9)


def load_mfe_mae_dataset(path: Union[Path, str] = DEFAULT_MFE_MAE_PATH) -> list[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("is_trade_command") is False:
            rows.append(dict(row))
    return rows


def build_mfe_mae_report(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    usable = [row for row in rows if row.get("is_trade_command") is False]
    stop_hit_rows = [row for row in usable if _number(row.get("time_to_stop_hours")) is not None]
    return {
        "mfe_mae_report_schema_version": MFE_MAE_REPORT_SCHEMA_VERSION,
        "record_count": len(usable),
        "overall": {
            "mfe": _distribution(usable, "mfe_pct"),
            "mae": _distribution(usable, "mae_pct"),
            "time_to_peak_hours": _distribution(usable, "time_to_peak_hours"),
            "time_to_stop_hours_stop_hits_only": _distribution(stop_hit_rows, "time_to_stop_hours"),
            "stop_hit_count": len(stop_hit_rows),
            "stop_hit_ratio": round(len(stop_hit_rows) / len(usable), 6) if usable else None,
        },
        "profit_zones": _quantile_map(_values(usable, "mfe_pct")),
        "loss_zones": _quantile_map(_values(usable, "mae_pct")),
        "peak_time": _peak_time_summary(usable),
        "stop_time": _stop_time_summary(stop_hit_rows),
        "by_structure": _grouped_summary(usable, "structure_type", tracked_values=TRACKED_STRUCTURES),
        "by_promotion_status": _grouped_summary(usable, "promotion_status"),
        "by_signal_hour": _grouped_summary(usable, "signal_hour"),
        "is_trade_command": False,
    }


def build_mfe_mae_report_file(
    *,
    input_path: Union[Path, str] = DEFAULT_MFE_MAE_PATH,
    output_path: Union[Path, str] = DEFAULT_MFE_MAE_REPORT_PATH,
) -> Dict[str, Any]:
    rows = load_mfe_mae_dataset(input_path)
    report = build_mfe_mae_report(rows)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "mfe_mae_report_schema_version": MFE_MAE_REPORT_SCHEMA_VERSION,
        "input_path": str(input_path),
        "output_path": str(output),
        "record_count": report["record_count"],
        "is_trade_command": False,
        "report": report,
    }


def _grouped_summary(
    rows: Sequence[Mapping[str, Any]],
    key: str,
    *,
    tracked_values: Sequence[str] = (),
) -> Dict[str, Any]:
    groups: Dict[str, list[Mapping[str, Any]]] = {value: [] for value in tracked_values}
    for row in rows:
        value = row.get(key)
        if value is None or value == "":
            if tracked_values:
                continue
            value = "UNKNOWN"
        name = str(value).upper()
        groups.setdefault(name, []).append(row)
    return {name: _summary(items) for name, items in sorted(groups.items())}


def _summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    stop_hit_rows = [row for row in rows if _number(row.get("time_to_stop_hours")) is not None]
    return {
        "count": len(rows),
        "average_mfe": _average(rows, "mfe_pct"),
        "median_mfe": _median(rows, "mfe_pct"),
        "average_mae": _average(rows, "mae_pct"),
        "median_mae": _median(rows, "mae_pct"),
        "average_time_to_peak_hours": _average(rows, "time_to_peak_hours"),
        "average_time_to_stop_hours": _average(stop_hit_rows, "time_to_stop_hours"),
        "stop_hit_count": len(stop_hit_rows),
    }


def _distribution(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, Any]:
    values = _values(rows, key)
    return {
        "count": len(values),
        "average": round(mean(values), 6) if values else None,
        "median": round(median(values), 6) if values else None,
        "quantiles": _quantile_map(values),
    }


def _peak_time_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    values = _values(rows, "time_to_peak_hours")
    return {
        "average": round(mean(values), 6) if values else None,
        "median": round(median(values), 6) if values else None,
        "p75": _quantile(values, 0.75),
        "p90": _quantile(values, 0.9),
    }


def _stop_time_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    values = _values(rows, "time_to_stop_hours")
    return {
        "count": len(values),
        "average": round(mean(values), 6) if values else None,
        "median": round(median(values), 6) if values else None,
        "p75": _quantile(values, 0.75),
        "p90": _quantile(values, 0.9),
    }


def _quantile_map(values: Sequence[float]) -> Dict[str, float | None]:
    return {f"p{int(q * 100)}": _quantile(values, q) for q in QUANTILES}


def _quantile(values: Sequence[float], q: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 6)


def _average(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = _values(rows, key)
    return round(mean(values), 6) if values else None


def _median(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = _values(rows, key)
    return round(median(values), 6) if values else None


def _values(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    values = []
    for row in rows:
        value = _number(row.get(key))
        if value is not None:
            values.append(value)
    return values


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    result = build_mfe_mae_report_file()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
