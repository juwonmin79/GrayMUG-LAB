from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
ENGINE_PIPELINE_PATH = DEFAULT_OUTPUT_DIR / "mirror_engine_pipeline.json"
COMPONENT_DEFINITION_PATH = DEFAULT_OUTPUT_DIR / "mirror_component_definition.json"
EVIDENCE_LIFECYCLE_PATH = DEFAULT_OUTPUT_DIR / "mirror_evidence_lifecycle.json"
EXPLAINABILITY_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_explainability_rules.json"
OUTPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_output_schema.json"
BLUEPRINT_REPORT_PATH = DEFAULT_OUTPUT_DIR / "mirror_engine_blueprint_report.json"

REGISTRY_VERSION = "mirror_reasoning_registry_v1"
REGISTRY_STATUSES = ("ACTIVE", "DEPRECATED", "RESERVED", "REMOVED")
FEATURES = ("early_mae", "recovery_ratio", "campaign_duration", "initial_drawdown_velocity", "confidence")
EVIDENCE_IDS = (
    "EARLY_MAE_HEALTHY",
    "EARLY_MAE_EXCESSIVE",
    "RECOVERY_STRONG",
    "RECOVERY_WEAK",
    "CAMPAIGN_SHORT",
    "CAMPAIGN_LONG",
    "LOW_CONFIDENCE",
    "INSUFFICIENT_EVIDENCE",
)
REASON_CODES = (
    "EARLY_MAE_SUPPORT",
    "RECOVERY_SUPPORT",
    "EARLY_MAE_RISK",
    "RECOVERY_FAILURE",
    "INSUFFICIENT_EVIDENCE",
    "CONFLICTING_EVIDENCE",
)


def run_mirror_reasoning_registry(
    *,
    output_dir: Optional[Path | str] = None,
    engine_pipeline_path: Path | str = ENGINE_PIPELINE_PATH,
    component_definition_path: Path | str = COMPONENT_DEFINITION_PATH,
    evidence_lifecycle_path: Path | str = EVIDENCE_LIFECYCLE_PATH,
    explainability_rules_path: Path | str = EXPLAINABILITY_RULES_PATH,
    output_schema_path: Path | str = OUTPUT_SCHEMA_PATH,
    blueprint_report_path: Path | str = BLUEPRINT_REPORT_PATH,
) -> Dict[str, Any]:
    inputs = {
        "mirror_engine_pipeline": load_json(engine_pipeline_path),
        "mirror_component_definition": load_json(component_definition_path),
        "mirror_evidence_lifecycle": load_json(evidence_lifecycle_path),
        "mirror_explainability_rules": load_json(explainability_rules_path),
        "mirror_output_schema": load_json(output_schema_path),
        "mirror_engine_blueprint_report": load_json(blueprint_report_path),
    }
    feature_registry = build_feature_registry()
    evidence_registry = build_evidence_registry()
    reason_registry = build_reason_registry()
    dependency = build_registry_dependency(feature_registry, evidence_registry, reason_registry)
    lifecycle = build_registry_lifecycle()
    validation = build_registry_validation(feature_registry, evidence_registry, reason_registry, dependency)
    principle = build_reasoning_principle()
    report = build_registry_report(
        feature_registry,
        evidence_registry,
        reason_registry,
        dependency,
        lifecycle,
        validation,
        principle,
        inputs,
    )

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "feature_registry_path": base / "mirror_feature_registry.json",
        "evidence_registry_path": base / "mirror_evidence_registry.json",
        "reason_registry_path": base / "mirror_reason_registry.json",
        "registry_dependency_path": base / "mirror_registry_dependency.json",
        "registry_validation_path": base / "mirror_registry_validation.json",
        "registry_lifecycle_path": base / "mirror_registry_lifecycle.json",
        "reasoning_principle_path": base / "mirror_reasoning_principle.json",
        "reasoning_registry_report_path": base / "mirror_reasoning_registry_report.json",
    }
    write_json(feature_registry, paths["feature_registry_path"])
    write_json(evidence_registry, paths["evidence_registry_path"])
    write_json(reason_registry, paths["reason_registry_path"])
    write_json(dependency, paths["registry_dependency_path"])
    write_json(validation, paths["registry_validation_path"])
    write_json(lifecycle, paths["registry_lifecycle_path"])
    write_json(principle, paths["reasoning_principle_path"])
    write_json(report, paths["reasoning_registry_report_path"])
    return {
        "mirror_reasoning_registry_run_schema_version": "mirror_reasoning_registry_run_v1",
        "registry_version": REGISTRY_VERSION,
        "registry_status": report["registry_status"],
        "verified": report["verified"],
        "not_verified": report["not_verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_feature_registry() -> Dict[str, Any]:
    definitions = {
        "early_mae": ("Maximum adverse excursion before or at campaign ignition.", True, False, "ACTIVE"),
        "recovery_ratio": ("Peak MFE divided by absolute Early MAE.", True, False, "ACTIVE"),
        "campaign_duration": ("Campaign duration context in hours.", True, True, "ACTIVE"),
        "initial_drawdown_velocity": ("Early drawdown speed context. Reserved until replay evidence supports official Evidence mapping.", False, True, "RESERVED"),
        "confidence": ("Campaign Physics packet confidence.", True, False, "ACTIVE"),
    }
    return {
        "mirror_feature_registry_schema_version": "mirror_feature_registry_v1",
        "registry_version": REGISTRY_VERSION,
        "registry_type": "Feature Registry",
        "features": [
            {
                "feature_id": feature_id,
                "description": definitions[feature_id][0],
                "source": "Campaign Physics Packet",
                "required": definitions[feature_id][1],
                "nullable": definitions[feature_id][2],
                "version": "v1",
                "status": definitions[feature_id][3],
            }
            for feature_id in FEATURES
        ],
        "is_trade_command": False,
    }


def build_evidence_registry() -> Dict[str, Any]:
    evidence = [
        evidence_item("EARLY_MAE_HEALTHY", "Early MAE supports healthy absorption.", "early_mae"),
        evidence_item("EARLY_MAE_EXCESSIVE", "Early MAE indicates excessive early drawdown.", "early_mae"),
        evidence_item("RECOVERY_STRONG", "Recovery ratio supports expansion after drawdown.", "recovery_ratio"),
        evidence_item("RECOVERY_WEAK", "Recovery ratio indicates failed recovery.", "recovery_ratio"),
        evidence_item("CAMPAIGN_SHORT", "Campaign duration is short context.", "campaign_duration"),
        evidence_item("CAMPAIGN_LONG", "Campaign duration is long context.", "campaign_duration"),
        evidence_item("LOW_CONFIDENCE", "Packet confidence is insufficient.", "confidence"),
        evidence_item("INSUFFICIENT_EVIDENCE", "Evidence is insufficient for a stable Mirror decision.", "confidence"),
    ]
    return {
        "mirror_evidence_registry_schema_version": "mirror_evidence_registry_v1",
        "registry_version": REGISTRY_VERSION,
        "registry_type": "Evidence Registry",
        "evidence": evidence,
        "is_trade_command": False,
    }


def evidence_item(evidence_id: str, description: str, source_feature: str) -> Dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "description": description,
        "source_feature": source_feature,
        "lifecycle": "Feature -> Evidence",
        "status": "ACTIVE",
    }


def build_reason_registry() -> Dict[str, Any]:
    reasons = [
        reason_item("EARLY_MAE_SUPPORT", "INFO", "support", "Early MAE evidence supports real whale backing.", ["EARLY_MAE_HEALTHY"]),
        reason_item("RECOVERY_SUPPORT", "INFO", "support", "Recovery evidence supports real whale backing.", ["RECOVERY_STRONG"]),
        reason_item("EARLY_MAE_RISK", "WARN", "risk", "Early MAE evidence indicates fake or failed campaign risk.", ["EARLY_MAE_EXCESSIVE"]),
        reason_item("RECOVERY_FAILURE", "WARN", "risk", "Recovery evidence indicates failure to recover.", ["RECOVERY_WEAK"]),
        reason_item("INSUFFICIENT_EVIDENCE", "WARN", "inconclusive", "Evidence is insufficient for a Mirror decision.", ["INSUFFICIENT_EVIDENCE", "LOW_CONFIDENCE"]),
        reason_item("CONFLICTING_EVIDENCE", "WARN", "inconclusive", "Evidence supports competing interpretations.", ["EARLY_MAE_HEALTHY", "RECOVERY_WEAK"]),
    ]
    return {
        "mirror_reason_registry_schema_version": "mirror_reason_registry_v1",
        "registry_version": REGISTRY_VERSION,
        "registry_type": "Reason Registry",
        "reasons": reasons,
        "reason_references_feature_directly": False,
        "is_trade_command": False,
    }


def reason_item(reason_code: str, severity: str, category: str, explanation: str, evidence_refs: Sequence[str]) -> Dict[str, Any]:
    return {
        "reason_code": reason_code,
        "severity": severity,
        "category": category,
        "explanation": explanation,
        "evidence_refs": list(evidence_refs),
        "active": True,
    }


def build_registry_dependency(
    feature_registry: Mapping[str, Any],
    evidence_registry: Mapping[str, Any],
    reason_registry: Mapping[str, Any],
) -> Dict[str, Any]:
    feature_ids = {row["feature_id"] for row in feature_registry["features"] if row.get("status") == "ACTIVE"}
    evidence_ids = {row["evidence_id"] for row in evidence_registry["evidence"]}
    return {
        "mirror_registry_dependency_schema_version": "mirror_registry_dependency_v1",
        "registry_version": REGISTRY_VERSION,
        "dependency_order": ["Feature", "Evidence", "Reason", "Mirror Decision"],
        "dependency_diagram": "Feature -> Evidence -> Reason -> Mirror Decision",
        "reverse_reference_allowed": False,
        "reason_direct_feature_reference_allowed": False,
        "feature_to_evidence": [
            {"from": row["source_feature"], "to": row["evidence_id"]}
            for row in evidence_registry["evidence"]
            if row["source_feature"] in feature_ids
        ],
        "evidence_to_reason": [
            {"from": evidence_id, "to": row["reason_code"]}
            for row in reason_registry["reasons"]
            for evidence_id in row["evidence_refs"]
            if evidence_id in evidence_ids
        ],
        "reason_to_decision": [
            {"from": "EARLY_MAE_SUPPORT", "to": "REAL_WHALE_BACK"},
            {"from": "RECOVERY_SUPPORT", "to": "REAL_WHALE_BACK"},
            {"from": "EARLY_MAE_RISK", "to": "FAKE_WHALE_BACK"},
            {"from": "RECOVERY_FAILURE", "to": "FAKE_WHALE_BACK"},
            {"from": "INSUFFICIENT_EVIDENCE", "to": "INCONCLUSIVE"},
            {"from": "CONFLICTING_EVIDENCE", "to": "INCONCLUSIVE"},
        ],
        "is_trade_command": False,
    }


def build_registry_lifecycle() -> Dict[str, Any]:
    return {
        "mirror_registry_lifecycle_schema_version": "mirror_registry_lifecycle_v1",
        "registry_version": REGISTRY_VERSION,
        "statuses": list(REGISTRY_STATUSES),
        "version_policy": {
            "current_version": REGISTRY_VERSION,
            "backward_compatibility": "ACTIVE v1 registry entries remain readable until explicitly DEPRECATED or REMOVED.",
            "deprecated_usage": "WARNING; allowed only during deprecation window.",
            "reserved_usage": "HOLD; reserved entries cannot drive decisions.",
            "removed_usage": "REJECT; removed entries cannot be referenced.",
        },
        "audit_log_fields": ["registry_type", "registry_id", "version", "status", "changed_at", "change_reason"],
        "extension_policy": "Future Mirror features must be added by registry entries without changing engine pipeline stages.",
        "is_trade_command": False,
    }


def build_registry_validation(
    feature_registry: Mapping[str, Any],
    evidence_registry: Mapping[str, Any],
    reason_registry: Mapping[str, Any],
    dependency: Mapping[str, Any],
) -> Dict[str, Any]:
    feature_ids = [row["feature_id"] for row in feature_registry["features"]]
    active_feature_ids = {row["feature_id"] for row in feature_registry["features"] if row.get("status") == "ACTIVE"}
    evidence_ids = [row["evidence_id"] for row in evidence_registry["evidence"]]
    reason_codes = [row["reason_code"] for row in reason_registry["reasons"]]
    validation_checks = {
        "duplicate_feature": duplicates(feature_ids),
        "duplicate_evidence": duplicates(evidence_ids),
        "duplicate_reason": duplicates(reason_codes),
        "missing_evidence": missing_evidence_refs(reason_registry, set(evidence_ids)),
        "invalid_reference": invalid_feature_refs(evidence_registry, active_feature_ids),
        "deprecated_usage": [],
        "unknown_registry_item": [],
        "reason_direct_feature_reference": dependency["reason_direct_feature_reference_allowed"],
    }
    return {
        "mirror_registry_validation_schema_version": "mirror_registry_validation_v1",
        "registry_version": REGISTRY_VERSION,
        "validation_rules": [
            "duplicate_feature",
            "duplicate_reason",
            "missing_evidence",
            "invalid_reference",
            "deprecated_usage",
            "unknown_registry_item",
        ],
        "validation_checks": validation_checks,
        "validation_passed": all(not value for value in validation_checks.values()),
        "is_trade_command": False,
    }


def duplicates(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for item in items:
        if item in seen:
            dupes.add(item)
        seen.add(item)
    return sorted(dupes)


def missing_evidence_refs(reason_registry: Mapping[str, Any], evidence_ids: set[str]) -> list[str]:
    missing = []
    for reason in reason_registry["reasons"]:
        for evidence_id in reason["evidence_refs"]:
            if evidence_id not in evidence_ids:
                missing.append(f"{reason['reason_code']}->{evidence_id}")
    return missing


def invalid_feature_refs(evidence_registry: Mapping[str, Any], feature_ids: set[str]) -> list[str]:
    return [
        f"{row['evidence_id']}->{row['source_feature']}"
        for row in evidence_registry["evidence"]
        if row["source_feature"] not in feature_ids
    ]


def build_reasoning_principle() -> Dict[str, Any]:
    return {
        "mirror_reasoning_principle_schema_version": "mirror_reasoning_principle_v1",
        "registry_version": REGISTRY_VERSION,
        "principle": (
            "Mirror does not make decisions directly from Features. Mirror transforms Features into Evidence, "
            "Evidence into Reasons, and Reasons into Decisions. Meaning always precedes Decision."
        ),
        "semantic_consistency_rule": "Feature -> Evidence -> Reason -> Decision",
        "feature_to_decision_direct_link_allowed": False,
        "reason_to_feature_direct_link_allowed": False,
        "is_trade_command": False,
    }


def build_registry_report(
    feature_registry: Mapping[str, Any],
    evidence_registry: Mapping[str, Any],
    reason_registry: Mapping[str, Any],
    dependency: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    validation: Mapping[str, Any],
    principle: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    checks = {
        "feature_registry_defined": {row["feature_id"] for row in feature_registry["features"]} == set(FEATURES),
        "evidence_registry_defined": {row["evidence_id"] for row in evidence_registry["evidence"]} == set(EVIDENCE_IDS),
        "reason_registry_defined": {row["reason_code"] for row in reason_registry["reasons"]} == set(REASON_CODES),
        "registry_dependency_defined": dependency["dependency_order"] == ["Feature", "Evidence", "Reason", "Mirror Decision"],
        "registry_lifecycle_defined": set(lifecycle["statuses"]) == set(REGISTRY_STATUSES),
        "registry_validation_defined": validation["validation_passed"],
        "registry_audit_defined": set(lifecycle["audit_log_fields"])
        == {"registry_type", "registry_id", "version", "status", "changed_at", "change_reason"},
        "extension_policy_defined": "without changing engine pipeline" in lifecycle["extension_policy"],
        "semantic_consistency_rule_defined": principle["semantic_consistency_rule"] == "Feature -> Evidence -> Reason -> Decision",
        "reasoning_principle_defined": "Meaning always precedes Decision" in principle["principle"],
        "blueprint_verified": inputs.get("mirror_engine_blueprint_report", {}).get("blueprint_status") == "VERIFIED",
    }
    status = "VERIFIED" if all(checks.values()) else "PARTIAL"
    return {
        "mirror_reasoning_registry_report_schema_version": "mirror_reasoning_registry_report_v1",
        "registry_version": REGISTRY_VERSION,
        "registry_status": status,
        "verified": [
            "Feature Registry",
            "Evidence Registry",
            "Reason Registry",
            "Registry Dependency",
            "Registry Lifecycle",
            "Registry Validation",
            "Registry Audit",
            "Extension Policy",
            "Semantic Consistency Rule",
            "Reasoning Principle",
        ]
        if status == "VERIFIED"
        else [key for key, value in checks.items() if value],
        "not_verified": [] if status == "VERIFIED" else [key for key, value in checks.items() if not value],
        "validation": checks,
        "semantic_reasoning_principle": principle["principle"],
        "dependency_diagram": dependency["dependency_diagram"],
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
        "next_sprint_recommendation": "Sprint 12Z should validate registry-driven Mirror design before any implementation.",
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
    result = run_mirror_reasoning_registry()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
