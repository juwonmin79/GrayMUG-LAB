from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CAMPAIGN_PHYSICS_CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_contract.json"
MIRROR_INPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_input_schema.json"
MIRROR_DECISION_SCOPE_PATH = DEFAULT_OUTPUT_DIR / "mirror_decision_scope.json"
MIRROR_OUTPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_output_schema.json"
MIRROR_VALIDATION_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_validation_rules.json"
MIRROR_EXPLAINABILITY_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_explainability_rules.json"
MIRROR_ENGINE_PIPELINE_PATH = DEFAULT_OUTPUT_DIR / "mirror_engine_pipeline.json"
MIRROR_COMPONENT_DEFINITION_PATH = DEFAULT_OUTPUT_DIR / "mirror_component_definition.json"
MIRROR_STATE_MACHINE_PATH = DEFAULT_OUTPUT_DIR / "mirror_state_machine.json"
MIRROR_FEATURE_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_feature_registry.json"
MIRROR_EVIDENCE_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_evidence_registry.json"
MIRROR_REASON_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_reason_registry.json"
MIRROR_REGISTRY_DEPENDENCY_PATH = DEFAULT_OUTPUT_DIR / "mirror_registry_dependency.json"
MIRROR_REASONING_PRINCIPLE_PATH = DEFAULT_OUTPUT_DIR / "mirror_reasoning_principle.json"

AUDIT_VERSION = "mirror_v1_readiness_audit_v1"
REQUIRED_VERDICTS = ("ACCEPT", "WARNING", "HOLD", "REJECT")
FORBIDDEN_DIRECT_INPUTS = ("Snapshot", "Lead Line", "Raw Candle")
REQUIRED_PIPELINE = (
    "Campaign Physics Packet",
    "Packet Validation",
    "Evidence Builder",
    "Evidence Normalizer",
    "Pattern Matcher",
    "Decision Builder",
    "Explainability Builder",
    "Mirror Pattern Packet",
)


def run_mirror_v1_readiness_audit(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_physics_contract_path: Path | str = CAMPAIGN_PHYSICS_CONTRACT_PATH,
    mirror_input_schema_path: Path | str = MIRROR_INPUT_SCHEMA_PATH,
    mirror_decision_scope_path: Path | str = MIRROR_DECISION_SCOPE_PATH,
    mirror_output_schema_path: Path | str = MIRROR_OUTPUT_SCHEMA_PATH,
    mirror_validation_rules_path: Path | str = MIRROR_VALIDATION_RULES_PATH,
    mirror_explainability_rules_path: Path | str = MIRROR_EXPLAINABILITY_RULES_PATH,
    mirror_engine_pipeline_path: Path | str = MIRROR_ENGINE_PIPELINE_PATH,
    mirror_component_definition_path: Path | str = MIRROR_COMPONENT_DEFINITION_PATH,
    mirror_state_machine_path: Path | str = MIRROR_STATE_MACHINE_PATH,
    mirror_feature_registry_path: Path | str = MIRROR_FEATURE_REGISTRY_PATH,
    mirror_evidence_registry_path: Path | str = MIRROR_EVIDENCE_REGISTRY_PATH,
    mirror_reason_registry_path: Path | str = MIRROR_REASON_REGISTRY_PATH,
    mirror_registry_dependency_path: Path | str = MIRROR_REGISTRY_DEPENDENCY_PATH,
    mirror_reasoning_principle_path: Path | str = MIRROR_REASONING_PRINCIPLE_PATH,
) -> Dict[str, Any]:
    inputs = {
        "campaign_physics_contract": load_json(campaign_physics_contract_path),
        "mirror_input_schema": load_json(mirror_input_schema_path),
        "mirror_decision_scope": load_json(mirror_decision_scope_path),
        "mirror_output_schema": load_json(mirror_output_schema_path),
        "mirror_validation_rules": load_json(mirror_validation_rules_path),
        "mirror_explainability_rules": load_json(mirror_explainability_rules_path),
        "mirror_engine_pipeline": load_json(mirror_engine_pipeline_path),
        "mirror_component_definition": load_json(mirror_component_definition_path),
        "mirror_state_machine": load_json(mirror_state_machine_path),
        "mirror_feature_registry": load_json(mirror_feature_registry_path),
        "mirror_evidence_registry": load_json(mirror_evidence_registry_path),
        "mirror_reason_registry": load_json(mirror_reason_registry_path),
        "mirror_registry_dependency": load_json(mirror_registry_dependency_path),
        "mirror_reasoning_principle": load_json(mirror_reasoning_principle_path),
    }
    compatibility = build_contract_compatibility(inputs)
    registry_chain = build_registry_chain_audit(inputs)
    reason_coverage = build_reason_coverage_report(inputs)
    validation_flow = build_validation_flow_audit(inputs)
    implementation = build_implementation_readiness(compatibility, registry_chain, reason_coverage, validation_flow, inputs)
    report = build_readiness_report(compatibility, registry_chain, reason_coverage, validation_flow, implementation)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "readiness_report_path": base / "mirror_v1_readiness_report.json",
        "contract_compatibility_path": base / "mirror_contract_compatibility.json",
        "registry_chain_audit_path": base / "mirror_registry_chain_audit.json",
        "reason_coverage_report_path": base / "mirror_reason_coverage_report.json",
        "validation_flow_audit_path": base / "mirror_validation_flow_audit.json",
        "implementation_readiness_path": base / "mirror_implementation_readiness.json",
    }
    write_json(report, paths["readiness_report_path"])
    write_json(compatibility, paths["contract_compatibility_path"])
    write_json(registry_chain, paths["registry_chain_audit_path"])
    write_json(reason_coverage, paths["reason_coverage_report_path"])
    write_json(validation_flow, paths["validation_flow_audit_path"])
    write_json(implementation, paths["implementation_readiness_path"])
    return {
        "mirror_v1_readiness_audit_run_schema_version": "mirror_v1_readiness_audit_run_v1",
        "audit_version": AUDIT_VERSION,
        "readiness_verdict": report["readiness_verdict"],
        "blocking_issues": report["blocking_issues"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_contract_compatibility(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    contract = inputs["campaign_physics_contract"]
    input_schema = inputs["mirror_input_schema"]
    scope = inputs["mirror_decision_scope"]
    output_schema = inputs["mirror_output_schema"]
    contract_fields = {row.get("field") for row in contract.get("fields", [])}
    required_input = set(input_schema.get("required_packet_fields", []))
    output_fields = set(output_schema.get("required_fields", []))
    checks = {
        "campaign_packet_fields_cover_mirror_input": required_input.issubset(contract_fields),
        "mirror_accepts_campaign_physics_packet_only": input_schema.get("accepted_input") == "Campaign Physics Packet"
        and scope.get("accepted_input") == "Campaign Physics Packet",
        "input_contract_version_matches": input_schema.get("accepted_contract_version") == contract.get("contract_version"),
        "mirror_output_schema_has_decision_packet_fields": {
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
        }.issubset(output_fields),
        "mirror_decision_enum_matches_output_schema": set(scope.get("decision_enum", [])) == set(output_schema.get("decision_enum", [])),
    }
    return audit_payload("mirror_contract_compatibility_v1", checks)


def build_registry_chain_audit(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    features = {
        row["feature_id"]
        for row in inputs["mirror_feature_registry"].get("features", [])
        if row.get("status", "ACTIVE") == "ACTIVE"
    }
    evidence = {row["evidence_id"] for row in inputs["mirror_evidence_registry"].get("evidence", [])}
    reasons = {row["reason_code"] for row in inputs["mirror_reason_registry"].get("reasons", [])}
    dependency = inputs["mirror_registry_dependency"]
    feature_edges = dependency.get("feature_to_evidence", [])
    evidence_edges = dependency.get("evidence_to_reason", [])
    reason_edges = dependency.get("reason_to_decision", [])
    checks = {
        "all_features_have_evidence": features.issubset({edge["from"] for edge in feature_edges}),
        "all_evidence_sources_are_registered": {edge["to"] for edge in feature_edges}.issubset(evidence),
        "all_reason_evidence_refs_are_registered": {edge["from"] for edge in evidence_edges}.issubset(evidence),
        "all_reasons_are_connected_to_decision": reasons.issubset({edge["from"] for edge in reason_edges}),
        "dependency_order_is_semantic": dependency.get("dependency_order") == ["Feature", "Evidence", "Reason", "Mirror Decision"],
        "reason_direct_feature_reference_forbidden": dependency.get("reason_direct_feature_reference_allowed") is False,
        "reverse_reference_forbidden": dependency.get("reverse_reference_allowed") is False,
    }
    return audit_payload("mirror_registry_chain_audit_v1", checks)


def build_reason_coverage_report(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    decisions = set(inputs["mirror_decision_scope"].get("decision_enum", []))
    reason_edges = inputs["mirror_registry_dependency"].get("reason_to_decision", [])
    decision_reason_map = inputs["mirror_explainability_rules"].get("decision_reason_map", {})
    checks = {
        "every_decision_has_registry_reason": decisions.issubset({edge["to"] for edge in reason_edges}),
        "every_decision_has_explainability_reason": decisions.issubset(set(decision_reason_map)),
        "reason_code_required": inputs["mirror_explainability_rules"].get("reason_code_required") is True
        and inputs["mirror_output_schema"].get("reason_code_required") is True,
        "freeform_explanation_forbidden": inputs["mirror_explainability_rules"].get("freeform_llm_narrative_allowed") is False
        and inputs["mirror_output_schema"].get("freeform_explanation_allowed") is False,
    }
    payload = audit_payload("mirror_reason_coverage_report_v1", checks)
    payload["decision_reason_coverage"] = {
        decision: sorted(edge["from"] for edge in reason_edges if edge["to"] == decision) for decision in sorted(decisions)
    }
    return payload


def build_validation_flow_audit(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    rules = inputs["mirror_validation_rules"].get("rules", [])
    verdicts = {row.get("verdict") for row in rules}
    rule_codes = {row.get("validation_error_code") for row in rules}
    audit_fields = set(inputs["mirror_validation_rules"].get("audit_policy", {}).get("audit_log_fields", []))
    contract_fields = {row.get("field") for row in inputs["campaign_physics_contract"].get("fields", [])}
    checks = {
        "validation_verdicts_supported": set(REQUIRED_VERDICTS).issubset(verdicts),
        "required_validation_codes_present": {
            "missing_decision",
            "missing_confidence",
            "invalid_enum",
            "missing_reason_code",
            "invalid_schema",
            "missing_field",
            "partial_packet",
            "unknown_field",
            "invalid_reason_code",
        }.issubset(rule_codes),
        "mirror_audit_fields_complete": {
            "contract_version",
            "mirror_pattern_id",
            "campaign_id",
            "signal_id",
            "decision",
            "reason_code",
            "validation_result",
            "action",
            "timestamp",
        }.issubset(audit_fields),
        "contract_and_mirror_audit_share_packet_ids": {"campaign_id", "signal_id", "symbol"}.issubset(contract_fields),
        "state_machine_has_failure_states": {"REJECTED", "HOLD"}.issubset(set(inputs["mirror_state_machine"].get("states", []))),
    }
    return audit_payload("mirror_validation_flow_audit_v1", checks)


def build_implementation_readiness(
    compatibility: Mapping[str, Any],
    registry_chain: Mapping[str, Any],
    reason_coverage: Mapping[str, Any],
    validation_flow: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    pipeline_stages = [row.get("stage") for row in inputs["mirror_engine_pipeline"].get("pipeline", [])]
    components = {row.get("component") for row in inputs["mirror_component_definition"].get("components", [])}
    principle = inputs["mirror_reasoning_principle"]
    dependency_checks = {
        "pipeline_accepts_contract_and_registry": tuple(pipeline_stages) == REQUIRED_PIPELINE
        and {"Evidence Normalizer", "Pattern Matcher"}.issubset(set(pipeline_stages)),
        "components_cover_pipeline": {
            "Packet Validator",
            "Evidence Builder",
            "Evidence Normalizer",
            "Pattern Matcher",
            "Decision Builder",
            "Confidence Manager",
            "Explainability Builder",
            "Packet Serializer",
        }.issubset(components),
        "forbidden_direct_inputs_maintained": set(FORBIDDEN_DIRECT_INPUTS).issubset(
            set(inputs["mirror_decision_scope"].get("forbidden_direct_inputs", []))
        ),
        "semantic_rule_maintained": principle.get("semantic_consistency_rule") == "Feature -> Evidence -> Reason -> Decision"
        and principle.get("feature_to_decision_direct_link_allowed") is False,
    }
    prior = [compatibility, registry_chain, reason_coverage, validation_flow]
    checks = {
        "contract_compatibility_pass": all(item["status"] == "PASS" for item in prior[:1]),
        "registry_chain_pass": registry_chain["status"] == "PASS",
        "reason_coverage_pass": reason_coverage["status"] == "PASS",
        "validation_flow_pass": validation_flow["status"] == "PASS",
        **dependency_checks,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    blocking = [key for key, value in checks.items() if not value]
    verdict = "READY" if status == "PASS" else ("PARTIAL" if len(blocking) <= 2 else "BLOCKED")
    return {
        "mirror_implementation_readiness_schema_version": "mirror_implementation_readiness_v1",
        "status": status,
        "readiness_verdict": verdict,
        "checks": checks,
        "blocking_issues": blocking,
        "implementation_scope_allowed_next": verdict == "READY",
        "forbidden_actions_confirmed": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold, gate, score, replay, Campaign Physics, or Production change",
        ],
        "is_trade_command": False,
    }


def build_readiness_report(
    compatibility: Mapping[str, Any],
    registry_chain: Mapping[str, Any],
    reason_coverage: Mapping[str, Any],
    validation_flow: Mapping[str, Any],
    implementation: Mapping[str, Any],
) -> Dict[str, Any]:
    sections = {
        "Contract Compatibility": compatibility["status"],
        "Registry Chain": registry_chain["status"],
        "Reason Coverage": reason_coverage["status"],
        "Validation Flow": validation_flow["status"],
        "Implementation Readiness": implementation["status"],
    }
    blocking = list(implementation["blocking_issues"])
    return {
        "mirror_v1_readiness_report_schema_version": "mirror_v1_readiness_report_v1",
        "audit_version": AUDIT_VERSION,
        "readiness_verdict": implementation["readiness_verdict"],
        "section_status": sections,
        "verified": [key for key, status in sections.items() if status == "PASS"],
        "not_verified": [key for key, status in sections.items() if status != "PASS"],
        "blocking_issues": blocking,
        "next_sprint_recommendation": (
            "READY: proceed to Sprint 12AA Mirror Pattern Engine v1 Implementation. "
            "PARTIAL/BLOCKED: resolve blocking issues before implementation."
        ),
        "is_trade_command": False,
    }


def audit_payload(schema_version: str, checks: Mapping[str, bool]) -> Dict[str, Any]:
    failed = [key for key, value in checks.items() if not value]
    return {
        schema_version.replace("_v1", "_schema_version"): schema_version,
        "status": "PASS" if not failed else "FAIL",
        "checks": dict(checks),
        "blocking_issues": failed,
        "is_trade_command": False,
    }


def load_json(path: Path | str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_v1_readiness_audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
