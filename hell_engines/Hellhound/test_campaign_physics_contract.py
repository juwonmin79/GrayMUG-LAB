from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import campaign_physics_contract as contract
except ImportError:
    from . import campaign_physics_contract as contract


class CampaignPhysicsContractTest(unittest.TestCase):
    def test_contract_schema_defines_required_packet_fields(self) -> None:
        schema = contract.build_contract_schema(_inputs())
        fields = {row["field"]: row for row in schema["fields"]}

        self.assertEqual(schema["contract_version"], "campaign_physics_contract_v1")
        self.assertEqual(fields["schema_version"]["valid_enum"], ["campaign_physics_contract_v1"])
        self.assertTrue(fields["campaign_id"]["required"])
        self.assertFalse(fields["early_mae"]["nullable"])
        self.assertEqual(fields["outcome"]["valid_enum"], ["SUCCESS", "FAILURE", "INCONCLUSIVE"])
        self.assertEqual(fields["early_mae"]["evidence_verdict"], "VERIFIED")
        self.assertEqual(fields["campaign_duration"]["evidence_verdict"], "NOT_ENOUGH_EVIDENCE")

    def test_mirror_input_schema_blocks_direct_snapshot_and_lead_line_access(self) -> None:
        schema = contract.build_contract_schema(_inputs())
        mirror_input = contract.build_mirror_input_schema(schema)

        self.assertEqual(mirror_input["accepted_input"], "Campaign Physics Packet")
        self.assertFalse(mirror_input["direct_snapshot_access"])
        self.assertFalse(mirror_input["direct_lead_line_access"])
        self.assertIn("Snapshot", mirror_input["forbidden_inputs"])
        self.assertIn("Lead Line", mirror_input["forbidden_inputs"])
        self.assertIn("campaign_id", mirror_input["required_packet_fields"])

    def test_validation_and_audit_policy_cover_required_conditions(self) -> None:
        validation = contract.build_validation_rules()
        audit = contract.build_audit_policy()
        rules = {row["validation_error_code"]: row for row in validation["rules"]}
        audit_fields = {row["field"] for row in audit["audit_log_fields"]}

        self.assertEqual(rules["required_field_missing"]["verdict"], "REJECT")
        self.assertIn("SKIP", rules["required_field_missing"]["actions"])
        self.assertEqual(rules["schema_version_mismatch"]["verdict"], "HOLD")
        self.assertEqual(rules["unknown_field"]["verdict"], "WARNING")
        self.assertEqual(rules["partial_packet"]["verdict"], "HOLD")
        self.assertTrue(
            {
                "contract_version",
                "campaign_id",
                "signal_id",
                "symbol",
                "validation_error_code",
                "validation_reason",
                "action",
                "timestamp",
            }.issubset(audit_fields)
        )

    def test_run_writes_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            physics_layer = base / "campaign_physics_layer.json"
            dependencies = base / "campaign_physics_dependencies.json"
            feature_flow = base / "campaign_feature_flow.json"
            summary = base / "campaign_physics_summary.json"
            early_mae = base / "early_mae_discriminator.json"
            physics_layer.write_text(json.dumps(_inputs()["campaign_physics_layer"]), encoding="utf-8")
            dependencies.write_text(json.dumps(_inputs()["campaign_physics_dependencies"]), encoding="utf-8")
            feature_flow.write_text(json.dumps(_inputs()["campaign_feature_flow"]), encoding="utf-8")
            summary.write_text(json.dumps(_inputs()["campaign_physics_summary"]), encoding="utf-8")
            early_mae.write_text(json.dumps(_inputs()["early_mae_discriminator"]), encoding="utf-8")

            result = contract.run_campaign_physics_contract(
                output_dir=base,
                physics_layer_path=physics_layer,
                dependencies_path=dependencies,
                feature_flow_path=feature_flow,
                physics_summary_path=summary,
                early_mae_path=early_mae,
            )

            self.assertEqual(result["contract_status"], "VERIFIED")
            self.assertTrue((base / "campaign_physics_contract.json").exists())
            self.assertTrue((base / "mirror_input_schema.json").exists())
            self.assertTrue((base / "contract_validation_rules.json").exists())
            self.assertTrue((base / "interface_contract_report.json").exists())
            self.assertTrue((base / "interface_audit_policy.json").exists())


def _inputs() -> dict:
    candidates = [
        {"candidate": "early_mae", "evidence_verdict": "VERIFIED"},
        {"candidate": "recovery_ratio", "evidence_verdict": "VERIFIED"},
        {"candidate": "initial_drawdown_velocity", "evidence_verdict": "NOT_ENOUGH_EVIDENCE"},
        {"candidate": "campaign_duration", "evidence_verdict": "NOT_ENOUGH_EVIDENCE"},
    ]
    return {
        "campaign_physics_layer": {
            "campaign_physics_layer_schema_version": "campaign_physics_layer_v1",
            "candidates": candidates,
        },
        "campaign_physics_dependencies": {
            "campaign_physics_dependencies_schema_version": "campaign_physics_dependencies_v1",
            "cycle_check": {"has_cycle": False, "candidate_has_cycle": False},
        },
        "campaign_feature_flow": {
            "campaign_feature_flow_schema_version": "campaign_feature_flow_v1",
            "dependency_diagram": "Snapshot -> Lead Line -> Campaign Physics -> Mirror Pattern -> ML -> Medusa Board",
        },
        "campaign_physics_summary": {
            "campaign_physics_summary_schema_version": "campaign_physics_summary_v1",
            "verified": ["early_mae", "recovery_ratio"],
            "not_verified": ["initial_drawdown_velocity", "campaign_duration"],
        },
        "early_mae_discriminator": {"early_mae_discriminator_schema_version": "early_mae_discriminator_v1"},
    }


if __name__ == "__main__":
    unittest.main()
