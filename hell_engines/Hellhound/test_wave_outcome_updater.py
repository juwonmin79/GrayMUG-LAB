from __future__ import annotations

import unittest

try:
    from wave_outcome_updater import create_wave_outcome_update, create_wave_outcome_updates
except ImportError:
    from .wave_outcome_updater import create_wave_outcome_update, create_wave_outcome_updates


class WaveOutcomeUpdaterTest(unittest.TestCase):
    def test_create_wave_outcome_update_fills_mfe_mae_windows(self) -> None:
        row = {"signal_id": "signal-1", "snapshot_t0": {}, "is_trade_command": False}

        updated = create_wave_outcome_update(
            row,
            entry_price=100.0,
            price_paths_by_window={
                "6h": _path([100.0, 105.0, 96.0, 110.0]),
                "24h": _path([100.0, 112.0, 98.0]),
                "72h": _path([100.0, 90.0, 130.0]),
            },
        )

        self.assertEqual(updated["outcome_mfe_6h"], 10.0)
        self.assertEqual(updated["outcome_mae_6h"], -4.0)
        self.assertEqual(updated["outcome_time_to_peak_6h"], 3.0)
        self.assertEqual(updated["outcome_mfe_72h"], 30.0)
        self.assertFalse(updated["is_trade_command"])

    def test_create_wave_outcome_updates_maps_by_signal_id(self) -> None:
        rows = [{"signal_id": "signal-1", "snapshot_t0": {}, "is_trade_command": False}]

        updates = create_wave_outcome_updates(
            rows,
            price_paths_by_signal_id={"signal-1": {"6h": _path([100.0, 103.0])}},
        )

        self.assertEqual(len(updates), 1)
        self.assertIsNone(updates[0]["outcome_mfe_6h"])
        self.assertFalse(updates[0]["is_trade_command"])


def _path(prices: list[float]) -> list[dict[str, float]]:
    return [{"hours_since_entry": float(index), "price": price} for index, price in enumerate(prices)]


if __name__ == "__main__":
    unittest.main()
