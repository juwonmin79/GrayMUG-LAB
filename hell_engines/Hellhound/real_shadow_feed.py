from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib import error, parse, request

try:
    from .shadow_advisor import run_shadow_evaluation_pipeline
except ImportError:
    from shadow_advisor import run_shadow_evaluation_pipeline


REAL_SHADOW_FEED_SCHEMA_VERSION = "hellhound_real_shadow_feed_v1"
DEFAULT_SIGNAL_TABLES = ("hound_scan_log", "hellhound_shadow_signals")
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "hellhound_shadow_decisions.jsonl"
DAILY_OPEN_CLUSTER_NAMESPACE = uuid.UUID("0f8a9a1d-3211-48f8-a297-4937608db1fd")


class RealShadowFeedError(RuntimeError):
    pass


def load_recent_signals(
    *,
    limit: int = 100,
    table_candidates: Sequence[str] = DEFAULT_SIGNAL_TABLES,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Read recent Hound/Hellhound signals with GET only."""
    supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
    supabase_key = (
        supabase_key
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )
    if not supabase_url or not supabase_key:
        return {
            "ok": True,
            "skipped": True,
            "source_table": None,
            "signals": [],
            "message": "missing Supabase environment; real shadow feed read skipped",
        }

    last_error = None
    for table in table_candidates:
        try:
            rows = _read_signal_table(
                table=table,
                limit=limit,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
            )
            return {
                "ok": True,
                "skipped": False,
                "source_table": table,
                "signals": rows,
                "message": f"loaded {len(rows)} signals from {table}",
            }
        except RealShadowFeedError as exc:
            last_error = str(exc)
            continue
    return {
        "ok": False,
        "skipped": False,
        "source_table": None,
        "signals": [],
        "message": last_error or "no signal table could be read",
    }


def load_recent_outcomes(
    *,
    limit: int = 500,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Read outcome rows for optional read-only joins. No writes are performed."""
    supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
    supabase_key = (
        supabase_key
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )
    if not supabase_url or not supabase_key:
        return {
            "ok": True,
            "skipped": True,
            "outcomes": [],
            "message": "missing Supabase environment; outcome join skipped",
        }
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/hellhound_outcomes"
        f"?select=symbol,evaluation_window,result,shadow_signal_id,created_at"
        f"&order=created_at.desc&limit={int(limit)}"
    )
    status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key)
    if status < 200 or status >= 300:
        return {
            "ok": False,
            "skipped": False,
            "outcomes": [],
            "message": f"unexpected Supabase outcome status {status}",
        }
    return {
        "ok": True,
        "skipped": False,
        "outcomes": rows if isinstance(rows, list) else [],
        "message": "loaded outcome rows",
    }


def build_real_shadow_decision(
    signal: Mapping[str, Any],
    *,
    outcome_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    decision_enabled: Optional[bool] = True,
) -> Dict[str, Any]:
    symbol = str(signal.get("symbol") or signal.get("market") or "").upper()
    if not symbol:
        return _feed_fail_safe(signal, "signal is missing symbol")
    pipeline = run_shadow_evaluation_pipeline(
        symbol=symbol,
        signal=signal,
        shadow_signals=[signal],
        log_path=None,
        decision_enabled=decision_enabled,
    )
    decision = dict(pipeline.get("hellhound_decision") or {})
    outcomes = join_outcomes(signal, outcome_rows or [])
    return {
        "real_shadow_feed_schema_version": REAL_SHADOW_FEED_SCHEMA_VERSION,
        "symbol": symbol,
        "signal_time": _signal_time(signal),
        "event_id": decision.get("event_id"),
        "hellhound_score": decision.get("hellhound_score", 0.0),
        "promotion_status": decision.get("promotion_status", "WATCH"),
        "advisory": decision.get("advisory", "WATCH"),
        "structure_type": decision.get("structure_type", "UNAVAILABLE"),
        "setup_type": decision.get("setup_type"),
        "distribution_risk": decision.get("distribution_risk", 0.0),
        "entry_bias": decision.get("entry_bias", "neutral"),
        "reasons": decision.get("reasons", []),
        "decision_source": decision.get("decision_source"),
        "actual_1h_outcome": outcomes.get("actual_1h_outcome"),
        "actual_4h_outcome": outcomes.get("actual_4h_outcome"),
        "actual_24h_outcome": outcomes.get("actual_24h_outcome"),
        "is_trade_command": False,
    }


def process_recent_signals(
    signals: Sequence[Mapping[str, Any]],
    *,
    outcome_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    output_path: Optional[Path] = DEFAULT_OUTPUT_PATH,
    dry_run: bool = True,
    decision_enabled: Optional[bool] = True,
) -> Dict[str, Any]:
    decisions = [
        build_real_shadow_decision(signal, outcome_rows=outcome_rows, decision_enabled=decision_enabled)
        for signal in signals
    ]
    clusters = detect_daily_open_clusters(signals)
    write_result = None
    if not dry_run and output_path is not None:
        write_result = write_shadow_feed_log(
            list(decisions) + list(clusters),
            output_path=output_path,
        )
    return {
        "real_shadow_feed_schema_version": REAL_SHADOW_FEED_SCHEMA_VERSION,
        "dry_run": dry_run,
        "input_count": len(signals),
        "decision_count": len(decisions),
        "cluster_count": len(clusters),
        "output_path": str(output_path) if output_path is not None else None,
        "write_result": write_result,
        "decisions": decisions,
        "clusters": clusters,
        "is_trade_command": False,
    }


def detect_daily_open_clusters(
    signals: Sequence[Mapping[str, Any]],
    *,
    window_minutes: int = 15,
) -> list[Dict[str, Any]]:
    buckets: Dict[str, list[Mapping[str, Any]]] = {}
    for signal in signals:
        signal_time = _parse_time(_signal_time(signal))
        if signal_time is None:
            continue
        bucket = _daily_open_bucket(signal_time, window_minutes=window_minutes)
        if bucket is None:
            continue
        buckets.setdefault(bucket, []).append(signal)

    clusters = []
    for bucket, rows in sorted(buckets.items()):
        symbols = sorted(
            {
                str(row.get("symbol") or row.get("market") or "").upper()
                for row in rows
                if row.get("symbol") or row.get("market")
            }
        )
        vol_ratios = [
            ratio
            for ratio in (_extract_vol_ratio(row) for row in rows)
            if ratio is not None
        ]
        cluster_id = stable_daily_open_cluster_id(bucket, symbols)
        clusters.append(
            {
                "real_shadow_feed_schema_version": REAL_SHADOW_FEED_SCHEMA_VERSION,
                "record_type": "daily_open_alert_cluster",
                "cluster_id": cluster_id,
                "cluster_time": f"{bucket}T00:00:00+00:00",
                "symbols": symbols,
                "alert_count": len(rows),
                "avg_vol_ratio": _round_or_none(sum(vol_ratios) / len(vol_ratios) if vol_ratios else None),
                "max_vol_ratio": _round_or_none(max(vol_ratios) if vol_ratios else None),
                "daily_open_cluster": True,
                "detection_delay_candidate": True,
                "is_trade_command": False,
            }
        )
    return clusters


def stable_daily_open_cluster_id(bucket: str, symbols: Sequence[str]) -> str:
    seed = f"hellhound:daily-open-cluster:v1:{bucket}:{','.join(sorted(symbols))}"
    return str(uuid.uuid5(DAILY_OPEN_CLUSTER_NAMESPACE, seed))


def write_shadow_feed_log(
    decisions: Sequence[Mapping[str, Any]],
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        for decision in decisions:
            file.write(json.dumps(dict(decision), sort_keys=True) + "\n")
    return {
        "real_shadow_feed_schema_version": REAL_SHADOW_FEED_SCHEMA_VERSION,
        "output_path": str(output_path),
        "written_count": len(decisions),
        "is_trade_command": False,
    }


def join_outcomes(
    signal: Mapping[str, Any],
    outcome_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Optional[str]]:
    signal_id = str(signal.get("id") or signal.get("shadow_signal_id") or "")
    symbol = str(signal.get("symbol") or "").upper()
    joined = {
        "actual_1h_outcome": None,
        "actual_4h_outcome": None,
        "actual_24h_outcome": None,
    }
    for outcome in outcome_rows:
        outcome_signal_id = str(outcome.get("shadow_signal_id") or "")
        outcome_symbol = str(outcome.get("symbol") or "").upper()
        if signal_id and outcome_signal_id and outcome_signal_id != signal_id:
            continue
        if symbol and outcome_symbol and outcome_symbol != symbol:
            continue
        window = str(outcome.get("evaluation_window") or "").lower()
        result = outcome.get("result")
        if window == "1h":
            joined["actual_1h_outcome"] = result
        elif window == "4h":
            joined["actual_4h_outcome"] = result
        elif window == "24h":
            joined["actual_24h_outcome"] = result
    return joined


def mock_signal_rows(limit: int = 5) -> list[Dict[str, Any]]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(limit):
        rows.append(
            {
                "id": f"33333333-3333-4333-8333-{index:012d}",
                "symbol": "BELUSDT" if index % 2 == 0 else "ACTUSDT",
                "source_time": now.isoformat(),
                "hypothesis": {"name": "mock-real-feed"},
                "shadow_action": "WATCH",
                "pattern": "REAL_SHADOW_FEED_DRY_RUN",
                "vol_ratio": 1.5 + index * 0.1,
            }
        )
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hellhound real shadow feed reader")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock", action="store_true", help="Use mock rows instead of Supabase")
    parser.add_argument("--output-path", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    if args.mock:
        signals = mock_signal_rows(args.limit)
        outcomes = []
        source = "mock"
    else:
        loaded = load_recent_signals(limit=args.limit)
        if not loaded["ok"]:
            print(json.dumps(loaded, indent=2, sort_keys=True))
            return 1
        signals = loaded["signals"]
        source = loaded["source_table"] or "none"
        outcomes_result = load_recent_outcomes(limit=args.limit * 3)
        outcomes = outcomes_result.get("outcomes", [])

    result = process_recent_signals(
        signals,
        outcome_rows=outcomes,
        output_path=Path(args.output_path),
        dry_run=args.dry_run,
    )
    result["source"] = source
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _read_signal_table(
    *,
    table: str,
    limit: int,
    supabase_url: str,
    supabase_key: str,
) -> list[Dict[str, Any]]:
    fields = "id,symbol,source_time,created_at,pattern,shadow_action,hypothesis,confidence"
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{parse.quote(table, safe='')}"
        f"?select={fields}&order=created_at.desc&limit={int(limit)}"
    )
    status, rows = _supabase_json(endpoint=endpoint, supabase_key=supabase_key)
    if status < 200 or status >= 300:
        raise RealShadowFeedError(f"{table} returned status {status}")
    if not isinstance(rows, list):
        raise RealShadowFeedError(f"{table} response was not a list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _supabase_json(*, endpoint: str, supabase_key: str) -> tuple[int, Any]:
    req = request.Request(
        endpoint,
        method="GET",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else []
    except error.HTTPError as exc:
        return exc.code, []
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RealShadowFeedError(str(exc)) from exc


def _signal_time(signal: Mapping[str, Any]) -> str:
    return str(signal.get("source_time") or signal.get("created_at") or _now_utc())


def _parse_time(value: str) -> Optional[datetime]:
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _daily_open_bucket(value: datetime, *, window_minutes: int) -> Optional[str]:
    current_midnight = value.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = current_midnight + timedelta(days=1)
    previous_midnight = current_midnight - timedelta(days=1)
    candidates = (previous_midnight, current_midnight, next_midnight)
    nearest = min(candidates, key=lambda item: abs((value - item).total_seconds()))
    if abs((value - nearest).total_seconds()) <= window_minutes * 60:
        return nearest.date().isoformat()
    return None


def _extract_vol_ratio(signal: Mapping[str, Any]) -> Optional[float]:
    for key in ("vol_ratio", "volume_ratio", "vol_ma_ratio", "volume_ma_ratio"):
        value = _optional_float(signal.get(key))
        if value is not None:
            return value
    for payload_key in ("payload", "market_snapshot", "lead_line_payload", "target_feed"):
        payload = signal.get(payload_key)
        if not isinstance(payload, Mapping):
            continue
        for key in ("vol_ratio", "volume_ratio", "vol_ma_ratio", "volume_ma_ratio"):
            value = _optional_float(payload.get(key))
            if value is not None:
                return value
    return None


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 6)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feed_fail_safe(signal: Mapping[str, Any], error: str) -> Dict[str, Any]:
    return {
        "real_shadow_feed_schema_version": REAL_SHADOW_FEED_SCHEMA_VERSION,
        "symbol": str(signal.get("symbol") or "").upper(),
        "signal_time": _signal_time(signal),
        "event_id": None,
        "hellhound_score": 0.0,
        "promotion_status": "WATCH",
        "structure_type": "UNAVAILABLE",
        "setup_type": None,
        "distribution_risk": 0.0,
        "entry_bias": "neutral",
        "reasons": ["Hellhound real shadow feed returned fail-safe neutral."],
        "actual_1h_outcome": None,
        "actual_4h_outcome": None,
        "actual_24h_outcome": None,
        "is_trade_command": False,
        "error": error,
    }


if __name__ == "__main__":
    sys.exit(main())
