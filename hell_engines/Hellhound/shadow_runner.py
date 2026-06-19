from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional
from urllib import error, request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

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
        "is_order_executed": False,
        "is_shadow": True,
        "note": " ".join(note_parts),
    }
    return _drop_none(signal)


def run_shadow_payload(payload: Mapping[str, Any]) -> ShadowRunnerResult:
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
        signals = [
            normalize_oraclejp_payload(_payload_for_hypothesis(payload, hypothesis))
            for hypothesis in hypotheses
        ]
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
            "Dry-run enabled; %s hypothesis shadow signals not inserted", len(signals)
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
        for signal in signals:
            _insert_shadow_signal(
                supabase_url=supabase_url, supabase_key=supabase_key, signal=signal
            )
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

    LOGGER.info("Inserted %s Hellhound hypothesis shadow signals", len(signals))
    return ShadowRunnerResult(
        ok=True,
        dry_run=False,
        inserted=True,
        skipped=False,
        message=f"inserted {len(signals)} hypothesis shadow signals",
        signal=signals[0] if signals else None,
        signals=signals,
    )


class ShadowInsertError(RuntimeError):
    pass


def _insert_shadow_signal(
    *, supabase_url: str, supabase_key: str, signal: Mapping[str, Any]
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
    body = json.dumps(signal).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise ShadowInsertError(f"unexpected Supabase status {response.status}")
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
    next_payload = dict(payload)
    next_payload.update(config)
    next_payload["hypothesis"] = hypothesis_payload
    next_payload["target_feed"] = _merge_json_object(
        config.get("target_feed") or payload.get("target_feed"),
        {"hypothesis": hypothesis_payload},
    )
    next_payload["execution_guidance"] = _merge_json_object(
        config.get("execution_guidance")
        or payload.get("execution_guidance")
        or payload.get("guidance"),
        {"hypothesis": hypothesis_payload},
    )
    return next_payload


def _merge_json_object(value: Any, addition: Mapping[str, Any]) -> Dict[str, Any]:
    merged = _as_mapping(value)
    merged.update(_json_ready(addition))
    return merged


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
