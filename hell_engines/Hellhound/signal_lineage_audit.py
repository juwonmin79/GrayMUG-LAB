from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union


LINEAGE_AUDIT_SCHEMA_VERSION = "hellhound_signal_lineage_audit_v1"
DEFAULT_SIGNAL_PATH = Path(__file__).resolve().parents[2] / "outputs" / "production_hellhound_shadow.jsonl"
DEFAULT_WAVE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_wave_log.jsonl"
DEFAULT_OUTCOME_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_validation_dataset.jsonl"
DEFAULT_MFE_MAE_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_mfe_mae_dataset.jsonl"


def audit_lineage_files(
    *,
    signal_path: Union[Path, str] = DEFAULT_SIGNAL_PATH,
    wave_path: Union[Path, str] = DEFAULT_WAVE_PATH,
    outcome_path: Union[Path, str] = DEFAULT_OUTCOME_PATH,
    mfe_mae_path: Union[Path, str] = DEFAULT_MFE_MAE_PATH,
    limit: int = 100,
) -> Dict[str, Any]:
    signal_file = Path(signal_path)
    return audit_signal_lineage(
        signal_rows=_tail_rows(signal_file, limit=limit),
        wave_rows=load_jsonl(wave_path),
        outcome_rows=load_jsonl(outcome_path),
        mfe_mae_rows=load_jsonl(mfe_mae_path),
        limit=limit,
        signal_path_exists=signal_file.exists(),
    )


def audit_signal_lineage(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    wave_rows: Sequence[Mapping[str, Any]],
    outcome_rows: Sequence[Mapping[str, Any]],
    mfe_mae_rows: Sequence[Mapping[str, Any]],
    limit: int = 100,
    signal_path_exists: bool = True,
) -> Dict[str, Any]:
    recent_signals = list(signal_rows)[-limit:]
    wave_by_signal = _index_by_signal_id(wave_rows)
    outcome_by_signal = _index_by_signal_id(outcome_rows)
    mfe_by_signal = _index_by_signal_id(mfe_mae_rows)
    broken = []
    complete_count = 0

    for index, signal in enumerate(recent_signals):
        signal_id = _signal_id(signal)
        wave = wave_by_signal.get(signal_id or "")
        outcome = outcome_by_signal.get(signal_id or "")
        mfe = mfe_by_signal.get(signal_id or "")
        checks = {
            "signal_id": bool(signal_id),
            "snapshot": _has_snapshot(signal, wave),
            "wave": wave is not None,
            "outcome": outcome is not None,
            "mfe": _has_number(mfe, "mfe_pct") or _has_wave_metric(wave, "outcome_mfe"),
            "mae": _has_number(mfe, "mae_pct") or _has_wave_metric(wave, "outcome_mae"),
            "peak": _has_number(mfe, "time_to_peak_hours") or _has_wave_metric(wave, "outcome_time_to_peak"),
            "stop": _has_number(mfe, "time_to_stop_hours") or _has_wave_metric(wave, "outcome_time_to_stop"),
        }
        missing = [name for name, passed in checks.items() if not passed]
        if missing:
            broken.append(
                {
                    "row_index": index,
                    "signal_id": signal_id,
                    "symbol": _symbol(signal),
                    "missing": missing,
                    "link_fields": {
                        "signal_id": "signal_id/id/shadow_signal_id",
                        "wave": "wave.signal_id",
                        "outcome": "outcome.signal_id/shadow_signal_id",
                        "mfe_mae": "mfe_mae.signal_id/shadow_signal_id",
                    },
                }
            )
        else:
            complete_count += 1

    signal_count = len(recent_signals)
    return {
        "lineage_audit_schema_version": LINEAGE_AUDIT_SCHEMA_VERSION,
        "signal_path_exists": signal_path_exists,
        "signal_count": signal_count,
        "complete_count": complete_count,
        "broken_count": len(broken),
        "lineage_coverage_pct": _pct(complete_count, signal_count),
        "broken_links": broken,
        "coverage_counts": _coverage_counts(recent_signals, wave_by_signal, outcome_by_signal, mfe_by_signal),
        "is_trade_command": False,
    }


def load_jsonl(path: Union[Path, str]) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def lineage_link_table() -> list[Dict[str, str]]:
    return [
        {"stage": "Signal -> Snapshot", "linked": "O", "field": "signal_id plus mtf_snapshot/snapshot_t0"},
        {"stage": "Snapshot -> Wave", "linked": "O", "field": "hound_wave_log.signal_id, snapshot_t0"},
        {"stage": "Wave -> Outcome", "linked": "partial", "field": "signal_id or shadow_signal_id; window mismatch remains"},
        {"stage": "Outcome -> MFE", "linked": "partial", "field": "mfe_mae.signal_id preferred; current dataset often lead_line_id"},
        {"stage": "Outcome -> MAE", "linked": "partial", "field": "mfe_mae.signal_id preferred; current dataset often lead_line_id"},
        {"stage": "Outcome -> Peak", "linked": "partial", "field": "time_to_peak_hours or wave outcome_time_to_peak_*"},
        {"stage": "Outcome -> Stop", "linked": "O", "field": "time_to_stop_hours or wave outcome_time_to_stop_*"},
    ]


def _tail_rows(path: Path, *, limit: int) -> list[Dict[str, Any]]:
    rows = load_jsonl(path)
    return rows[-limit:]


def _index_by_signal_id(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    indexed = {}
    for row in rows:
        signal_id = _signal_id(row)
        if signal_id:
            indexed[signal_id] = row
    return indexed


def _coverage_counts(
    signals: Sequence[Mapping[str, Any]],
    wave_by_signal: Mapping[str, Mapping[str, Any]],
    outcome_by_signal: Mapping[str, Mapping[str, Any]],
    mfe_by_signal: Mapping[str, Mapping[str, Any]],
) -> Dict[str, int]:
    counts = {
        "signals": len(signals),
        "signals_with_signal_id": 0,
        "signals_with_snapshot": 0,
        "signals_with_wave": 0,
        "signals_with_outcome": 0,
        "signals_with_mfe": 0,
        "signals_with_mae": 0,
        "signals_with_peak": 0,
        "signals_with_stop": 0,
    }
    for signal in signals:
        signal_id = _signal_id(signal)
        wave = wave_by_signal.get(signal_id or "")
        outcome = outcome_by_signal.get(signal_id or "")
        mfe = mfe_by_signal.get(signal_id or "")
        counts["signals_with_signal_id"] += int(bool(signal_id))
        counts["signals_with_snapshot"] += int(_has_snapshot(signal, wave))
        counts["signals_with_wave"] += int(wave is not None)
        counts["signals_with_outcome"] += int(outcome is not None)
        counts["signals_with_mfe"] += int(_has_number(mfe, "mfe_pct") or _has_wave_metric(wave, "outcome_mfe"))
        counts["signals_with_mae"] += int(_has_number(mfe, "mae_pct") or _has_wave_metric(wave, "outcome_mae"))
        counts["signals_with_peak"] += int(_has_number(mfe, "time_to_peak_hours") or _has_wave_metric(wave, "outcome_time_to_peak"))
        counts["signals_with_stop"] += int(_has_number(mfe, "time_to_stop_hours") or _has_wave_metric(wave, "outcome_time_to_stop"))
    return counts


def _signal_id(row: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not row:
        return None
    for key in ("signal_id", "shadow_signal_id", "id"):
        value = row.get(key)
        if value:
            return str(value)
    payload = row.get("payload")
    if isinstance(payload, Mapping):
        return _signal_id(payload)
    return None


def _symbol(row: Mapping[str, Any]) -> Optional[str]:
    value = row.get("symbol")
    if value:
        return str(value).upper()
    payload = row.get("payload")
    if isinstance(payload, Mapping) and payload.get("symbol"):
        return str(payload["symbol"]).upper()
    return None


def _has_snapshot(signal: Mapping[str, Any], wave: Optional[Mapping[str, Any]]) -> bool:
    if any(key in signal for key in ("mtf_snapshot", "snapshot", "snapshot_t0")):
        return True
    payload = signal.get("payload")
    if isinstance(payload, Mapping) and any(key in payload for key in ("mtf_snapshot", "snapshot")):
        return True
    return bool(wave and "snapshot_t0" in wave)


def _has_wave_metric(wave: Optional[Mapping[str, Any]], prefix: str) -> bool:
    if not wave:
        return False
    return any(key.startswith(prefix) and _is_number(value) for key, value in wave.items())


def _has_number(row: Optional[Mapping[str, Any]], key: str) -> bool:
    return bool(row and _is_number(row.get(key)))


def _is_number(value: Any) -> bool:
    if value is None:
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)
