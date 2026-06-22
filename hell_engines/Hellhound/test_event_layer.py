from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

try:
    import decision_api
    from event_layer import build_events_from_signals, signal_dedupe_key, stable_event_id
except ImportError:
    from . import decision_api
    from .event_layer import build_events_from_signals, signal_dedupe_key, stable_event_id


class EventLayerTest(unittest.TestCase):
    def test_metusdt_many_signals_collapse_to_one_event(self) -> None:
        signals = _signals("METUSDT", count=84, start=datetime(2026, 6, 20, tzinfo=timezone.utc))

        result = build_events_from_signals(signals, max_gap_hours=24)

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0]["symbol"], "METUSDT")
        self.assertEqual(result.events[0]["observation_count"], 84)
        self.assertEqual(result.events[0]["event_state"], "extended_timeline")

    def test_event_id_is_stable(self) -> None:
        first_seen = "2026-06-20T00:00:00+00:00"

        self.assertEqual(
            stable_event_id("metusdt", first_seen),
            stable_event_id("METUSDT", first_seen),
        )

    def test_duplicate_signal_does_not_pollute_event_analysis(self) -> None:
        signal = _signals("METUSDT", count=1)[0]
        duplicate = dict(signal)
        duplicate["id"] = "duplicate-id"

        result = build_events_from_signals([signal, duplicate])

        self.assertEqual(result.duplicate_count, 1)
        self.assertEqual(result.events[0]["observation_count"], 1)
        self.assertEqual(signal_dedupe_key(signal), signal_dedupe_key(duplicate))

    def test_same_source_time_preserves_different_hypotheses_only(self) -> None:
        source_time = "2026-06-20T00:00:00+00:00"
        signals = [
            {
                "id": "11111111-1111-4111-8111-000000000001",
                "symbol": "METUSDT",
                "source_time": source_time,
                "hypothesis": {"name": "confirmation-wait"},
                "confidence": 0.49,
                "shadow_action": "WAIT_CONFIRMATION",
                "pattern": "CHAIN_ROTATION",
            },
            {
                "id": "11111111-1111-4111-8111-000000000002",
                "symbol": "METUSDT",
                "source_time": source_time,
                "hypothesis": {"name": "lead-line-watch"},
                "confidence": 0.57,
                "shadow_action": "WATCH",
                "pattern": "SLOW_CREEP",
            },
            {
                "id": "11111111-1111-4111-8111-000000000003",
                "symbol": "METUSDT",
                "source_time": source_time,
                "hypothesis": {"name": "lead-line-watch"},
                "confidence": 0.57,
                "shadow_action": "WATCH",
                "pattern": "SLOW_CREEP",
            },
        ]

        result = build_events_from_signals(signals)

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.duplicate_count, 1)
        self.assertEqual(result.events[0]["observation_count"], 2)
        self.assertEqual(
            result.events[0]["hypotheses"],
            ["confirmation-wait", "lead-line-watch"],
        )
        self.assertEqual(len(result.observations), 2)

    def test_evaluate_symbol_fail_safe_off(self) -> None:
        os.environ.pop("HELLHOUND_DECISION_ENABLED", None)

        result = decision_api.evaluate_symbol("METUSDT")

        self.assertEqual(result["entry_bias"], "neutral")
        self.assertEqual(result["confidence"], 0)
        self.assertIn("error", result)

    def test_evaluate_symbol_with_real_snapshot_scores_pre_spike(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        signals = _signals("METUSDT", count=84, start=datetime(2026, 6, 20, tzinfo=timezone.utc))
        candles = _met_pre_spike_candles()

        result = decision_api.evaluate_symbol(
            "METUSDT",
            shadow_signals=signals,
            candles_by_timeframe={
                "1m": candles,
                "15m": candles,
                "1h": candles,
                "4h": candles,
                "1d": candles,
                "1w": candles,
            },
        )

        self.assertGreater(result["pre_spike_score"], 0)
        self.assertEqual(result["mtf_snapshot"]["timeframes"]["15m"]["status"], "ready")
        self.assertEqual(result["mtf_snapshot"]["timeframes"]["15m"]["candle_count"], len(candles))
        self.assertIsNotNone(result["mtf_snapshot"]["timeframes"]["15m"]["last_close"])
        self.assertIsNotNone(result["mtf_snapshot"]["timeframes"]["15m"]["last_volume"])
        self.assertIsNotNone(result["mtf_snapshot"]["timeframes"]["15m"]["range_pct"])
        self.assertIsNotNone(result["mtf_snapshot"]["timeframes"]["15m"]["volume_ma_ratio"])
        self.assertIn(
            "volume_acceleration",
            result["mtf_snapshot"]["timeframes"]["15m"]["pre_spike_features"],
        )
        self.assertIn(
            "volatility_contraction",
            result["mtf_snapshot"]["timeframes"]["15m"]["pre_spike_features"],
        )


def _signals(
    symbol: str,
    *,
    count: int,
    start: datetime | None = None,
) -> list[dict[str, object]]:
    start = start or datetime(2026, 6, 20, tzinfo=timezone.utc)
    return [
        {
            "id": f"11111111-1111-4111-8111-{index:012d}",
            "symbol": symbol,
            "source_time": (start + timedelta(minutes=index * 10)).isoformat(),
            "hypothesis": {"name": f"hypothesis-{index % 3}"},
            "shadow_action": "WATCH",
            "pattern": "SLOW_CREEP",
        }
        for index in range(count)
    ]


def _met_pre_spike_candles() -> list[dict[str, object]]:
    candles = []
    start = datetime(2026, 6, 20, tzinfo=timezone.utc)
    for index in range(20):
        close = 1.0 + index * 0.0015
        range_width = 0.030 - min(index, 15) * 0.0014
        if index >= 17:
            close += (index - 16) * 0.01
        open_price = close * (0.996 if index < 17 else 0.982)
        volume = 100.0 + index * 3.0
        if index >= 14:
            volume += (index - 13) * 35.0
        candles.append(
            {
                "time": (start + timedelta(minutes=15 * index)).isoformat(),
                "open": open_price,
                "high": close * (1.0 + range_width / 2),
                "low": close * (1.0 - range_width / 2),
                "close": close,
                "volume": volume,
                "btc_close": 60000.0 + index * 3.0,
            }
        )
    return candles


if __name__ == "__main__":
    unittest.main()
