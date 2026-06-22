from __future__ import annotations

import os
import unittest

try:
    from library_interface import (
        detect_cluster_rows,
        evaluate_event_row,
        evaluate_real_feed_row,
        evaluate_signal_row,
        evaluate_snapshot_row,
    )
    from real_shadow_feed import mock_signal_rows
except ImportError:
    from .library_interface import (
        detect_cluster_rows,
        evaluate_event_row,
        evaluate_real_feed_row,
        evaluate_signal_row,
        evaluate_snapshot_row,
    )
    from .real_shadow_feed import mock_signal_rows


class LibraryInterfaceTest(unittest.TestCase):
    def test_signal_interface_returns_non_trade_shadow_decision(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        signal = mock_signal_rows(1)[0]

        result = evaluate_signal_row(signal, shadow_signals=[signal])

        self.assertEqual(result["input_type"], "signal")
        self.assertEqual(result["output_type"], "shadow_decision")
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertFalse(result["is_trade_command"])

    def test_event_interface_returns_non_trade_advisor_result(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        event = {
            "event_id": "event-1",
            "symbol": "BELUSDT",
            "first_seen_time": "2026-01-01T00:00:00+00:00",
            "last_seen_time": "2026-01-01T01:00:00+00:00",
            "event_state": "active",
        }

        result = evaluate_event_row(event)

        self.assertEqual(result["input_type"], "event")
        self.assertEqual(result["output_type"], "advisor_result")
        self.assertFalse(result["is_trade_command"])

    def test_snapshot_interface_returns_non_trade_advisor_result(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        snapshot = {
            "id": "snapshot-1",
            "symbol": "BELUSDT",
            "as_of_time": "2026-01-01T00:00:00+00:00",
        }

        result = evaluate_snapshot_row(snapshot)

        self.assertEqual(result["input_type"], "snapshot")
        self.assertEqual(result["output_type"], "advisor_result")
        self.assertFalse(result["is_trade_command"])

    def test_cluster_interface_returns_cluster_rows(self) -> None:
        result = detect_cluster_rows(mock_signal_rows(3))

        self.assertEqual(result["output_type"], "cluster")
        self.assertEqual(result["cluster_count"], 1)
        self.assertTrue(result["clusters"][0]["daily_open_cluster"])
        self.assertFalse(result["is_trade_command"])

    def test_real_feed_interface_returns_non_trade_decision(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        signal = mock_signal_rows(1)[0]

        result = evaluate_real_feed_row(signal)

        self.assertEqual(result["input_type"], "signal")
        self.assertEqual(result["output_type"], "shadow_decision")
        self.assertFalse(result["is_trade_command"])

    def test_interface_fail_safe_has_no_trade_command(self) -> None:
        result = evaluate_signal_row({})

        self.assertEqual(result["output_type"], "fail_safe")
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertFalse(result["is_trade_command"])


if __name__ == "__main__":
    unittest.main()
