from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import patch

try:
    import outcome_scheduler as outcome_scheduler_module
    from outcome_scheduler import run_outcome_scheduler_once
except ImportError:
    from . import outcome_scheduler as outcome_scheduler_module
    from .outcome_scheduler import run_outcome_scheduler_once


@dataclass(frozen=True)
class _SnapshotResult:
    ok: bool
    skipped: bool
    message: str
    snapshots: list[dict[str, object]]


@dataclass(frozen=True)
class _ResolverResult:
    ok: bool
    skipped: bool
    message: str
    resolved: list[dict[str, object]]


class OutcomeSchedulerTest(unittest.TestCase):
    def test_scheduler_runs_snapshot_then_resolver(self) -> None:
        calls: list[str] = []

        def snapshot() -> _SnapshotResult:
            calls.append("snapshot")
            return _SnapshotResult(ok=True, skipped=False, message="snapshots updated", snapshots=[{}])

        def resolver() -> _ResolverResult:
            calls.append("resolver")
            return _ResolverResult(ok=True, skipped=False, message="outcomes resolved", resolved=[{}, {}])

        with patch.object(outcome_scheduler_module.market_snapshot, "update_pending_market_snapshots", snapshot), patch.object(
            outcome_scheduler_module.outcome_resolver, "resolve_pending_from_supabase", resolver
        ):
            result = run_outcome_scheduler_once()

        self.assertEqual(calls, ["snapshot", "resolver"])
        self.assertTrue(result.ok)
        self.assertEqual(result.snapshots_updated, 1)
        self.assertEqual(result.outcomes_resolved, 2)
        self.assertFalse(result.is_trade_command)

    def test_scheduler_fail_open_when_snapshot_raises(self) -> None:
        def snapshot() -> _SnapshotResult:
            raise RuntimeError("snapshot failed")

        def resolver() -> _ResolverResult:
            return _ResolverResult(ok=True, skipped=False, message="outcomes resolved", resolved=[])

        with patch.object(outcome_scheduler_module.market_snapshot, "update_pending_market_snapshots", snapshot), patch.object(
            outcome_scheduler_module.outcome_resolver, "resolve_pending_from_supabase", resolver
        ):
            result = run_outcome_scheduler_once()

        self.assertFalse(result.ok)
        self.assertFalse(result.snapshot_ok)
        self.assertTrue(result.resolver_ok)
        self.assertEqual(result.error, "snapshot failed")
        self.assertFalse(result.is_trade_command)


if __name__ == "__main__":
    unittest.main()
