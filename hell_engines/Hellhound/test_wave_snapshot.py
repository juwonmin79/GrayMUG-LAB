from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from wave_snapshot import _build_snapshot, build_wave_features, diff_snapshots, write_wave_log
except ImportError:
    from .wave_snapshot import _build_snapshot, build_wave_features, diff_snapshots, write_wave_log


class WaveSnapshotTest(unittest.TestCase):
    def test_build_snapshot_returns_state_vector(self) -> None:
        snapshot = _build_snapshot(
            "belusdt",
            "15m",
            "2026-06-01T00:00:00+00:00",
            candles=_candles(120, start=100.0, step=0.2),
            btc_candles_by_timeframe=_btc_frames(),
        )

        self.assertEqual(snapshot["symbol"], "BELUSDT")
        self.assertIn("price_vs_ma20", snapshot)
        self.assertIn("volume_ratio_ma5", snapshot)
        self.assertIn("rsi_15m", snapshot)
        self.assertIn("macd_hist_15m", snapshot)
        self.assertTrue(snapshot["is_daily_open"])
        self.assertTrue(snapshot["is_weekly_open"])
        self.assertTrue(snapshot["is_monthly_open"])
        self.assertFalse(snapshot["is_trade_command"])

    def test_diff_snapshots_and_delta_are_numeric_vectors(self) -> None:
        previous = {"price_vs_ma20": 0.1, "is_daily_open": False, "signal_hour": 1}
        current = {"price_vs_ma20": 0.15, "is_daily_open": True, "signal_hour": 3}

        diff = diff_snapshots(current, previous)

        self.assertEqual(diff["price_vs_ma20"], 0.05)
        self.assertEqual(diff["is_daily_open"], 1.0)
        self.assertEqual(diff["signal_hour"], 2.0)
        self.assertFalse(diff["is_trade_command"])

    def test_build_wave_features_creates_t2_t1_t0_diff_delta(self) -> None:
        row = build_wave_features(
            signal_id="signal-1",
            symbol="BELUSDT",
            timeframe="15m",
            timestamp_t2="2026-06-01T00:00:00+00:00",
            timestamp_t1="2026-06-01T00:15:00+00:00",
            timestamp_t0="2026-06-01T00:30:00+00:00",
            candles_t2=_candles(120, start=100.0, step=0.1),
            candles_t1=_candles(120, start=101.0, step=0.12),
            candles_t0=_candles(120, start=102.0, step=0.2),
            btc_candles_by_timeframe_t2=_btc_frames(),
            btc_candles_by_timeframe_t1=_btc_frames(),
            btc_candles_by_timeframe_t0=_btc_frames(),
        )

        self.assertEqual(row["signal_id"], "signal-1")
        self.assertIn("snapshot_t2", row)
        self.assertIn("diff_a", row)
        self.assertIn("diff_b", row)
        self.assertIn("delta", row)
        self.assertIsNone(row["outcome_mfe_6h"])
        self.assertFalse(row["is_trade_command"])

    def test_write_wave_log_append_only(self) -> None:
        row = build_wave_features(
            signal_id="signal-1",
            symbol="BELUSDT",
            timeframe="15m",
            timestamp_t2="2026-06-01T00:00:00+00:00",
            timestamp_t1="2026-06-01T00:15:00+00:00",
            timestamp_t0="2026-06-01T00:30:00+00:00",
            candles_t2=_candles(120),
            candles_t1=_candles(120, start=101.0),
            candles_t0=_candles(120, start=102.0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wave.jsonl"
            write_wave_log([row], output_path=path, append=True)
            write_wave_log([row], output_path=path, append=True)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[0]["is_trade_command"])


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
                "volume": 1000.0 + index * 4.0,
            }
        )
    return candles


def _btc_frames() -> dict[str, list[dict[str, float]]]:
    return {
        "15m": _candles(10, start=60000.0, step=5.0),
        "1h": _candles(10, start=60000.0, step=20.0),
        "4h": _candles(10, start=60000.0, step=120.0),
        "1d": _candles(10, start=60000.0, step=-30.0),
    }


if __name__ == "__main__":
    unittest.main()
