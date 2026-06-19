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
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

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
    try:
        signal = normalize_oraclejp_payload(payload)
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
        LOGGER.info("Dry-run enabled; shadow signal not inserted")
        print(json.dumps(signal, indent=2, sort_keys=True))
        return ShadowRunnerResult(
            ok=True,
            dry_run=True,
            inserted=False,
            skipped=False,
            message="dry-run signal generated",
            signal=signal,
        )

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "SUPABASE_ANON_KEY"
    )
    if not supabase_url or not supabase_key:
        LOGGER.warning(
            "Supabase credentials missing; shadow signal skipped without insert"
        )
        return ShadowRunnerResult(
            ok=True,
            dry_run=False,
            inserted=False,
            skipped=True,
            message="missing Supabase environment; skipped insert",
            signal=signal,
        )

    try:
        _insert_shadow_signal(supabase_url=supabase_url, supabase_key=supabase_key, signal=signal)
    except ShadowInsertError as exc:
        LOGGER.error("Supabase shadow signal insert failed: %s", exc)
        return ShadowRunnerResult(
            ok=False,
            dry_run=False,
            inserted=False,
            skipped=False,
            message=str(exc),
            signal=signal,
        )

    LOGGER.info("Inserted Hellhound shadow signal for %s", signal["symbol"])
    return ShadowRunnerResult(
        ok=True,
        dry_run=False,
        inserted=True,
        skipped=False,
        message="shadow signal inserted",
        signal=signal,
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
