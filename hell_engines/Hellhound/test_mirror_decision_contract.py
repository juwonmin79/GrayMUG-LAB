from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_decision_contract as contract
except ImportError:
    from . import mirror_decision_contract as contract


class MirrorDecisionContractTest(unittest.TestCase):
    def test_decision_scope_uses_campaign_physics_packet_only(self) -> None:
        scope = contract.build_decision_scope(_inputs())

        self.assertEqual(scope["decision_enum"], ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"])
        self.assertEqual(scope["decision_objective"], "Judge Campaign authenticity, not price direction.")
        self.assertEqual(scope["accepted_input"], "Campaign Physics Packet")
        self.assertIn("early_mae", scope["allowed_input_features"])
        self.assertIn("Snapshot", scope["forbidden_direct_inputs"])
        self.assertIn("Raw Score", scope["forbidden_direct_inputs"])

    def test_output_schema_requires_reason_code_based_packet(self) -> None:
        scope = contract.build_decision_scope(_inputs())
        schema = contract.build_output_schema(scope)

        required = set(schema["required_fields"])
        self.assertIn("mirror_decision", required)
        self.assertIn("explainability", required)
        self.assertIn("supporting_features", required)
        self.assertEqual(schema["decision_enum"], ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"])
        self.assertTrue(schema["reason_code_required"])
        self.assertFalse(schema["freeform_explanation_allowed"])

    def test_explainability_validation_and_dependency_policy(self) -> None:
        explainability = contract.build_explainability_rules()
        validation = contract.build_validation_rules()
        dependency = contract.build_dependency_graph(_inputs())
        rules = {row["validation_error_code"]: row for row in validation["rules"]}

        self.assertFalse(explainability["freeform_llm_narrative_allowed"])
        self.assertIn("EARLY_MAE_NORMAL", explainability["allowed_reason_codes"])
        self.assertEqual(rules["missing_decision"]["verdict"], "REJECT")
        self.assertEqual(rules["partial_packet"]["verdict"], "HOLD")
        self.assertEqual(rules["unknown_field"]["verdict"], "WARNING")
        self.assertIn("reason_code", validation["audit_policy"]["audit_log_fields"])
        self.assertFalse(dependency["mirror_depends_on_ml"])
        self.assertTrue(dependency["ml_learns_from_mirror"])
        self.assertFalse(dependency["has_cycle"])

    def test_run_writes_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = {
                "campaign_physics_contract": base / "campaign_physics_contract.json",
                "mirror_input_schema": base / "mirror_input_schema.json",
                "campaign_physics_summary": base / "campaign_physics_summary.json",
                "early_mae_discriminator": base / "early_mae_discriminator.json",
                "campaign_feature_flow": base / "campaign_feature_flow.json",
                "interface_contract_report": base / "interface_contract_report.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps(_inputs()[key]), encoding="utf-8")

            result = contract.run_mirror_decision_contract(
                output_dir=base,
                campaign_physics_contract_path=paths["campaign_physics_contract"],
                mirror_input_schema_path=paths["mirror_input_schema"],
                physics_summary_path=paths["campaign_physics_summary"],
                early_mae_path=paths["early_mae_discriminator"],
                feature_flow_path=paths["campaign_feature_flow"],
                interface_report_path=paths["interface_contract_report"],
            )

            self.assertEqual(result["contract_status"], "VERIFIED")
            self.assertTrue((base / "mirror_decision_scope.json").exists())
            self.assertTrue((base / "mirror_output_schema.json").exists())
            self.assertTrue((base / "mirror_explainability_rules.json").exists())
            self.assertTrue((base / "mirror_validation_rules.json").exists())
            self.assertTrue((base / "mirror_decision_contract_report.json").exists())
            self.assertTrue((base / "mirror_dependency_graph.json").exists())


def _inputs() -> dict:
    return {
        "campaign_physics_contract": {
            "contract_version": "campaign_physics_contract_v1",
            "fields": [
                {"field": "early_mae"},
                {"field": "recovery_ratio"},
                {"field": "campaign_duration"},
                {"field": "initial_drawdown_velocity"},
                {"field": "confidence"},
            ],
        },
        "mirror_input_schema": {
            "accepted_input": "Campaign Physics Packet",
            "direct_snapshot_access": False,
            "direct_lead_line_access": False,
        },
        "campaign_physics_summary": {
            "evidence_level": "VERIFIED",
            "verified": ["early_mae", "recovery_ratio"],
            "not_verified": ["initial_drawdown_velocity", "campaign_duration"],
        },
        "early_mae_discriminator": {"evidence_level": "VERIFIED"},
        "campaign_feature_flow": {
            "dependency_diagram": "Snapshot -> Lead Line -> Campaign Physics -> Mirror Pattern -> ML -> Medusa Board"
        },
        "interface_contract_report": {"contract_status": "VERIFIED"},
    }


if __name__ == "__main__":
    unittest.main()
