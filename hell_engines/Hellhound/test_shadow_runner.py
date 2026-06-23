from __future__ import annotations

import unittest

try:
    from shadow_runner import _db_insert_signal, normalize_oraclejp_payload
except ImportError:
    from .shadow_runner import _db_insert_signal, normalize_oraclejp_payload


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


if __name__ == "__main__":
    unittest.main()
