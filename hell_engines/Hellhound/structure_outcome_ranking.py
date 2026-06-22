from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Sequence, Union

try:
    from .mfe_mae_engine import DEFAULT_MFE_MAE_PATH
except ImportError:
    from mfe_mae_engine import DEFAULT_MFE_MAE_PATH


STRUCTURE_STATS_SCHEMA_VERSION = "hellhound_structure_stats_v1"
DEFAULT_STRUCTURE_STATS_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_structure_stats.jsonl"
TRACKED_STRUCTURES = ("BEL", "ACT", "ACE", "MET", "NIGHT")


def aggregate_structure_outcomes(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    stats = {}
    for structure in TRACKED_STRUCTURES:
        items = [
            row
            for row in rows
            if row.get("is_trade_command") is False
            and str(row.get("structure_type") or row.get("structure_classification") or "").upper() == structure
        ]
        validated = [row for row in items if str(row.get("validation_status") or "").upper() == "VALIDATED"]
        stats[structure] = {
            "structure_type": structure,
            "count": len(items),
            "validated_ratio": round(len(validated) / len(items), 6) if items else None,
            "average_mfe": _average(items, "mfe_pct"),
            "average_mae": _average(items, "mae_pct"),
            "average_time_to_peak_hours": _average(items, "time_to_peak_hours"),
            "is_trade_command": False,
        }
    return {
        "structure_stats_schema_version": STRUCTURE_STATS_SCHEMA_VERSION,
        "structures": stats,
        "is_trade_command": False,
    }


def load_mfe_mae_rows(path: Union[Path, str] = DEFAULT_MFE_MAE_PATH) -> list[Dict[str, Any]]:
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
            rows.append(row)
    return rows


def build_structure_stats(
    *,
    input_path: Union[Path, str] = DEFAULT_MFE_MAE_PATH,
    output_path: Union[Path, str] = DEFAULT_STRUCTURE_STATS_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    rows = load_mfe_mae_rows(input_path)
    result = aggregate_structure_outcomes(rows)
    write_structure_stats(result["structures"].values(), output_path=output_path, append=append)
    return {
        "structure_stats_schema_version": STRUCTURE_STATS_SCHEMA_VERSION,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "structure_count": len(result["structures"]),
        "is_trade_command": False,
        "structures": result["structures"],
    }


def write_structure_stats(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_STRUCTURE_STATS_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            normalized = dict(row)
            normalized["structure_stats_schema_version"] = STRUCTURE_STATS_SCHEMA_VERSION
            normalized["is_trade_command"] = False
            file.write(json.dumps(normalized, sort_keys=True) + "\n")
    return {
        "structure_stats_schema_version": STRUCTURE_STATS_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def _average(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = []
    for row in rows:
        try:
            if row.get(key) is not None:
                values.append(float(row[key]))
        except (TypeError, ValueError):
            continue
    return round(mean(values), 6) if values else None
