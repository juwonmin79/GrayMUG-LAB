from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib import error, parse, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from .mfe_mae_engine import DEFAULT_MFE_MAE_PATH, create_mfe_mae_record, write_mfe_mae_dataset
except ImportError:
    from mfe_mae_engine import DEFAULT_MFE_MAE_PATH, create_mfe_mae_record, write_mfe_mae_dataset

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


OUTCOME_TABLE = "hellhound_outcomes"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
PRODUCTION_MFE_MAE_SCHEMA_VERSION = "hellhound_production_mfe_mae_v1"
WINDOW_HOURS = {"1h": 1.0, "4h": 4.0, "24h": 24.0}
LOGGER = logging.getLogger("hellhound.mfe_mae_production")


@dataclass(frozen=True)
class ProductionMfeMaeResult:
    ok: bool
    dry_run: bool
    updated: bool
    skipped: bool
    message: str
    records: list[Dict[str, Any]]
    output_path: str


class ProductionMfeMaeError(RuntimeError):
    pass


def update_mfe_mae_from_supabase(
    *,
    output_path: Path | str = DEFAULT_MFE_MAE_PATH,
    signal_limit: Optional[int] = None,
) -> ProductionMfeMaeResult:
    supabase_url, supabase_key = _supabase_credentials()
    output = Path(output_path)
    if not supabase_url or not supabase_key:
        LOGGER.warning("Supabase credentials missing; MFE/MAE update skipped")
        return ProductionMfeMaeResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=True,
            message="missing Supabase environment; skipped MFE/MAE update",
            records=[],
            output_path=str(output),
        )

    try:
        signals = _load_recent_shadow_signals(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            limit=signal_limit or _signal_limit(),
        )
        outcomes_by_signal = _load_outcomes_for_signals(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            signal_ids=[str(row["id"]) for row in signals if row.get("id")],
        )
        candidates = build_mfe_mae_records_from_outcomes(signals, outcomes_by_signal)
        records = _records_to_append(candidates, output)
    except (OSError, ValueError, json.JSONDecodeError, ProductionMfeMaeError) as exc:
        LOGGER.error("MFE/MAE production update failed: %s", exc)
        return ProductionMfeMaeResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=False,
            message=str(exc),
            records=[],
            output_path=str(output),
        )

    if _dry_run_enabled():
        print(json.dumps(records, indent=2, sort_keys=True))
        return ProductionMfeMaeResult(
            ok=True,
            dry_run=True,
            updated=False,
            skipped=False,
            message=f"dry-run generated {len(records)} MFE/MAE records",
            records=records,
            output_path=str(output),
        )

    if not records:
        return ProductionMfeMaeResult(
            ok=True,
            dry_run=False,
            updated=False,
            skipped=True,
            message="no new MFE/MAE records",
            records=[],
            output_path=str(output),
        )

    write_mfe_mae_dataset(records, output_path=output, append=True)
    LOGGER.info("Wrote %s Hellhound MFE/MAE records", len(records))
    return ProductionMfeMaeResult(
        ok=True,
        dry_run=False,
        updated=True,
        skipped=False,
        message=f"wrote {len(records)} MFE/MAE records",
        records=records,
        output_path=str(output),
    )


def build_mfe_mae_records_from_outcomes(
    signals: Sequence[Mapping[str, Any]],
    outcomes_by_signal: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[Dict[str, Any]]:
    records: list[Dict[str, Any]] = []
    for signal in signals:
        signal_id = str(signal.get("id") or "")
        if not signal_id:
            continue
        outcomes = _calculated_outcomes(outcomes_by_signal.get(signal_id) or [])
        if not outcomes:
            continue
        price_path = _price_path_from_outcomes(outcomes)
        if len(price_path) < 2:
            continue
        validation_row = _validation_row_from_signal(signal)
        record = create_mfe_mae_record(
            validation_row,
            price_path,
            entry_price=price_path[0]["price"],
        )
        record.update(
            {
                "production_mfe_mae_schema_version": PRODUCTION_MFE_MAE_SCHEMA_VERSION,
                "source": "supabase_hellhound_outcomes",
                "outcome_windows": [str(row.get("evaluation_window")) for row in outcomes],
                "calculated_window_count": len(outcomes),
                "is_trade_command": False,
            }
        )
        records.append(record)
    return records


def _validation_row_from_signal(signal: Mapping[str, Any]) -> Dict[str, Any]:
    signal_id = str(signal.get("id") or "")
    return {
        "validation_id": f"production-outcome-{signal_id}",
        "signal_id": signal_id,
        "shadow_signal_id": signal_id,
        "lead_line_id": signal_id,
        "symbol": str(signal.get("symbol") or "").upper(),
        "structure_type": signal.get("pattern") or signal.get("shadow_action") or "UNKNOWN",
        "validation_status": "OUTCOME_CALCULATED",
        "is_trade_command": False,
    }


def _calculated_outcomes(outcomes: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows = []
    for row in outcomes:
        if row.get("result") == "PENDING":
            continue
        if _optional_float(row.get("entry_price")) is None:
            continue
        if _optional_float(row.get("current_price")) is None:
            continue
        if str(row.get("evaluation_window") or "") not in WINDOW_HOURS:
            continue
        rows.append(row)
    return sorted(rows, key=lambda item: WINDOW_HOURS[str(item.get("evaluation_window"))])


def _price_path_from_outcomes(outcomes: Sequence[Mapping[str, Any]]) -> list[Dict[str, float]]:
    first = outcomes[0]
    entry = _optional_float(first.get("entry_price"))
    if entry is None:
        return []
    path = [{"hours_since_entry": 0.0, "price": entry}]
    seen_hours = {0.0}
    for row in outcomes:
        hours = WINDOW_HOURS[str(row.get("evaluation_window"))]
        price = _optional_float(row.get("current_price"))
        if price is None or hours in seen_hours:
            continue
        path.append({"hours_since_entry": hours, "price": price})
        seen_hours.add(hours)
    return sorted(path, key=lambda item: item["hours_since_entry"])


def _records_to_append(records: Sequence[Mapping[str, Any]], output_path: Path) -> list[Dict[str, Any]]:
    existing = _existing_window_counts(output_path)
    selected = []
    for record in records:
        signal_id = str(record.get("signal_id") or "")
        window_count = int(record.get("calculated_window_count") or 0)
        if not signal_id or window_count <= 0:
            continue
        if window_count > existing.get(signal_id, 0):
            selected.append(dict(record))
    return selected


def _existing_window_counts(output_path: Path) -> Dict[str, int]:
    if not output_path.exists():
        return {}
    counts: Dict[str, int] = {}
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        signal_id = str(row.get("signal_id") or "")
        window_count = int(row.get("calculated_window_count") or 0)
        if signal_id:
            counts[signal_id] = max(counts.get(signal_id, 0), window_count)
    return counts


def _load_recent_shadow_signals(*, supabase_url: str, supabase_key: str, limit: int) -> list[Dict[str, Any]]:
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
        f"?select=id,symbol,created_at,pattern,shadow_action&order=created_at.desc&limit={int(limit)}"
    )
    status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key, method="GET")
    if status < 200 or status >= 300:
        raise ProductionMfeMaeError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list):
        raise ProductionMfeMaeError("Supabase shadow signals response was not a list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _load_outcomes_for_signals(
    *, supabase_url: str, supabase_key: str, signal_ids: Sequence[str]
) -> Dict[str, list[Dict[str, Any]]]:
    grouped: Dict[str, list[Dict[str, Any]]] = {signal_id: [] for signal_id in signal_ids}
    for chunk in _chunks(signal_ids, 80):
        if not chunk:
            continue
        signal_filter = parse.quote(f"in.({','.join(chunk)})", safe="(),")
        fields = "shadow_signal_id,symbol,evaluation_window,entry_price,current_price,outcome_return,result,target_time,snapshot_time"
        endpoint = (
            f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}"
            f"?select={fields}&shadow_signal_id={signal_filter}"
        )
        status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key, method="GET")
        if status < 200 or status >= 300:
            raise ProductionMfeMaeError(f"unexpected Supabase status {status}")
        if not isinstance(rows, list):
            raise ProductionMfeMaeError("Supabase outcomes response was not a list")
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            signal_id = str(row.get("shadow_signal_id") or "")
            grouped.setdefault(signal_id, []).append(dict(row))
    return grouped


def _supabase_json(
    *,
    endpoint: str,
    supabase_key: str,
    method: str,
) -> tuple[int, Any]:
    req = request.Request(
        endpoint,
        method=method,
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ProductionMfeMaeError(f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}") from exc
    except error.URLError as exc:
        raise ProductionMfeMaeError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ProductionMfeMaeError("Supabase MFE/MAE query timed out") from exc
    except json.JSONDecodeError as exc:
        raise ProductionMfeMaeError("Supabase response was not JSON") from exc


def _chunks(values: Sequence[str], size: int) -> list[list[str]]:
    return [list(values[index : index + size]) for index in range(0, len(values), size)]


def _signal_limit() -> int:
    raw = os.environ.get("MFE_MAE_SIGNAL_LIMIT", "300")
    try:
        return max(1, int(raw))
    except ValueError:
        return 300


def _dry_run_enabled() -> bool:
    return os.environ.get("MFE_MAE_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _redact_secret_text(value: str) -> str:
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    redacted = value
    for secret in (service_key, anon_key):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = update_mfe_mae_from_supabase()
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0 if result.ok or result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
