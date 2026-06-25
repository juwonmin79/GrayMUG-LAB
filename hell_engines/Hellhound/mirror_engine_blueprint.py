from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DECISION_SCOPE_PATH = DEFAULT_OUTPUT_DIR / "mirror_decision_scope.json"
OUTPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_output_schema.json"
VALIDATION_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_validation_rules.json"
EXPLAINABILITY_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_explainability_rules.json"
CAMPAIGN_PHYSICS_CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_contract.json"
DEPENDENCY_GRAPH_PATH = DEFAULT_OUTPUT_DIR / "mirror_dependency_graph.json"
INTERFACE_REPORT_PATH = DEFAULT_OUTPUT_DIR / "interface_contract_report.json"

BLUEPRINT_VERSION = "mirror_engine_blueprint_v1"
PIPELINE_STAGES = (
    "Campaign Physics Packet",
    "Packet Validation",
    "Evidence Builder",
    "Evidence Normalizer",
    "Pattern Matcher",
    "Decision Builder",
    "Explainability Builder",
    "Mirror Pattern Packet",
)
ENGINE_STATES = (
    "IDLE",
    "WAIT_PACKET",
    "VALIDATING",
    "BUILDING_EVIDENCE",
    "NORMALIZING",
    "MATCHING",
    "BUILDING_DECISION",
    "BUILDING_EXPLAINABILITY",
    "PACKET_READY",
    "REJECTED",
    "HOLD",
)
FORBIDDEN_DEPENDENCIES = ("Snapshot", "Lead Line", "Raw Candle", "ML", "Medusa", "Production")


def run_mirror_engine_blueprint(
    *,
    output_dir: Optional[Path | str] = None,
    decision_scope_path: Path | str = DECISION_SCOPE_PATH,
    output_schema_path: Path | str = OUTPUT_SCHEMA_PATH,
    validation_rules_path: Path | str = VALIDATION_RULES_PATH,
    explainability_rules_path: Path | str = EXPLAINABILITY_RULES_PATH,
    campaign_physics_contract_path: Path | str = CAMPAIGN_PHYSICS_CONTRACT_PATH,
    dependency_graph_path: Path | str = DEPENDENCY_GRAPH_PATH,
    interface_report_path: Path | str = INTERFACE_REPORT_PATH,
) -> Dict[str, Any]:
    inputs = {
        "mirror_decision_scope": load_json(decision_scope_path),
        "mirror_output_schema": load_json(output_schema_path),
        "mirror_validation_rules": load_json(validation_rules_path),
        "mirror_explainability_rules": load_json(explainability_rules_path),
        "campaign_physics_contract": load_json(campaign_physics_contract_path),
        "mirror_dependency_graph": load_json(dependency_graph_path),
        "interface_contract_report": load_json(interface_report_path),
    }
    pipeline = build_engine_pipeline(inputs)
    components = build_component_definition()
    state_machine = build_state_machine()
    evidence_lifecycle = build_evidence_lifecycle()
    confidence_lifecycle = build_confidence_lifecycle()
    failure_flow = build_failure_flow(inputs)
    extension_points = build_extension_points()
    report = build_blueprint_report(
        pipeline,
        components,
        state_machine,
        evidence_lifecycle,
        confidence_lifecycle,
        failure_flow,
        extension_points,
        inputs,
    )

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "engine_pipeline_path": base / "mirror_engine_pipeline.json",
        "component_definition_path": base / "mirror_component_definition.json",
        "state_machine_path": base / "mirror_state_machine.json",
        "evidence_lifecycle_path": base / "mirror_evidence_lifecycle.json",
        "confidence_lifecycle_path": base / "mirror_confidence_lifecycle.json",
        "failure_flow_path": base / "mirror_failure_flow.json",
        "extension_points_path": base / "mirror_extension_points.json",
        "blueprint_report_path": base / "mirror_engine_blueprint_report.json",
    }
    write_json(pipeline, paths["engine_pipeline_path"])
    write_json(components, paths["component_definition_path"])
    write_json(state_machine, paths["state_machine_path"])
    write_json(evidence_lifecycle, paths["evidence_lifecycle_path"])
    write_json(confidence_lifecycle, paths["confidence_lifecycle_path"])
    write_json(failure_flow, paths["failure_flow_path"])
    write_json(extension_points, paths["extension_points_path"])
    write_json(report, paths["blueprint_report_path"])
    return {
        "mirror_engine_blueprint_run_schema_version": "mirror_engine_blueprint_run_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "blueprint_status": report["blueprint_status"],
        "verified": report["verified"],
        "not_verified": report["not_verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_engine_pipeline(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "mirror_engine_pipeline_schema_version": "mirror_engine_pipeline_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "semantic_layer_definition": semantic_layer_definition(),
        "pipeline": [
            stage("Campaign Physics Packet", "Contract-valid input packet.", "Campaign Physics Contract output.", "Packet Validation", ["Campaign Physics Contract"]),
            stage("Packet Validation", "Validate packet schema and allowed input boundary.", "Campaign Physics Packet", "Validated Packet or failure state", ["Mirror validation rules"]),
            stage("Evidence Builder", "Select allowed physics fields and create internal evidence record.", "Validated Packet", "Evidence", ["Mirror Decision Scope"]),
            stage("Evidence Normalizer", "Convert evidence into comparable internal representation without changing thresholds.", "Evidence", "Normalized Evidence", ["Feature Registry"]),
            stage("Pattern Matcher", "Map normalized evidence to registered semantic pattern candidates.", "Normalized Evidence", "Matched Pattern", ["Evidence Registry", "Reason Registry"]),
            stage("Decision Builder", "Create Mirror decision enum from matched pattern evidence.", "Matched Pattern", "Decision", ["Mirror Decision Contract"]),
            stage("Explainability Builder", "Attach reason codes as the only explanation source.", "Decision and Matched Evidence", "Reason Code set", ["Reason Registry"]),
            stage("Mirror Pattern Packet", "Serialize decision into Mirror output packet.", "Decision and Reason Code set", "Mirror Pattern Packet", ["Mirror Output Schema"]),
        ],
        "is_trade_command": False,
    }


def stage(name: str, role: str, input_name: str, output_name: str, dependencies: Sequence[str]) -> Dict[str, Any]:
    return {"stage": name, "role": role, "input": input_name, "output": output_name, "dependencies": list(dependencies)}


def build_component_definition() -> Dict[str, Any]:
    components = [
        component("Packet Validator", "Validate Campaign Physics Packet contract only.", "Campaign Physics Packet", "Validated Packet or validation failure"),
        component("Evidence Builder", "Extract allowed Campaign Physics evidence.", "Validated Packet", "Evidence"),
        component("Evidence Normalizer", "Normalize evidence representation without calculating thresholds.", "Evidence", "Normalized Evidence"),
        component("Pattern Matcher", "Match normalized evidence to registered semantic pattern definitions.", "Normalized Evidence", "Matched Pattern"),
        component("Decision Builder", "Build REAL_WHALE_BACK, FAKE_WHALE_BACK, or INCONCLUSIVE decision.", "Matched Pattern", "Decision"),
        component("Confidence Manager", "Own confidence lifecycle and freeze point; no formula defined.", "Evidence and Decision context", "Confidence state"),
        component("Explainability Builder", "Generate reason codes; no free-form narrative.", "Matched Evidence and Decision", "Reason Code set"),
        component("Packet Serializer", "Serialize Mirror Pattern Packet from schema.", "Decision, confidence, reason codes", "Mirror Pattern Packet"),
    ]
    return {
        "mirror_component_definition_schema_version": "mirror_component_definition_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "single_responsibility_required": True,
        "components": components,
        "is_trade_command": False,
    }


def component(name: str, responsibility: str, input_name: str, output_name: str) -> Dict[str, Any]:
    return {"component": name, "responsibility": responsibility, "input": input_name, "output": output_name}


def build_state_machine() -> Dict[str, Any]:
    transitions = [
        transition("IDLE", "WAIT_PACKET", "engine_ready"),
        transition("WAIT_PACKET", "VALIDATING", "packet_received"),
        transition("VALIDATING", "BUILDING_EVIDENCE", "packet_accept_or_warning"),
        transition("VALIDATING", "REJECTED", "validation_reject"),
        transition("VALIDATING", "HOLD", "validation_hold"),
        transition("BUILDING_EVIDENCE", "NORMALIZING", "evidence_available"),
        transition("BUILDING_EVIDENCE", "HOLD", "evidence_missing"),
        transition("NORMALIZING", "MATCHING", "normalization_complete"),
        transition("MATCHING", "BUILDING_DECISION", "pattern_match_complete"),
        transition("MATCHING", "HOLD", "unsupported_feature_or_version"),
        transition("BUILDING_DECISION", "BUILDING_EXPLAINABILITY", "decision_built"),
        transition("BUILDING_EXPLAINABILITY", "PACKET_READY", "reason_code_attached"),
        transition("BUILDING_EXPLAINABILITY", "REJECTED", "reason_code_failure"),
        transition("PACKET_READY", "IDLE", "packet_emitted"),
        transition("REJECTED", "IDLE", "failure_audited"),
        transition("HOLD", "WAIT_PACKET", "additional_data_or_version_available"),
    ]
    return {
        "mirror_state_machine_schema_version": "mirror_state_machine_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "states": list(ENGINE_STATES),
        "transitions": transitions,
        "state_transition_diagram": "IDLE -> WAIT_PACKET -> VALIDATING -> BUILDING_EVIDENCE -> NORMALIZING -> MATCHING -> BUILDING_DECISION -> BUILDING_EXPLAINABILITY -> PACKET_READY",
        "failure_states": ["REJECTED", "HOLD"],
        "is_trade_command": False,
    }


def transition(source: str, target: str, event: str) -> Dict[str, str]:
    return {"from": source, "to": target, "event": event}


def build_evidence_lifecycle() -> Dict[str, Any]:
    return {
        "mirror_evidence_lifecycle_schema_version": "mirror_evidence_lifecycle_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "lifecycle": [
            {"stage": "Packet", "owner": "Packet Validator", "artifact": "Campaign Physics Packet"},
            {"stage": "Evidence", "owner": "Evidence Builder", "artifact": "Allowed Campaign Physics evidence"},
            {"stage": "Normalized Evidence", "owner": "Evidence Normalizer", "artifact": "Comparable evidence representation"},
            {"stage": "Matched Pattern", "owner": "Pattern Matcher", "artifact": "Registered semantic match"},
            {"stage": "Decision", "owner": "Decision Builder", "artifact": "Mirror decision enum"},
            {"stage": "Reason Code", "owner": "Explainability Builder", "artifact": "Reason-code evidence"},
            {"stage": "Mirror Packet", "owner": "Packet Serializer", "artifact": "Mirror Pattern Packet"},
        ],
        "explainability_lifecycle": [
            "Evidence",
            "Matched Evidence",
            "Reason Code",
            "Mirror Packet",
            "Audit Log",
            "ML",
            "Medusa",
        ],
        "reason_code_is_only_explainability_source": True,
        "is_trade_command": False,
    }


def build_confidence_lifecycle() -> Dict[str, Any]:
    return {
        "mirror_confidence_lifecycle_schema_version": "mirror_confidence_lifecycle_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "calculation_formula_defined": False,
        "created_by": "Confidence Manager",
        "creation_point": "After Evidence Normalizer and before Decision Builder.",
        "modifiable_by": ["Confidence Manager", "Decision Builder"],
        "freeze_point": "Packet Serializer freezes final confidence in Mirror Pattern Packet.",
        "audit_requirement": "Any confidence state used in a Mirror Packet must be reproducible from registered evidence and reason codes.",
        "is_trade_command": False,
    }


def build_failure_flow(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    validation_rules = inputs.get("mirror_validation_rules", {}).get("rules", [])
    return {
        "mirror_failure_flow_schema_version": "mirror_failure_flow_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "failure_policy": [
            failure("Packet Error", "REJECT", ["SKIP"], "Packet Validator"),
            failure("Validation Fail", "REJECT", ["SKIP", "ALERT"], "Packet Validator"),
            failure("Evidence Missing", "HOLD", ["HOLD"], "Evidence Builder"),
            failure("Unsupported Version", "HOLD", ["HOLD", "ALERT"], "Packet Validator"),
            failure("Unknown Feature", "WARNING", ["WARNING"], "Evidence Normalizer"),
            failure("Reason Code Failure", "REJECT", ["SKIP"], "Explainability Builder"),
        ],
        "source_validation_rules": validation_rules,
        "mirror_repairs_or_infers_rejected_packets": False,
        "is_trade_command": False,
    }


def failure(name: str, verdict: str, actions: Sequence[str], owner: str) -> Dict[str, Any]:
    return {"failure": name, "verdict": verdict, "actions": list(actions), "owner": owner}


def build_extension_points() -> Dict[str, Any]:
    return {
        "mirror_extension_points_schema_version": "mirror_extension_points_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "extension_points": [
            {
                "registry": "Feature Registry",
                "purpose": "Register future Campaign Physics features without changing engine pipeline stages.",
                "allowed_to_change_engine": False,
            },
            {
                "registry": "Reason Registry",
                "purpose": "Register reason codes for new Mirror semantics.",
                "allowed_to_change_engine": False,
            },
            {
                "registry": "Evidence Registry",
                "purpose": "Register semantic evidence groups consumed by Pattern Matcher.",
                "allowed_to_change_engine": False,
            },
        ],
        "compatibility_rule": "New features must enter through Campaign Physics Packet and registry metadata.",
        "is_trade_command": False,
    }


def semantic_layer_definition() -> str:
    return (
        "Mirror is not a price prediction engine. Mirror is the Semantic Interpretation Layer that converts "
        "Campaign Physics Evidence into Meaning."
    )


def build_blueprint_report(
    pipeline: Mapping[str, Any],
    components: Mapping[str, Any],
    state_machine: Mapping[str, Any],
    evidence_lifecycle: Mapping[str, Any],
    confidence_lifecycle: Mapping[str, Any],
    failure_flow: Mapping[str, Any],
    extension_points: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    checks = {
        "engine_pipeline_defined": [row["stage"] for row in pipeline["pipeline"]] == list(PIPELINE_STAGES),
        "component_definition_defined": len(components["components"]) == 8 and components["single_responsibility_required"],
        "state_machine_defined": set(ENGINE_STATES).issubset(set(state_machine["states"])),
        "evidence_lifecycle_defined": evidence_lifecycle["reason_code_is_only_explainability_source"],
        "confidence_lifecycle_defined": confidence_lifecycle["calculation_formula_defined"] is False,
        "explainability_lifecycle_defined": "Reason Code" in evidence_lifecycle["explainability_lifecycle"],
        "failure_flow_defined": len(failure_flow["failure_policy"]) >= 6,
        "extension_points_defined": {row["registry"] for row in extension_points["extension_points"]}
        == {"Feature Registry", "Reason Registry", "Evidence Registry"},
        "semantic_layer_defined": "Semantic Interpretation Layer" in pipeline["semantic_layer_definition"],
        "dependency_rule_defined": inputs.get("mirror_dependency_graph", {}).get("mirror_depends_on_ml") is False,
        "input_contract_verified": inputs.get("interface_contract_report", {}).get("contract_status") == "VERIFIED",
    }
    status = "VERIFIED" if all(checks.values()) else "PARTIAL"
    return {
        "mirror_engine_blueprint_report_schema_version": "mirror_engine_blueprint_report_v1",
        "blueprint_version": BLUEPRINT_VERSION,
        "blueprint_status": status,
        "semantic_layer_definition": semantic_layer_definition(),
        "verified": [
            "Engine Pipeline",
            "Component Definition",
            "State Machine",
            "Evidence Lifecycle",
            "Confidence Lifecycle",
            "Explainability Lifecycle",
            "Failure Flow",
            "Extension Point",
            "Semantic Layer Definition",
            "Dependency Rule",
        ]
        if status == "VERIFIED"
        else [key for key, value in checks.items() if value],
        "not_verified": [] if status == "VERIFIED" else [key for key, value in checks.items() if not value],
        "validation": checks,
        "forbidden_dependencies": list(FORBIDDEN_DEPENDENCIES),
        "forbidden_actions_confirmed": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold generation or change",
            "No gate change",
            "No score change",
            "No Replay change",
            "No Campaign Physics change",
            "No Production change",
        ],
        "next_sprint_recommendation": "Sprint 12Y should review registry contracts before any Mirror implementation.",
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
    result = run_mirror_engine_blueprint()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
