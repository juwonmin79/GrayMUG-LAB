from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib import error, parse, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


OUTCOME_TABLE = "hellhound_outcomes"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
LOCAL_TEST_OUTCOMES_PATH = (
    Path(__file__).resolve().parent / "test_data" / "pending_outcomes_for_snapshot.json"
)
LOCAL_MARKET_PRICES_PATH = (
    Path(__file__).resolve().parent / "test_data" / "local_market_prices.json"
)

LOGGER = logging.getLogger("hellhound.market_snapshot")


@dataclass(frozen=True)
class MarketSnapshotResult:
    ok: bool
    dry_run: bool
    updated: bool
    skipped: bool
    message: str
    snapshots: list[Dict[str, Any]]


class MarketSnapshotError(RuntimeError):
    pass


def build_market_snapshots(
    pending_outcomes: list[Mapping[str, Any]],
    market_prices: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    snapshots = []
    for outcome in pending_outcomes:
        if outcome.get("result") != "PENDING":
            continue
        signal = _signal_for_outcome(outcome)
        symbol = str(signal.get("symbol") or outcome.get("symbol") or "").upper()
        evaluation_window = str(outcome.get("evaluation_window") or "")
        if not symbol or not evaluation_window:
            continue

        prices = _prices_for_window(market_prices, symbol, evaluation_window)
        if not prices:
            snapshots.append(_incomplete_snapshot(outcome, signal, symbol))
            continue

        entry_price = _float_or_none(prices.get("entry_price"))
        current_price = _float_or_none(prices.get("current_price"))
        if entry_price is None or current_price is None or entry_price == 0:
            snapshots.append(_incomplete_snapshot(outcome, signal, symbol))
            continue

        return_pct = (current_price - entry_price) / entry_price
        snapshots.append(
            {
                "id": outcome.get("id"),
                "shadow_signal_id": outcome.get("shadow_signal_id"),
                "symbol": symbol,
                "signal_time": signal.get("source_time") or signal.get("created_at"),
                "evaluation_window": evaluation_window,
                "entry_price": entry_price,
                "current_price": current_price,
                "return_pct": return_pct,
                "outcome_return": return_pct,
                "snapshot_time": prices.get("snapshot_time") or _now_utc(),
            }
        )
    return snapshots


def update_pending_market_snapshots() -> MarketSnapshotResult:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        LOGGER.warning("Supabase credentials missing; market snapshot update skipped")
        return MarketSnapshotResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=True,
            message="missing Supabase environment; skipped market snapshot update",
            snapshots=[],
        )

    try:
        pending = _load_pending_outcomes(
            supabase_url=supabase_url, supabase_key=supabase_key
        )
        market_prices = _load_market_prices()
        snapshots = build_market_snapshots(pending, market_prices)
    except (OSError, ValueError, json.JSONDecodeError, MarketSnapshotError) as exc:
        LOGGER.error("Market snapshot build failed: %s", exc)
        return MarketSnapshotResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=False,
            message=str(exc),
            snapshots=[],
        )

    if _dry_run_enabled():
        LOGGER.info("Dry-run enabled; market snapshots not updated")
        print(json.dumps(snapshots, indent=2, sort_keys=True))
        return MarketSnapshotResult(
            ok=True,
            dry_run=True,
            updated=False,
            skipped=False,
            message=f"dry-run generated {len(snapshots)} market snapshots",
            snapshots=snapshots,
        )

    try:
        _update_outcomes(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            snapshots=snapshots,
        )
    except MarketSnapshotError as exc:
        LOGGER.error("Market snapshot update failed: %s", exc)
        return MarketSnapshotResult(
            ok=False,
            dry_run=False,
            updated=False,
            skipped=False,
            message=str(exc),
            snapshots=snapshots,
        )

    LOGGER.info("Updated %s Hellhound outcome market snapshots", len(snapshots))
    return MarketSnapshotResult(
        ok=True,
        dry_run=False,
        updated=True,
        skipped=False,
        message=f"updated {len(snapshots)} market snapshots",
        snapshots=snapshots,
    )


def _load_pending_outcomes(
    *, supabase_url: str, supabase_key: str
) -> list[Dict[str, Any]]:
    outcome_fields = "id,shadow_signal_id,symbol,evaluation_window,result"
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}"
        f"?select={outcome_fields}&result=eq.PENDING"
    )
    status, rows = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="GET",
    )
    if status < 200 or status >= 300:
        raise MarketSnapshotError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list):
        raise MarketSnapshotError("Supabase pending outcomes response was not a list")

    signal_cache: Dict[str, Dict[str, Any]] = {}
    pending: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        outcome = dict(row)
        signal_id = outcome.get("shadow_signal_id")
        if signal_id:
            signal_id = str(signal_id)
            if signal_id not in signal_cache:
                signal_cache[signal_id] = _load_shadow_signal(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    shadow_signal_id=signal_id,
                )
            outcome["shadow_signal"] = signal_cache[signal_id]
        pending.append(outcome)
    return pending


def _load_shadow_signal(
    *, supabase_url: str, supabase_key: str, shadow_signal_id: str
) -> Dict[str, Any]:
    signal_filter = parse.quote(f"eq.{shadow_signal_id}", safe="")
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
        f"?select=id,symbol,source_time,created_at,pattern,shadow_action"
        f"&id={signal_filter}&limit=1"
    )
    status, rows = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="GET",
    )
    if status < 200 or status >= 300:
        raise MarketSnapshotError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list) or not rows:
        return {}
    signal = rows[0]
    return dict(signal) if isinstance(signal, Mapping) else {}


def _update_outcomes(
    *, supabase_url: str, supabase_key: str, snapshots: list[Mapping[str, Any]]
) -> None:
    for snapshot in snapshots:
        outcome_id = snapshot.get("id")
        if not outcome_id:
            raise MarketSnapshotError("market snapshot is missing outcome id")
        outcome_filter = parse.quote(f"eq.{outcome_id}", safe="")
        endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}?id={outcome_filter}"
        status, _ = _supabase_json(
            endpoint=endpoint,
            supabase_key=supabase_key,
            method="PATCH",
            body={
                "entry_price": snapshot.get("entry_price"),
                "current_price": snapshot.get("current_price"),
                "return_pct": snapshot.get("return_pct"),
                "outcome_return": snapshot.get("return_pct"),
                "snapshot_time": snapshot.get("snapshot_time"),
            },
            prefer="return=minimal",
        )
        if status < 200 or status >= 300:
            raise MarketSnapshotError(f"unexpected Supabase status {status}")


def _supabase_json(
    *,
    endpoint: str,
    supabase_key: str,
    method: str,
    body: Optional[Mapping[str, Any]] = None,
    prefer: Optional[str] = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = request.Request(endpoint, data=data, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=15) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise MarketSnapshotError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise MarketSnapshotError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise MarketSnapshotError("Supabase market snapshot timed out") from exc
    except json.JSONDecodeError as exc:
        raise MarketSnapshotError("Supabase response was not JSON") from exc


def _prices_for_window(
    market_prices: Mapping[str, Any], symbol: str, evaluation_window: str
) -> Dict[str, Any]:
    symbol_prices = market_prices.get(symbol)
    if not isinstance(symbol_prices, Mapping):
        return {}
    current_prices = symbol_prices.get("current_prices")
    if not isinstance(current_prices, Mapping):
        return {}
    return {
        "entry_price": symbol_prices.get("entry_price"),
        "current_price": current_prices.get(evaluation_window),
        "snapshot_time": symbol_prices.get("snapshot_time"),
    }


def _incomplete_snapshot(
    outcome: Mapping[str, Any], signal: Mapping[str, Any], symbol: str
) -> Dict[str, Any]:
    return {
        "id": outcome.get("id"),
        "shadow_signal_id": outcome.get("shadow_signal_id"),
        "symbol": symbol,
        "signal_time": signal.get("source_time") or signal.get("created_at"),
        "evaluation_window": outcome.get("evaluation_window"),
        "entry_price": None,
        "current_price": None,
        "return_pct": None,
        "outcome_return": None,
        "snapshot_time": _now_utc(),
    }


def _signal_for_outcome(outcome: Mapping[str, Any]) -> Dict[str, Any]:
    signal = outcome.get("shadow_signal")
    return dict(signal) if isinstance(signal, Mapping) else {}


def _load_local_pending_outcomes() -> list[Dict[str, Any]]:
    with LOCAL_TEST_OUTCOMES_PATH.open("r", encoding="utf-8") as file:
        outcomes = json.load(file)
    if not isinstance(outcomes, list):
        raise ValueError("local pending outcomes must be a JSON list")
    return [dict(outcome) for outcome in outcomes if isinstance(outcome, Mapping)]


def _load_market_prices() -> Dict[str, Any]:
    path = Path(os.environ.get("MARKET_SNAPSHOT_DATA_PATH", LOCAL_MARKET_PRICES_PATH))
    with path.open("r", encoding="utf-8") as file:
        prices = json.load(file)
    if not isinstance(prices, dict):
        raise ValueError("market snapshot data must be a JSON object")
    return prices


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dry_run_enabled() -> bool:
    raw = os.environ.get("MARKET_SNAPSHOT_DRY_RUN", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _local_mode_enabled() -> bool:
    raw = os.environ.get("MARKET_SNAPSHOT_LOCAL", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


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
    if _local_mode_enabled() or _dry_run_enabled():
        try:
            snapshots = build_market_snapshots(
                _load_local_pending_outcomes(),
                _load_market_prices(),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.error("Local market snapshot test data load failed: %s", exc)
            return 1
        print(json.dumps(snapshots, indent=2, sort_keys=True))
        return 0

    result = update_pending_market_snapshots()
    if not result.ok and not result.skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
