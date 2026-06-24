from __future__ import annotations

import unittest

try:
    from shadow_runner import _db_insert_signal, _payload_for_universe_row, normalize_oraclejp_payload
except ImportError:
    from .shadow_runner import _db_insert_signal, _payload_for_universe_row, normalize_oraclejp_payload


class ShadowRunnerLineageTest(unittest.TestCase):
    def test_normalized_shadow_signal_preserves_existing_signal_id(self) -> None:
        signal = normalize_oraclejp_payload(
            {
                "signal_id": "signal-1",
                "symbol": "BELUSDT",
                "source_time": "2026-01-01T00:00:00+00:00",
                "shadow_action": "WATCH",
            }
        )

        self.assertEqual(signal["signal_id"], "signal-1")
        self.assertEqual(signal["symbol"], "BELUSDT")
        self.assertFalse(signal["is_order_executed"])

    def test_normalized_shadow_signal_generates_signal_id_when_missing(self) -> None:
        signal = normalize_oraclejp_payload(
            {
                "symbol": "BELUSDT",
                "source_time": "2026-01-01T00:00:00+00:00",
                "pattern": "FIXTURE",
            }
        )

        self.assertTrue(signal["signal_id"])
        self.assertEqual(signal["symbol"], "BELUSDT")

    def test_db_insert_signal_maps_uuid_signal_id_to_existing_id_column(self) -> None:
        row = _db_insert_signal(
            {
                "signal_id": "33333333-3333-4333-8333-000000000001",
                "shadow_signal_id": "33333333-3333-4333-8333-000000000001",
                "symbol": "BELUSDT",
            }
        )

        self.assertEqual(row["id"], "33333333-3333-4333-8333-000000000001")
        self.assertNotIn("signal_id", row)
        self.assertNotIn("shadow_signal_id", row)

    def test_normalized_shadow_signal_persists_feature_capture_payload(self) -> None:
        signal = normalize_oraclejp_payload(
            {
                "signal_id": "signal-1",
                "symbol": "BELUSDT",
                "source_time": "2026-01-01T00:00:00+00:00",
                "hellhound_score": 0.72,
                "decision_source": "decision_api",
                "target_feed": {"btc_weather": 0.3, "volume_ratio_ma5": 1.8},
                "market_snapshot": {
                    "volume_ratio_ma20": 1.2,
                    "rsi_15m": 61.0,
                    "macd_hist_15m": 0.04,
                },
            }
        )

        self.assertEqual(signal["payload"]["hellhound_score"], 0.72)
        self.assertEqual(signal["payload"]["decision_source"], "decision_api")
        self.assertEqual(signal["payload"]["btc_weather"], 0.3)
        self.assertEqual(signal["payload"]["volume_ratio_ma5"], 1.8)
        self.assertEqual(signal["payload"]["volume_ratio_ma20"], 1.2)
        self.assertEqual(signal["payload"]["rsi_15m"], 61.0)
        self.assertEqual(signal["payload"]["macd_hist_15m"], 0.04)

    def test_universe_payload_generates_features_from_candles(self) -> None:
        payload = _payload_for_universe_row(
            {
                "symbol": "BELUSDT",
                "rank": 1,
                "rank_score": 100.0,
                "last_price": 112.0,
                "candles_15m": _candles(50, start=100.0, step=0.2),
                "btc_candles_by_timeframe": {
                    "4h": _candles(10, start=60000.0, step=120.0),
                },
            }
        )
        signal = normalize_oraclejp_payload(payload)

        self.assertIsNotNone(signal["payload"]["hellhound_score"])
        self.assertEqual(signal["payload"]["decision_source"], "decision_api")
        self.assertIsNotNone(signal["payload"]["btc_weather"])
        self.assertIsNotNone(signal["payload"]["volume_ratio_ma5"])
        self.assertIsNotNone(signal["payload"]["volume_ratio_ma20"])
        self.assertIsNotNone(signal["payload"]["rsi_15m"])
        self.assertIsNotNone(signal["payload"]["macd_hist_15m"])
        self.assertEqual(signal["target_feed"]["volume_ratio_ma5"], signal["payload"]["volume_ratio_ma5"])


def _candles(count: int, *, start: float = 100.0, step: float = 0.1) -> list[dict[str, float]]:
    candles = []
    for index in range(count):
        close = start + index * step
        candles.append(
            {
                "open": close - 0.05,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 1000.0 + index * 5.0,
            }
        )
    return candles


if __name__ == "__main__":
    unittest.main()
