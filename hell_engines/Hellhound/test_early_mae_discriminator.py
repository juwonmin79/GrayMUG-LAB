from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import early_mae_discriminator as early_mae
except ImportError:
    from . import early_mae_discriminator as early_mae


class EarlyMaeDiscriminatorTest(unittest.TestCase):
    def test_recovery_ratio_and_velocity(self) -> None:
        self.assertEqual(early_mae.recovery_ratio_value(-2.0, 6.0), 3.0)
        self.assertEqual(early_mae.drawdown_velocity(-2.0, 2.0), -1.0)
        self.assertEqual(early_mae.drawdown_velocity(-2.0, 0.0), -8.0)

    def test_compute_campaign_physics_from_replay_rows(self) -> None:
        campaign = _campaign("SUCCESS", "case-1")
        rows = _rows("SOLUSDT")

        physics = early_mae.compute_campaign_physics(campaign, rows)

        self.assertEqual(physics["early_mae"], -3.0)
        self.assertEqual(physics["peak_mfe"], 8.0)
        self.assertEqual(physics["time_to_early_mae"], 1.0)
        self.assertEqual(physics["time_to_peak_mfe"], 2.0)
        self.assertEqual(physics["recovery_time"], 1.0)
        self.assertEqual(physics["recovery_ratio"], 2.666667)

    def test_run_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign_dataset = base / "campaign_replay_dataset.json"
            replay_expansion = base / "replay_expansion_report.json"
            validation = base / "mirror_candidate_validation.json"
            contrast = base / "mirror_contrast_dataset.json"
            btc = base / "btc_replay_dataset.jsonl"
            campaigns = []
            cases = []
            for index in range(10):
                success_id = f"success-{index}"
                failure_id = f"failure-{index}"
                campaigns.append(_campaign("SUCCESS", success_id))
                campaigns.append(_campaign("FAILURE", failure_id))
                cases.append({"case_id": success_id, "rows": _rows("SOLUSDT", mae=-2.0, mfe=8.0)})
                cases.append({"case_id": failure_id, "rows": _rows("ARBUSDT", mae=-8.0, mfe=3.0)})
            campaign_dataset.write_text(
                json.dumps(
                    {
                        "campaign_replay_dataset_schema_version": "campaign_replay_dataset_v1",
                        "success_campaign_count": 10,
                        "failure_campaign_count": 10,
                        "campaigns": campaigns,
                    }
                ),
                encoding="utf-8",
            )
            replay_expansion.write_text(json.dumps({"replay_expansion_report_schema_version": "replay_expansion_report_v1"}), encoding="utf-8")
            validation.write_text(json.dumps({"mirror_candidate_validation_schema_version": "mirror_candidate_validation_v1"}), encoding="utf-8")
            contrast.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            btc.write_text("", encoding="utf-8")

            result = early_mae.run_early_mae_discriminator(
                output_dir=base,
                campaign_dataset_path=campaign_dataset,
                replay_expansion_path=replay_expansion,
                validation_path=validation,
                contrast_dataset_path=contrast,
                btc_replay_dataset_path=btc,
            )

            self.assertEqual(result["success_count"], 10)
            self.assertEqual(result["failure_count"], 10)
            self.assertTrue((base / "early_mae_discriminator.json").exists())
            self.assertTrue((base / "early_mae_statistics.json").exists())
            self.assertTrue((base / "early_mae_candidate_report.json").exists())
            self.assertTrue((base / "early_mae_confidence.json").exists())
            self.assertTrue((base / "campaign_physics_summary.json").exists())


def _campaign(outcome: str, source_case_id: str) -> dict:
    return {
        "campaign_id": f"campaign-{source_case_id}",
        "symbol": "SOLUSDT" if outcome == "SUCCESS" else "ARBUSDT",
        "outcome": outcome,
        "campaign_type": f"{outcome}_CAMPAIGN",
        "source_case_id": source_case_id,
        "source_sample_id": source_case_id,
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-01T02:00:00+00:00",
        "replay": {"ignition_time": "2026-01-01T01:00:00+00:00"},
        "metrics": {"campaign_duration": 2.0, "early_mae": -3.0, "peak_mfe": 8.0},
        "is_trade_command": False,
    }


def _rows(symbol: str, *, mae: float = -3.0, mfe: float = 8.0) -> list[dict[str, object]]:
    return [
        {"timestamp": "2026-01-01T00:00:00+00:00", "symbol": symbol, "mae_pct": -1.0, "mfe_pct": 1.0, "is_trade_command": False},
        {"timestamp": "2026-01-01T01:00:00+00:00", "symbol": symbol, "mae_pct": mae, "mfe_pct": 2.0, "is_trade_command": False},
        {"timestamp": "2026-01-01T02:00:00+00:00", "symbol": symbol, "mae_pct": -1.5, "mfe_pct": mfe, "is_trade_command": False},
    ]


if __name__ == "__main__":
    unittest.main()
