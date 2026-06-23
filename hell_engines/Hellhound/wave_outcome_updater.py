from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

try:
    from .mfe_mae_engine import calculate_mae, calculate_mfe, calculate_time_to_peak
except ImportError:
    from mfe_mae_engine import calculate_mae, calculate_mfe, calculate_time_to_peak


WAVE_OUTCOME_UPDATER_SCHEMA_VERSION = "hellhound_wave_outcome_updater_v0"
OUTCOME_WINDOWS = ("6h", "24h", "72h")


def create_wave_outcome_update(
    wave_row: Mapping[str, Any],
    *,
    price_paths_by_window: Mapping[str, Sequence[Mapping[str, Any]]],
    entry_price: float | None = None,
) -> Dict[str, Any]:
    """Return a new wave row with outcome fields filled. No DB update is performed."""
    updated = dict(wave_row)
    updated["wave_outcome_updater_schema_version"] = WAVE_OUTCOME_UPDATER_SCHEMA_VERSION
    entry = entry_price if entry_price is not None else _entry_price_from_wave_row(wave_row)
    for window in OUTCOME_WINDOWS:
        price_path = list(price_paths_by_window.get(window) or [])
        suffix = window.replace("h", "h")
        if entry is None or not price_path:
            updated[f"outcome_mfe_{suffix}"] = None
            updated[f"outcome_mae_{suffix}"] = None
            updated[f"outcome_time_to_peak_{suffix}"] = None
            continue
        updated[f"outcome_mfe_{suffix}"] = calculate_mfe(entry, price_path)
        updated[f"outcome_mae_{suffix}"] = calculate_mae(entry, price_path)
        updated[f"outcome_time_to_peak_{suffix}"] = calculate_time_to_peak(price_path)
    updated["is_trade_command"] = False
    return updated


def create_wave_outcome_updates(
    wave_rows: Sequence[Mapping[str, Any]],
    *,
    price_paths_by_signal_id: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> list[Dict[str, Any]]:
    updates = []
    for row in wave_rows:
        signal_id = str(row.get("signal_id") or "")
        updates.append(
            create_wave_outcome_update(
                row,
                price_paths_by_window=price_paths_by_signal_id.get(signal_id) or {},
            )
        )
    return updates


def _entry_price_from_wave_row(row: Mapping[str, Any]) -> float | None:
    # Snapshot v0 is a state vector, not a raw price store. Exact MFE/MAE needs
    # an explicit entry price from the signal/outcome layer.
    return None
