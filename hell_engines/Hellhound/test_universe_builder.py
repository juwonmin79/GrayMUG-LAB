from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from universe_builder import (
        ExchangeConfig,
        _attach_feature_candles,
        _kline_to_candle,
    )
except ImportError:
    from .universe_builder import (
        ExchangeConfig,
        _attach_feature_candles,
        _kline_to_candle,
    )


class UniverseBuilderFeatureCandleTest(unittest.TestCase):
    def test_kline_to_candle_normalizes_binance_payload(self) -> None:
        candle = _kline_to_candle([1710000000000, "1", "2", "0.5", "1.5", "100"])

        self.assertEqual(candle["open_time"], 1710000000000)
        self.assertEqual(candle["open"], 1.0)
        self.assertEqual(candle["high"], 2.0)
        self.assertEqual(candle["low"], 0.5)
        self.assertEqual(candle["close"], 1.5)
        self.assertEqual(candle["volume"], 100.0)

    def test_attach_feature_candles_adds_symbol_and_btc_frames(self) -> None:
        def fake_loader(*, base_url: str, symbol: str, interval: str, limit: int):
            del base_url, limit
            if symbol == "BTCUSDT" and interval == "4h":
                return [_candle(60000.0)]
            return [_candle(100.0), _candle(101.0)]

        config = ExchangeConfig(
            exchange_name="binance",
            api_key_present=False,
            api_secret_present=False,
            testnet=False,
        )
        with patch(f"{_attach_feature_candles.__module__}._safe_load_klines", side_effect=fake_loader):
            rows = _attach_feature_candles([{"symbol": "BELUSDT", "rank": 1}], config)

        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["candles_15m"]), 2)
        self.assertEqual(len(rows[0]["btc_candles_by_timeframe"]["4h"]), 1)


def _candle(close: float) -> dict[str, float]:
    return {
        "open": close - 0.1,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "volume": 1000.0,
    }


if __name__ == "__main__":
    unittest.main()
