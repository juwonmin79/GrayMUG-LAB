from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_candidate_validation as validation
except ImportError:
    from . import mirror_candidate_validation as validation


class MirrorCandidateValidationTest(unittest.TestCase):
    def test_volume_delay_state(self) -> None:
        self.assertEqual(validation.volume_delay_state(2), "Delay")
        self.assertEqual(validation.volume_delay_state(0), "Overlap")
        self.assertEqual(validation.volume_delay_state(None), "Missing")
        self.assertEqual(validation.volume_delay_state(-1), "Volume Leads")

    def test_statistics_include_required_candidates(self) -> None:
        samples = [
            _sample("success", "SOLUSDT", 0.03, 5, 1),
            _sample("success", "BTCUSDT", 0.02, 4, 0),
            _sample("failure", "ARBUSDT", -0.01, 2, -1),
            _sample("failure", "WLDUSDT", -0.02, 1, -2),
        ]

        stats = validation.build_candidate_statistics(samples)
        stability = validation.build_candidate_stability(stats)
        ranking = validation.build_discriminator_ranking(stability, stats)

        self.assertEqual([row["candidate"] for row in stats["candidates"]], list(validation.CANDIDATES))
        self.assertEqual(len(ranking["ranking"]), 3)
        self.assertFalse(ranking["is_trade_command"])

    def test_run_writes_deliverables_from_existing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            contrast = base / "mirror_contrast_dataset.json"
            btc_dataset = base / "btc_replay_dataset.jsonl"
            btc_report = base / "btc_replay_report.json"
            contrast.write_text(json.dumps({"cases": _contrast_cases()}), encoding="utf-8")
            btc_rows = _rows("BTCUSDT", "success", 96, ret24=1.5)
            btc_dataset.write_text("".join(json.dumps(row) + "\n" for row in btc_rows), encoding="utf-8")
            btc_report.write_text(
                json.dumps({"target": {"symbol": "BTCUSDT", "case_type": "success", "ignition_time": btc_rows[48]["timestamp"]}}),
                encoding="utf-8",
            )

            result = validation.run_mirror_candidate_validation(
                output_dir=base,
                contrast_dataset_path=contrast,
                btc_replay_dataset_path=btc_dataset,
                btc_replay_report_path=btc_report,
            )

            self.assertGreaterEqual(result["success_count"], 10)
            self.assertGreaterEqual(result["failure_count"], 10)
            self.assertTrue((base / "mirror_candidate_validation.json").exists())
            self.assertTrue((base / "mirror_candidate_statistics.json").exists())
            self.assertTrue((base / "mirror_discriminator_ranking.json").exists())
            self.assertTrue((base / "mirror_candidate_stability.json").exists())
            self.assertTrue((base / "replay_expansion_report.json").exists())


def _sample(case_type: str, symbol: str, slope: float, rsi: int, delay: int) -> dict:
    return {
        "case_type": case_type,
        "symbol": symbol,
        "candidate_metrics": {
            "score_slope": {"primary_value": slope},
            "rsi_persistence": {"primary_value": rsi},
            "volume_delay": {"primary_value": delay},
        },
    }


def _contrast_cases() -> list[dict]:
    return [
        {
            "case_id": "success-sol",
            "case_type": "success",
            "symbol": "SOLUSDT",
            "target": {"symbol": "SOLUSDT", "case_type": "success"},
            "rows": _rows("SOLUSDT", "success", 110, ret24=5.0),
        },
        {
            "case_id": "success-wld",
            "case_type": "success",
            "symbol": "WLDUSDT",
            "target": {"symbol": "WLDUSDT", "case_type": "success"},
            "rows": _rows("WLDUSDT", "success", 110, ret24=6.0),
        },
        {
            "case_id": "failure-arb",
            "case_type": "failure",
            "symbol": "ARBUSDT",
            "target": {"symbol": "ARBUSDT", "case_type": "failure"},
            "rows": _rows("ARBUSDT", "failure", 120, ret24=-3.0),
        },
        {
            "case_id": "failure-wld",
            "case_type": "failure",
            "symbol": "WLDUSDT",
            "target": {"symbol": "WLDUSDT", "case_type": "failure"},
            "rows": _rows("WLDUSDT", "failure", 120, ret24=-4.0),
        },
    ]


def _rows(symbol: str, case_type: str, count: int, *, ret24: float) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        close = 100.0 + index * (0.1 if case_type == "success" else -0.04)
        rows.append(
            {
                "timestamp": f"2026-01-{1 + index // 96:02d}T{index // 4 % 24:02d}:{(index % 4) * 15:02d}:00+00:00",
                "symbol": symbol,
                "case_type": case_type,
                "close": close,
                "hellhound_score": 0.2 + (index % 8) * (0.01 if case_type == "success" else -0.004),
                "rsi_15m": 35 + (index % 10) * (1 if case_type == "success" else -1),
                "volume_ratio_ma20": 1.0 + (index % 6) * 0.2,
                "return_4h": 2.0 if case_type == "failure" else 1.5,
                "return_24h": ret24,
                "mfe_pct": 6.0 if case_type == "success" else 2.0,
                "mae_pct": -0.5 if case_type == "success" else -6.0,
                "is_trade_command": False,
            }
        )
    return rows


if __name__ == "__main__":
    unittest.main()
