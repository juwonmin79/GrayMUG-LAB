from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib import error, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


OUTCOME_TABLE = "hellhound_outcomes"
EVALUATION_WINDOWS = ("1h", "4h", "24h")
OUTCOME_RESULTS = {"PENDING", "SUCCESS", "FAIL", "INCONCLUSIVE"}
LOCAL_TEST_SIGNAL_PATH = Path(__file__).resolve().parent / "test_data" / "slow_creep_shadow_signal.json"

LOGGER = logging.getLogger("hellhound.outcome_tracker")


@dataclass(frozen=True)
class OutcomeTrackerResult:
    ok: bool
    dry_run: bool
    inserted: bool
    skipped: bool
    message: str
    outcomes: list[Dict[str, Any]]


class OutcomeTrackerError(RuntimeError):
    pass


def build_pending_outcomes(shadow_signal: Mapping[str, Any]) -> list[Dict[str, Any]]:
    shadow_signal_id = (
        shadow_signal.get("id")
        or shadow_signal.get("shadow_signal_id")
        or shadow_signal.get("signal_id")
    )
    symbol = shadow_signal.get("symbol")
    if not shadow_signal_id:
        raise ValueError("shadow signal is missing id")
    if not symbol:
        raise ValueError("shadow signal is missing symbol")

    return [
        {
            "shadow_signal_id": str(shadow_signal_id),
            "symbol": str(symbol).upper(),
            "evaluation_window": window,
            "outcome_return": None,
            "result": "PENDING",
        }
        for window in EVALUATION_WINDOWS
    ]


def attach_pending_outcomes(shadow_signal: Mapping[str, Any]) -> OutcomeTrackerResult:
    try:
        outcomes = build_pending_outcomes(shadow_signal)
    except ValueError as exc:
        LOGGER.error("Outcome build failed: %s", exc)
        return OutcomeTrackerResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            inserted=False,
            skipped=True,
            message=str(exc),
            outcomes=[],
        )

    if _dry_run_enabled():
        LOGGER.info("Dry-run enabled; outcome records not inserted")
        print(json.dumps(outcomes, indent=2, sort_keys=True))
        return OutcomeTrackerResult(
            ok=True,
            dry_run=True,
            inserted=False,
            skipped=False,
            message="dry-run outcome records generated",
            outcomes=outcomes,
        )

    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        LOGGER.warning("Supabase credentials missing; outcome insert skipped")
        return OutcomeTrackerResult(
            ok=True,
            dry_run=False,
            inserted=False,
            skipped=True,
            message="missing Supabase environment; skipped outcome insert",
            outcomes=outcomes,
        )

    try:
        _insert_outcomes(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            outcomes=outcomes,
        )
    except OutcomeTrackerError as exc:
        LOGGER.error("Outcome insert failed: %s", exc)
        return OutcomeTrackerResult(
            ok=False,
            dry_run=False,
            inserted=False,
            skipped=False,
            message=str(exc),
            outcomes=outcomes,
        )

    LOGGER.info("Inserted %s Hellhound outcome records", len(outcomes))
    return OutcomeTrackerResult(
        ok=True,
        dry_run=False,
        inserted=True,
        skipped=False,
        message=f"inserted {len(outcomes)} outcome records",
        outcomes=outcomes,
    )


def _insert_outcomes(
    *, supabase_url: str, supabase_key: str, outcomes: list[Mapping[str, Any]]
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}"
    body = json.dumps(outcomes).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=ignore-duplicates",
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise OutcomeTrackerError(f"unexpected Supabase status {response.status}")
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise OutcomeTrackerError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise OutcomeTrackerError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise OutcomeTrackerError("Supabase outcome insert timed out") from exc


def _load_local_test_signal() -> Dict[str, Any]:
    with LOCAL_TEST_SIGNAL_PATH.open("r", encoding="utf-8") as file:
        signal = json.load(file)
    if not isinstance(signal, dict):
        raise ValueError("local test signal must be a JSON object")
    return signal


def _dry_run_enabled() -> bool:
    raw = os.environ.get("OUTCOME_TRACKER_DRY_RUN", os.environ.get("SHADOW_RUNNER_DRY_RUN", ""))
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
    try:
        signal = _load_local_test_signal()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("Local outcome test data load failed: %s", exc)
        return 1

    result = attach_pending_outcomes(signal)
    if not result.ok and not result.skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
