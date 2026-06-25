from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_contract.json"
MIRROR_INPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_input_schema.json"
VALIDATION_RULES_PATH = DEFAULT_OUTPUT_DIR / "contract_validation_rules.json"
AUDIT_POLICY_PATH = DEFAULT_OUTPUT_DIR / "interface_audit_policy.json"
CAMPAIGN_DATASET_PATH = DEFAULT_OUTPUT_DIR / "campaign_replay_dataset.json"
PHYSICS_SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_summary.json"
EARLY_MAE_PATH = DEFAULT_OUTPUT_DIR / "early_mae_discriminator.json"


def run_mirror_input_readiness(
    *,
    output_dir: Optional[Path | str] = None,
    contract_path: Path | str = CONTRACT_PATH,
    mirror_input_schema_path: Path | str = MIRROR_INPUT_SCHEMA_PATH,
    validation_rules_path: Path | str = VALIDATION_RULES_PATH,
    audit_policy_path: Path | str = AUDIT_POLICY_PATH,
    campaign_dataset_path: Path | str = CAMPAIGN_DATASET_PATH,
    physics_summary_path: Path | str = PHYSICS_SUMMARY_PATH,
    early_mae_path: Path | str = EARLY_MAE_PATH,
) -> Dict[str, Any]:
    inputs = {
        "contract": load_json(contract_path),
        "mirror_input_schema": load_json(mirror_input_schema_path),
        "validation_rules": load_json(validation_rules_path),
        "audit_policy": load_json(audit_policy_path),
        "campaign_dataset": load_json(campaign_dataset_path),
        "campaign_physics_summary": load_json(physics_summary_path),
        "early_mae_discriminator": load_json(early_mae_path),
    }
    packets = build_campaign_physics_packets(inputs)
    validation_result = validate_packets(packets, inputs["contract"], inputs["validation_rules"])
    audit = simulate_audit_log(validation_result, inputs["audit_policy"], inputs["contract"])
    summary = build_readiness_summary(validation_result, audit)
    report = build_readiness_report(inputs, validation_result, audit, summary)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "readiness_report_path": base / "mirror_input_readiness_report.json",
        "validation_result_path": base / "mirror_contract_validation_result.json",
        "audit_simulation_path": base / "mirror_input_audit_simulation.json",
        "packet_readiness_summary_path": base / "mirror_packet_readiness_summary.json",
    }
    write_json(report, paths["readiness_report_path"])
    write_json(validation_result, paths["validation_result_path"])
    write_json(audit, paths["audit_simulation_path"])
    write_json(summary, paths["packet_readiness_summary_path"])
    return {
        "mirror_input_readiness_run_schema_version": "mirror_input_readiness_run_v1",
        "readiness_verdict": summary["mirror_input_readiness_verdict"],
        "packet_count": summary["packet_count"],
        "rates": summary["readiness_rates"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_campaign_physics_packets(inputs: Mapping[str, Mapping[str, Any]]) -> list[Dict[str, Any]]:
    dataset = inputs["campaign_dataset"]
    contract = inputs["contract"]
    summary = inputs["campaign_physics_summary"]
    physics_rows = {
        row.get("campaign_id"): row
        for row in inputs["early_mae_discriminator"].get("campaign_physics_rows", [])
        if isinstance(row, Mapping)
    }
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    confidence = 1.0 if summary.get("evidence_level") == "VERIFIED" else 0.5
    packets: list[Dict[str, Any]] = []
    for campaign in dataset.get("campaigns", []):
        if not isinstance(campaign, Mapping):
            continue
        metrics = campaign.get("metrics", {}) if isinstance(campaign.get("metrics"), Mapping) else {}
        row = physics_rows.get(campaign.get("campaign_id"), {})
        packet = {
            "schema_version": contract.get("contract_version"),
            "campaign_id": campaign.get("campaign_id"),
            "signal_id": campaign.get("source_sample_id") or campaign.get("source_case_id"),
            "symbol": campaign.get("symbol"),
            "timeframe": "15m",
            "outcome": campaign.get("outcome"),
            "early_mae": first_present(row.get("early_mae"), metrics.get("early_mae")),
            "recovery_ratio": row.get("recovery_ratio"),
            "initial_drawdown_velocity": row.get("initial_drawdown_velocity"),
            "campaign_duration": first_present(row.get("campaign_duration"), metrics.get("campaign_duration"), campaign.get("duration")),
            "confidence": confidence,
            "created_at": created_at,
        }
        packets.append(packet)
    return packets


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def validate_packets(
    packets: Iterable[Mapping[str, Any]],
    contract: Mapping[str, Any],
    validation_rules: Mapping[str, Any],
) -> Dict[str, Any]:
    fields = {row["field"]: row for row in contract.get("fields", [])}
    rule_by_code = {row["validation_error_code"]: row for row in validation_rules.get("rules", [])}
    results = []
    for packet in packets:
        issues = validate_packet(packet, fields, contract.get("contract_version"))
        verdict = packet_verdict(issues)
        actions = merged_actions(issues, rule_by_code)
        results.append(
            {
                "campaign_id": packet.get("campaign_id"),
                "signal_id": packet.get("signal_id"),
                "symbol": packet.get("symbol"),
                "verdict": verdict,
                "actions": actions,
                "issues": issues,
                "mirror_input_usable": verdict in {"ACCEPT", "WARNING"},
                "is_trade_command": False,
            }
        )
    return {
        "mirror_contract_validation_result_schema_version": "mirror_contract_validation_result_v1",
        "contract_version": contract.get("contract_version"),
        "packet_count": len(results),
        "results": results,
        "is_trade_command": False,
    }


def validate_packet(packet: Mapping[str, Any], fields: Mapping[str, Mapping[str, Any]], contract_version: Any) -> list[Dict[str, Any]]:
    issues: list[Dict[str, Any]] = []
    for name, spec in fields.items():
        if spec.get("required") and name not in packet:
            issues.append(issue("required_field_missing", name, "Required field is absent."))
            continue
        value = packet.get(name)
        if value is None:
            if not spec.get("nullable"):
                issues.append(issue("required_field_missing", name, "Required non-null field is missing."))
            elif name in {"initial_drawdown_velocity", "campaign_duration"}:
                issues.append(issue("partial_packet", name, "Nullable Campaign Physics value is unresolved."))
            continue
        if not type_matches(value, spec.get("type")):
            issues.append(issue("type_mismatch", name, f"Expected {spec.get('type')}, got {type(value).__name__}."))
            continue
        enum = spec.get("valid_enum")
        if enum and value not in enum:
            code = "schema_version_mismatch" if name == "schema_version" else "invalid_value"
            issues.append(issue(code, name, f"Value {value!r} is outside valid enum."))
            continue
        valid_range = spec.get("valid_range") or {}
        minimum = valid_range.get("minimum")
        maximum = valid_range.get("maximum")
        if isinstance(value, (int, float)) and ((minimum is not None and value < minimum) or (maximum is not None and value > maximum)):
            issues.append(issue("invalid_value", name, f"Value {value!r} is outside valid range."))
    for name in packet:
        if name not in fields:
            issues.append(issue("unknown_field", name, "Packet includes a field not defined by contract."))
    if packet.get("schema_version") is not None and packet.get("schema_version") != contract_version:
        if not any(row["validation_error_code"] == "schema_version_mismatch" for row in issues):
            issues.append(issue("schema_version_mismatch", "schema_version", "Packet schema version does not match contract."))
    return issues


def issue(code: str, field: str, reason: str) -> Dict[str, Any]:
    return {"validation_error_code": code, "field": field, "validation_reason": reason}


def type_matches(value: Any, expected: Any) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def packet_verdict(issues: list[Mapping[str, Any]]) -> str:
    codes = {row["validation_error_code"] for row in issues}
    if any(code in codes for code in ("required_field_missing", "type_mismatch", "invalid_value")):
        return "REJECT"
    if any(code in codes for code in ("schema_version_mismatch", "partial_packet")):
        return "HOLD"
    if "unknown_field" in codes:
        return "WARNING"
    return "ACCEPT"


def merged_actions(issues: list[Mapping[str, Any]], rule_by_code: Mapping[str, Mapping[str, Any]]) -> list[str]:
    actions: list[str] = []
    for row in issues:
        for action in rule_by_code.get(row["validation_error_code"], {}).get("actions", []):
            if action not in actions:
                actions.append(action)
    return actions


def simulate_audit_log(
    validation_result: Mapping[str, Any],
    audit_policy: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    required_for = set(audit_policy.get("audit_log_required_for", []))
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    events = []
    for result in validation_result.get("results", []):
        if result.get("verdict") not in required_for:
            continue
        for issue_row in result.get("issues", []):
            actions = result.get("actions") or [result.get("verdict")]
            for action in actions:
                events.append(
                    {
                        "contract_version": contract.get("contract_version"),
                        "campaign_id": result.get("campaign_id"),
                        "signal_id": result.get("signal_id"),
                        "symbol": result.get("symbol"),
                        "validation_error_code": issue_row.get("validation_error_code"),
                        "validation_reason": issue_row.get("validation_reason"),
                        "action": action,
                        "timestamp": timestamp,
                    }
                )
    return {
        "mirror_input_audit_simulation_schema_version": "mirror_input_audit_simulation_v1",
        "audit_log_required_for": sorted(required_for),
        "event_count": len(events),
        "events": events,
        "audit_log_generation_possible": audit_fields_complete(events, audit_policy),
        "is_trade_command": False,
    }


def audit_fields_complete(events: Iterable[Mapping[str, Any]], audit_policy: Mapping[str, Any]) -> bool:
    required = {row["field"] for row in audit_policy.get("audit_log_fields", []) if row.get("required")}
    return all(required.issubset(set(event.keys())) for event in events)


def build_readiness_summary(validation_result: Mapping[str, Any], audit: Mapping[str, Any]) -> Dict[str, Any]:
    results = validation_result.get("results", [])
    packet_count = len(results)
    counts = Counter(row.get("verdict") for row in results)
    usable = sum(1 for row in results if row.get("mirror_input_usable"))
    reason_counts = Counter(issue_row["validation_error_code"] for row in results for issue_row in row.get("issues", []))
    rates = {name: ratio(counts.get(name, 0), packet_count) for name in ("ACCEPT", "WARNING", "HOLD", "REJECT")}
    readiness_rate = ratio(usable, packet_count)
    verdict = "READY" if packet_count > 0 and counts.get("REJECT", 0) == 0 and counts.get("HOLD", 0) == 0 else "NOT_READY"
    return {
        "mirror_packet_readiness_summary_schema_version": "mirror_packet_readiness_summary_v1",
        "packet_count": packet_count,
        "readiness_counts": {name: counts.get(name, 0) for name in ("ACCEPT", "WARNING", "HOLD", "REJECT")},
        "readiness_rates": rates,
        "mirror_input_usable_count": usable,
        "mirror_input_readiness_rate": readiness_rate,
        "mirror_input_readiness_verdict": verdict,
        "failure_reason_counts": dict(sorted(reason_counts.items())),
        "audit_event_count": audit.get("event_count", 0),
        "audit_log_generation_possible": audit.get("audit_log_generation_possible"),
        "is_trade_command": False,
    }


def ratio(value: int, total: int) -> float:
    return round(value / total, 6) if total else 0.0


def build_readiness_report(
    inputs: Mapping[str, Mapping[str, Any]],
    validation_result: Mapping[str, Any],
    audit: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "mirror_input_readiness_report_schema_version": "mirror_input_readiness_report_v1",
        "objective": "Validate whether Campaign Physics outputs are ready to be used as future Mirror Pattern inputs.",
        "contract_version": inputs["contract"].get("contract_version"),
        "mirror_input_rule": inputs["mirror_input_schema"].get("accepted_input"),
        "packet_count": summary["packet_count"],
        "readiness_counts": summary["readiness_counts"],
        "readiness_rates": summary["readiness_rates"],
        "mirror_input_readiness_rate": summary["mirror_input_readiness_rate"],
        "mirror_input_readiness_verdict": summary["mirror_input_readiness_verdict"],
        "major_failure_reasons": summary["failure_reason_counts"],
        "audit_simulation": {
            "event_count": audit.get("event_count"),
            "audit_log_generation_possible": audit.get("audit_log_generation_possible"),
        },
        "forbidden_actions_confirmed": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold change",
            "No gate change",
            "No Hellhound Score change",
            "No Replay change",
            "No Production code change",
        ],
        "next_sprint_recommendation": (
            "Mirror Pattern design may be reviewed only if this readiness result remains READY; implementation remains out of scope."
        ),
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
    result = run_mirror_input_readiness()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
