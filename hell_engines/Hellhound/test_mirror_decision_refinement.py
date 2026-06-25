from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_decision_refinement as refinement
except ImportError:
    from . import mirror_decision_refinement as refinement


class MirrorDecisionRefinementTest(unittest.TestCase):
    def test_conflict_resolution_report_counts_moved_packets(self) -> None:
        before = {"inconclusive_candidate_count": 1}
        packets = [
            {
                "campaign_id": "c1",
                "mirror_decision": "INCONCLUSIVE",
                "reason_code": ["RECOVERY_FAILURE", "CONFLICTING_EVIDENCE"],
                "confidence": 0.35,
                "supporting_features": {
                    "conflict_resolution": {
                        "conflict_detected": True,
                        "decision_targets": ["FAKE_WHALE_BACK", "INCONCLUSIVE"],
                    }
                },
            }
        ]

        report = refinement.build_conflict_resolution_report(before, packets)

        self.assertEqual(report["conflict_candidate_count"], 1)
        self.assertEqual(report["conflict_to_inconclusive_count"], 1)

    def test_refinement_report_passes_when_all_conflicts_move(self) -> None:
        before = {
            "decision_distribution": {"INCONCLUSIVE": 0},
            "confidence_consistency_counts": {"OVERCONFIDENT_CONFLICT": 1},
        }
        engine_result = {
            "decision_distribution": {"INCONCLUSIVE": 1},
            "contract_validation": "PASS",
            "registry_validation": "PASS",
            "mirror_packet_validation": "PASS",
        }
        conflict = {"conflict_candidate_count": 1, "conflict_to_inconclusive_count": 1}
        inconclusive = {"counts": {"INCONCLUSIVE": 1}}

        report = refinement.build_refinement_report(before, engine_result, conflict, inconclusive)

        self.assertEqual(report["refinement_status"], "PASS")
        self.assertTrue(report["inconclusive_increased"])
        self.assertEqual(report["next_sprint_recommendation"], "12AD Mirror Shadow Integration Offline Shadow Mode")

    def test_run_writes_refinement_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before = {
                "decision_distribution": {"FAKE_WHALE_BACK": 1, "INCONCLUSIVE": 0},
                "confidence_consistency_counts": {"OVERCONFIDENT_CONFLICT": 1},
                "inconclusive_candidate_count": 1,
            }
            calibration = base / "mirror_decision_calibration_report.json"
            calibration.write_text(json.dumps(before), encoding="utf-8")

            result = refinement.run_mirror_decision_refinement(output_dir=base, calibration_report_path=calibration)

            self.assertEqual(result["contract_validation"], "PASS")
            self.assertTrue((base / "mirror_conflict_resolution_report.json").exists())
            self.assertTrue((base / "mirror_inconclusive_statistics.json").exists())
            self.assertTrue((base / "mirror_decision_refinement_report.json").exists())


if __name__ == "__main__":
    unittest.main()
