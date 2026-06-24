from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib import error, request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from .integration_stub import optional_hellhound_decision
    from .wave_snapshot import _build_snapshot
except ImportError:
    from integration_stub import optional_hellhound_decision
    from wave_snapshot import _build_snapshot

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


HYPOTHESES_TABLE = "hypotheses"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
NODE_NAME = "Hellhound-001"
DEFAULT_MODE = "BTC_ACCUMULATION"
ALLOWED_SHADOW_ACTIONS = {"OBSERVE", "WATCH", "AVOID", "WAIT_CONFIRMATION"}
FORBIDDEN_SHADOW_ACTIONS = {
    "BUY",
    "SELL",
    "ORDER",
    "CLOSE_POSITION",
    "OPEN_POSITION",
}
SIGNAL_ID_NAMESPACE = uuid.UUID("b5e72a54-3fd4-4f4f-95f5-5917dc49f65d")

LOGGER = logging.getLogger("hellhound.shadow_runner")


@dataclass(frozen=True)
class ShadowRunnerResult:
    ok: bool
    dry_run: bool
    inserted: bool
    skipped: bool
    message: str
    signal: Optional[Dict[str, Any]] = None
    signals: Optional[list[Dict[str, Any]]] = None


def normalize_oraclejp_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize one OracleJP-style payload into one Hellhound shadow signal."""
    symbol = _first_present(
        payload,
        "symbol",
        "pair",
        "market",
        nested=("market_snapshot", "symbol"),
    )
    if not symbol:
        raise ValueError("OracleJP payload is missing symbol")

    symbol = str(symbol).upper()
    base_asset, quote_asset = _asset_pair(symbol, payload)

    lead_line_payload = _as_mapping(payload.get("lead_line") or payload.get("lead_line_payload"))
    execution_guidance = _as_mapping(
        payload.get("execution_guidance") or payload.get("guidance")
    )

    requested_action = str(
        payload.get("shadow_action")
        or execution_guidance.get("shadow_action")
        or "OBSERVE"
    ).upper()
    shadow_action, action_note = _safe_shadow_action(requested_action)

    note_parts = [
        "Hellhound-001-D minimal shadow runner.",
        "Shadow-only signal; no order execution.",
    ]
    if action_note:
        note_parts.append(action_note)
    if payload.get("note"):
        note_parts.append(str(payload["note"]))
    if payload.get("hypothesis"):
        hypothesis = _as_mapping(payload["hypothesis"])
        note_parts.append(
            f"Hypothesis {hypothesis.get('id', 'unknown')} {hypothesis.get('name', 'unnamed')}."
        )

    signal: Dict[str, Any] = {
        "signal_id": str(payload.get("signal_id") or payload.get("shadow_signal_id") or payload.get("id") or _stable_signal_id(symbol, payload)),
        "run_id": str(payload.get("run_id") or _new_run_id()),
        "mode": str(payload.get("mode") or DEFAULT_MODE),
        "node_name": NODE_NAME,
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "source_time": _source_time(payload),
        "lead_line_rank": _int_or_none(
            payload.get("lead_line_rank") or lead_line_payload.get("rank")
        ),
        "lead_line_score": _float_or_none(
            payload.get("lead_line_score") or lead_line_payload.get("score")
        ),
        "lead_line_payload": _json_ready(lead_line_payload) or None,
        "target_feed": _json_ready(payload.get("target_feed")),
        "fitness_payload": _json_ready(
            payload.get("fitness_payload") or payload.get("fitness")
        ),
        "calibration_payload": _json_ready(
            payload.get("calibration_payload") or payload.get("calibration")
        ),
        "execution_guidance": _json_ready(execution_guidance) or None,
        "hound_baseline_signal": _json_ready(payload.get("hound_baseline_signal")),
        "pattern": payload.get("pattern") or execution_guidance.get("pattern"),
        "entry_guidance": payload.get("entry_guidance")
        or execution_guidance.get("entry_guidance"),
        "tp_case": payload.get("tp_case") or execution_guidance.get("tp_case"),
        "sl_case": payload.get("sl_case") or execution_guidance.get("sl_case"),
        "exit_triggers": _json_ready(
            payload.get("exit_triggers") or execution_guidance.get("exit_triggers")
        ),
        "shadow_action": shadow_action,
        "confidence": _float_or_none(
            payload.get("confidence") or execution_guidance.get("confidence")
        ),
        "final_weight": _float_or_none(
            payload.get("final_weight") or payload.get("weight")
        ),
        "payload": _feature_capture_payload(payload),
        "is_order_executed": False,
        "is_shadow": True,
        "note": " ".join(note_parts),
    }
    return _drop_none(signal)


def run_shadow_payload(payload: Mapping[str, Any]) -> ShadowRunnerResult:
    return _run_shadow_payloads([payload], shadow_signal_source="local_fixture")


def run_shadow_universe(universe: Sequence[Mapping[str, Any] | str]) -> ShadowRunnerResult:
    payloads = [_payload_for_universe_row(row) for row in universe]
    LOGGER.info(
        "shadow_signal_source=live_universe target_symbols=%s",
        ",".join(str(payload.get("symbol", "")) for payload in payloads),
    )
    return _run_shadow_payloads(payloads, shadow_signal_source="live_universe")


def _run_shadow_payloads(
    payloads: Sequence[Mapping[str, Any]], *, shadow_signal_source: str
) -> ShadowRunnerResult:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        LOGGER.warning(
            "Supabase credentials missing; active hypotheses and shadow inserts skipped"
        )
        return ShadowRunnerResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            inserted=False,
            skipped=True,
            message="missing Supabase environment; skipped hypotheses load and insert",
        )

    try:
        hypotheses = _load_active_hypotheses(
            supabase_url=supabase_url, supabase_key=supabase_key
        )
    except ShadowInsertError as exc:
        LOGGER.error("Active hypothesis load failed: %s", exc)
        return ShadowRunnerResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            inserted=False,
            skipped=False,
            message=str(exc),
        )

    if not hypotheses:
        LOGGER.info("No active hypotheses found; no shadow signals generated")
        return ShadowRunnerResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            inserted=False,
            skipped=True,
            message="no active hypotheses",
            signals=[],
        )

    try:
        signals = []
        for payload in payloads:
            for hypothesis in hypotheses:
                signals.append(
                    normalize_oraclejp_payload(_payload_for_hypothesis(payload, hypothesis))
                )
    except ValueError as exc:
        LOGGER.error("Shadow signal normalization failed: %s", exc)
        return ShadowRunnerResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            inserted=False,
            skipped=True,
            message=str(exc),
        )

    if _dry_run_enabled():
        LOGGER.info(
            "Dry-run enabled; %s hypothesis shadow signals not inserted source=%s",
            len(signals),
            shadow_signal_source,
        )
        print(json.dumps(signals, indent=2, sort_keys=True))
        return ShadowRunnerResult(
            ok=True,
            dry_run=True,
            inserted=False,
            skipped=False,
            message=f"dry-run generated {len(signals)} hypothesis shadow signals",
            signal=signals[0] if signals else None,
            signals=signals,
        )

    try:
        inserted_signals = []
        for signal in signals:
            inserted_signal = _insert_shadow_signal(
                supabase_url=supabase_url, supabase_key=supabase_key, signal=signal
            )
            inserted_signals.append(inserted_signal or signal)
    except ShadowInsertError as exc:
        LOGGER.error("Supabase shadow signal insert failed: %s", exc)
        return ShadowRunnerResult(
            ok=False,
            dry_run=False,
            inserted=False,
            skipped=False,
            message=str(exc),
            signals=signals,
        )

    LOGGER.info(
        "Inserted %s Hellhound hypothesis shadow signals shadow_signal_source=%s",
        len(inserted_signals),
        shadow_signal_source,
    )
    return ShadowRunnerResult(
        ok=True,
        dry_run=False,
        inserted=True,
        skipped=False,
        message=f"inserted {len(inserted_signals)} hypothesis shadow signals",
        signal=inserted_signals[0] if inserted_signals else None,
        signals=inserted_signals,
    )


class ShadowInsertError(RuntimeError):
    pass


def _insert_shadow_signal(
    *, supabase_url: str, supabase_key: str, signal: Mapping[str, Any]
) -> Optional[Dict[str, Any]]:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
    insert_signal = _db_insert_signal(signal)
    body = json.dumps(insert_signal).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise ShadowInsertError(f"unexpected Supabase status {response.status}")
            body = response.read().decode("utf-8")
            rows = json.loads(body) if body else []
            if isinstance(rows, list) and rows:
                returned = dict(rows[0])
                returned["signal_id"] = str(returned.get("id") or signal.get("signal_id") or "")
                returned["shadow_signal_id"] = returned["signal_id"]
                return returned
            return None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ShadowInsertError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise ShadowInsertError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ShadowInsertError("Supabase insert timed out") from exc


def _load_active_hypotheses(
    *, supabase_url: str, supabase_key: str
) -> list[Dict[str, Any]]:
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{HYPOTHESES_TABLE}"
        "?select=id,name,status,config,created_at&status=eq.active"
    )
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
        with request.urlopen(req, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise ShadowInsertError(f"unexpected Supabase status {response.status}")
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ShadowInsertError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise ShadowInsertError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ShadowInsertError("Supabase hypothesis load timed out") from exc

    try:
        hypotheses = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ShadowInsertError("Supabase hypotheses response was not JSON") from exc

    if not isinstance(hypotheses, list):
        raise ShadowInsertError("Supabase hypotheses response was not a list")
    return [
        _json_ready(hypothesis)
        for hypothesis in hypotheses
        if isinstance(hypothesis, Mapping) and hypothesis.get("status") == "active"
    ]


def _payload_for_hypothesis(
    payload: Mapping[str, Any], hypothesis: Mapping[str, Any]
) -> Dict[str, Any]:
    config = _as_mapping(hypothesis.get("config"))
    hypothesis_payload = {
        "id": hypothesis.get("id"),
        "name": hypothesis.get("name"),
        "status": hypothesis.get("status"),
        "config": _json_ready(config),
        "created_at": hypothesis.get("created_at"),
    }
    protected_payload = {
        key: payload.get(key)
        for key in (
            "symbol",
            "base_asset",
            "quote_asset",
            "source_time",
            "lead_line",
            "lead_line_payload",
            "lead_line_rank",
            "lead_line_score",
            "target_feed",
            "hellhound_score",
            "decision_source",
            "btc_weather",
            "btc_4h_weather",
            "volume_ratio_ma5",
            "volume_ratio_ma20",
            "rsi_15m",
            "macd_hist_15m",
        )
        if key in payload
    }
    next_payload = dict(payload)
    next_payload.update(config)
    next_payload.update(protected_payload)
    next_payload["hypothesis"] = hypothesis_payload
    next_payload["target_feed"] = _merge_json_object(
        config.get("target_feed") or payload.get("target_feed"),
        {
            "hypothesis": hypothesis_payload,
            "market_source": payload.get("market_source") or "live_universe",
            "universe_rank": payload.get("universe_rank"),
            "universe_score": payload.get("universe_score"),
            "rank_score": payload.get("rank_score"),
        },
    )
    next_payload["execution_guidance"] = _merge_json_object(
        config.get("execution_guidance")
        or payload.get("execution_guidance")
        or payload.get("guidance"),
        {"hypothesis": hypothesis_payload},
    )
    return next_payload


def _payload_for_universe_row(row: Mapping[str, Any] | str) -> Dict[str, Any]:
    if isinstance(row, str):
        universe_row: Dict[str, Any] = {"symbol": row}
    elif isinstance(row, Mapping):
        universe_row = dict(row)
    else:
        raise ValueError("universe row must be a mapping or symbol string")

    symbol = str(universe_row.get("symbol") or "").upper()
    if not symbol:
        raise ValueError("universe row is missing symbol")

    universe_row = _enrich_universe_row_features(universe_row, symbol)
    base_asset, quote_asset = _asset_pair(symbol, universe_row)
    rank = _int_or_none(universe_row.get("rank") or universe_row.get("universe_rank"))
    rank_score = _float_or_none(
        universe_row.get("rank_score") or universe_row.get("universe_score")
    )
    source_time = str(universe_row.get("source_time") or datetime.now(timezone.utc).isoformat())
    last_price = _float_or_none(
        universe_row.get("last_price")
        or universe_row.get("lastPrice")
        or universe_row.get("price")
    )

    return {
        "signal_id": str(
            universe_row.get("signal_id")
            or universe_row.get("shadow_signal_id")
            or universe_row.get("id")
            or _stable_signal_id(symbol, {**universe_row, "source_time": source_time})
        ),
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "mode": DEFAULT_MODE,
        "source_time": source_time,
        "market_source": "live_universe",
        "universe_rank": rank,
        "universe_score": rank_score,
        "rank_score": rank_score,
        "hellhound_score": _float_or_none(universe_row.get("hellhound_score")),
        "decision_source": universe_row.get("decision_source"),
        "structure_type": universe_row.get("structure_type"),
        "setup_type": universe_row.get("setup_type"),
        "promotion_status": universe_row.get("promotion_status"),
        "lead_line": {
            "rank": rank,
            "score": rank_score,
            "source": "live_universe",
            "symbol": symbol,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "last_price": last_price,
            "volume_ratio_ma5": _float_or_none(universe_row.get("volume_ratio_ma5")),
            "volume_ratio_ma20": _float_or_none(universe_row.get("volume_ratio_ma20")),
            "rsi_15m": _float_or_none(universe_row.get("rsi_15m")),
            "macd_hist_15m": _float_or_none(universe_row.get("macd_hist_15m")),
            "btc_weather": _float_or_none(universe_row.get("btc_weather") or universe_row.get("btc_4h_weather")),
            "hellhound_score": _float_or_none(universe_row.get("hellhound_score")),
            "decision_source": universe_row.get("decision_source"),
        },
        "target_feed": {
            "mode": DEFAULT_MODE,
            "focus_assets": [base_asset] if base_asset else [],
            "symbol": symbol,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "market_source": "live_universe",
            "universe_rank": rank,
            "universe_score": rank_score,
            "rank_score": rank_score,
            "last_price": last_price,
            "volume_ratio_ma5": _float_or_none(universe_row.get("volume_ratio_ma5")),
            "volume_ratio_ma20": _float_or_none(universe_row.get("volume_ratio_ma20")),
            "rsi_15m": _float_or_none(universe_row.get("rsi_15m")),
            "macd_hist_15m": _float_or_none(universe_row.get("macd_hist_15m")),
            "btc_weather": _float_or_none(universe_row.get("btc_weather") or universe_row.get("btc_4h_weather")),
            "hellhound_score": _float_or_none(universe_row.get("hellhound_score")),
            "decision_source": universe_row.get("decision_source"),
        },
        "fitness_payload": {
            "source": "live_universe",
            "universe_rank": rank,
            "universe_score": rank_score,
            "hellhound_score": _float_or_none(universe_row.get("hellhound_score")),
            "decision_source": universe_row.get("decision_source"),
        },
        "calibration_payload": {
            "source": "live_universe",
            "price_change_pct": universe_row.get("price_change_pct"),
            "volatility": universe_row.get("volatility"),
            "quote_volume": universe_row.get("quote_volume"),
            "volume_ratio_ma5": _float_or_none(universe_row.get("volume_ratio_ma5")),
            "volume_ratio_ma20": _float_or_none(universe_row.get("volume_ratio_ma20")),
            "rsi_15m": _float_or_none(universe_row.get("rsi_15m")),
            "macd_hist_15m": _float_or_none(universe_row.get("macd_hist_15m")),
            "btc_weather": _float_or_none(universe_row.get("btc_weather") or universe_row.get("btc_4h_weather")),
            "hellhound_score": _float_or_none(universe_row.get("hellhound_score")),
            "decision_source": universe_row.get("decision_source"),
        },
        "execution_guidance": {
            "pattern": "LIVE_UNIVERSE_OBSERVE",
            "entry_guidance": "Observe only; no executable order.",
            "shadow_action": "WATCH",
        },
        "final_weight": rank_score,
        "note": "Live universe shadow payload.",
    }


def _enrich_universe_row_features(
    universe_row: Mapping[str, Any], symbol: str
) -> Dict[str, Any]:
    enriched = dict(universe_row)
    candles_by_timeframe = _candles_by_timeframe(enriched)
    primary_candles = candles_by_timeframe.get("15m") or []
    if primary_candles:
        btc_candles_by_timeframe = _btc_candles_by_timeframe(enriched)
        source_time = enriched.get("source_time") or _last_candle_time(primary_candles) or datetime.now(timezone.utc).isoformat()
        snapshot = _build_snapshot(
            symbol,
            "15m",
            source_time,
            candles=primary_candles,
            btc_candles_by_timeframe=btc_candles_by_timeframe,
        )
        enriched["wave_snapshot"] = _merge_json_object(
            enriched.get("wave_snapshot") or enriched.get("market_snapshot"),
            snapshot,
        )
        for source_key, target_key in (
            ("volume_ratio_ma5", "volume_ratio_ma5"),
            ("volume_ratio_ma20", "volume_ratio_ma20"),
            ("rsi_15m", "rsi_15m"),
            ("macd_hist_15m", "macd_hist_15m"),
            ("btc_4h_weather", "btc_weather"),
            ("btc_4h_weather", "btc_4h_weather"),
        ):
            if enriched.get(target_key) is None and snapshot.get(source_key) is not None:
                enriched[target_key] = snapshot.get(source_key)

    if enriched.get("hellhound_score") is None or enriched.get("decision_source") is None:
        decision = optional_hellhound_decision(
            symbol=symbol,
            signal=enriched,
            shadow_signals=[enriched],
            candles_by_timeframe=candles_by_timeframe,
            historical_candles=_historical_candles(enriched, candles_by_timeframe),
            as_of_time=enriched.get("source_time"),
            decision_enabled=True,
        )
        if enriched.get("hellhound_score") is None and decision.get("hellhound_score") is not None:
            enriched["hellhound_score"] = decision.get("hellhound_score")
        if enriched.get("decision_source") is None and decision.get("decision_source") is not None:
            enriched["decision_source"] = decision.get("decision_source")
        for key in ("structure_type", "setup_type", "promotion_status", "distribution_risk"):
            if enriched.get(key) is None and decision.get(key) is not None:
                enriched[key] = decision.get(key)

    return enriched


def _candles_by_timeframe(payload: Mapping[str, Any]) -> Dict[str, Sequence[Mapping[str, Any]]]:
    result: Dict[str, Sequence[Mapping[str, Any]]] = {}
    raw = payload.get("candles_by_timeframe")
    if isinstance(raw, Mapping):
        for timeframe, candles in raw.items():
            if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes)):
                result[str(timeframe)] = [dict(candle) for candle in candles if isinstance(candle, Mapping)]
    for key, timeframe in (
        ("candles_1m", "1m"),
        ("candles_15m", "15m"),
        ("candles", "15m"),
        ("historical_candles", "15m"),
        ("candles_1h", "1h"),
        ("candles_4h", "4h"),
        ("candles_1d", "1d"),
    ):
        candles = payload.get(key)
        if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes)):
            normalized = [dict(candle) for candle in candles if isinstance(candle, Mapping)]
            if normalized:
                result[timeframe] = normalized
    return result


def _btc_candles_by_timeframe(payload: Mapping[str, Any]) -> Dict[str, Sequence[Mapping[str, Any]]]:
    result: Dict[str, Sequence[Mapping[str, Any]]] = {}
    raw = payload.get("btc_candles_by_timeframe")
    if isinstance(raw, Mapping):
        for timeframe, candles in raw.items():
            if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes)):
                result[str(timeframe)] = [dict(candle) for candle in candles if isinstance(candle, Mapping)]
    for key, timeframe in (
        ("btc_candles_15m", "15m"),
        ("btc_candles_1h", "1h"),
        ("btc_candles_4h", "4h"),
        ("btc_candles_1d", "1d"),
    ):
        candles = payload.get(key)
        if isinstance(candles, Sequence) and not isinstance(candles, (str, bytes)):
            normalized = [dict(candle) for candle in candles if isinstance(candle, Mapping)]
            if normalized:
                result[timeframe] = normalized
    return result


def _historical_candles(
    payload: Mapping[str, Any], candles_by_timeframe: Mapping[str, Sequence[Mapping[str, Any]]]
) -> Sequence[Mapping[str, Any]]:
    raw = payload.get("historical_candles")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return [dict(candle) for candle in raw if isinstance(candle, Mapping)]
    return candles_by_timeframe.get("1d") or []


def _last_candle_time(candles: Sequence[Mapping[str, Any]]) -> Optional[Any]:
    if not candles:
        return None
    last = candles[-1]
    return last.get("time") or last.get("timestamp") or last.get("open_time")


def _merge_json_object(value: Any, addition: Mapping[str, Any]) -> Dict[str, Any]:
    merged = _as_mapping(value)
    merged.update(_json_ready(addition))
    return merged


def _feature_capture_payload(payload: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    existing = _as_mapping(payload.get("payload"))
    feature_capture = dict(existing)
    for key in (
        "hellhound_score",
        "decision_source",
        "btc_weather",
        "btc_4h_weather",
        "volume_ratio_ma5",
        "volume_ratio_ma20",
        "rsi_15m",
        "macd_hist_15m",
    ):
        value = _feature_value(payload, key)
        if value is not None:
            feature_capture[key] = value
    return _json_ready(feature_capture) or None


def _feature_value(payload: Mapping[str, Any], key: str) -> Any:
    if payload.get(key) is not None:
        return payload.get(key)
    for container_name in (
        "payload",
        "market_snapshot",
        "wave_snapshot",
        "snapshot",
        "lead_line",
        "lead_line_payload",
        "target_feed",
        "calibration_payload",
        "calibration",
        "execution_guidance",
        "guidance",
    ):
        container = payload.get(container_name)
        if isinstance(container, Mapping) and container.get(key) is not None:
            return container.get(key)
    return None


def _stable_signal_id(symbol: str, payload: Mapping[str, Any]) -> str:
    seed = f"hellhound:signal:v1:{str(symbol).upper()}:{payload.get('source_time') or payload.get('created_at') or ''}:{payload.get('pattern') or ''}"
    return str(uuid.uuid5(SIGNAL_ID_NAMESPACE, seed))


def _db_insert_signal(signal: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(signal)
    signal_id = row.pop("signal_id", None)
    row.pop("shadow_signal_id", None)
    if signal_id and not row.get("id") and _is_uuid(signal_id):
        row["id"] = str(signal_id)
    return row


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


def _safe_shadow_action(requested_action: str) -> tuple[str, Optional[str]]:
    if requested_action in ALLOWED_SHADOW_ACTIONS:
        return requested_action, None
    if requested_action in FORBIDDEN_SHADOW_ACTIONS:
        return (
            "WAIT_CONFIRMATION",
            f"Requested forbidden action {requested_action}; converted to WAIT_CONFIRMATION.",
        )
    return (
        "OBSERVE",
        f"Unknown shadow action {requested_action}; converted to OBSERVE.",
    )


def _dry_run_enabled() -> bool:
    raw = os.environ.get("SHADOW_RUNNER_DRY_RUN", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _first_present(
    payload: Mapping[str, Any], *keys: str, nested: tuple[str, str]
) -> Optional[Any]:
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    parent = payload.get(nested[0])
    if isinstance(parent, Mapping):
        return parent.get(nested[1])
    return None


def _asset_pair(symbol: str, payload: Mapping[str, Any]) -> tuple[Optional[str], Optional[str]]:
    base_asset = payload.get("base_asset")
    quote_asset = payload.get("quote_asset")
    if base_asset or quote_asset:
        return _string_or_none(base_asset), _string_or_none(quote_asset)

    if "/" in symbol:
        base, quote = symbol.split("/", 1)
        return base or None, quote or None

    for quote in ("USDT", "USDC", "BTC", "ETH", "KRW"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote
    return None, None


def _source_time(payload: Mapping[str, Any]) -> str:
    value = payload.get("source_time") or payload.get("timestamp")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"hellhound-001-d-{stamp}-{uuid.uuid4().hex[:8]}"


def _as_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return {"value": value}


def _json_ready(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "__dataclass_fields__"):
        return _json_ready(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _drop_none(signal: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in signal.items() if value is not None}


def _int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value).upper()


def _redact_secret_text(value: str) -> str:
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    redacted = value
    for secret in (service_key, anon_key):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _local_test_payload() -> Dict[str, Any]:
    return {
        "symbol": "ETHUSDT",
        "mode": DEFAULT_MODE,
        "source_time": datetime.now(timezone.utc).isoformat(),
        "lead_line": {
            "rank": 3,
            "score": 0.72,
            "source": "local_shadow_runner_payload",
        },
        "target_feed": {
            "mode": DEFAULT_MODE,
            "focus_assets": ["ETH"],
            "confidence": 0.61,
        },
        "fitness_payload": {
            "score": 0.58,
            "source": "local_shadow_runner_payload",
        },
        "calibration_payload": {
            "risk_alignment": "neutral",
            "source": "local_shadow_runner_payload",
        },
        "execution_guidance": {
            "pattern": "SLOW_CREEP",
            "entry_guidance": "Observe only; no executable order.",
            "tp_case": "shadow_tp_case",
            "sl_case": "shadow_sl_case",
            "exit_triggers": ["btc_relative_weakness"],
            "shadow_action": "WATCH",
            "confidence": 0.57,
        },
        "final_weight": 0.41,
        "note": "Local __main__ payload.",
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = run_shadow_payload(_local_test_payload())
    if not result.ok and not result.skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
