from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import campaign_physics_design as design
except ImportError:
    from . import campaign_physics_design as design


class CampaignPhysicsDesignTest(unittest.TestCase):
    def test_cycle_detection(self) -> None:
        self.assertFalse(design.has_cycle([{"from": "A", "to": "B"}, {"from": "B", "to": "C"}]))
        self.assertTrue(design.has_cycle([{"from": "A", "to": "B"}, {"from": "B", "to": "A"}]))

    def test_layer_definition_marks_verified_candidates(self) -> None:
        layer = design.build_layer_definition(_inputs())

        candidates = {row["candidate"]: row for row in layer["candidates"]}
        self.assertEqual(candidates["early_mae"]["evidence_verdict"], "VERIFIED")
        self.assertFalse(candidates["early_mae"]["mirror_dependency"])
        self.assertTrue(candidates["recovery_ratio"]["replayable"])
        self.assertTrue(candidates["campaign_duration"]["real_time_calculable"])

    def test_run_writes_design_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign_dataset = base / "campaign_replay_dataset.json"
            discriminator = base / "early_mae_discriminator.json"
            statistics = base / "early_mae_statistics.json"
            summary = base / "campaign_physics_summary.json"
            campaign_dataset.write_text(json.dumps(_inputs()["campaign_replay_dataset"]), encoding="utf-8")
            discriminator.write_text(json.dumps(_inputs()["early_mae_discriminator"]), encoding="utf-8")
            statistics.write_text(json.dumps(_inputs()["early_mae_statistics"]), encoding="utf-8")
            summary.write_text(json.dumps(_inputs()["campaign_physics_summary"]), encoding="utf-8")

            result = design.run_campaign_physics_design(
                output_dir=base,
                campaign_dataset_path=campaign_dataset,
                discriminator_path=discriminator,
                statistics_path=statistics,
                summary_path=summary,
            )

            self.assertEqual(result["design_status"], "VERIFIED")
            self.assertIn("early_mae", result["verified"])
            self.assertTrue((base / "campaign_physics_layer.json").exists())
            self.assertTrue((base / "campaign_physics_dependencies.json").exists())
            self.assertTrue((base / "campaign_feature_flow.json").exists())
            self.assertTrue((base / "campaign_physics_design_report.json").exists())


def _inputs() -> dict:
    ranking = [
        {"candidate": "early_mae", "rank": 1, "candidate_score": 1.0, "verdict": "VERIFIED"},
        {"candidate": "recovery_ratio", "rank": 2, "candidate_score": 0.8, "verdict": "VERIFIED"},
        {"candidate": "initial_drawdown_velocity", "rank": 3, "candidate_score": 0.4, "verdict": "NOT_ENOUGH_EVIDENCE"},
        {"candidate": "campaign_duration", "rank": 4, "candidate_score": 0.2, "verdict": "NOT_ENOUGH_EVIDENCE"},
    ]
    return {
        "campaign_replay_dataset": {
            "campaign_replay_dataset_schema_version": "campaign_replay_dataset_v1",
            "campaign_count": 20,
            "success_campaign_count": 10,
            "failure_campaign_count": 10,
        },
        "early_mae_discriminator": {"early_mae_discriminator_schema_version": "early_mae_discriminator_v1"},
        "early_mae_statistics": {"early_mae_statistics_schema_version": "early_mae_statistics_v1"},
        "campaign_physics_summary": {
            "campaign_physics_summary_schema_version": "campaign_physics_summary_v1",
            "evidence_level": "VERIFIED",
            "candidate_ranking": ranking,
        },
    }


if __name__ == "__main__":
    unittest.main()
