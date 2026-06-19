from __future__ import annotations

import unittest
from datetime import datetime, timezone

import market_snapshot
import outcome_resolver
import outcome_tracker


class OutcomeTimeWindowTest(unittest.TestCase):
    def test_tracker_creates_target_time_per_window(self) -> None:
        outcomes = outcome_tracker.build_pending_outcomes(
            {
                "id": "11111111-1111-4111-8111-111111111111",
                "symbol": "ETHUSDT",
                "created_at": "2026-06-19T02:00:00+00:00",
            }
        )

        self.assertEqual([row["evaluation_window"] for row in outcomes], ["1h", "4h", "24h"])
        self.assertEqual(outcomes[0]["target_time"], "2026-06-19T03:00:00+00:00")
        self.assertEqual(outcomes[1]["target_time"], "2026-06-19T06:00:00+00:00")
        self.assertEqual(outcomes[2]["target_time"], "2026-06-20T02:00:00+00:00")

    def test_resolver_only_resolves_due_outcomes(self) -> None:
        now = datetime(2026, 6, 19, 3, 30, tzinfo=timezone.utc)
        outcomes = _pending_outcomes()

        resolved = outcome_resolver.resolve_pending_outcomes(outcomes, now=now)

        self.assertEqual([row["evaluation_window"] for row in resolved], ["1h"])
        self.assertEqual(resolved[0]["result"], "SUCCESS")

    def test_market_snapshot_only_updates_due_outcomes(self) -> None:
        now = datetime(2026, 6, 19, 3, 30, tzinfo=timezone.utc)
        prices = {
            "ETHUSDT": {
                "entry_price": 100.0,
                "current_prices": {
                    "1h": 102.0,
                    "4h": 104.0,
                    "24h": 124.0,
                },
                "snapshot_time": "2026-06-19T03:30:00+00:00",
            }
        }

        snapshots = market_snapshot.build_market_snapshots(
            _pending_outcomes(),
            prices,
            now=now,
        )

        self.assertEqual([row["evaluation_window"] for row in snapshots], ["1h"])
        self.assertEqual(snapshots[0]["current_price"], 102.0)


def _pending_outcomes() -> list[dict[str, object]]:
    signal = {
        "id": "11111111-1111-4111-8111-111111111111",
        "symbol": "ETHUSDT",
        "created_at": "2026-06-19T02:00:00+00:00",
        "shadow_action": "WATCH",
    }
    return [
        {
            "id": "22222222-2222-4222-8222-222222222221",
            "shadow_signal_id": signal["id"],
            "symbol": "ETHUSDT",
            "evaluation_window": "1h",
            "target_time": "2026-06-19T03:00:00+00:00",
            "outcome_return": 0.01,
            "result": "PENDING",
            "shadow_signal": signal,
        },
        {
            "id": "22222222-2222-4222-8222-222222222222",
            "shadow_signal_id": signal["id"],
            "symbol": "ETHUSDT",
            "evaluation_window": "4h",
            "target_time": "2026-06-19T06:00:00+00:00",
            "outcome_return": 0.04,
            "result": "PENDING",
            "shadow_signal": signal,
        },
        {
            "id": "22222222-2222-4222-8222-222222222223",
            "shadow_signal_id": signal["id"],
            "symbol": "ETHUSDT",
            "evaluation_window": "24h",
            "target_time": "2026-06-20T02:00:00+00:00",
            "outcome_return": 0.24,
            "result": "PENDING",
            "shadow_signal": signal,
        },
    ]


if __name__ == "__main__":
    unittest.main()
