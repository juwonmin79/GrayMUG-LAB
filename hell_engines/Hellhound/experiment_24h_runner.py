from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, Optional

import evaluation_loop
import market_snapshot
import outcome_resolver
import outcome_tracker
import shadow_runner


DEFAULT_INTERVAL_MINUTES = 15.0
DEFAULT_DURATION_HOURS = 24.0

LOGGER = logging.getLogger("hellhound.experiment_24h_runner")


@dataclass
class CycleSummary:
    cycle_number: int
    timestamp: str
    signals_generated: int = 0
    outcomes_created: int = 0
    snapshots_updated: int = 0
    outcomes_resolved: int = 0
    hypotheses_evaluated: int = 0
    ok: bool = True
    message: str = "cycle complete"
    scoreboard: Optional[list[Dict[str, object]]] = None


@dataclass
class ExperimentSummary:
    started_at: str
    stopped_at: Optional[str] = None
    total_cycles: int = 0
    total_signals: int = 0
    total_outcomes: int = 0
    total_snapshots: int = 0
    total_resolved_outcomes: int = 0
    final_scoreboard: Optional[list[Dict[str, object]]] = None
    interrupted: bool = False


def run_experiment() -> ExperimentSummary:
    interval_seconds = max(1.0, _env_float("HELLHOUND_EXPERIMENT_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES) * 60)
    duration_seconds = max(1.0, _env_float("HELLHOUND_EXPERIMENT_DURATION_HOURS", DEFAULT_DURATION_HOURS) * 3600)
    dry_run = _env_bool("HELLHOUND_EXPERIMENT_DRY_RUN", False)

    started_at = datetime.now(timezone.utc)
    deadline = started_at + timedelta(seconds=duration_seconds)
    summary = ExperimentSummary(started_at=started_at.isoformat())

    LOGGER.info(
        "Starting Hellhound 24h experiment interval=%ss duration=%ss dry_run=%s",
        interval_seconds,
        duration_seconds,
        dry_run,
    )
    print(
        json.dumps(
            {
                "event": "experiment_started",
                "started_at": summary.started_at,
                "interval_seconds": interval_seconds,
                "duration_seconds": duration_seconds,
                "dry_run": dry_run,
            },
            indent=2,
            sort_keys=True,
        )
    )

    try:
        cycle_number = 1
        while datetime.now(timezone.utc) < deadline:
            with _experiment_dry_run_env(dry_run):
                cycle = run_cycle(cycle_number)
            _accumulate(summary, cycle)
            _print_cycle(cycle)

            cycle_number += 1
            remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(interval_seconds, remaining))
    except KeyboardInterrupt:
        summary.interrupted = True
        LOGGER.warning("Hellhound experiment interrupted")
    finally:
        summary.stopped_at = datetime.now(timezone.utc).isoformat()
        _print_final(summary)

    return summary


def run_cycle(cycle_number: int) -> CycleSummary:
    cycle = CycleSummary(
        cycle_number=cycle_number,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    try:
        shadow_result = shadow_runner.run_shadow_payload(shadow_runner._local_test_payload())
        signals = shadow_result.signals or []
        cycle.signals_generated = len(signals)

        for index, signal in enumerate(signals, start=1):
            signal_with_id = dict(signal)
            signal_with_id.setdefault("id", signal.get("id") or f"dry-run-signal-{cycle_number}-{index}")
            outcome_result = outcome_tracker.attach_pending_outcomes(signal_with_id)
            cycle.outcomes_created += len(outcome_result.outcomes or [])
            if not outcome_result.ok and not outcome_result.skipped:
                cycle.ok = False
                cycle.message = outcome_result.message

        snapshot_result = market_snapshot.update_pending_market_snapshots()
        cycle.snapshots_updated = len(snapshot_result.snapshots or [])
        if not snapshot_result.ok and not snapshot_result.skipped:
            cycle.ok = False
            cycle.message = snapshot_result.message

        resolver_result = outcome_resolver.resolve_pending_from_supabase()
        cycle.outcomes_resolved = len(resolver_result.resolved or [])
        if not resolver_result.ok and not resolver_result.skipped:
            cycle.ok = False
            cycle.message = resolver_result.message

        evaluation_result = evaluation_loop.run_evaluation_loop()
        cycle.hypotheses_evaluated = len(evaluation_result.scoreboard or [])
        cycle.scoreboard = evaluation_result.scoreboard or []
        if not evaluation_result.ok and not evaluation_result.skipped:
            cycle.ok = False
            cycle.message = evaluation_result.message

    except Exception as exc:
        LOGGER.exception("Hellhound experiment cycle failed")
        cycle.ok = False
        cycle.message = str(exc)

    return cycle


def _accumulate(summary: ExperimentSummary, cycle: CycleSummary) -> None:
    summary.total_cycles += 1
    summary.total_signals += cycle.signals_generated
    summary.total_outcomes += cycle.outcomes_created
    summary.total_snapshots += cycle.snapshots_updated
    summary.total_resolved_outcomes += cycle.outcomes_resolved
    if cycle.scoreboard is not None:
        summary.final_scoreboard = cycle.scoreboard


def _print_cycle(cycle: CycleSummary) -> None:
    data = asdict(cycle)
    data.pop("scoreboard", None)
    print(json.dumps({"cycle_summary": data}, indent=2, sort_keys=True))


def _print_final(summary: ExperimentSummary) -> None:
    print(json.dumps({"final_summary": asdict(summary)}, indent=2, sort_keys=True))


@contextmanager
def _experiment_dry_run_env(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    keys = {
        "SHADOW_RUNNER_DRY_RUN": "1",
        "OUTCOME_TRACKER_DRY_RUN": "1",
        "MARKET_SNAPSHOT_DRY_RUN": "1",
        "OUTCOME_RESOLVER_DRY_RUN": "1",
        "EVALUATION_LOOP_DRY_RUN": "1",
    }
    previous = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.update(keys)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        LOGGER.warning("Invalid %s=%r; using default %s", name, raw, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _install_signal_handlers() -> None:
    # KeyboardInterrupt already handles Ctrl+C; installing SIGTERM keeps service stops tidy.
    def handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_sigterm)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _install_signal_handlers()
    summary = run_experiment()
    return 130 if summary.interrupted else 0


if __name__ == "__main__":
    sys.exit(main())
