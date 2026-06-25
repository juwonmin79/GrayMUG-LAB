from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_v1_readiness_audit as audit
except ImportError:
    from . import mirror_v1_readiness_audit as audit


class MirrorV1ReadinessAuditTest(unittest.TestCase):
    def test_contract_registry_reason_and_validation_pass(self) -> None:
        inputs = _inputs()
        compatibility = audit.build_contract_compatibility(inputs)
        chain = audit.build_registry_chain_audit(inputs)
        coverage = audit.build_reason_coverage_report(inputs)
        validation = audit.build_validation_flow_audit(inputs)

        self.assertEqual(compatibility["status"], "PASS")
        self.assertEqual(chain["status"], "PASS")
        self.assertEqual(coverage["status"], "PASS")
        self.assertEqual(validation["status"], "PASS")
        self.assertEqual(coverage["decision_reason_coverage"]["REAL_WHALE_BACK"], ["EARLY_MAE_SUPPORT"])

    def test_implementation_readiness_is_ready(self) -> None:
        inputs = _inputs()
        compatibility = audit.build_contract_compatibility(inputs)
        chain = audit.build_registry_chain_audit(inputs)
        coverage = audit.build_reason_coverage_report(inputs)
        validation = audit.build_validation_flow_audit(inputs)
        readiness = audit.build_implementation_readiness(compatibility, chain, coverage, validation, inputs)
        report = audit.build_readiness_report(compatibility, chain, coverage, validation, readiness)

        self.assertEqual(readiness["readiness_verdict"], "READY")
        self.assertEqual(report["readiness_verdict"], "READY")
        self.assertEqual(report["blocking_issues"], [])

    def test_semantic_shortcut_violation_blocks_readiness(self) -> None:
        inputs = _inputs()
        inputs["mirror_reasoning_principle"]["feature_to_decision_direct_link_allowed"] = True
        compatibility = audit.build_contract_compatibility(inputs)
        chain = audit.build_registry_chain_audit(inputs)
        coverage = audit.build_reason_coverage_report(inputs)
        validation = audit.build_validation_flow_audit(inputs)
        readiness = audit.build_implementation_readiness(compatibility, chain, coverage, validation, inputs)

        self.assertNotEqual(readiness["readiness_verdict"], "READY")
        self.assertIn("semantic_rule_maintained", readiness["blocking_issues"])

    def test_run_writes_audit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = {
                "campaign_physics_contract": base / "campaign_physics_contract.json",
                "mirror_input_schema": base / "mirror_input_schema.json",
                "mirror_decision_scope": base / "mirror_decision_scope.json",
                "mirror_output_schema": base / "mirror_output_schema.json",
                "mirror_validation_rules": base / "mirror_validation_rules.json",
                "mirror_explainability_rules": base / "mirror_explainability_rules.json",
                "mirror_engine_pipeline": base / "mirror_engine_pipeline.json",
                "mirror_component_definition": base / "mirror_component_definition.json",
                "mirror_state_machine": base / "mirror_state_machine.json",
                "mirror_feature_registry": base / "mirror_feature_registry.json",
                "mirror_evidence_registry": base / "mirror_evidence_registry.json",
                "mirror_reason_registry": base / "mirror_reason_registry.json",
                "mirror_registry_dependency": base / "mirror_registry_dependency.json",
                "mirror_reasoning_principle": base / "mirror_reasoning_principle.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps(_inputs()[key]), encoding="utf-8")

            result = audit.run_mirror_v1_readiness_audit(
                output_dir=base,
                campaign_physics_contract_path=paths["campaign_physics_contract"],
                mirror_input_schema_path=paths["mirror_input_schema"],
                mirror_decision_scope_path=paths["mirror_decision_scope"],
                mirror_output_schema_path=paths["mirror_output_schema"],
                mirror_validation_rules_path=paths["mirror_validation_rules"],
                mirror_explainability_rules_path=paths["mirror_explainability_rules"],
                mirror_engine_pipeline_path=paths["mirror_engine_pipeline"],
                mirror_component_definition_path=paths["mirror_component_definition"],
                mirror_state_machine_path=paths["mirror_state_machine"],
                mirror_feature_registry_path=paths["mirror_feature_registry"],
                mirror_evidence_registry_path=paths["mirror_evidence_registry"],
                mirror_reason_registry_path=paths["mirror_reason_registry"],
                mirror_registry_dependency_path=paths["mirror_registry_dependency"],
                mirror_reasoning_principle_path=paths["mirror_reasoning_principle"],
            )

            self.assertEqual(result["readiness_verdict"], "READY")
            self.assertTrue((base / "mirror_v1_readiness_report.json").exists())
            self.assertTrue((base / "mirror_contract_compatibility.json").exists())
            self.assertTrue((base / "mirror_registry_chain_audit.json").exists())
            self.assertTrue((base / "mirror_reason_coverage_report.json").exists())
            self.assertTrue((base / "mirror_validation_flow_audit.json").exists())
            self.assertTrue((base / "mirror_implementation_readiness.json").exists())


def _inputs() -> dict:
    decisions = ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"]
    contract_fields = [
        {"field": field}
        for field in [
            "schema_version",
            "campaign_id",
            "signal_id",
            "symbol",
            "timeframe",
            "outcome",
            "early_mae",
            "recovery_ratio",
            "initial_drawdown_velocity",
            "campaign_duration",
            "confidence",
            "created_at",
        ]
    ]
    return {
        "campaign_physics_contract": {"contract_version": "campaign_physics_contract_v1", "fields": contract_fields},
        "mirror_input_schema": {
            "accepted_input": "Campaign Physics Packet",
            "accepted_contract_version": "campaign_physics_contract_v1",
            "required_packet_fields": [row["field"] for row in contract_fields],
        },
        "mirror_decision_scope": {
            "accepted_input": "Campaign Physics Packet",
            "decision_enum": decisions,
            "forbidden_direct_inputs": ["Snapshot", "Lead Line", "Raw Candle", "Raw Score"],
        },
        "mirror_output_schema": {
            "decision_enum": decisions,
            "reason_code_required": True,
            "freeform_explanation_allowed": False,
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
            ],
        },
        "mirror_validation_rules": {
            "rules": [
                {"validation_error_code": "missing_decision", "verdict": "REJECT"},
                {"validation_error_code": "missing_confidence", "verdict": "REJECT"},
                {"validation_error_code": "invalid_enum", "verdict": "REJECT"},
                {"validation_error_code": "missing_reason_code", "verdict": "REJECT"},
                {"validation_error_code": "invalid_schema", "verdict": "REJECT"},
                {"validation_error_code": "missing_field", "verdict": "REJECT"},
                {"validation_error_code": "partial_packet", "verdict": "HOLD"},
                {"validation_error_code": "unknown_field", "verdict": "WARNING"},
                {"validation_error_code": "valid_packet", "verdict": "ACCEPT"},
                {"validation_error_code": "invalid_reason_code", "verdict": "REJECT"},
            ],
            "audit_policy": {
                "audit_log_fields": [
                    "contract_version",
                    "mirror_pattern_id",
                    "campaign_id",
                    "signal_id",
                    "decision",
                    "reason_code",
                    "validation_result",
                    "action",
                    "timestamp",
                ]
            },
        },
        "mirror_explainability_rules": {
            "reason_code_required": True,
            "freeform_llm_narrative_allowed": False,
            "decision_reason_map": {decision: ["SOME_REASON"] for decision in decisions},
        },
        "mirror_engine_pipeline": {
            "pipeline": [{"stage": stage} for stage in audit.REQUIRED_PIPELINE],
        },
        "mirror_component_definition": {
            "components": [
                {"component": name}
                for name in [
                    "Packet Validator",
                    "Evidence Builder",
                    "Evidence Normalizer",
                    "Pattern Matcher",
                    "Decision Builder",
                    "Confidence Manager",
                    "Explainability Builder",
                    "Packet Serializer",
                ]
            ]
        },
        "mirror_state_machine": {"states": ["IDLE", "REJECTED", "HOLD"]},
        "mirror_feature_registry": {
            "features": [{"feature_id": "early_mae"}, {"feature_id": "recovery_ratio"}, {"feature_id": "confidence"}]
        },
        "mirror_evidence_registry": {
            "evidence": [
                {"evidence_id": "EARLY_MAE_HEALTHY"},
                {"evidence_id": "RECOVERY_WEAK"},
                {"evidence_id": "LOW_CONFIDENCE"},
            ]
        },
        "mirror_reason_registry": {
            "reasons": [
                {"reason_code": "EARLY_MAE_SUPPORT"},
                {"reason_code": "RECOVERY_FAILURE"},
                {"reason_code": "INSUFFICIENT_EVIDENCE"},
            ]
        },
        "mirror_registry_dependency": {
            "dependency_order": ["Feature", "Evidence", "Reason", "Mirror Decision"],
            "reverse_reference_allowed": False,
            "reason_direct_feature_reference_allowed": False,
            "feature_to_evidence": [
                {"from": "early_mae", "to": "EARLY_MAE_HEALTHY"},
                {"from": "recovery_ratio", "to": "RECOVERY_WEAK"},
                {"from": "confidence", "to": "LOW_CONFIDENCE"},
            ],
            "evidence_to_reason": [
                {"from": "EARLY_MAE_HEALTHY", "to": "EARLY_MAE_SUPPORT"},
                {"from": "RECOVERY_WEAK", "to": "RECOVERY_FAILURE"},
                {"from": "LOW_CONFIDENCE", "to": "INSUFFICIENT_EVIDENCE"},
            ],
            "reason_to_decision": [
                {"from": "EARLY_MAE_SUPPORT", "to": "REAL_WHALE_BACK"},
                {"from": "RECOVERY_FAILURE", "to": "FAKE_WHALE_BACK"},
                {"from": "INSUFFICIENT_EVIDENCE", "to": "INCONCLUSIVE"},
            ],
        },
        "mirror_reasoning_principle": {
            "semantic_consistency_rule": "Feature -> Evidence -> Reason -> Decision",
            "feature_to_decision_direct_link_allowed": False,
        },
    }


if __name__ == "__main__":
    unittest.main()
