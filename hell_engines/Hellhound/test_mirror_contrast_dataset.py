from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import mirror_contrast_dataset as mirror_contrast_dataset_module
except ImportError:
    from . import mirror_contrast_dataset as mirror_contrast_dataset_module

build_contrast_matrix = mirror_contrast_dataset_module.build_contrast_matrix
run_mirror_contrast_dataset = mirror_contrast_dataset_module.run_mirror_contrast_dataset
select_failure_target = mirror_contrast_dataset_module.select_failure_target
select_success_target = mirror_contrast_dataset_module.select_success_target


class MirrorContrastDatasetTest(unittest.TestCase):
    def test_select_success_and_failure_targets(self) -> None:
        success = _candles(260)
        for index in range(150, 250):
            success[index]["close"] = 100.0 + (index - 150) * 0.2
            success[index]["high"] = success[index]["close"] + 0.1
        failure = _candles(260)
        for index in range(150, 166):
            failure[index]["close"] = 100.0 + (index - 150) * 0.3
            failure[index]["high"] = failure[index]["close"] + 0.2
        for index in range(166, 260):
            failure[index]["close"] = 104.0 - (index - 166) * 0.08
            failure[index]["low"] = failure[index]["close"] - 0.2

        self.assertIsNotNone(select_success_target("BELUSDT", success))
        self.assertIsNotNone(select_failure_target("BADUSDT", failure))

    def test_contrast_matrix_groups_success_and_failure(self) -> None:
        cases = [
            _case("success", "SOLUSDT", 0.02, 4, 2, 8.0),
            _case("failure", "DOGEUSDT", -0.01, 1, 5, -2.0),
        ]

        matrix = build_contrast_matrix(cases)

        self.assertEqual(matrix["summary"]["success"]["count"], 1)
        self.assertEqual(matrix["summary"]["failure"]["count"], 1)
        self.assertFalse(matrix["is_trade_command"])

    def test_run_writes_contrast_outputs_with_mocked_data(self) -> None:
        def fake_fetch(symbol: str, interval: str, *, limit: int):
            del limit
            if interval == "4h":
                return _candles(120, step=0.4)
            if symbol in {"SOLUSDT", "ETHUSDT"}:
                return _success_candles()
            return _failure_candles()

        with tempfile.TemporaryDirectory() as directory, patch(
            f"{mirror_contrast_dataset_module.__name__}.fetch_binance_klines",
            side_effect=fake_fetch,
        ):
            result = run_mirror_contrast_dataset(
                output_dir=Path(directory),
                symbols=("SOLUSDT", "ETHUSDT", "DOGEUSDT", "ADAUSDT"),
                success_count=2,
                failure_count=2,
            )

            self.assertEqual(result["success_count"], 2)
            self.assertEqual(result["failure_count"], 2)
            self.assertTrue((Path(directory) / "mirror_contrast_dataset.json").exists())
            self.assertTrue((Path(directory) / "mirror_feature_validation.json").exists())


def _case(case_type: str, symbol: str, score_slope: float, rsi_persistence: int, volume_delay: int, ret24: float) -> dict:
    return {
        "case_id": f"{case_type}-{symbol}",
        "case_type": case_type,
        "symbol": symbol,
        "analysis": {
            "metrics": {
                "score_slope_4": score_slope,
                "rsi_persistence": rsi_persistence,
                "volume_delay_after_score": volume_delay,
                "sequence": "hellhound_score -> rsi_15m -> volume_ratio_ma20",
                "ignition_return_24h": ret24,
            }
        },
    }


def _candles(count: int, *, step: float = 0.0) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        close = 100.0 + index * step
        rows.append(
            {
                "timestamp": f"2026-01-01T{index // 4 % 24:02d}:{(index % 4) * 15:02d}:00+00:00",
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 1000.0 + index,
            }
        )
    return rows


def _success_candles() -> list[dict[str, object]]:
    rows = _candles(260)
    for index in range(130, 260):
        rows[index]["close"] = 100.0 + (index - 130) * 0.2
        rows[index]["high"] = rows[index]["close"] + 0.2
    return rows


def _failure_candles() -> list[dict[str, object]]:
    rows = _candles(260)
    for index in range(130, 148):
        rows[index]["close"] = 100.0 + (index - 130) * 0.3
        rows[index]["high"] = rows[index]["close"] + 0.2
    for index in range(148, 260):
        rows[index]["close"] = 105.0 - (index - 148) * 0.08
        rows[index]["low"] = rows[index]["close"] - 0.2
    return rows


if __name__ == "__main__":
    unittest.main()
