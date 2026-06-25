from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_reasoning_registry as registry
except ImportError:
    from . import mirror_reasoning_registry as registry


class MirrorReasoningRegistryTest(unittest.TestCase):
    def test_feature_evidence_reason_registries_are_defined(self) -> None:
        features = registry.build_feature_registry()
        evidence = registry.build_evidence_registry()
        reasons = registry.build_reason_registry()

        self.assertEqual(
            {row["feature_id"] for row in features["features"]},
            {"early_mae", "recovery_ratio", "campaign_duration", "initial_drawdown_velocity", "confidence"},
        )
        statuses = {row["feature_id"]: row["status"] for row in features["features"]}
        self.assertEqual(statuses["initial_drawdown_velocity"], "RESERVED")
        self.assertIn("EARLY_MAE_HEALTHY", {row["evidence_id"] for row in evidence["evidence"]})
        self.assertIn("RECOVERY_FAILURE", {row["reason_code"] for row in reasons["reasons"]})
        self.assertFalse(reasons["reason_references_feature_directly"])

    def test_dependency_blocks_feature_to_decision_shortcut(self) -> None:
        features = registry.build_feature_registry()
        evidence = registry.build_evidence_registry()
        reasons = registry.build_reason_registry()
        dependency = registry.build_registry_dependency(features, evidence, reasons)
        principle = registry.build_reasoning_principle()

        self.assertEqual(dependency["dependency_order"], ["Feature", "Evidence", "Reason", "Mirror Decision"])
        self.assertFalse(dependency["reverse_reference_allowed"])
        self.assertFalse(dependency["reason_direct_feature_reference_allowed"])
        self.assertFalse(principle["feature_to_decision_direct_link_allowed"])
        self.assertIn("Meaning always precedes Decision", principle["principle"])

    def test_validation_lifecycle_and_report(self) -> None:
        features = registry.build_feature_registry()
        evidence = registry.build_evidence_registry()
        reasons = registry.build_reason_registry()
        dependency = registry.build_registry_dependency(features, evidence, reasons)
        lifecycle = registry.build_registry_lifecycle()
        validation = registry.build_registry_validation(features, evidence, reasons, dependency)
        principle = registry.build_reasoning_principle()
        report = registry.build_registry_report(features, evidence, reasons, dependency, lifecycle, validation, principle, _runner_inputs())

        self.assertTrue(validation["validation_passed"])
        self.assertEqual(lifecycle["statuses"], ["ACTIVE", "DEPRECATED", "RESERVED", "REMOVED"])
        self.assertIn("registry_type", lifecycle["audit_log_fields"])
        self.assertEqual(report["registry_status"], "VERIFIED")
        self.assertIn("Semantic Consistency Rule", report["verified"])

    def test_run_writes_registry_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = {
                "engine_pipeline": base / "mirror_engine_pipeline.json",
                "component_definition": base / "mirror_component_definition.json",
                "evidence_lifecycle": base / "mirror_evidence_lifecycle.json",
                "explainability_rules": base / "mirror_explainability_rules.json",
                "output_schema": base / "mirror_output_schema.json",
                "blueprint_report": base / "mirror_engine_blueprint_report.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps(_inputs()[key]), encoding="utf-8")

            result = registry.run_mirror_reasoning_registry(
                output_dir=base,
                engine_pipeline_path=paths["engine_pipeline"],
                component_definition_path=paths["component_definition"],
                evidence_lifecycle_path=paths["evidence_lifecycle"],
                explainability_rules_path=paths["explainability_rules"],
                output_schema_path=paths["output_schema"],
                blueprint_report_path=paths["blueprint_report"],
            )

            self.assertEqual(result["registry_status"], "VERIFIED")
            self.assertTrue((base / "mirror_feature_registry.json").exists())
            self.assertTrue((base / "mirror_evidence_registry.json").exists())
            self.assertTrue((base / "mirror_reason_registry.json").exists())
            self.assertTrue((base / "mirror_registry_dependency.json").exists())
            self.assertTrue((base / "mirror_registry_validation.json").exists())
            self.assertTrue((base / "mirror_registry_lifecycle.json").exists())
            self.assertTrue((base / "mirror_reasoning_principle.json").exists())
            self.assertTrue((base / "mirror_reasoning_registry_report.json").exists())


def _inputs() -> dict:
    return {
        "engine_pipeline": {"semantic_layer_definition": "Mirror is the Semantic Interpretation Layer."},
        "component_definition": {"components": [{"component": "Pattern Matcher"}]},
        "evidence_lifecycle": {"reason_code_is_only_explainability_source": True},
        "explainability_rules": {"reason_code_required": True},
        "output_schema": {"reason_code_required": True},
        "blueprint_report": {"blueprint_status": "VERIFIED"},
    }


def _runner_inputs() -> dict:
    data = _inputs()
    return {
        "mirror_engine_pipeline": data["engine_pipeline"],
        "mirror_component_definition": data["component_definition"],
        "mirror_evidence_lifecycle": data["evidence_lifecycle"],
        "mirror_explainability_rules": data["explainability_rules"],
        "mirror_output_schema": data["output_schema"],
        "mirror_engine_blueprint_report": data["blueprint_report"],
    }


if __name__ == "__main__":
    unittest.main()
