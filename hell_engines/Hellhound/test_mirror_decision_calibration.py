from __future__ import annotations

import unittest

try:
    import mirror_decision_calibration as calibration
except ImportError:
    from . import mirror_decision_calibration as calibration


class MirrorDecisionCalibrationTest(unittest.TestCase):
    def test_distribution_conflict_and_sufficiency_audit(self) -> None:
        inputs = _inputs()
        decision = calibration.build_decision_distribution_audit(inputs)
        conflict = calibration.build_conflict_analysis(inputs)
        sufficiency = calibration.build_evidence_sufficiency(inputs, conflict)

        self.assertEqual(decision["counts"]["REAL_WHALE_BACK"], 1)
        self.assertEqual(decision["counts"]["FAKE_WHALE_BACK"], 1)
        self.assertEqual(decision["counts"]["INCONCLUSIVE"], 0)
        self.assertEqual(conflict["conflict_count"], 1)
        self.assertEqual(conflict["inconclusive_candidate_count"], 1)
        self.assertEqual(sufficiency["issue_counts"]["reason_conflict"], 1)

    def test_confidence_and_inconclusive_analysis_detect_calibration_need(self) -> None:
        inputs = _inputs()
        decision = calibration.build_decision_distribution_audit(inputs)
        conflict = calibration.build_conflict_analysis(inputs)
        sufficiency = calibration.build_evidence_sufficiency(inputs, conflict)
        confidence = calibration.build_confidence_calibration(inputs, conflict)
        stability = {"deterministic": True}
        inconclusive = calibration.build_inconclusive_analysis(inputs, conflict, sufficiency)
        report = calibration.build_calibration_report(decision, conflict, sufficiency, confidence, stability, inconclusive)

        self.assertEqual(confidence["consistency_counts"]["OVERCONFIDENT_CONFLICT"], 1)
        self.assertTrue(inconclusive["root_cause_candidates"]["conflict_handling_gap"])
        self.assertEqual(report["calibration_verdict"], "CALIBRATION_NEEDED")
        self.assertEqual(report["next_sprint_recommendation"], "12AC Mirror Decision Refinement")

    def test_explainability_is_reason_code_only(self) -> None:
        inputs = _inputs()

        for packet in inputs["packets"]:
            self.assertIsInstance(packet["reason_code"], list)
            self.assertNotIn("explanation", packet)


def _inputs() -> dict:
    return {
        "packets": [
            {
                "campaign_id": "campaign-real",
                "mirror_decision": "REAL_WHALE_BACK",
                "confidence": 0.9,
                "reason_code": ["RECOVERY_SUPPORT"],
                "supporting_features": {"evidence": ["RECOVERY_STRONG"]},
            },
            {
                "campaign_id": "campaign-fake",
                "mirror_decision": "FAKE_WHALE_BACK",
                "confidence": 0.95,
                "reason_code": ["RECOVERY_FAILURE", "CONFLICTING_EVIDENCE"],
                "supporting_features": {"evidence": ["RECOVERY_WEAK"]},
            },
        ],
        "decision_distribution": {"counts": {"REAL_WHALE_BACK": 1, "FAKE_WHALE_BACK": 1}},
        "engine_report": {},
        "reason_statistics": {},
        "confidence_distribution": {},
        "registry_dependency": {
            "reason_to_decision": [
                {"from": "RECOVERY_SUPPORT", "to": "REAL_WHALE_BACK"},
                {"from": "RECOVERY_FAILURE", "to": "FAKE_WHALE_BACK"},
                {"from": "CONFLICTING_EVIDENCE", "to": "INCONCLUSIVE"},
            ]
        },
        "reason_registry": {},
    }


if __name__ == "__main__":
    unittest.main()
