from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Optional, Sequence, Union
from urllib import error, parse, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from .mfe_mae_engine import DEFAULT_MFE_MAE_PATH
except ImportError:
    from mfe_mae_engine import DEFAULT_MFE_MAE_PATH

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if load_dotenv:
    load_dotenv(ENV_PATH)
else:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


MFE_MAE_FEATURE_SCHEMA_VERSION = "hellhound_mfe_mae_feature_dataset_v1"
DEFAULT_FEATURE_DATASET_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_mfe_mae_feature_dataset.jsonl"
DEFAULT_FEATURE_REPORT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_mfe_mae_feature_report.json"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
FEATURE_FIELDS = (
    "structure_type",
    "hellhound_score",
    "decision_source",
    "signal_hour",
    "signal_day_of_week",
    "btc_weather",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "rsi_15m",
    "macd_hist_15m",
)
COMPARE_FIELDS = (
    "hellhound_score",
    "rsi_15m",
    "volume_ratio_ma5",
    "volume_ratio_ma20",
    "signal_hour",
    "btc_weather",
)


class MfeMaeFeatureError(RuntimeError):
    pass


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
            rows.append(dict(row))
    return rows


def build_feature_dataset(
    mfe_rows: Sequence[Mapping[str, Any]],
    signals_by_id: Mapping[str, Mapping[str, Any]],
) -> list[Dict[str, Any]]:
    enriched = []
    for row in mfe_rows:
        signal_id = str(row.get("signal_id") or row.get("shadow_signal_id") or "")
        signal = signals_by_id.get(signal_id) or {}
        signal_time = _signal_time(signal)
        features = _feature_values(row, signal, signal_time)
        enriched.append(
            {
                **dict(row),
                "mfe_mae_feature_schema_version": MFE_MAE_FEATURE_SCHEMA_VERSION,
                **features,
                "mfe_bucket": mfe_bucket(row.get("mfe_pct")),
                "mae_bucket": mae_bucket(row.get("mae_pct")),
                "feature_join_success": bool(signal),
                "feature_source": "supabase_hellhound_shadow_signals" if signal else None,
                "is_trade_command": False,
            }
        )
    return enriched


def build_feature_report(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    high_rows = [row for row in rows if row.get("mfe_bucket") in {"HIGH", "EXTREME"}]
    loss_rows = [row for row in rows if row.get("mfe_bucket") == "LOSS"]
    return {
        "mfe_mae_feature_schema_version": MFE_MAE_FEATURE_SCHEMA_VERSION,
        "record_count": total,
        "join_success_count": sum(1 for row in rows if row.get("feature_join_success") is True),
        "join_success_rate": _rate(sum(1 for row in rows if row.get("feature_join_success") is True), total),
        "feature_coverage": {field: _coverage(rows, field) for field in FEATURE_FIELDS},
        "mfe_bucket_counts": _bucket_counts(rows, "mfe_bucket", ("LOSS", "LOW", "MID", "HIGH", "EXTREME")),
        "mae_bucket_counts": _bucket_counts(rows, "mae_bucket", ("SAFE", "NORMAL", "RISK", "DANGER")),
        "high_mfe_vs_loss": {
            "high_group": _group_compare_summary(high_rows),
            "loss_group": _group_compare_summary(loss_rows),
            "delta_high_minus_loss": _group_delta(high_rows, loss_rows),
        },
        "is_trade_command": False,
    }


def build_feature_dataset_file(
    *,
    input_path: Union[Path, str] = DEFAULT_MFE_MAE_PATH,
    output_path: Union[Path, str] = DEFAULT_FEATURE_DATASET_PATH,
    report_path: Union[Path, str] = DEFAULT_FEATURE_REPORT_PATH,
) -> Dict[str, Any]:
    rows = load_mfe_mae_rows(input_path)
    signals = load_shadow_signals_for_rows(rows)
    enriched = build_feature_dataset(rows, signals)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for row in enriched:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    report = build_feature_report(enriched)
    report_output = Path(report_path)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "mfe_mae_feature_schema_version": MFE_MAE_FEATURE_SCHEMA_VERSION,
        "input_path": str(input_path),
        "output_path": str(output),
        "report_path": str(report_output),
        "record_count": len(enriched),
        "join_success_count": report["join_success_count"],
        "is_trade_command": False,
        "report": report,
    }


def load_shadow_signals_for_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        return {}
    signal_ids = sorted({str(row.get("signal_id") or row.get("shadow_signal_id") or "") for row in rows if row.get("signal_id") or row.get("shadow_signal_id")})
    signals: Dict[str, Dict[str, Any]] = {}
    fields = (
        "id,symbol,created_at,source_time,pattern,shadow_action,confidence,"
        "lead_line_score,lead_line_payload,target_feed,calibration_payload,fitness_payload,payload"
    )
    for chunk in _chunks(signal_ids, 80):
        signal_filter = parse.quote(f"in.({','.join(chunk)})", safe="(),")
        endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}?select={fields}&id={signal_filter}"
        status, data = _supabase_json(endpoint=endpoint, supabase_key=supabase_key)
        if status < 200 or status >= 300:
            raise MfeMaeFeatureError(f"unexpected Supabase status {status}")
        if not isinstance(data, list):
            raise MfeMaeFeatureError("Supabase signal response was not a list")
        for row in data:
            if isinstance(row, Mapping) and row.get("id"):
                signals[str(row["id"])] = dict(row)
    return signals


def mfe_bucket(value: Any) -> str:
    mfe = _number(value)
    if mfe is None or mfe <= 0:
        return "LOSS"
    if mfe < 2:
        return "LOW"
    if mfe < 5:
        return "MID"
    if mfe < 10:
        return "HIGH"
    return "EXTREME"


def mae_bucket(value: Any) -> str:
    mae = _number(value)
    if mae is None or mae >= -2:
        return "SAFE"
    if mae >= -5:
        return "NORMAL"
    if mae >= -10:
        return "RISK"
    return "DANGER"


def _feature_values(row: Mapping[str, Any], signal: Mapping[str, Any], signal_time: Optional[datetime]) -> Dict[str, Any]:
    return {
        "structure_type": row.get("structure_type") or signal.get("pattern"),
        "hellhound_score": _first_number(signal, row, key="hellhound_score"),
        "decision_source": _first_value(signal, row, key="decision_source"),
        "signal_hour": signal_time.hour if signal_time else None,
        "signal_day_of_week": signal_time.weekday() if signal_time else None,
        "btc_weather": _nested_number(signal, "btc_weather", "btc_4h_weather"),
        "volume_ratio_ma5": _nested_number(signal, "volume_ratio_ma5"),
        "volume_ratio_ma20": _nested_number(signal, "volume_ratio_ma20"),
        "rsi_15m": _nested_number(signal, "rsi_15m"),
        "macd_hist_15m": _nested_number(signal, "macd_hist_15m"),
    }


def _signal_time(signal: Mapping[str, Any]) -> Optional[datetime]:
    raw = signal.get("source_time") or signal.get("created_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _nested_number(signal: Mapping[str, Any], *keys: str) -> Optional[float]:
    containers = [signal]
    for container_name in ("payload", "lead_line_payload", "target_feed", "calibration_payload", "fitness_payload"):
        container = signal.get(container_name)
        if isinstance(container, Mapping):
            containers.append(container)
    for container in containers:
        for key in keys:
            value = _number(container.get(key))
            if value is not None:
                return value
    return None


def _first_number(*rows: Mapping[str, Any], key: str) -> Optional[float]:
    for row in rows:
        value = _number(row.get(key))
        if value is not None:
            return value
        for container_name in ("payload", "lead_line_payload", "target_feed", "calibration_payload", "fitness_payload"):
            container = row.get(container_name)
            if isinstance(container, Mapping):
                nested = _number(container.get(key))
                if nested is not None:
                    return nested
    return None


def _first_value(*rows: Mapping[str, Any], key: str) -> Any:
    for row in rows:
        if row.get(key) not in (None, ""):
            return row.get(key)
        for container_name in ("payload", "lead_line_payload", "target_feed", "calibration_payload", "fitness_payload"):
            container = row.get(container_name)
            if isinstance(container, Mapping) and container.get(key) not in (None, ""):
                return container.get(key)
    return None


def _coverage(rows: Sequence[Mapping[str, Any]], field: str) -> Dict[str, Any]:
    total = len(rows)
    present = sum(1 for row in rows if row.get(field) is not None)
    joined = sum(1 for row in rows if row.get("feature_join_success") is True and row.get(field) is not None)
    return {
        "present_count": present,
        "null_count": total - present,
        "present_rate": _rate(present, total),
        "null_rate": _rate(total - present, total),
        "join_present_rate": _rate(joined, total),
    }


def _bucket_counts(rows: Sequence[Mapping[str, Any]], key: str, buckets: Sequence[str]) -> Dict[str, int]:
    counts = {bucket: 0 for bucket in buckets}
    for row in rows:
        value = row.get(key)
        if value in counts:
            counts[str(value)] += 1
    return counts


def _group_compare_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "count": len(rows),
        **{f"average_{field}": _average(rows, field) for field in COMPARE_FIELDS},
        "average_mfe_pct": _average(rows, "mfe_pct"),
        "average_mae_pct": _average(rows, "mae_pct"),
    }


def _group_delta(high_rows: Sequence[Mapping[str, Any]], loss_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    fields = (*COMPARE_FIELDS, "mfe_pct", "mae_pct")
    result = {}
    for field in fields:
        high = _average(high_rows, field)
        loss = _average(loss_rows, field)
        result[field] = round(high - loss, 6) if high is not None and loss is not None else None
    return result


def _average(rows: Sequence[Mapping[str, Any]], key: str) -> Optional[float]:
    values = [_number(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return round(mean(values), 6) if values else None


def _rate(count: int, total: int) -> Optional[float]:
    return round(count / total, 6) if total else None


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
        with request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise MfeMaeFeatureError(f"Supabase HTTP {exc.code}: {safe_body}") from exc
    except error.URLError as exc:
        raise MfeMaeFeatureError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise MfeMaeFeatureError("Supabase feature query timed out") from exc
    except json.JSONDecodeError as exc:
        raise MfeMaeFeatureError("Supabase response was not JSON") from exc


def main() -> int:
    result = build_feature_dataset_file()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
