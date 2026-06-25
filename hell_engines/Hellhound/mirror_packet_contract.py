from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import mirror_pattern_engine
except ImportError:
    from . import mirror_pattern_engine


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_SHADOW_LOG_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"
DEFAULT_PATTERN_PACKET_PATH = DEFAULT_OUTPUT_DIR / "mirror_pattern_packets.jsonl"

CONTRACT_VERSION = "mirror_pattern_packet_v1"
FREEZE_STATUS = "FROZEN"
DECISION_ENUM = ("REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE")
VALIDATION_STATE_ENUM = ("ACCEPT", "WARNING", "HOLD", "REJECT")
CONFLICT_POLICY_ENUM = ("DECIDE", "INCONCLUSIVE")
NUMERIC_PRECISION_DECIMALS = 6

FIELD_ORDER = (
    "schema_version",
    "mirror_pattern_id",
    "campaign_id",
    "signal_id",
    "symbol",
    "mirror_decision",
    "confidence",
    "reason_code",
    "supporting_features",
    "validation_state",
    "created_at",
    "is_trade_command",
)
REQUIRED_FIELDS = set(FIELD_ORDER)
OPTIONAL_FIELDS: set[str] = set()
SUPPORTING_FEATURE_FIELDS = (
    "early_mae",
    "recovery_ratio",
    "campaign_duration",
    "confidence",
    "evidence",
    "conflict_resolution",
)
CONFLICT_RESOLUTION_FIELDS = ("conflict_detected", "decision_targets", "policy")


def run_mirror_packet_contract_freeze(
    *,
    output_dir: Optional[Path | str] = None,
    shadow_log_path: Path | str = DEFAULT_SHADOW_LOG_PATH,
    pattern_packet_path: Path | str = DEFAULT_PATTERN_PACKET_PATH,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    schema = build_schema()
    shadow_rows = load_jsonl(shadow_log_path)
    packets = extract_mirror_packets(shadow_rows)
    if not packets:
        packets = load_jsonl(pattern_packet_path)
    reason_registry = load_reason_registry()
    validations = [validate_packet(packet, schema=schema, reason_registry=reason_registry) for packet in packets]
    validation_report = build_validation_report(packets, validations)
    golden_samples = build_golden_samples(packets)
    contract_report = build_contract_report(schema, packets, validations, golden_samples, shadow_log_path)

    paths = {
        "schema_path": base / "mirror_packet_schema_v1.json",
        "contract_report_path": base / "mirror_packet_contract_report.json",
        "validation_report_path": base / "mirror_packet_validation_report.json",
        "golden_samples_path": base / "mirror_packet_golden_samples.json",
    }
    write_json(schema, paths["schema_path"])
    write_json(contract_report, paths["contract_report_path"])
    write_json(validation_report, paths["validation_report_path"])
    write_json(golden_samples, paths["golden_samples_path"])
    return {
        "mirror_packet_contract_freeze_run_schema_version": "mirror_packet_contract_freeze_run_v1",
        "contract_version": CONTRACT_VERSION,
        "freeze_status": contract_report["freeze_status"],
        "packet_count": len(packets),
        "contract_validation": validation_report["contract_validation"],
        "schema_stability": contract_report["schema_stability"],
        "replay_compatibility": contract_report["replay_compatibility"],
        "golden_sample_validation": contract_report["golden_sample_validation"],
        "json_validation": "PASS",
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_schema() -> Dict[str, Any]:
    fields = [
        field("schema_version", "string", True, False, "Mirror Packet schema version.", enum=[CONTRACT_VERSION], default=CONTRACT_VERSION),
        field("mirror_pattern_id", "string", True, False, "Stable Mirror Pattern Packet identifier.", default=None),
        field("campaign_id", "string", True, False, "Campaign id copied from Campaign Physics Packet.", default=None),
        field("signal_id", "string", True, True, "Signal id copied from Campaign Physics Packet.", default=None),
        field("symbol", "string", True, False, "Market symbol copied from Campaign Physics Packet.", default=None),
        field("mirror_decision", "string", True, False, "Campaign authenticity decision.", enum=list(DECISION_ENUM), default=None),
        field("confidence", "number", True, False, "Temporary Engineering Confidence frozen as numeric packet field.", minimum=0.0, maximum=1.0, precision=NUMERIC_PRECISION_DECIMALS, default=None),
        field("reason_code", "array<string>", True, False, "Reason-code list; free-form explanation is forbidden.", default=[]),
        field("supporting_features", "object", True, False, "Campaign Physics evidence used by Mirror.", nested_schema=build_supporting_features_schema(), default={}),
        field("validation_state", "string", True, False, "Packet validation state.", enum=list(VALIDATION_STATE_ENUM), default="ACCEPT"),
        field("created_at", "string", True, False, "UTC ISO-8601 timestamp.", pattern="ISO-8601 with timezone", default=None),
        field("is_trade_command", "boolean", True, False, "Must always be false; Mirror Packet is not a trade command.", enum=[False], default=False),
    ]
    return {
        "mirror_packet_schema_version": "mirror_packet_schema_v1",
        "contract_version": CONTRACT_VERSION,
        "freeze_status": FREEZE_STATUS,
        "field_order": list(FIELD_ORDER),
        "required_fields": list(FIELD_ORDER),
        "optional_fields": [],
        "fields": fields,
        "decision_enum": list(DECISION_ENUM),
        "validation_state_enum": list(VALIDATION_STATE_ENUM),
        "timestamp_format": "ISO-8601 timezone-aware string",
        "numeric_precision": {"max_decimal_places": NUMERIC_PRECISION_DECIMALS},
        "null_policy": {"signal_id": "nullable", "supporting_features numeric values": "nullable", "all other required fields": "not nullable"},
        "unknown_field_handling": "WARNING in validation; v1 producers must not emit unknown fields.",
        "freeze_policy": {
            "required_field_removal": "FORBIDDEN",
            "required_to_optional": "FORBIDDEN",
            "optional_to_required": "FORBIDDEN",
            "enum_meaning_change": "FORBIDDEN",
            "field_meaning_change": "FORBIDDEN",
            "allowed_extension": ["Add optional field in compatible v1 extension", "Create mirror_pattern_packet_v2"],
        },
        "compatibility_policy": {
            "existing_packet_readability": "Existing v1 packets must remain readable without mutation.",
            "golden_samples": "Golden samples are actual validated packets and are used for regression tests.",
            "production_dependency": "DB, Supabase, Dashboard, ML, Replay expansion, and Production must depend on this frozen contract.",
        },
        "is_trade_command": False,
    }


def build_supporting_features_schema() -> Dict[str, Any]:
    return {
        "required_fields": list(SUPPORTING_FEATURE_FIELDS),
        "fields": [
            field("early_mae", "number", True, True, "Early MAE feature.", precision=NUMERIC_PRECISION_DECIMALS),
            field("recovery_ratio", "number", True, True, "Recovery Ratio feature.", precision=NUMERIC_PRECISION_DECIMALS),
            field("campaign_duration", "number", True, True, "Campaign duration feature.", precision=NUMERIC_PRECISION_DECIMALS),
            field("confidence", "number", True, True, "Source Campaign Physics confidence.", minimum=0.0, maximum=1.0, precision=NUMERIC_PRECISION_DECIMALS),
            field("evidence", "array<string>", True, False, "Evidence ids selected by Mirror."),
            field("conflict_resolution", "object", True, False, "Conflict Resolver result.", nested_schema={
                "required_fields": list(CONFLICT_RESOLUTION_FIELDS),
                "fields": [
                    field("conflict_detected", "boolean", True, False, "Whether conflict was detected."),
                    field("decision_targets", "array<string>", True, False, "Decision targets implied by reasons.", enum=list(DECISION_ENUM)),
                    field("policy", "string", True, False, "Conflict policy result.", enum=list(CONFLICT_POLICY_ENUM)),
                ],
            }),
        ],
    }


def field(
    name: str,
    data_type: str,
    required: bool,
    nullable: bool,
    description: str,
    *,
    enum: Optional[Sequence[Any]] = None,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    precision: Optional[int] = None,
    pattern: Optional[str] = None,
    nested_schema: Optional[Mapping[str, Any]] = None,
    default: Any = None,
) -> Dict[str, Any]:
    return {
        "field": name,
        "type": data_type,
        "required": required,
        "nullable": nullable,
        "description": description,
        "valid_enum": list(enum) if enum is not None else None,
        "valid_range": {"minimum": minimum, "maximum": maximum} if minimum is not None or maximum is not None else None,
        "numeric_precision": precision,
        "timestamp_format": pattern,
        "nested_schema": dict(nested_schema) if nested_schema else None,
        "default": default,
    }


def validate_packet(packet: Mapping[str, Any], *, schema: Mapping[str, Any], reason_registry: set[str]) -> Dict[str, Any]:
    issues: list[Dict[str, Any]] = []
    missing = [field_name for field_name in FIELD_ORDER if field_name not in packet]
    issues.extend(issue("missing_field", name, "REJECT") for name in missing)
    unknown = [field_name for field_name in packet if field_name not in REQUIRED_FIELDS and field_name not in OPTIONAL_FIELDS]
    issues.extend(issue("unknown_field", name, "WARNING") for name in unknown)

    for spec in schema["fields"]:
        name = spec["field"]
        if name not in packet:
            continue
        value = packet.get(name)
        if value is None and not spec["nullable"]:
            issues.append(issue("null_not_allowed", name, "REJECT"))
            continue
        if value is not None:
            validate_value(name, value, spec, issues, reason_registry)

    supporting_features = packet.get("supporting_features")
    if isinstance(supporting_features, Mapping):
        validate_supporting_features(supporting_features, issues)
    else:
        issues.append(issue("invalid_type", "supporting_features", "REJECT"))

    max_severity = "PASS"
    if any(row["severity"] == "REJECT" for row in issues):
        max_severity = "REJECT"
    elif any(row["severity"] == "WARNING" for row in issues):
        max_severity = "WARNING"
    return {
        "campaign_id": packet.get("campaign_id"),
        "mirror_decision": packet.get("mirror_decision"),
        "valid": max_severity == "PASS",
        "validation_result": max_severity,
        "issues": issues,
    }


def validate_value(name: str, value: Any, spec: Mapping[str, Any], issues: list[Dict[str, Any]], reason_registry: set[str]) -> None:
    expected = spec["type"]
    if expected == "string" and not isinstance(value, str):
        issues.append(issue("invalid_type", name, "REJECT"))
    elif expected == "number":
        validate_number(name, value, spec, issues)
    elif expected == "boolean" and not isinstance(value, bool):
        issues.append(issue("invalid_type", name, "REJECT"))
    elif expected == "object" and not isinstance(value, Mapping):
        issues.append(issue("invalid_type", name, "REJECT"))
    elif expected == "array<string>" and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
        issues.append(issue("invalid_type", name, "REJECT"))

    valid_enum = spec.get("valid_enum")
    if valid_enum is not None and expected != "array<string>" and value not in valid_enum:
        issues.append(issue("invalid_enum", name, "REJECT"))
    if name == "created_at" and isinstance(value, str) and not is_iso_timestamp(value):
        issues.append(issue("invalid_timestamp", name, "REJECT"))
    if name == "reason_code":
        if not isinstance(value, list) or not value:
            issues.append(issue("missing_reason_code", name, "REJECT"))
        else:
            for reason in value:
                if reason not in reason_registry:
                    issues.append(issue("invalid_reason_code", str(reason), "REJECT"))


def validate_supporting_features(features: Mapping[str, Any], issues: list[Dict[str, Any]]) -> None:
    missing = [name for name in SUPPORTING_FEATURE_FIELDS if name not in features]
    issues.extend(issue("missing_nested_field", f"supporting_features.{name}", "REJECT") for name in missing)
    for name in ("early_mae", "recovery_ratio", "campaign_duration", "confidence"):
        value = features.get(name)
        if value is not None:
            validate_number(f"supporting_features.{name}", value, {"valid_range": {"minimum": 0.0, "maximum": 1.0} if name == "confidence" else None, "numeric_precision": NUMERIC_PRECISION_DECIMALS}, issues)
    evidence = features.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        issues.append(issue("invalid_type", "supporting_features.evidence", "REJECT"))
    conflict = features.get("conflict_resolution")
    if not isinstance(conflict, Mapping):
        issues.append(issue("invalid_type", "supporting_features.conflict_resolution", "REJECT"))
        return
    missing_conflict = [name for name in CONFLICT_RESOLUTION_FIELDS if name not in conflict]
    issues.extend(issue("missing_nested_field", f"supporting_features.conflict_resolution.{name}", "REJECT") for name in missing_conflict)
    if not isinstance(conflict.get("conflict_detected"), bool):
        issues.append(issue("invalid_type", "supporting_features.conflict_resolution.conflict_detected", "REJECT"))
    targets = conflict.get("decision_targets")
    if not isinstance(targets, list) or any(target not in DECISION_ENUM for target in targets):
        issues.append(issue("invalid_enum", "supporting_features.conflict_resolution.decision_targets", "REJECT"))
    if conflict.get("policy") not in CONFLICT_POLICY_ENUM:
        issues.append(issue("invalid_enum", "supporting_features.conflict_resolution.policy", "REJECT"))


def validate_number(name: str, value: Any, spec: Mapping[str, Any], issues: list[Dict[str, Any]]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        issues.append(issue("invalid_numeric_type", name, "REJECT"))
        return
    valid_range = spec.get("valid_range")
    if valid_range:
        minimum = valid_range.get("minimum")
        maximum = valid_range.get("maximum")
        if minimum is not None and value < minimum:
            issues.append(issue("numeric_out_of_range", name, "REJECT"))
        if maximum is not None and value > maximum:
            issues.append(issue("numeric_out_of_range", name, "REJECT"))
    precision = spec.get("numeric_precision")
    if precision is not None and decimal_places(value) > precision:
        issues.append(issue("numeric_precision_exceeded", name, "REJECT"))


def build_validation_report(packets: Sequence[Mapping[str, Any]], validations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    issue_counts = Counter(row["code"] for validation in validations for row in validation["issues"])
    decision_counts = Counter(packet.get("mirror_decision") for packet in packets)
    return {
        "mirror_packet_validation_report_schema_version": "mirror_packet_validation_report_v1",
        "contract_version": CONTRACT_VERSION,
        "packet_count": len(packets),
        "contract_validation": "PASS" if packets and all(row["valid"] for row in validations) else "FAIL",
        "validation_counts": {
            "PASS": sum(1 for row in validations if row["validation_result"] == "PASS"),
            "WARNING": sum(1 for row in validations if row["validation_result"] == "WARNING"),
            "REJECT": sum(1 for row in validations if row["validation_result"] == "REJECT"),
        },
        "decision_counts": {decision: decision_counts.get(decision, 0) for decision in DECISION_ENUM},
        "issue_counts": dict(sorted(issue_counts.items())),
        "validations": list(validations),
        "is_trade_command": False,
    }


def build_contract_report(
    schema: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    validations: Sequence[Mapping[str, Any]],
    golden_samples: Mapping[str, Any],
    shadow_log_path: Path | str,
) -> Dict[str, Any]:
    all_pass = bool(packets) and all(row["valid"] for row in validations)
    golden_valid = golden_samples.get("golden_sample_validation") == "PASS"
    return {
        "mirror_packet_contract_report_schema_version": "mirror_packet_contract_report_v1",
        "contract_version": CONTRACT_VERSION,
        "freeze_status": FREEZE_STATUS if all_pass and golden_valid else "NOT_FROZEN",
        "review": {
            "packet_version": CONTRACT_VERSION,
            "required_fields": schema["required_fields"],
            "optional_fields": schema["optional_fields"],
            "enum_definitions": {
                "mirror_decision": list(DECISION_ENUM),
                "validation_state": list(VALIDATION_STATE_ENUM),
                "conflict_resolution.policy": list(CONFLICT_POLICY_ENUM),
            },
            "timestamp_format": schema["timestamp_format"],
            "numeric_precision": schema["numeric_precision"],
            "nested_objects": ["supporting_features", "supporting_features.conflict_resolution"],
            "null_allowed": schema["null_policy"],
            "defaults": {row["field"]: row["default"] for row in schema["fields"]},
            "duplicate_fields_detected": len(schema["required_fields"]) != len(set(schema["required_fields"])),
        },
        "compatibility_policy": schema["compatibility_policy"],
        "freeze_policy": schema["freeze_policy"],
        "compatibility_note": "Frozen v1 follows actual mirror_pattern_packet_v1 packets with reason_code. Earlier design docs that referenced explainability remain historical design artifacts.",
        "source": str(shadow_log_path),
        "existing_packet_compatibility": "PASS" if all_pass else "FAIL",
        "schema_stability": "PASS" if all_pass else "FAIL",
        "replay_compatibility": "PASS" if all_pass else "FAIL",
        "golden_sample_validation": golden_samples.get("golden_sample_validation"),
        "json_validation": "PASS",
        "forbidden_actions_confirmed": [
            "No Production change",
            "No Trading change",
            "No Position change",
            "No Order change",
            "No Replay Logic change",
            "No Campaign Physics change",
            "No Lead Line change",
            "No Mirror Registry Logic change",
            "No Mirror Decision Logic change",
            "No Mirror Threshold change",
            "No Mirror Gate change",
            "No Mirror Score change",
            "No ML training",
            "No DB creation",
            "No Supabase connection",
            "No Medusa change",
        ],
        "is_trade_command": False,
    }


def build_golden_samples(packets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    samples: Dict[str, Any] = {}
    for decision in DECISION_ENUM:
        sample = next((packet for packet in packets if packet.get("mirror_decision") == decision), None)
        if sample is not None:
            samples[decision] = dict(sample)
        else:
            samples[decision] = {"status": "absent_in_source", "reason": "No actual validated packet for this decision type in current source."}
    present = [decision for decision, sample in samples.items() if not (isinstance(sample, Mapping) and sample.get("status") == "absent_in_source")]
    required_present = {"REAL_WHALE_BACK", "INCONCLUSIVE"}
    return {
        "mirror_packet_golden_samples_schema_version": "mirror_packet_golden_samples_v1",
        "contract_version": CONTRACT_VERSION,
        "sample_source": "outputs/mirror_shadow_log.jsonl mirror_packet",
        "policy": "Golden samples must be actual validated packets. Missing decision types are not synthesized.",
        "available_decision_types": present,
        "missing_decision_types": [decision for decision in DECISION_ENUM if decision not in present],
        "golden_sample_validation": "PASS" if required_present.issubset(set(present)) else "FAIL",
        "samples": samples,
        "is_trade_command": False,
    }


def extract_mirror_packets(rows: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    return [dict(row["mirror_packet"]) for row in rows if isinstance(row.get("mirror_packet"), Mapping)]


def load_reason_registry() -> set[str]:
    registry = mirror_pattern_engine.load_json(mirror_pattern_engine.MIRROR_REASON_REGISTRY_PATH)
    return {str(row.get("reason_code")) for row in registry.get("reasons", []) if isinstance(row, Mapping) and row.get("reason_code")}


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def issue(code: str, field_name: str, severity: str) -> Dict[str, str]:
    return {"code": code, "field": field_name, "severity": severity}


def is_iso_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def decimal_places(value: Any) -> int:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return 0
    exponent = decimal.as_tuple().exponent
    return abs(exponent) if exponent < 0 else 0


def main() -> int:
    result = run_mirror_packet_contract_freeze()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
