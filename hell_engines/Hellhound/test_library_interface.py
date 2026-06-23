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
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        signal = mock_signal_rows(1)[0]

        result = evaluate_signal_row(signal, shadow_signals=[signal])

        self.assertEqual(result["input_type"], "signal")
        self.assertEqual(result["output_type"], "shadow_decision")
        self.assertEqual(result["decision_source"], "decision_api")
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

    def test_snapshot_candles_15m_uses_optional_decision_score(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        snapshot = {
            "id": "snapshot-1",
            "symbol": "BELUSDT",
            "as_of_time": "2026-01-01T00:00:00+00:00",
            "candles_15m": _snapshot_candles(50),
        }

        result = evaluate_snapshot_row(snapshot)
        decision = result["hellhound_decision"]

        self.assertEqual(decision["decision_source"], "decision_api")
        self.assertEqual(len(snapshot["candles_15m"]), 50)
        self.assertNotEqual(round(float(decision["hellhound_score"]), 3), 0.100)
        self.assertNotIn(
            "Pre-spike features are placeholders because no candle snapshot was provided.",
            decision["reasons"],
        )
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

    def test_disabled_optional_import_uses_strong_bel_signal_fallback(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        result = evaluate_signal_row(_production_signal("BELUSDT"), decision_enabled=False)

        self.assertEqual(result["structure_type"], "BEL")
        self.assertEqual(result["promotion_status"], "PROMOTE")
        self.assertEqual(result["decision_source"], "signal_fallback")
        self.assertGreater(result["hellhound_score"], 0.0)
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertFalse(result["is_trade_command"])

    def test_disabled_optional_import_logs_fallback_reason(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"

        with self.assertLogs("hellhound.library_interface", level="WARNING") as logs:
            result = evaluate_signal_row(_production_signal("BELUSDT"), decision_enabled=False)

        self.assertEqual(result["decision_source"], "signal_fallback")
        self.assertTrue(any("source_error=Hellhound optional decision import is disabled." in line for line in logs.output))
        self.assertTrue(any("Hellhound fallback used" in line for line in logs.output))

    def test_weak_signal_fallback_rejects_without_crashing(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        result = evaluate_signal_row(
            {
                "symbol": "WEAKUSDT",
                "rsi": 33,
                "volume_ratio": 0.2,
                "rs_rising": False,
                "passes_entry": False,
                "is_whale": False,
                "reasons": ["weak volume", "risk elevated"],
            },
            decision_enabled=False,
        )

        self.assertEqual(result["promotion_status"], "REJECT")
        self.assertLess(result["hellhound_score"], 0.35)
        self.assertFalse(result["is_trade_command"])

    def test_high_rsi_or_candle_tail_fallback_is_act(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        high_rsi = evaluate_signal_row(_production_signal("ACTUSDT", rsi=74, reasons=[]), decision_enabled=False)
        candle_tail = evaluate_signal_row(
            _production_signal("TAILUSDT", rsi=55, reasons=["candle_tail detected"]),
            decision_enabled=False,
        )

        self.assertEqual(high_rsi["structure_type"], "ACT")
        self.assertEqual(candle_tail["structure_type"], "ACT")
        self.assertFalse(high_rsi["is_trade_command"])
        self.assertFalse(candle_tail["is_trade_command"])

    def test_passes_entry_increases_fallback_score(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        base = _production_signal("BASEUSDT", passes_entry=False, is_whale=False)
        entry = _production_signal("ENTRYUSDT", passes_entry=True, is_whale=False)

        base_result = evaluate_signal_row(base, decision_enabled=False)
        entry_result = evaluate_signal_row(entry, decision_enabled=False)

        self.assertGreater(entry_result["hellhound_score"], base_result["hellhound_score"])
        self.assertFalse(entry_result["is_trade_command"])

    def test_malformed_signal_fields_are_fail_safe_non_trade(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "false"
        result = evaluate_signal_row(
            {
                "symbol": "BADUSDT",
                "rsi": "not-a-number",
                "volume_ratio": None,
                "rs_rising": "no",
                "passes_entry": "bad",
                "reasons": "weak data",
            },
            decision_enabled=False,
        )

        self.assertEqual(result["structure_type"], "UNCLASSIFIED")
        self.assertEqual(result["promotion_status"], "REJECT")
        self.assertEqual(result["entry_bias"], "neutral")
        self.assertFalse(result["is_trade_command"])


def _production_signal(
    symbol: str,
    *,
    rsi: float = 58,
    volume_ratio: float = 2.8,
    rs_rising: bool = True,
    passes_entry: bool = True,
    is_whale: bool = False,
    reasons: list[str] | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "price": 1.23,
        "rsi": rsi,
        "volume_ratio": volume_ratio,
        "rs_value": 1.08,
        "rs_rising": rs_rising,
        "fng": 55,
        "passes_entry": passes_entry,
        "is_whale": is_whale,
        "reasons": [] if reasons is None else reasons,
        "spike_type": "volume",
        "volume_spike": True,
        "taker_buy_ratio": 0.64,
    }


def _snapshot_candles(count: int) -> list[dict[str, float]]:
    candles = []
    price = 1.0
    for index in range(count):
        price += 0.001 + (0.0005 if index % 8 == 0 else 0.0)
        candles.append(
            {
                "open": price,
                "high": price * (1.006 + (0.001 if index > count - 5 else 0.0)),
                "low": price * 0.997,
                "close": price * (1.002 + (0.002 if index > count - 4 else 0.0)),
                "volume": 900 + index * 18 + (180 if index > count - 4 else 0),
                "btc_close": 50000 + index * 6,
            }
        )
    return candles


if __name__ == "__main__":
    unittest.main()
