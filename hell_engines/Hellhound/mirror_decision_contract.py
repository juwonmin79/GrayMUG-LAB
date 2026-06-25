from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CAMPAIGN_PHYSICS_CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_contract.json"
MIRROR_INPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_input_schema.json"
PHYSICS_SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_summary.json"
EARLY_MAE_PATH = DEFAULT_OUTPUT_DIR / "early_mae_discriminator.json"
FEATURE_FLOW_PATH = DEFAULT_OUTPUT_DIR / "campaign_feature_flow.json"
INTERFACE_REPORT_PATH = DEFAULT_OUTPUT_DIR / "interface_contract_report.json"

MIRROR_CONTRACT_VERSION = "mirror_decision_contract_v1"
MIRROR_DECISION_ENUM = ("REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE")
ALLOWED_INPUT_FEATURES = ("early_mae", "recovery_ratio", "campaign_duration", "initial_drawdown_velocity", "confidence")
FORBIDDEN_INPUTS = ("Raw Candle", "Snapshot", "Lead Line", "Raw Score")
REASON_CODES = (
    "EARLY_MAE_NORMAL",
    "EARLY_MAE_EXCESSIVE",
    "RECOVERY_RATIO_STRONG",
    "RECOVERY_RATIO_WEAK",
    "CAMPAIGN_DURATION_CONTEXT_ONLY",
    "INITIAL_DRAWDOWN_VELOCITY_CONTEXT_ONLY",
    "CAMPAIGN_EVIDENCE_INSUFFICIENT",
    "CONTRACT_VALIDATION_PASSED",
)


def run_mirror_decision_contract(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_physics_contract_path: Path | str = CAMPAIGN_PHYSICS_CONTRACT_PATH,
    mirror_input_schema_path: Path | str = MIRROR_INPUT_SCHEMA_PATH,
    physics_summary_path: Path | str = PHYSICS_SUMMARY_PATH,
    early_mae_path: Path | str = EARLY_MAE_PATH,
    feature_flow_path: Path | str = FEATURE_FLOW_PATH,
    interface_report_path: Path | str = INTERFACE_REPORT_PATH,
) -> Dict[str, Any]:
    inputs = {
        "campaign_physics_contract": load_json(campaign_physics_contract_path),
        "mirror_input_schema": load_json(mirror_input_schema_path),
        "campaign_physics_summary": load_json(physics_summary_path),
        "early_mae_discriminator": load_json(early_mae_path),
        "campaign_feature_flow": load_json(feature_flow_path),
        "interface_contract_report": load_json(interface_report_path),
    }
    scope = build_decision_scope(inputs)
    output_schema = build_output_schema(scope)
    explainability = build_explainability_rules()
    validation_rules = build_validation_rules()
    dependency_graph = build_dependency_graph(inputs)
    report = build_contract_report(scope, output_schema, explainability, validation_rules, dependency_graph, inputs)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "decision_scope_path": base / "mirror_decision_scope.json",
        "output_schema_path": base / "mirror_output_schema.json",
        "explainability_rules_path": base / "mirror_explainability_rules.json",
        "validation_rules_path": base / "mirror_validation_rules.json",
        "decision_contract_report_path": base / "mirror_decision_contract_report.json",
        "dependency_graph_path": base / "mirror_dependency_graph.json",
    }
    write_json(scope, paths["decision_scope_path"])
    write_json(output_schema, paths["output_schema_path"])
    write_json(explainability, paths["explainability_rules_path"])
    write_json(validation_rules, paths["validation_rules_path"])
    write_json(report, paths["decision_contract_report_path"])
    write_json(dependency_graph, paths["dependency_graph_path"])
    return {
        "mirror_decision_contract_run_schema_version": "mirror_decision_contract_run_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "contract_status": report["contract_status"],
        "verified": report["verified"],
        "not_verified": report["not_verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_decision_scope(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "mirror_decision_scope_schema_version": "mirror_decision_scope_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "decision_objective": "Judge Campaign authenticity, not price direction.",
        "decision_enum": list(MIRROR_DECISION_ENUM),
        "accepted_input": inputs.get("mirror_input_schema", {}).get("accepted_input", "Campaign Physics Packet"),
        "input_contract_version": inputs.get("campaign_physics_contract", {}).get("contract_version"),
        "allowed_input_features": list(ALLOWED_INPUT_FEATURES),
        "forbidden_direct_inputs": list(FORBIDDEN_INPUTS),
        "decision_scope_limits": [
            "No price direction prediction.",
            "No entry or exit advice.",
            "No threshold change.",
            "No raw candle, Snapshot, Lead Line, or Raw Score access.",
        ],
        "is_trade_command": False,
    }


def build_output_schema(scope: Mapping[str, Any]) -> Dict[str, Any]:
    fields = [
        field("schema_version", "string", True, False, "Mirror output schema version.", enum=[MIRROR_CONTRACT_VERSION]),
        field("mirror_pattern_id", "string", True, False, "Stable Mirror Pattern decision identifier."),
        field("campaign_id", "string", True, False, "Campaign id copied from Campaign Physics Packet."),
        field("signal_id", "string", True, True, "Signal id copied from Campaign Physics Packet when available."),
        field("symbol", "string", True, False, "Market symbol copied from Campaign Physics Packet."),
        field("mirror_decision", "string", True, False, "Campaign authenticity decision.", enum=list(MIRROR_DECISION_ENUM)),
        field("confidence", "number", True, False, "Mirror decision confidence.", minimum=0.0, maximum=1.0),
        field("explainability", "object", True, False, "Reason-code based explanation object; free-form LLM prose is forbidden."),
        field("supporting_features", "object", True, False, "Allowed Campaign Physics features used for the decision."),
        field("validation_state", "string", True, False, "Mirror output validation state.", enum=["ACCEPT", "WARNING", "HOLD", "REJECT"]),
        field("created_at", "string", True, False, "UTC timestamp when Mirror output packet is created.", pattern="ISO-8601 timestamp"),
    ]
    return {
        "mirror_output_schema_version": "mirror_output_schema_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "input_rule": scope["accepted_input"],
        "fields": fields,
        "required_fields": [row["field"] for row in fields if row["required"]],
        "decision_enum": list(MIRROR_DECISION_ENUM),
        "reason_code_required": True,
        "freeform_explanation_allowed": False,
        "is_trade_command": False,
    }


def field(
    name: str,
    data_type: str,
    required: bool,
    nullable: bool,
    description: str,
    *,
    enum: Optional[Sequence[str]] = None,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "field": name,
        "type": data_type,
        "required": required,
        "nullable": nullable,
        "description": description,
        "valid_enum": list(enum) if enum else None,
        "valid_range": {"minimum": minimum, "maximum": maximum}
        if minimum is not None or maximum is not None
        else None,
        "valid_pattern": pattern,
    }


def build_explainability_rules() -> Dict[str, Any]:
    return {
        "mirror_explainability_rules_schema_version": "mirror_explainability_rules_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "freeform_llm_narrative_allowed": False,
        "reason_code_required": True,
        "allowed_reason_codes": list(REASON_CODES),
        "decision_reason_map": {
            "REAL_WHALE_BACK": ["EARLY_MAE_NORMAL", "RECOVERY_RATIO_STRONG", "CONTRACT_VALIDATION_PASSED"],
            "FAKE_WHALE_BACK": ["EARLY_MAE_EXCESSIVE", "RECOVERY_RATIO_WEAK", "CONTRACT_VALIDATION_PASSED"],
            "INCONCLUSIVE": ["CAMPAIGN_EVIDENCE_INSUFFICIENT"],
        },
        "supporting_feature_policy": {
            "allowed": list(ALLOWED_INPUT_FEATURES),
            "forbidden": list(FORBIDDEN_INPUTS),
        },
        "is_trade_command": False,
    }


def build_validation_rules() -> Dict[str, Any]:
    return {
        "mirror_validation_rules_schema_version": "mirror_validation_rules_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "rules": [
            rule("missing_decision", "mirror_decision is missing.", "REJECT", ["SKIP"]),
            rule("missing_confidence", "confidence is missing.", "REJECT", ["SKIP"]),
            rule("invalid_enum", "mirror_decision or validation_state is outside valid enum.", "REJECT", ["ALERT"]),
            rule("missing_reason_code", "explainability.reason_codes is missing or empty.", "REJECT", ["SKIP"]),
            rule("invalid_schema", "schema_version does not match Mirror contract.", "REJECT", ["ALERT"]),
            rule("missing_field", "Required Mirror output field is missing.", "REJECT", ["SKIP"]),
            rule("partial_packet", "Mirror output packet is structurally incomplete.", "HOLD", ["HOLD"]),
            rule("unknown_field", "Mirror output packet includes an unknown field.", "WARNING", ["WARNING"]),
            rule("invalid_reason_code", "Reason code is not in allowed reason-code registry.", "REJECT", ["SKIP"]),
            rule("valid_packet", "Mirror output packet passes validation and can be emitted.", "ACCEPT", ["PASS"]),
        ],
        "error_handling_policy": [
            "missing_field -> REJECT -> SKIP",
            "invalid_enum -> REJECT -> ALERT",
            "partial_packet -> HOLD",
            "unknown_field -> WARNING",
            "invalid_reason_code -> REJECT",
            "valid_packet -> ACCEPT -> PASS",
            "Mirror does not repair or infer rejected packets.",
        ],
        "audit_policy": {
            "audit_log_required": True,
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
            ],
            "reproducibility_required": True,
        },
        "is_trade_command": False,
    }


def rule(code: str, condition: str, verdict: str, actions: Sequence[str]) -> Dict[str, Any]:
    return {
        "validation_error_code": code,
        "condition": condition,
        "verdict": verdict,
        "actions": list(actions),
    }


def build_dependency_graph(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    edges = [
        {"from": "Campaign Physics", "to": "Mirror Decision", "dependency_type": "contract_packet_input"},
        {"from": "Mirror Decision", "to": "Mirror Packet", "dependency_type": "decision_output"},
        {"from": "Mirror Packet", "to": "ML", "dependency_type": "future_training_input"},
        {"from": "ML", "to": "Medusa", "dependency_type": "future_board_input"},
    ]
    return {
        "mirror_dependency_graph_schema_version": "mirror_dependency_graph_v1",
        "dependency_diagram": "Campaign Physics -> Mirror Decision -> Mirror Packet -> ML -> Medusa",
        "edges": edges,
        "mirror_depends_on_ml": False,
        "ml_learns_from_mirror": True,
        "mirror_input_source": inputs.get("mirror_input_schema", {}).get("accepted_input", "Campaign Physics Packet"),
        "forbidden_direct_inputs": list(FORBIDDEN_INPUTS),
        "has_cycle": has_cycle(edges),
        "is_trade_command": False,
    }


def has_cycle(edges: Sequence[Mapping[str, str]]) -> bool:
    graph: Dict[str, list[str]] = {}
    for edge in edges:
        graph.setdefault(str(edge["from"]), []).append(str(edge["to"]))
        graph.setdefault(str(edge["to"]), [])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, []):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def build_contract_report(
    scope: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    explainability: Mapping[str, Any],
    validation_rules: Mapping[str, Any],
    dependency_graph: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    validation_codes = {row["validation_error_code"] for row in validation_rules["rules"]}
    required_codes = {
        "missing_decision",
        "missing_confidence",
        "invalid_enum",
        "missing_reason_code",
        "invalid_schema",
        "missing_field",
        "partial_packet",
        "unknown_field",
        "invalid_reason_code",
    }
    required_audit = {
        "contract_version",
        "mirror_pattern_id",
        "campaign_id",
        "signal_id",
        "decision",
        "reason_code",
        "validation_result",
        "action",
        "timestamp",
    }
    audit_fields = set(validation_rules["audit_policy"]["audit_log_fields"])
    checks = {
        "decision_scope_defined": tuple(scope["decision_enum"]) == MIRROR_DECISION_ENUM,
        "campaign_physics_packet_only": scope["accepted_input"] == "Campaign Physics Packet",
        "forbidden_inputs_blocked": set(FORBIDDEN_INPUTS).issubset(set(scope["forbidden_direct_inputs"])),
        "output_schema_defined": set(output_schema["required_fields"]) == {
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
        },
        "explainability_reason_code_based": explainability["reason_code_required"]
        and not explainability["freeform_llm_narrative_allowed"],
        "validation_rules_defined": required_codes.issubset(validation_codes),
        "audit_policy_defined": required_audit.issubset(audit_fields),
        "dependency_rule_defined": dependency_graph["mirror_depends_on_ml"] is False
        and dependency_graph["ml_learns_from_mirror"] is True
        and not dependency_graph["has_cycle"],
        "input_contract_verified": inputs.get("interface_contract_report", {}).get("contract_status") == "VERIFIED",
    }
    status = "VERIFIED" if all(checks.values()) else "PARTIAL"
    return {
        "mirror_decision_contract_report_schema_version": "mirror_decision_contract_report_v1",
        "contract_version": MIRROR_CONTRACT_VERSION,
        "contract_status": status,
        "verified": [
            "Mirror Decision Scope",
            "Mirror Output Schema",
            "Explainability Rule",
            "Validation Rule",
            "Error Handling Policy",
            "Audit Policy",
            "Dependency Rule",
        ]
        if status == "VERIFIED"
        else [key for key, value in checks.items() if value],
        "not_verified": [] if status == "VERIFIED" else [key for key, value in checks.items() if not value],
        "decision_enum": list(MIRROR_DECISION_ENUM),
        "allowed_input_features": list(ALLOWED_INPUT_FEATURES),
        "forbidden_direct_inputs": list(FORBIDDEN_INPUTS),
        "validation": checks,
        "dependency_diagram": dependency_graph["dependency_diagram"],
        "next_sprint_recommendation": (
            "Review Mirror Pattern design against this Decision Contract before any implementation."
        ),
        "forbidden_actions_confirmed": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold change",
            "No gate change",
            "No score change",
            "No Replay change",
            "No Campaign Physics calculation change",
            "No Production change",
        ],
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
    result = run_mirror_decision_contract()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
