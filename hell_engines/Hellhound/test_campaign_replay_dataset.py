from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import campaign_replay_dataset as campaign
except ImportError:
    from . import campaign_replay_dataset as campaign


class CampaignReplayDatasetTest(unittest.TestCase):
    def test_phase_assignment_covers_campaign_flow(self) -> None:
        self.assertEqual(campaign.phase_for("2026-01-01T00:15:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "SUCCESS"), "Pre-Accumulation")
        self.assertEqual(campaign.phase_for("2026-01-01T00:45:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "SUCCESS"), "Accumulation")
        self.assertEqual(campaign.phase_for("2026-01-01T01:00:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "SUCCESS"), "Ignition")
        self.assertEqual(campaign.phase_for("2026-01-01T01:30:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "SUCCESS"), "Expansion")
        self.assertEqual(campaign.phase_for("2026-01-01T02:15:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "SUCCESS"), "Distribution")
        self.assertEqual(campaign.phase_for("2026-01-01T02:15:00+00:00", "2026-01-01T00:00:00+00:00", "2026-01-01T01:00:00+00:00", "2026-01-01T02:00:00+00:00", "FAILURE"), "Failure")

    def test_dataset_status_partial_when_minimum_not_met(self) -> None:
        dataset = campaign.build_campaign_dataset([_campaign("SUCCESS")])

        self.assertEqual(dataset["sprint_status"], "PARTIAL")
        self.assertEqual(dataset["success_campaign_count"], 1)
        self.assertEqual(dataset["failure_campaign_count"], 0)

    def test_run_writes_campaign_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            validation = base / "mirror_candidate_validation.json"
            contrast = base / "mirror_contrast_dataset.json"
            btc = base / "btc_replay_dataset.jsonl"
            samples = []
            cases = []
            for index in range(10):
                success_rows = _rows("SOLUSDT", "success", index)
                failure_rows = _rows("ARBUSDT", "failure", index)
                success_case = f"success-{index}"
                failure_case = f"failure-{index}"
                cases.append({"case_id": success_case, "rows": success_rows})
                cases.append({"case_id": failure_case, "rows": failure_rows})
                samples.append(_sample(success_case, "success", "SOLUSDT", index))
                samples.append(_sample(failure_case, "failure", "ARBUSDT", index))
            validation.write_text(json.dumps({"samples": samples}), encoding="utf-8")
            contrast.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            btc.write_text("", encoding="utf-8")

            result = campaign.run_campaign_replay_dataset(
                output_dir=base,
                validation_path=validation,
                contrast_dataset_path=contrast,
                btc_replay_dataset_path=btc,
            )

            self.assertEqual(result["sprint_status"], "COMPLETE")
            self.assertEqual(result["success_campaign_count"], 10)
            self.assertEqual(result["failure_campaign_count"], 10)
            self.assertTrue((base / "campaign_replay_dataset.json").exists())
            self.assertTrue((base / "campaign_summary_report.json").exists())
            self.assertTrue((base / "campaign_statistics.json").exists())
            self.assertTrue((base / "campaign_feature_timeline.json").exists())
            self.assertTrue((base / "campaign_duration_distribution.json").exists())
            self.assertTrue((base / "campaign_candidate_matrix.json").exists())


def _campaign(outcome: str) -> dict:
    return {
        "campaign_id": f"campaign-{outcome}",
        "outcome": outcome,
        "feature_timeline": [],
        "metrics": {"campaign_duration": 1.0},
        "is_trade_command": False,
    }


def _sample(source_case_id: str, case_type: str, symbol: str, index: int) -> dict:
    return {
        "sample_id": f"{case_type}-{index}",
        "source_case_id": source_case_id,
        "sample_source": "fixture",
        "case_type": case_type,
        "symbol": symbol,
        "coverage_start": "2026-01-01T00:00:00+00:00",
        "coverage_end": "2026-01-01T02:00:00+00:00",
        "candidate_metrics": {
            "score_slope": {"primary_value": 0.01 if case_type == "success" else -0.01},
            "rsi_persistence": {"primary_value": 4},
            "volume_delay": {"primary_value": 1},
        },
        "target": {
            "symbol": symbol,
            "case_type": case_type,
            "accumulation_start": "2026-01-01T00:00:00+00:00",
            "ignition_time": "2026-01-01T01:00:00+00:00",
            "local_peak_time": "2026-01-01T01:30:00+00:00",
            "replay_end_time": "2026-01-01T02:00:00+00:00",
        },
        "is_trade_command": False,
    }


def _rows(symbol: str, case_type: str, seed: int) -> list[dict[str, object]]:
    rows = []
    for index in range(9):
        rows.append(
            {
                "timestamp": f"2026-01-01T0{index // 4}:{(index % 4) * 15:02d}:00+00:00",
                "symbol": symbol,
                "case_type": case_type,
                "hellhound_score": 0.2 + seed * 0.001 + index * 0.01,
                "rsi_15m": 40 + index,
                "volume_ratio_ma20": 1.0 + index * 0.1,
                "mae_pct": -1.0 - index * 0.1,
                "mfe_pct": 1.0 + index * 0.2,
                "is_trade_command": False,
            }
        )
    return rows


if __name__ == "__main__":
    unittest.main()
