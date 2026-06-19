from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
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
OUTCOME_RESULTS = {"PENDING", "SUCCESS", "FAIL", "INCONCLUSIVE"}
DEFAULT_THRESHOLDS = {
    "WATCH": {"success_gt": 0.0},
    "AVOID": {"success_lt": 0.0},
}
LOCAL_TEST_OUTCOMES_PATH = (
    Path(__file__).resolve().parent / "test_data" / "pending_outcomes_to_resolve.json"
)

LOGGER = logging.getLogger("hellhound.outcome_resolver")


@dataclass(frozen=True)
class OutcomeResolverResult:
    ok: bool
    dry_run: bool
    updated: bool
    skipped: bool
    message: str
    resolved: list[Dict[str, Any]]


class OutcomeResolverError(RuntimeError):
    pass


def resolve_pending_outcomes(
    pending_outcomes: list[Mapping[str, Any]],
    thresholds: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> list[Dict[str, Any]]:
    active_thresholds = _merge_thresholds(thresholds or _thresholds_from_env())
    return [
        _resolve_outcome(outcome, active_thresholds)
        for outcome in pending_outcomes
        if outcome.get("result") == "PENDING"
    ]


def resolve_pending_from_supabase() -> OutcomeResolverResult:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        LOGGER.warning("Supabase credentials missing; outcome resolve skipped")
        return OutcomeResolverResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=True,
            message="missing Supabase environment; skipped outcome resolve",
            resolved=[],
        )

    try:
        pending = _load_pending_outcomes(
            supabase_url=supabase_url, supabase_key=supabase_key
        )
    except OutcomeResolverError as exc:
        LOGGER.error("Pending outcome load failed: %s", exc)
        return OutcomeResolverResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=False,
            message=str(exc),
            resolved=[],
        )

    if not pending:
        LOGGER.info("No pending outcomes found")
        return OutcomeResolverResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=True,
            message="no pending outcomes",
            resolved=[],
        )

    resolved = resolve_pending_outcomes(pending)
    if _dry_run_enabled():
        LOGGER.info("Dry-run enabled; resolved outcomes not updated")
        print(json.dumps(resolved, indent=2, sort_keys=True))
        return OutcomeResolverResult(
            ok=True,
            dry_run=True,
            updated=False,
            skipped=False,
            message=f"dry-run resolved {len(resolved)} outcomes",
            resolved=resolved,
        )

    try:
        _update_resolved_outcomes(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            resolved=resolved,
        )
    except OutcomeResolverError as exc:
        LOGGER.error("Outcome resolve update failed: %s", exc)
        return OutcomeResolverResult(
            ok=False,
            dry_run=False,
            updated=False,
            skipped=False,
            message=str(exc),
            resolved=resolved,
        )

    LOGGER.info("Updated %s Hellhound outcomes", len(resolved))
    return OutcomeResolverResult(
        ok=True,
        dry_run=False,
        updated=True,
        skipped=False,
        message=f"updated {len(resolved)} outcomes",
        resolved=resolved,
    )


def _resolve_outcome(
    outcome: Mapping[str, Any],
    thresholds: Mapping[str, Mapping[str, float]],
) -> Dict[str, Any]:
    shadow_action = _shadow_action_for_outcome(outcome)
    outcome_return = _float_or_none(outcome.get("outcome_return"))

    if outcome_return is None:
        result = "INCONCLUSIVE"
    elif shadow_action == "WATCH":
        result = (
            "SUCCESS"
            if outcome_return > thresholds["WATCH"]["success_gt"]
            else "FAIL"
        )
    elif shadow_action == "AVOID":
        result = (
            "SUCCESS"
            if outcome_return < thresholds["AVOID"]["success_lt"]
            else "FAIL"
        )
    elif shadow_action == "WAIT_CONFIRMATION":
        result = "INCONCLUSIVE"
    else:
        result = "INCONCLUSIVE"

    return {
        "id": outcome.get("id"),
        "shadow_signal_id": outcome.get("shadow_signal_id"),
        "symbol": outcome.get("symbol"),
        "evaluation_window": outcome.get("evaluation_window"),
        "outcome_return": outcome_return,
        "shadow_action": shadow_action,
        "result": result,
    }


def _load_pending_outcomes(
    *, supabase_url: str, supabase_key: str
) -> list[Dict[str, Any]]:
    outcome_fields = "id,shadow_signal_id,symbol,evaluation_window,outcome_return,result"
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
        raise OutcomeResolverError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list):
        raise OutcomeResolverError("Supabase pending outcomes response was not a list")

    signal_cache: Dict[str, Dict[str, Any]] = {}
    pending: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        resolved_row = dict(row)
        signal_id = resolved_row.get("shadow_signal_id")
        if signal_id:
            if signal_id not in signal_cache:
                signal_cache[str(signal_id)] = _load_shadow_signal(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    shadow_signal_id=str(signal_id),
                )
            resolved_row["shadow_signal"] = signal_cache[str(signal_id)]
        pending.append(resolved_row)
    return pending


def _load_shadow_signal(
    *, supabase_url: str, supabase_key: str, shadow_signal_id: str
) -> Dict[str, Any]:
    signal_filter = parse.quote(f"eq.{shadow_signal_id}", safe="")
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
        f"?select=id,symbol,shadow_action,pattern&id={signal_filter}&limit=1"
    )
    status, rows = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="GET",
    )
    if status < 200 or status >= 300:
        raise OutcomeResolverError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list) or not rows:
        return {}
    signal = rows[0]
    return dict(signal) if isinstance(signal, Mapping) else {}


def _update_resolved_outcomes(
    *, supabase_url: str, supabase_key: str, resolved: list[Mapping[str, Any]]
) -> None:
    for outcome in resolved:
        outcome_id = outcome.get("id")
        result = outcome.get("result")
        if not outcome_id:
            raise OutcomeResolverError("resolved outcome is missing id")
        if result not in OUTCOME_RESULTS or result == "PENDING":
            raise OutcomeResolverError(f"invalid resolved outcome result {result}")
        outcome_filter = parse.quote(f"eq.{outcome_id}", safe="")
        endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}?id={outcome_filter}"
        status, _ = _supabase_json(
            endpoint=endpoint,
            supabase_key=supabase_key,
            method="PATCH",
            body={"result": result},
            prefer="return=minimal",
        )
        if status < 200 or status >= 300:
            raise OutcomeResolverError(f"unexpected Supabase status {status}")


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
        raise OutcomeResolverError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise OutcomeResolverError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise OutcomeResolverError("Supabase outcome resolver timed out") from exc
    except json.JSONDecodeError as exc:
        raise OutcomeResolverError("Supabase response was not JSON") from exc


def _shadow_action_for_outcome(outcome: Mapping[str, Any]) -> str:
    shadow_signal = outcome.get("shadow_signal")
    if isinstance(shadow_signal, Mapping):
        action = shadow_signal.get("shadow_action")
        if action:
            return str(action).upper()
    action = outcome.get("shadow_action")
    if action:
        return str(action).upper()
    return "WAIT_CONFIRMATION"


def _merge_thresholds(
    thresholds: Optional[Mapping[str, Mapping[str, float]]]
) -> Dict[str, Dict[str, float]]:
    merged = {
        action: dict(config)
        for action, config in DEFAULT_THRESHOLDS.items()
    }
    if thresholds:
        for action, config in thresholds.items():
            if isinstance(config, Mapping):
                merged.setdefault(str(action).upper(), {}).update(
                    {
                        str(key): float(value)
                        for key, value in config.items()
                        if _float_or_none(value) is not None
                    }
                )
    return merged


def _thresholds_from_env() -> Dict[str, Dict[str, float]]:
    raw = os.environ.get("OUTCOME_RESOLVER_THRESHOLDS")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.warning("OUTCOME_RESOLVER_THRESHOLDS is not valid JSON; defaults used")
        return {}
    return value if isinstance(value, dict) else {}


def _load_local_pending_outcomes() -> list[Dict[str, Any]]:
    with LOCAL_TEST_OUTCOMES_PATH.open("r", encoding="utf-8") as file:
        outcomes = json.load(file)
    if not isinstance(outcomes, list):
        raise ValueError("local pending outcomes must be a JSON list")
    return [dict(outcome) for outcome in outcomes if isinstance(outcome, Mapping)]


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dry_run_enabled() -> bool:
    raw = os.environ.get("OUTCOME_RESOLVER_DRY_RUN", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _local_mode_enabled() -> bool:
    raw = os.environ.get("OUTCOME_RESOLVER_LOCAL", "")
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
            resolved = resolve_pending_outcomes(_load_local_pending_outcomes())
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.error("Local resolver test data load failed: %s", exc)
            return 1
        print(json.dumps(resolved, indent=2, sort_keys=True))
        return 0

    result = resolve_pending_from_supabase()
    if not result.ok and not result.skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
