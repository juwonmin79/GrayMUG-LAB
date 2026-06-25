from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_engine_blueprint as blueprint
except ImportError:
    from . import mirror_engine_blueprint as blueprint


class MirrorEngineBlueprintTest(unittest.TestCase):
    def test_pipeline_and_semantic_layer_definition(self) -> None:
        pipeline = blueprint.build_engine_pipeline(_inputs())

        self.assertEqual(
            [row["stage"] for row in pipeline["pipeline"]],
            [
                "Campaign Physics Packet",
                "Packet Validation",
                "Evidence Builder",
                "Evidence Normalizer",
                "Pattern Matcher",
                "Decision Builder",
                "Explainability Builder",
                "Mirror Pattern Packet",
            ],
        )
        self.assertIn("Semantic Interpretation Layer", pipeline["semantic_layer_definition"])
        self.assertIn("not a price prediction engine", pipeline["semantic_layer_definition"])

    def test_components_state_and_lifecycles_are_defined(self) -> None:
        components = blueprint.build_component_definition()
        state_machine = blueprint.build_state_machine()
        evidence = blueprint.build_evidence_lifecycle()
        confidence = blueprint.build_confidence_lifecycle()

        self.assertTrue(components["single_responsibility_required"])
        self.assertIn("Packet Validator", {row["component"] for row in components["components"]})
        self.assertIn("PACKET_READY", state_machine["states"])
        self.assertIn({"from": "VALIDATING", "to": "REJECTED", "event": "validation_reject"}, state_machine["transitions"])
        self.assertTrue(evidence["reason_code_is_only_explainability_source"])
        self.assertFalse(confidence["calculation_formula_defined"])
        self.assertEqual(confidence["created_by"], "Confidence Manager")

    def test_failure_flow_extension_points_and_report(self) -> None:
        failure = blueprint.build_failure_flow(_inputs())
        extension = blueprint.build_extension_points()
        report = blueprint.build_blueprint_report(
            blueprint.build_engine_pipeline(_inputs()),
            blueprint.build_component_definition(),
            blueprint.build_state_machine(),
            blueprint.build_evidence_lifecycle(),
            blueprint.build_confidence_lifecycle(),
            failure,
            extension,
            _runner_inputs(),
        )

        self.assertFalse(failure["mirror_repairs_or_infers_rejected_packets"])
        self.assertIn("Feature Registry", {row["registry"] for row in extension["extension_points"]})
        self.assertEqual(report["blueprint_status"], "VERIFIED")
        self.assertIn("Extension Point", report["verified"])

    def test_run_writes_blueprint_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = {
                "decision_scope": base / "mirror_decision_scope.json",
                "output_schema": base / "mirror_output_schema.json",
                "validation_rules": base / "mirror_validation_rules.json",
                "explainability_rules": base / "mirror_explainability_rules.json",
                "campaign_physics_contract": base / "campaign_physics_contract.json",
                "dependency_graph": base / "mirror_dependency_graph.json",
                "interface_report": base / "interface_contract_report.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps(_inputs()[key]), encoding="utf-8")

            result = blueprint.run_mirror_engine_blueprint(
                output_dir=base,
                decision_scope_path=paths["decision_scope"],
                output_schema_path=paths["output_schema"],
                validation_rules_path=paths["validation_rules"],
                explainability_rules_path=paths["explainability_rules"],
                campaign_physics_contract_path=paths["campaign_physics_contract"],
                dependency_graph_path=paths["dependency_graph"],
                interface_report_path=paths["interface_report"],
            )

            self.assertEqual(result["blueprint_status"], "VERIFIED")
            self.assertTrue((base / "mirror_engine_pipeline.json").exists())
            self.assertTrue((base / "mirror_component_definition.json").exists())
            self.assertTrue((base / "mirror_state_machine.json").exists())
            self.assertTrue((base / "mirror_evidence_lifecycle.json").exists())
            self.assertTrue((base / "mirror_confidence_lifecycle.json").exists())
            self.assertTrue((base / "mirror_failure_flow.json").exists())
            self.assertTrue((base / "mirror_extension_points.json").exists())
            self.assertTrue((base / "mirror_engine_blueprint_report.json").exists())


def _inputs() -> dict:
    return {
        "decision_scope": {
            "accepted_input": "Campaign Physics Packet",
            "decision_enum": ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"],
            "allowed_input_features": ["early_mae", "recovery_ratio", "campaign_duration", "initial_drawdown_velocity", "confidence"],
        },
        "output_schema": {
            "required_fields": [
                "schema_version",
                "mirror_pattern_id",
                "campaign_id",
                "signal_id",
                "symbol",
                "mirror_decision",
                "confidence",
                "explainability",
                "supporting_features",
                "validation_state",
                "created_at",
            ]
        },
        "validation_rules": {
            "rules": [
                {"validation_error_code": "missing_decision", "verdict": "REJECT", "actions": ["SKIP"]},
                {"validation_error_code": "unknown_field", "verdict": "WARNING", "actions": ["WARNING"]},
            ]
        },
        "explainability_rules": {"reason_code_required": True, "freeform_llm_narrative_allowed": False},
        "campaign_physics_contract": {"contract_version": "campaign_physics_contract_v1"},
        "dependency_graph": {"mirror_depends_on_ml": False, "ml_learns_from_mirror": True},
        "interface_report": {"contract_status": "VERIFIED"},
    }


def _runner_inputs() -> dict:
    data = _inputs()
    return {
        "mirror_decision_scope": data["decision_scope"],
        "mirror_output_schema": data["output_schema"],
        "mirror_validation_rules": data["validation_rules"],
        "mirror_explainability_rules": data["explainability_rules"],
        "campaign_physics_contract": data["campaign_physics_contract"],
        "mirror_dependency_graph": data["dependency_graph"],
        "interface_contract_report": data["interface_report"],
    }


if __name__ == "__main__":
    unittest.main()
