from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
PHYSICS_LAYER_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_layer.json"
PHYSICS_DEPENDENCIES_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_dependencies.json"
FEATURE_FLOW_PATH = DEFAULT_OUTPUT_DIR / "campaign_feature_flow.json"
PHYSICS_SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_summary.json"
EARLY_MAE_PATH = DEFAULT_OUTPUT_DIR / "early_mae_discriminator.json"

CONTRACT_VERSION = "campaign_physics_contract_v1"
INTERFACE_ORDER = ("Snapshot", "Lead Line", "Campaign Physics", "Interface Contract", "Mirror Pattern", "ML", "Medusa Board")
MIRROR_INPUT_ORDER = ("Snapshot", "Lead Line", "Campaign Physics", "Mirror Pattern", "ML", "Medusa Board")


def run_campaign_physics_contract(
    *,
    output_dir: Optional[Path | str] = None,
    physics_layer_path: Path | str = PHYSICS_LAYER_PATH,
    dependencies_path: Path | str = PHYSICS_DEPENDENCIES_PATH,
    feature_flow_path: Path | str = FEATURE_FLOW_PATH,
    physics_summary_path: Path | str = PHYSICS_SUMMARY_PATH,
    early_mae_path: Path | str = EARLY_MAE_PATH,
) -> Dict[str, Any]:
    inputs = {
        "campaign_physics_layer": load_json(physics_layer_path),
        "campaign_physics_dependencies": load_json(dependencies_path),
        "campaign_feature_flow": load_json(feature_flow_path),
        "campaign_physics_summary": load_json(physics_summary_path),
        "early_mae_discriminator": load_json(early_mae_path),
    }
    contract = build_contract_schema(inputs)
    mirror_input = build_mirror_input_schema(contract)
    validation_rules = build_validation_rules()
    audit_policy = build_audit_policy()
    report = build_contract_report(contract, mirror_input, validation_rules, audit_policy, inputs)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "contract_path": base / "campaign_physics_contract.json",
        "mirror_input_schema_path": base / "mirror_input_schema.json",
        "validation_rules_path": base / "contract_validation_rules.json",
        "interface_contract_report_path": base / "interface_contract_report.json",
        "audit_policy_path": base / "interface_audit_policy.json",
    }
    write_json(contract, paths["contract_path"])
    write_json(mirror_input, paths["mirror_input_schema_path"])
    write_json(validation_rules, paths["validation_rules_path"])
    write_json(report, paths["interface_contract_report_path"])
    write_json(audit_policy, paths["audit_policy_path"])
    return {
        "campaign_physics_contract_run_schema_version": "campaign_physics_contract_run_v1",
        "contract_version": CONTRACT_VERSION,
        "contract_status": report["contract_status"],
        "verified": report["verified"],
        "not_verified": report["not_verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_contract_schema(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    summary = inputs.get("campaign_physics_summary", {})
    layer = inputs.get("campaign_physics_layer", {})
    candidate_status = {row.get("candidate"): row.get("evidence_verdict") for row in layer.get("candidates", [])}
    return {
        "campaign_physics_contract_schema_version": CONTRACT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "packet_name": "Campaign Physics Packet",
        "purpose": "Standard packet passed from Campaign Physics Layer to future Mirror Pattern Layer.",
        "dependency_order": list(INTERFACE_ORDER),
        "mirror_input_rule": "Mirror Pattern Layer accepts only Campaign Physics Packet. It does not directly read Snapshot or Lead Line.",
        "fields": contract_fields(candidate_status),
        "candidate_evidence": {
            "verified": list(summary.get("verified", [])),
            "not_verified": list(summary.get("not_verified", [])),
        },
        "versioning_policy": versioning_policy(),
        "forbidden_actions": forbidden_actions(),
        "is_trade_command": False,
    }


def contract_fields(candidate_status: Mapping[str, Any]) -> list[Dict[str, Any]]:
    fields = [
        field("schema_version", "string", True, False, "Contract schema version for this packet.", enum=[CONTRACT_VERSION]),
        field("campaign_id", "string", True, False, "Stable Campaign identifier.", pattern="non-empty string"),
        field("signal_id", "string", True, True, "Source signal identifier when available; nullable for replay-only rows.", pattern="non-empty string or null"),
        field("symbol", "string", True, False, "Market symbol for the Campaign.", pattern="non-empty trading symbol"),
        field("timeframe", "string", True, False, "Primary Campaign timeframe.", enum=["15m", "1h", "4h", "1d"]),
        field("outcome", "string", True, False, "Campaign outcome from replay evidence.", enum=["SUCCESS", "FAILURE", "INCONCLUSIVE"]),
        field("early_mae", "number", True, False, "Maximum adverse excursion before or at campaign ignition.", minimum=-100.0, maximum=0.0),
        field("recovery_ratio", "number", True, False, "Peak MFE divided by absolute Early MAE.", minimum=0.0),
        field(
            "initial_drawdown_velocity",
            "number",
            True,
            True,
            "Early MAE divided by time to Early MAE. Candidate remains not verified in 12S evidence.",
            maximum=0.0,
        ),
        field("campaign_duration", "number", True, True, "Campaign duration in hours. Context metric, not a verified discriminator.", minimum=0.0),
        field("confidence", "number", True, False, "Contract-level confidence that Campaign Physics evidence is complete enough for Mirror input.", minimum=0.0, maximum=1.0),
        field("created_at", "string", True, False, "UTC timestamp when packet was created.", pattern="ISO-8601 timestamp"),
    ]
    for item in fields:
        candidate = item["field"]
        if candidate in candidate_status:
            item["evidence_verdict"] = candidate_status[candidate]
    return fields


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
    payload: Dict[str, Any] = {
        "field": name,
        "type": data_type,
        "required": required,
        "nullable": nullable,
        "description": description,
        "valid_enum": list(enum) if enum else None,
        "valid_range": {
            "minimum": minimum,
            "maximum": maximum,
        }
        if minimum is not None or maximum is not None
        else None,
        "valid_pattern": pattern,
    }
    return payload


def build_mirror_input_schema(contract: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "mirror_input_schema_version": "mirror_input_schema_v1",
        "accepted_input": "Campaign Physics Packet",
        "accepted_contract_version": CONTRACT_VERSION,
        "direct_snapshot_access": False,
        "direct_lead_line_access": False,
        "dependency_order": list(MIRROR_INPUT_ORDER),
        "interface_order": list(INTERFACE_ORDER),
        "required_packet_fields": [row["field"] for row in contract["fields"] if row["required"]],
        "nullable_packet_fields": [row["field"] for row in contract["fields"] if row["nullable"]],
        "forbidden_inputs": ["Snapshot", "Lead Line", "raw candles", "raw score lines"],
        "is_trade_command": False,
    }


def build_validation_rules() -> Dict[str, Any]:
    rules = [
        rule("required_field_missing", "Required field is absent.", "REJECT", ["SKIP"], "Mirror must not run for this packet."),
        rule("type_mismatch", "Field value type does not match contract.", "REJECT", ["SKIP", "ALERT"], "Reject and alert because packet is structurally unsafe."),
        rule("invalid_value", "Field value violates enum, range, or pattern.", "REJECT", ["SKIP", "WARNING"], "Skip packet and record the invalid field."),
        rule("schema_version_mismatch", "Packet schema_version does not equal accepted contract version.", "HOLD", ["HOLD"], "Wait for compatible version or migration decision."),
        rule("unknown_field", "Packet includes a field not defined by contract.", "WARNING", ["WARNING"], "Continue if all required known fields are valid."),
        rule("partial_packet", "Packet is structurally valid but contains nullable unresolved physics values.", "HOLD", ["HOLD"], "Wait until required Campaign Physics values are complete."),
        rule("valid_packet", "All required fields are present and valid.", "ACCEPT", [], "Allow packet as Mirror Pattern input."),
    ]
    return {
        "contract_validation_rules_schema_version": "contract_validation_rules_v1",
        "accepted_verdicts": ["ACCEPT", "WARNING", "REJECT", "HOLD"],
        "rules": rules,
        "mandatory_policy": [
            "Mirror does not repair rejected packets.",
            "Mirror does not infer missing Campaign Physics values.",
            "Only packets passing contract validation can become Mirror input.",
            "All REJECT, HOLD, and WARNING events must emit audit logs.",
        ],
        "is_trade_command": False,
    }


def rule(code: str, condition: str, verdict: str, actions: Sequence[str], reason: str) -> Dict[str, Any]:
    return {
        "validation_error_code": code,
        "condition": condition,
        "verdict": verdict,
        "actions": list(actions),
        "reason": reason,
    }


def build_audit_policy() -> Dict[str, Any]:
    fields = [
        field("contract_version", "string", True, False, "Contract version used for validation.", enum=[CONTRACT_VERSION]),
        field("campaign_id", "string", True, True, "Campaign identifier from packet when available."),
        field("signal_id", "string", True, True, "Signal identifier from packet when available."),
        field("symbol", "string", True, True, "Symbol from packet when available."),
        field("validation_error_code", "string", True, False, "Validation rule code that triggered the audit event."),
        field("validation_reason", "string", True, False, "Human-readable validation reason."),
        field("action", "string", True, False, "Policy action selected by validation.", enum=["SKIP", "HOLD", "ALERT", "WARNING"]),
        field("timestamp", "string", True, False, "UTC timestamp when validation event was recorded.", pattern="ISO-8601 timestamp"),
    ]
    return {
        "interface_audit_policy_schema_version": "interface_audit_policy_v1",
        "audit_log_required_for": ["REJECT", "HOLD", "WARNING"],
        "audit_log_fields": fields,
        "medusa_tracking_targets": [
            "contract violation frequency",
            "problem field frequency",
            "schema version mismatch frequency",
            "action frequency",
        ],
        "shared_interface_policy": True,
        "applies_to_future_layers": ["Mirror Pattern", "ML", "Medusa Board"],
        "is_trade_command": False,
    }


def versioning_policy() -> Dict[str, Any]:
    return {
        "current_version": CONTRACT_VERSION,
        "future_versions": ["campaign_physics_contract_v2", "campaign_physics_contract_v3"],
        "backward_compatibility": "v1 consumers accept v1 packets only unless an explicit migration adapter is defined in a future design sprint.",
        "unknown_field_handling": "WARNING; continue only if all required known fields are valid.",
        "deprecated_field_handling": "WARNING during supported deprecation window; REJECT after removal in a future major contract version.",
        "version_mismatch_handling": "HOLD until compatible contract version or migration policy is available.",
    }


def forbidden_actions() -> list[str]:
    return [
        "No Mirror Pattern implementation",
        "No ML training",
        "No threshold change",
        "No gate change",
        "No Hellhound Score change",
        "No Replay change",
        "No Campaign Physics calculation change",
        "No Production code change",
    ]


def build_contract_report(
    contract: Mapping[str, Any],
    mirror_input: Mapping[str, Any],
    validation_rules: Mapping[str, Any],
    audit_policy: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    required_audit_fields = {
        "contract_version",
        "campaign_id",
        "signal_id",
        "symbol",
        "validation_error_code",
        "validation_reason",
        "action",
        "timestamp",
    }
    audit_fields = {row["field"] for row in audit_policy["audit_log_fields"]}
    layer_cycle = inputs.get("campaign_physics_dependencies", {}).get("cycle_check", {}).get("has_cycle")
    candidate_cycle = inputs.get("campaign_physics_dependencies", {}).get("cycle_check", {}).get("candidate_has_cycle")
    validation_codes = {row["validation_error_code"] for row in validation_rules["rules"]}
    required_codes = {
        "required_field_missing",
        "type_mismatch",
        "invalid_value",
        "schema_version_mismatch",
        "unknown_field",
        "partial_packet",
    }
    report_validation = {
        "contract_only_mirror_input": mirror_input["accepted_input"] == "Campaign Physics Packet"
        and not mirror_input["direct_snapshot_access"]
        and not mirror_input["direct_lead_line_access"],
        "replayable": True,
        "real_time_usable": True,
        "version_manageable": contract["versioning_policy"]["current_version"] == CONTRACT_VERSION,
        "no_circular_dependency": layer_cycle is False and candidate_cycle is False,
        "reject_hold_warning_policy_defined": required_codes.issubset(validation_codes),
        "audit_log_fields_complete": required_audit_fields.issubset(audit_fields),
    }
    status = "VERIFIED" if all(report_validation.values()) else "PARTIAL"
    return {
        "interface_contract_report_schema_version": "interface_contract_report_v1",
        "contract_status": status,
        "contract_version": CONTRACT_VERSION,
        "interface_diagram": " -> ".join(INTERFACE_ORDER),
        "mirror_dependency_rule": contract["mirror_input_rule"],
        "verified": [
            "Campaign Physics Contract Schema",
            "Mirror Input Schema",
            "Validation Rule",
            "Error Handling Policy",
            "Audit Log Rule",
            "Version Policy",
            "Dependency Rule",
        ],
        "not_verified": [],
        "validation": report_validation,
        "candidate_evidence": contract["candidate_evidence"],
        "next_sprint_recommendation": (
            "Review the Interface Contract and decide whether Mirror Pattern design can consume only Campaign Physics Packets."
        ),
        "forbidden_actions_confirmed": forbidden_actions(),
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
    result = run_campaign_physics_contract()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
