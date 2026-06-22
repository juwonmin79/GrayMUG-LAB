from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

try:
    from accumulation_features import compute_accumulation_features
    import decision_api
except ImportError:
    from .accumulation_features import compute_accumulation_features
    from . import decision_api


class AccumulationFeaturesTest(unittest.TestCase):
    def test_long_base_volume_growth_scores_accumulation(self) -> None:
        features = compute_accumulation_features("BELUSDT", _bel_base_candles())

        self.assertEqual(features["structure_type"], "ACCUMULATION_BASE")
        self.assertGreater(features["accumulation_score"], 0.55)
        self.assertGreater(features["hellhound_score"], 0.45)

    def test_high_area_volume_decay_marks_distribution_risk(self) -> None:
        features = compute_accumulation_features("ACTUSDT", _distribution_candles())

        self.assertEqual(features["structure_type"], "DISTRIBUTION")
        self.assertGreater(features["distribution_risk"], 0.75)
        self.assertLess(features["accumulation_score"], 0.35)

    def test_repeated_spikes_raise_repeat_activity_score(self) -> None:
        features = compute_accumulation_features("NIGHTUSDT", _repeat_spike_candles())

        self.assertGreaterEqual(features["spike_count_30d"], 3)
        self.assertGreater(features["repeat_activity_score"], 0.45)

    def test_act_like_data_is_distribution_or_capitulation(self) -> None:
        distribution = compute_accumulation_features("ACTUSDT", _distribution_candles())
        capitulation = compute_accumulation_features("ACTUSDT", _capitulation_candles())

        self.assertIn(distribution["structure_type"], {"DISTRIBUTION", "CAPITULATION"})
        self.assertIn(capitulation["structure_type"], {"DISTRIBUTION", "CAPITULATION"})
        self.assertEqual(distribution["setup_type"], "ACT")

    def test_bel_like_data_is_accumulation_base(self) -> None:
        features = compute_accumulation_features("BELUSDT", _bel_base_candles())

        self.assertEqual(features["structure_type"], "ACCUMULATION_BASE")
        self.assertEqual(features["setup_type"], "BEL")

    def test_decision_api_returns_hellhound_score_v02(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        signals = _signals("BELUSDT", 40)
        historical = _bel_base_candles()
        result = decision_api.evaluate_symbol(
            "BELUSDT",
            shadow_signals=signals,
            candles_by_timeframe={"1d": historical[-30:]},
            historical_candles=historical,
        )

        self.assertGreater(result["hellhound_score"], 0.45)
        self.assertEqual(result["structure_type"], "ACCUMULATION_BASE")
        self.assertEqual(result["setup_type"], "BEL")


def _signals(symbol: str, count: int) -> list[dict[str, object]]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "id": f"22222222-2222-4222-8222-{index:012d}",
            "symbol": symbol,
            "source_time": (start + timedelta(days=index)).isoformat(),
            "hypothesis": {"name": f"hypothesis-{index % 2}"},
            "shadow_action": "WATCH",
            "pattern": "ACCUMULATION_BASE",
        }
        for index in range(count)
    ]


def _bel_base_candles() -> list[dict[str, object]]:
    candles = []
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for index in range(365):
        if index < 230:
            close = 3.0 - index * 0.006
        elif index < 335:
            close = 1.62 + ((index - 230) % 20) * 0.003
        else:
            close = 1.68 + (index - 335) * 0.008
        volume = 1000.0 + max(index - 320, 0) * 55.0
        if index in {340, 350, 360}:
            volume *= 2.4
            close *= 1.06
        candles.append(_candle(start, index, close, volume, range_pct=0.035))
    return candles


def _distribution_candles() -> list[dict[str, object]]:
    candles = []
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for index in range(365):
        if index < 320:
            close = 1.0 + index * 0.012
        else:
            close = 4.82 - (index - 320) * 0.006
        volume = 2200.0 - max(index - 320, 0) * 22.0
        candles.append(_candle(start, index, close, max(volume, 700.0), range_pct=0.045))
    return candles


def _repeat_spike_candles() -> list[dict[str, object]]:
    candles = _bel_base_candles()
    for index in (338, 346, 354, 362):
        close = float(candles[index]["close"]) * 1.1
        candles[index] = _candle(
            datetime(2025, 6, 1, tzinfo=timezone.utc),
            index,
            close,
            float(candles[index]["volume"]) * 2.8,
            range_pct=0.07,
        )
    return candles


def _capitulation_candles() -> list[dict[str, object]]:
    candles = []
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    for index in range(365):
        close = 5.0 - index * 0.008
        if index > 335:
            close -= (index - 335) * 0.035
        volume = 1200.0 + max(index - 335, 0) * 40.0
        candles.append(_candle(start, index, max(close, 0.35), volume, range_pct=0.06))
    return candles


def _candle(
    start: datetime,
    index: int,
    close: float,
    volume: float,
    *,
    range_pct: float,
) -> dict[str, object]:
    return {
        "time": (start + timedelta(days=index)).isoformat(),
        "open": close * 0.995,
        "high": close * (1 + range_pct / 2),
        "low": close * (1 - range_pct / 2),
        "close": close,
        "volume": volume,
    }


if __name__ == "__main__":
    unittest.main()
