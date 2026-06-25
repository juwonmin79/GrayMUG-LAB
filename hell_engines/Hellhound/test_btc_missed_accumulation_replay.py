from __future__ import annotations

import unittest

try:
    from btc_missed_accumulation_replay import (
        classify_missed_reason,
        detectability_verdict,
        select_replay_target,
    )
except ImportError:
    from .btc_missed_accumulation_replay import (
        classify_missed_reason,
        detectability_verdict,
        select_replay_target,
    )


class BtcMissedAccumulationReplayTest(unittest.TestCase):
    def test_select_replay_target_uses_max_forward_return(self) -> None:
        candles = _candles(260)
        for index in range(160, 230):
            candles[index]["close"] = 100.0 + (index - 160) * 2.0
            candles[index]["high"] = candles[index]["close"] + 1.0
            candles[index]["low"] = candles[index]["close"] - 1.0

        target = select_replay_target(candles)

        self.assertEqual(target["symbol"], "BTCUSDT")
        self.assertLessEqual(target["accumulation_start_index"], target["ignition_index"])
        self.assertGreaterEqual(target["local_peak_index"], target["ignition_index"])
        self.assertGreater(target["ignition_return_24h"], 0)

    def test_missed_reason_classification(self) -> None:
        self.assertEqual(classify_missed_reason({"volume_ratio_ma5": None}), "C_FEATURE_MISSING")
        base = {
            "volume_ratio_ma5": 1.1,
            "volume_ratio_ma20": 1.0,
            "rsi_15m": 55,
            "macd_hist_15m": 0.1,
            "btc_weather": 0.0,
            "promotion_status": "WATCH",
        }
        self.assertEqual(classify_missed_reason({**base, "hellhound_score": 0.45}), "B_THRESHOLD_INSUFFICIENT")
        self.assertEqual(classify_missed_reason({**base, "hellhound_score": 0.2}), "E_NOT_DETECTABLE_CURRENT_PIPELINE")

    def test_detectability_verdict_now_when_promoted(self) -> None:
        rows = [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "promotion_status": "PROMOTE",
                "hellhound_score": 0.62,
                "volume_ratio_ma5": 1.1,
                "volume_ratio_ma20": 1.0,
                "rsi_15m": 55,
                "macd_hist_15m": 0.1,
                "btc_weather": 0.0,
            }
        ]
        target = {
            "accumulation_start": rows[0]["timestamp"],
            "ignition_time": rows[0]["timestamp"],
            "local_peak_time": rows[0]["timestamp"],
        }
        candidates = {"candidates": [{"lead_strength": 0.1}]}

        verdict = detectability_verdict(rows, target, candidates)

        self.assertEqual(verdict["detectability_verdict"], "DETECTABLE_NOW")


def _candles(count: int) -> list[dict[str, object]]:
    candles = []
    for index in range(count):
        close = 100.0
        candles.append(
            {
                "timestamp": f"2026-01-01T{index // 4 % 24:02d}:{(index % 4) * 15:02d}:00+00:00",
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000.0,
            }
        )
    return candles


if __name__ == "__main__":
    unittest.main()
