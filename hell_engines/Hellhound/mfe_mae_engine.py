from __future__ import annotations

import json
import uuid
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Mapping, Optional, Sequence, Union

try:
    from .outcome_validator import DEFAULT_VALIDATION_PATH
except ImportError:
    from outcome_validator import DEFAULT_VALIDATION_PATH


MFE_MAE_SCHEMA_VERSION = "hellhound_mfe_mae_v1"
DEFAULT_MFE_MAE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_mfe_mae_dataset.jsonl"
MFE_MAE_ID_NAMESPACE = uuid.UUID("4a67a2f7-2fb7-46ea-970f-cf44d6f74ac0")


def calculate_mfe(entry_price: float, price_path: Sequence[Mapping[str, Any]]) -> Optional[float]:
    prices = _prices(price_path)
    if entry_price == 0 or not prices:
        return None
    return round(((max(prices) - entry_price) / entry_price) * 100.0, 6)


def calculate_mae(entry_price: float, price_path: Sequence[Mapping[str, Any]]) -> Optional[float]:
    prices = _prices(price_path)
    if entry_price == 0 or not prices:
        return None
    return round(((min(prices) - entry_price) / entry_price) * 100.0, 6)


def calculate_time_to_peak(price_path: Sequence[Mapping[str, Any]]) -> Optional[float]:
    normalized = _normalized_path(price_path)
    if not normalized:
        return None
    peak = max(normalized, key=lambda row: row["price"])
    return round(float(peak["hours_since_entry"]), 6)


def calculate_time_to_stop(
    entry_price: float,
    price_path: Sequence[Mapping[str, Any]],
    *,
    stop_loss_pct: float = -5.0,
) -> Optional[float]:
    if entry_price == 0:
        return None
    threshold = entry_price * (1.0 + stop_loss_pct / 100.0)
    for row in _normalized_path(price_path):
        if row["price"] <= threshold:
            return round(float(row["hours_since_entry"]), 6)
    return None


def create_mfe_mae_record(
    validation_row: Mapping[str, Any],
    price_path: Sequence[Mapping[str, Any]],
    *,
    entry_price: Optional[float] = None,
    stop_loss_pct: float = -5.0,
) -> Dict[str, Any]:
    normalized = _normalized_path(price_path)
    if not _is_usable_validation_row(validation_row) or not normalized:
        return _empty_record(validation_row, error="validation row or price path is not usable")
    entry = _optional_float(entry_price)
    if entry is None:
        entry = normalized[0]["price"]
    peak = max(normalized, key=lambda row: row["price"])
    outcome = normalized[-1]
    stop_price = _stop_price(entry, normalized, stop_loss_pct=stop_loss_pct)
    lead_line_id = str(validation_row.get("lead_line_id") or "")
    symbol = str(validation_row.get("symbol") or "").upper()
    return {
        "mfe_mae_schema_version": MFE_MAE_SCHEMA_VERSION,
        "mfe_mae_id": _stable_mfe_mae_id(lead_line_id, symbol),
        "lead_line_id": lead_line_id or None,
        "validation_id": validation_row.get("validation_id"),
        "symbol": symbol or None,
        "structure_type": validation_row.get("structure_type"),
        "validation_status": validation_row.get("validation_status"),
        "mfe_pct": calculate_mfe(entry, normalized),
        "mae_pct": calculate_mae(entry, normalized),
        "time_to_peak_hours": calculate_time_to_peak(normalized),
        "time_to_stop_hours": calculate_time_to_stop(entry, normalized, stop_loss_pct=stop_loss_pct),
        "peak_price": round(peak["price"], 10),
        "stop_price": round(stop_price, 10) if stop_price is not None else None,
        "outcome_price": round(outcome["price"], 10),
        "entry_price": round(entry, 10),
        "is_trade_command": False,
        "error": None,
    }


def write_mfe_mae_dataset(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_path: Union[Path, str] = DEFAULT_MFE_MAE_PATH,
    append: bool = True,
) -> Dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(dict(row), sort_keys=True) + "\n")
    return {
        "mfe_mae_schema_version": MFE_MAE_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(rows),
        "append": append,
        "is_trade_command": False,
    }


def aggregate_mfe_mae_by_structure(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if row.get("is_trade_command") is not False:
            continue
        structure = str(row.get("structure_type") or "UNKNOWN").upper()
        grouped.setdefault(structure, []).append(row)
    stats = {}
    for structure, items in grouped.items():
        mfe_values = [_optional_float(row.get("mfe_pct")) for row in items]
        mae_values = [_optional_float(row.get("mae_pct")) for row in items]
        mfe_values = [value for value in mfe_values if value is not None]
        mae_values = [value for value in mae_values if value is not None]
        stats[structure] = {
            "count": len(items),
            "average_mfe": round(mean(mfe_values), 6) if mfe_values else None,
            "median_mfe": round(median(mfe_values), 6) if mfe_values else None,
            "average_mae": round(mean(mae_values), 6) if mae_values else None,
            "median_mae": round(median(mae_values), 6) if mae_values else None,
        }
    return {
        "mfe_mae_schema_version": MFE_MAE_SCHEMA_VERSION,
        "structures": stats,
        "is_trade_command": False,
    }


def load_validation_rows(path: Union[Path, str] = DEFAULT_VALIDATION_PATH) -> list[Dict[str, Any]]:
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
        if _is_usable_validation_row(row):
            rows.append(row)
    return rows


def _empty_record(validation_row: Mapping[str, Any], *, error: str) -> Dict[str, Any]:
    return {
        "mfe_mae_schema_version": MFE_MAE_SCHEMA_VERSION,
        "mfe_mae_id": _stable_mfe_mae_id(str(validation_row.get("lead_line_id") or ""), str(validation_row.get("symbol") or "")),
        "lead_line_id": validation_row.get("lead_line_id"),
        "validation_id": validation_row.get("validation_id"),
        "symbol": validation_row.get("symbol"),
        "structure_type": validation_row.get("structure_type"),
        "validation_status": validation_row.get("validation_status"),
        "mfe_pct": None,
        "mae_pct": None,
        "time_to_peak_hours": None,
        "time_to_stop_hours": None,
        "peak_price": None,
        "stop_price": None,
        "outcome_price": None,
        "entry_price": None,
        "is_trade_command": False,
        "error": error,
    }


def _normalized_path(price_path: Sequence[Mapping[str, Any]]) -> list[Dict[str, float]]:
    rows = []
    for index, row in enumerate(price_path):
        price = _optional_float(row.get("price") or row.get("close"))
        if price is None:
            continue
        hours = _optional_float(row.get("hours_since_entry"))
        if hours is None:
            hours = float(index)
        rows.append({"price": price, "hours_since_entry": hours})
    return rows


def _prices(price_path: Sequence[Mapping[str, Any]]) -> list[float]:
    return [row["price"] for row in _normalized_path(price_path)]


def _stop_price(entry_price: float, price_path: Sequence[Mapping[str, Any]], *, stop_loss_pct: float) -> Optional[float]:
    if entry_price == 0:
        return None
    threshold = entry_price * (1.0 + stop_loss_pct / 100.0)
    for row in _normalized_path(price_path):
        if row["price"] <= threshold:
            return row["price"]
    return None


def _is_usable_validation_row(row: Mapping[str, Any]) -> bool:
    if row.get("is_trade_command") is not False:
        return False
    return bool(row.get("lead_line_id") and row.get("symbol"))


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stable_mfe_mae_id(lead_line_id: str, symbol: str) -> str:
    seed = f"hellhound:mfe-mae:v1:{lead_line_id}:{symbol}"
    return str(uuid.uuid5(MFE_MAE_ID_NAMESPACE, seed))
