from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from . import market_snapshot, outcome_resolver
except ImportError:
    import market_snapshot
    import outcome_resolver


OUTCOME_SCHEDULER_SCHEMA_VERSION = "hellhound_outcome_scheduler_v1"
LOGGER = logging.getLogger("hellhound.outcome_scheduler")


@dataclass(frozen=True)
class OutcomeSchedulerResult:
    outcome_scheduler_schema_version: str
    started_at: str
    stopped_at: str
    ok: bool
    snapshot_ok: bool
    resolver_ok: bool
    snapshots_updated: int
    outcomes_resolved: int
    snapshot_message: str
    resolver_message: str
    error: Optional[str]
    is_trade_command: bool = False


def run_outcome_scheduler_once() -> OutcomeSchedulerResult:
    """Run the due-outcome calculation path once. Fail-open: no exception escapes."""
    started_at = _now_utc()
    snapshot_ok = False
    resolver_ok = False
    snapshots_updated = 0
    outcomes_resolved = 0
    snapshot_message = "not run"
    resolver_message = "not run"
    error = None

    try:
        snapshot_result = market_snapshot.update_pending_market_snapshots()
        snapshot_ok = bool(snapshot_result.ok or snapshot_result.skipped)
        snapshots_updated = len(snapshot_result.snapshots or [])
        snapshot_message = snapshot_result.message
        if not snapshot_result.ok and not snapshot_result.skipped:
            error = snapshot_result.message
            LOGGER.error("Outcome scheduler market snapshot step failed: %s", snapshot_result.message)
    except Exception as exc:
        error = str(exc)
        snapshot_message = str(exc)
        LOGGER.exception("Outcome scheduler market snapshot step raised")

    try:
        resolver_result = outcome_resolver.resolve_pending_from_supabase()
        resolver_ok = bool(resolver_result.ok or resolver_result.skipped)
        outcomes_resolved = len(resolver_result.resolved or [])
        resolver_message = resolver_result.message
        if not resolver_result.ok and not resolver_result.skipped:
            error = error or resolver_result.message
            LOGGER.error("Outcome scheduler resolver step failed: %s", resolver_result.message)
    except Exception as exc:
        error = error or str(exc)
        resolver_message = str(exc)
        LOGGER.exception("Outcome scheduler resolver step raised")

    return OutcomeSchedulerResult(
        outcome_scheduler_schema_version=OUTCOME_SCHEDULER_SCHEMA_VERSION,
        started_at=started_at,
        stopped_at=_now_utc(),
        ok=snapshot_ok and resolver_ok,
        snapshot_ok=snapshot_ok,
        resolver_ok=resolver_ok,
        snapshots_updated=snapshots_updated,
        outcomes_resolved=outcomes_resolved,
        snapshot_message=snapshot_message,
        resolver_message=resolver_message,
        error=error,
        is_trade_command=False,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = run_outcome_scheduler_once()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
