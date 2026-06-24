from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib import error, parse, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from .mfe_mae_engine import DEFAULT_MFE_MAE_PATH
    from .mfe_mae_feature_enrichment import DEFAULT_FEATURE_DATASET_PATH
except ImportError:
    from mfe_mae_engine import DEFAULT_MFE_MAE_PATH
    from mfe_mae_feature_enrichment import DEFAULT_FEATURE_DATASET_PATH


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if load_dotenv:
    load_dotenv(ENV_PATH)
else:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


FEATURE_LINEAGE_AUDIT_SCHEMA_VERSION = "hellhound_feature_lineage_audit_v1"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
OUTCOME_TABLE = "hellhound_outcomes"
FEATURE_FIELDS = (
    "hellhound_score",
    "decision_source",
    "btc_weather",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "rsi_15m",
    "macd_hist_15m",
)
COMPARE_FIELDS = (
    "hellhound_score",
    "rsi_15m",
    "btc_weather",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "macd_hist_15m",
)


class FeatureLineageAuditError(RuntimeError):
    pass


def audit_feature_lineage(
    *,
    limit: int = 20,
    mfe_path: Path | str = DEFAULT_MFE_MAE_PATH,
    feature_path: Path | str = DEFAULT_FEATURE_DATASET_PATH,
) -> Dict[str, Any]:
    signals = _load_recent_feature_signals(limit=limit)
    signal_ids = [str(row["id"]) for row in signals if row.get("id")]
    outcomes = _load_outcomes(signal_ids)
    mfe_rows = _load_jsonl_by_signal_id(mfe_path)
    feature_rows = _load_jsonl_by_signal_id(feature_path)
    rows = []
    for signal in signals:
        signal_id = str(signal.get("id") or "")
        signal_features = _feature_presence(signal)
        outcome_rows = outcomes.get(signal_id) or []
        mfe_row = mfe_rows.get(signal_id)
        feature_row = feature_rows.get(signal_id)
        rows.append(
            {
                "signal_id": signal_id,
                "symbol": signal.get("symbol"),
                "created_at": signal.get("created_at"),
                "shadow_signal_exists": bool(signal_id),
                "outcome_row_exists": bool(outcome_rows),
                "outcome_calculated": any(str(row.get("result") or "") != "PENDING" for row in outcome_rows),
                "mfe_row_exists": bool(mfe_row),
                "feature_row_exists": bool(feature_row),
                "signal_features_present": signal_features,
                "feature_dataset_features_present": _feature_presence(feature_row or {}),
                "complete_lineage": bool(signal_id and outcome_rows and mfe_row and feature_row),
                "is_trade_command": False,
            }
        )
    total = len(rows)
    report = {
        "feature_lineage_audit_schema_version": FEATURE_LINEAGE_AUDIT_SCHEMA_VERSION,
        "signal_count": total,
        "complete_lineage_count": sum(1 for row in rows if row["complete_lineage"]),
        "lineage_coverage_pct": _pct(sum(1 for row in rows if row["complete_lineage"]), total),
        "stage_counts": {
            "shadow_signal": sum(1 for row in rows if row["shadow_signal_exists"]),
            "outcome_row": sum(1 for row in rows if row["outcome_row_exists"]),
            "outcome_calculated": sum(1 for row in rows if row["outcome_calculated"]),
            "mfe_row": sum(1 for row in rows if row["mfe_row_exists"]),
            "feature_row": sum(1 for row in rows if row["feature_row_exists"]),
        },
        "feature_coverage": {
            field: _field_coverage(rows, field, source="feature_dataset_features_present")
            for field in FEATURE_FIELDS
        },
        "signal_feature_coverage": {
            field: _field_coverage(rows, field, source="signal_features_present")
            for field in FEATURE_FIELDS
        },
        "loss_audit": _loss_audit(rows),
        "high_mfe_vs_loss": _high_mfe_vs_loss(list(feature_rows.values())),
        "broken_links": [
            {
                "signal_id": row["signal_id"],
                "symbol": row["symbol"],
                "missing": _missing_stages(row),
                "is_trade_command": False,
            }
            for row in rows
            if not row["complete_lineage"]
        ],
        "rows": rows,
        "is_trade_command": False,
    }
    return report


def _load_recent_feature_signals(*, limit: int) -> list[Dict[str, Any]]:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        raise FeatureLineageAuditError("missing Supabase environment")
    fields = (
        "id,symbol,created_at,source_time,pattern,shadow_action,"
        "lead_line_payload,target_feed,calibration_payload,fitness_payload,payload"
    )
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
        f"?select={fields}&payload=not.is.null&order=created_at.desc&limit={int(limit)}"
    )
    status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key)
    if status < 200 or status >= 300:
        raise FeatureLineageAuditError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list):
        raise FeatureLineageAuditError("Supabase shadow signal response was not a list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _load_outcomes(signal_ids: Sequence[str]) -> Dict[str, list[Dict[str, Any]]]:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        raise FeatureLineageAuditError("missing Supabase environment")
    grouped: Dict[str, list[Dict[str, Any]]] = {signal_id: [] for signal_id in signal_ids}
    fields = "shadow_signal_id,evaluation_window,result,entry_price,current_price,target_time,snapshot_time"
    for chunk in _chunks(signal_ids, 80):
        if not chunk:
            continue
        signal_filter = parse.quote(f"in.({','.join(chunk)})", safe="(),")
        endpoint = (
            f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}"
            f"?select={fields}&shadow_signal_id={signal_filter}"
        )
        status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key)
        if status < 200 or status >= 300:
            raise FeatureLineageAuditError(f"unexpected Supabase status {status}")
        if not isinstance(rows, list):
            raise FeatureLineageAuditError("Supabase outcome response was not a list")
        for row in rows:
            if isinstance(row, Mapping):
                grouped.setdefault(str(row.get("shadow_signal_id") or ""), []).append(dict(row))
    return grouped


def _load_jsonl_by_signal_id(path: Path | str) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    path = Path(path)
    if not path.exists():
        return output
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping) or row.get("is_trade_command") is not False:
            continue
        signal_id = str(row.get("signal_id") or row.get("shadow_signal_id") or "")
        if signal_id:
            output[signal_id] = dict(row)
    return output


def _feature_presence(row: Mapping[str, Any]) -> Dict[str, bool]:
    return {field: _feature_value(row, field) is not None for field in FEATURE_FIELDS}


def _feature_value(row: Mapping[str, Any], field: str) -> Any:
    if not row:
        return None
    if row.get(field) is not None:
        return row.get(field)
    containers = ("payload", "lead_line_payload", "target_feed", "calibration_payload", "fitness_payload")
    for container_name in containers:
        container = row.get(container_name)
        if isinstance(container, Mapping) and container.get(field) is not None:
            return container.get(field)
    if field == "btc_weather":
        return _feature_value(row, "btc_4h_weather")
    return None


def _field_coverage(rows: Sequence[Mapping[str, Any]], field: str, *, source: str) -> Dict[str, Any]:
    total = len(rows)
    present = sum(1 for row in rows if row.get(source, {}).get(field) is True)
    return {
        "present_count": present,
        "missing_count": total - present,
        "coverage_pct": _pct(present, total),
    }


def _loss_audit(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    shadow = sum(1 for row in rows if row["shadow_signal_exists"])
    outcome = sum(1 for row in rows if row["outcome_row_exists"])
    mfe = sum(1 for row in rows if row["mfe_row_exists"])
    feature = sum(1 for row in rows if row["feature_row_exists"])
    return {
        "signal_to_shadow_loss_pct": _pct(total - shadow, total),
        "shadow_to_outcome_loss_pct": _pct(shadow - outcome, shadow),
        "outcome_to_mfe_loss_pct": _pct(outcome - mfe, outcome),
        "mfe_to_feature_dataset_loss_pct": _pct(mfe - feature, mfe),
    }


def _high_mfe_vs_loss(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    high_rows = [row for row in rows if row.get("mfe_bucket") in {"HIGH", "EXTREME"}]
    loss_rows = [row for row in rows if row.get("mfe_bucket") == "LOSS"]
    return {
        "high_extreme": _compare_group(high_rows),
        "loss": _compare_group(loss_rows),
        "delta_high_minus_loss": {
            field: _delta(high_rows, loss_rows, field) for field in (*COMPARE_FIELDS, "mfe_pct", "mae_pct")
        },
    }


def _compare_group(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "count": len(rows),
        "average_score": _average(rows, "hellhound_score"),
        "average_rsi": _average(rows, "rsi_15m"),
        "average_btc_weather": _average(rows, "btc_weather"),
        "average_volume_ratio_ma5": _average(rows, "volume_ratio_ma5"),
        "average_volume_ratio_ma20": _average(rows, "volume_ratio_ma20"),
        "average_macd": _average(rows, "macd_hist_15m"),
        "average_mfe_pct": _average(rows, "mfe_pct"),
        "average_mae_pct": _average(rows, "mae_pct"),
    }


def _missing_stages(row: Mapping[str, Any]) -> list[str]:
    missing = []
    if not row["shadow_signal_exists"]:
        missing.append("shadow_signal")
    if not row["outcome_row_exists"]:
        missing.append("outcome")
    if not row["mfe_row_exists"]:
        missing.append("mfe")
    if not row["feature_row_exists"]:
        missing.append("feature_dataset")
    return missing


def _average(rows: Sequence[Mapping[str, Any]], field: str) -> Optional[float]:
    values = [_number(_feature_value(row, field)) for row in rows]
    values = [value for value in values if value is not None]
    return round(mean(values), 6) if values else None


def _delta(left_rows: Sequence[Mapping[str, Any]], right_rows: Sequence[Mapping[str, Any]], field: str) -> Optional[float]:
    left = _average(left_rows, field)
    right = _average(right_rows, field)
    return round(left - right, 6) if left is not None and right is not None else None


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(count: int, total: int) -> Optional[float]:
    return round(count / total * 100.0, 2) if total else None


def _chunks(values: Sequence[str], size: int) -> list[list[str]]:
    return [list(values[index : index + size]) for index in range(0, len(values), size)]


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


def _supabase_json(*, endpoint: str, supabase_key: str) -> tuple[int, Any]:
    req = request.Request(
        endpoint,
        method="GET",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise FeatureLineageAuditError(f"Supabase HTTP {exc.code}: {safe_body}") from exc
    except error.URLError as exc:
        raise FeatureLineageAuditError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FeatureLineageAuditError("Supabase request timed out") from exc
    except json.JSONDecodeError as exc:
        raise FeatureLineageAuditError("Supabase response was not JSON") from exc


def main() -> int:
    limit = int(os.environ.get("FEATURE_LINEAGE_AUDIT_LIMIT", "20"))
    report = audit_feature_lineage(limit=limit)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
