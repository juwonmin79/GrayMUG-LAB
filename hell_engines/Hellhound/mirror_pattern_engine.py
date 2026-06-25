from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CAMPAIGN_DATASET_PATH = DEFAULT_OUTPUT_DIR / "campaign_replay_dataset.json"
EARLY_MAE_PATH = DEFAULT_OUTPUT_DIR / "early_mae_discriminator.json"
CAMPAIGN_PHYSICS_CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_contract.json"
MIRROR_OUTPUT_SCHEMA_PATH = DEFAULT_OUTPUT_DIR / "mirror_output_schema.json"
MIRROR_FEATURE_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_feature_registry.json"
MIRROR_EVIDENCE_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_evidence_registry.json"
MIRROR_REASON_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_reason_registry.json"
MIRROR_REGISTRY_DEPENDENCY_PATH = DEFAULT_OUTPUT_DIR / "mirror_registry_dependency.json"
MIRROR_VALIDATION_RULES_PATH = DEFAULT_OUTPUT_DIR / "mirror_validation_rules.json"
MIRROR_READINESS_PATH = DEFAULT_OUTPUT_DIR / "mirror_v1_readiness_report.json"

MIRROR_SCHEMA_VERSION = "mirror_pattern_packet_v1"
CAMPAIGN_CONTRACT_VERSION = "campaign_physics_contract_v1"
DECISIONS = ("REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE")
PIPELINE = (
    "Campaign Physics Packet",
    "Packet Validation",
    "Evidence Builder",
    "Evidence Normalizer",
    "Pattern Matcher",
    "Conflict Resolver",
    "Decision Builder",
    "Confidence Manager",
    "Explainability Builder",
    "Packet Serializer",
    "Mirror Pattern Packet",
)


def run_mirror_pattern_engine(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_dataset_path: Path | str = CAMPAIGN_DATASET_PATH,
    early_mae_path: Path | str = EARLY_MAE_PATH,
    campaign_contract_path: Path | str = CAMPAIGN_PHYSICS_CONTRACT_PATH,
    mirror_output_schema_path: Path | str = MIRROR_OUTPUT_SCHEMA_PATH,
    feature_registry_path: Path | str = MIRROR_FEATURE_REGISTRY_PATH,
    evidence_registry_path: Path | str = MIRROR_EVIDENCE_REGISTRY_PATH,
    reason_registry_path: Path | str = MIRROR_REASON_REGISTRY_PATH,
    registry_dependency_path: Path | str = MIRROR_REGISTRY_DEPENDENCY_PATH,
    validation_rules_path: Path | str = MIRROR_VALIDATION_RULES_PATH,
    readiness_path: Path | str = MIRROR_READINESS_PATH,
) -> Dict[str, Any]:
    inputs = {
        "campaign_dataset": load_json(campaign_dataset_path),
        "early_mae_discriminator": load_json(early_mae_path),
        "campaign_contract": load_json(campaign_contract_path),
        "mirror_output_schema": load_json(mirror_output_schema_path),
        "feature_registry": load_json(feature_registry_path),
        "evidence_registry": load_json(evidence_registry_path),
        "reason_registry": load_json(reason_registry_path),
        "registry_dependency": load_json(registry_dependency_path),
        "validation_rules": load_json(validation_rules_path),
        "readiness": load_json(readiness_path),
    }
    packets = build_campaign_physics_packets(inputs)
    engine = MirrorPatternEngine(inputs)
    mirror_packets = [engine.process(packet) for packet in packets]
    packet_validation = [engine.validate_mirror_packet(packet) for packet in mirror_packets]
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    report = build_engine_report(inputs, packets, mirror_packets, packet_validation)
    decision_distribution = distribution_report("mirror_decision_distribution_v1", mirror_packets, "mirror_decision")
    reason_statistics = reason_report(mirror_packets)
    confidence_distribution = confidence_report(mirror_packets)

    paths = {
        "packets_path": base / "mirror_pattern_packets.jsonl",
        "engine_report_path": base / "mirror_engine_report.json",
        "decision_distribution_path": base / "mirror_decision_distribution.json",
        "reason_statistics_path": base / "mirror_reason_statistics.json",
        "confidence_distribution_path": base / "mirror_confidence_distribution.json",
    }
    write_jsonl(mirror_packets, paths["packets_path"])
    write_json(report, paths["engine_report_path"])
    write_json(decision_distribution, paths["decision_distribution_path"])
    write_json(reason_statistics, paths["reason_statistics_path"])
    write_json(confidence_distribution, paths["confidence_distribution_path"])
    return {
        "mirror_pattern_engine_run_schema_version": "mirror_pattern_engine_run_v1",
        "packet_count": len(mirror_packets),
        "contract_validation": report["contract_validation"],
        "registry_validation": report["registry_validation"],
        "mirror_packet_validation": report["mirror_packet_validation"],
        "decision_distribution": decision_distribution["counts"],
        "reason_distribution": reason_statistics["reason_counts"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


class MirrorPatternEngine:
    def __init__(self, inputs: Mapping[str, Mapping[str, Any]]) -> None:
        self.inputs = inputs
        self.contract_fields = {row["field"]: row for row in inputs["campaign_contract"].get("fields", [])}
        self.output_fields = {row["field"]: row for row in inputs["mirror_output_schema"].get("fields", [])}
        self.active_features = {
            row["feature_id"]
            for row in inputs["feature_registry"].get("features", [])
            if row.get("status") == "ACTIVE"
        }
        self.evidence_by_feature = {}
        for edge in inputs["registry_dependency"].get("feature_to_evidence", []):
            self.evidence_by_feature.setdefault(edge["from"], []).append(edge["to"])
        self.reason_by_evidence = {}
        for edge in inputs["registry_dependency"].get("evidence_to_reason", []):
            self.reason_by_evidence.setdefault(edge["from"], []).append(edge["to"])
        self.decision_by_reason = {edge["from"]: edge["to"] for edge in inputs["registry_dependency"].get("reason_to_decision", [])}
        self.reason_registry = {row["reason_code"] for row in inputs["reason_registry"].get("reasons", [])}

    def process(self, packet: Mapping[str, Any]) -> Dict[str, Any]:
        validation = self.validate_campaign_packet(packet)
        if validation["validation_state"] != "ACCEPT":
            return self.serialize_packet(packet, "INCONCLUSIVE", 0.0, ["INSUFFICIENT_EVIDENCE"], {}, validation["validation_state"])
        evidence = self.build_evidence(packet)
        normalized = self.normalize_evidence(evidence)
        matched = self.match_patterns(normalized)
        matched = self.resolve_conflicts(matched)
        decision = self.build_decision(matched)
        confidence = self.manage_confidence(packet, matched, decision)
        reason_codes = self.build_explainability(matched, decision)
        return self.serialize_packet(packet, decision, confidence, reason_codes, matched, "ACCEPT")

    def validate_campaign_packet(self, packet: Mapping[str, Any]) -> Dict[str, Any]:
        issues = []
        for name, spec in self.contract_fields.items():
            if spec.get("required") and name not in packet:
                issues.append(f"missing:{name}")
                continue
            value = packet.get(name)
            if value is None and not spec.get("nullable"):
                issues.append(f"null:{name}")
                continue
            if value is not None and not type_matches(value, spec.get("type")):
                issues.append(f"type:{name}")
        if packet.get("schema_version") != self.inputs["campaign_contract"].get("contract_version", CAMPAIGN_CONTRACT_VERSION):
            issues.append("schema_version")
        return {"validation_state": "ACCEPT" if not issues else "REJECT", "issues": issues}

    def build_evidence(self, packet: Mapping[str, Any]) -> Dict[str, Any]:
        evidence: Dict[str, Any] = {}
        for feature_id in sorted(self.active_features):
            if feature_id not in packet:
                continue
            evidence[feature_id] = {"value": packet[feature_id], "evidence_candidates": self.evidence_by_feature.get(feature_id, [])}
        return evidence

    def normalize_evidence(self, evidence: Mapping[str, Any]) -> Dict[str, Any]:
        normalized = dict(evidence)
        recovery = evidence.get("recovery_ratio", {}).get("value")
        confidence = evidence.get("confidence", {}).get("value")
        selected: list[str] = []
        if isinstance(recovery, (int, float)):
            selected.append("RECOVERY_STRONG" if recovery >= 1.0 else "RECOVERY_WEAK")
        if isinstance(confidence, (int, float)) and confidence < 1.0:
            selected.append("LOW_CONFIDENCE")
        if not selected:
            selected.append("INSUFFICIENT_EVIDENCE")
        normalized["_selected_evidence"] = selected
        return normalized

    def match_patterns(self, normalized: Mapping[str, Any]) -> Dict[str, Any]:
        selected = list(normalized.get("_selected_evidence", []))
        reason_codes: list[str] = []
        for evidence_id in selected:
            for reason_code in self.reason_by_evidence.get(evidence_id, []):
                if reason_code in self.reason_registry and reason_code not in reason_codes:
                    reason_codes.append(reason_code)
        if not reason_codes:
            reason_codes = ["INSUFFICIENT_EVIDENCE"]
        return {"evidence": selected, "reason_codes": reason_codes}

    def resolve_conflicts(self, matched: Mapping[str, Any]) -> Dict[str, Any]:
        reason_codes = list(matched.get("reason_codes", []))
        decisions = [self.decision_by_reason.get(reason) for reason in reason_codes]
        decisions = [decision for decision in decisions if decision in DECISIONS]
        decision_set = set(decisions)
        support_present = "REAL_WHALE_BACK" in decision_set
        risk_present = "FAKE_WHALE_BACK" in decision_set
        inconclusive_present = "INCONCLUSIVE" in decision_set
        insufficient_reason = not reason_codes or reason_codes == ["INSUFFICIENT_EVIDENCE"]
        conflict_detected = (
            inconclusive_present
            or (support_present and risk_present)
            or insufficient_reason
            or len(decision_set) > 1
        )
        resolved = dict(matched)
        resolved["conflict_resolution"] = {
            "conflict_detected": conflict_detected,
            "decision_targets": sorted(decision_set),
            "policy": "INCONCLUSIVE" if conflict_detected else "DECIDE",
        }
        return resolved

    def build_decision(self, matched: Mapping[str, Any]) -> str:
        if matched.get("conflict_resolution", {}).get("conflict_detected"):
            return "INCONCLUSIVE"
        decisions = [self.decision_by_reason.get(reason) for reason in matched.get("reason_codes", [])]
        decisions = [decision for decision in decisions if decision in DECISIONS]
        if "FAKE_WHALE_BACK" in decisions:
            return "FAKE_WHALE_BACK"
        if "REAL_WHALE_BACK" in decisions:
            return "REAL_WHALE_BACK"
        return "INCONCLUSIVE"

    def manage_confidence(self, packet: Mapping[str, Any], matched: Mapping[str, Any], decision: str) -> float:
        if matched.get("conflict_resolution", {}).get("conflict_detected"):
            return 0.35
        base = 0.5
        if decision in {"REAL_WHALE_BACK", "FAKE_WHALE_BACK"}:
            base += 0.3
        if packet.get("confidence") == 1.0:
            base += 0.1
        if len(matched.get("reason_codes", [])) > 1:
            base += 0.05
        return round(min(base, 0.95), 6)

    def build_explainability(self, matched: Mapping[str, Any], decision: str) -> list[str]:
        reason_codes = [code for code in matched.get("reason_codes", []) if code in self.reason_registry]
        if not reason_codes:
            return ["INSUFFICIENT_EVIDENCE"]
        return reason_codes

    def serialize_packet(
        self,
        packet: Mapping[str, Any],
        decision: str,
        confidence: float,
        reason_codes: Sequence[str],
        matched: Mapping[str, Any],
        validation_state: str,
    ) -> Dict[str, Any]:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return {
            "schema_version": MIRROR_SCHEMA_VERSION,
            "mirror_pattern_id": f"mirror-{packet.get('campaign_id')}",
            "campaign_id": packet.get("campaign_id"),
            "signal_id": packet.get("signal_id"),
            "symbol": packet.get("symbol"),
            "mirror_decision": decision,
            "confidence": confidence,
            "reason_code": list(reason_codes),
            "supporting_features": {
                "early_mae": packet.get("early_mae"),
                "recovery_ratio": packet.get("recovery_ratio"),
                "campaign_duration": packet.get("campaign_duration"),
                "confidence": packet.get("confidence"),
                "evidence": list(matched.get("evidence", [])),
                "conflict_resolution": matched.get("conflict_resolution", {}),
            },
            "validation_state": validation_state,
            "created_at": created_at,
            "is_trade_command": False,
        }

    def validate_mirror_packet(self, packet: Mapping[str, Any]) -> Dict[str, Any]:
        required = {
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
        }
        issues = []
        missing = sorted(required - set(packet))
        issues.extend(f"missing:{name}" for name in missing)
        if packet.get("mirror_decision") not in DECISIONS:
            issues.append("invalid_decision")
        if not packet.get("reason_code"):
            issues.append("missing_reason_code")
        if any(code not in self.reason_registry for code in packet.get("reason_code", [])):
            issues.append("invalid_reason_code")
        if packet.get("validation_state") not in {"ACCEPT", "WARNING", "HOLD", "REJECT"}:
            issues.append("invalid_validation_state")
        return {"valid": not issues, "issues": issues}


def build_campaign_physics_packets(inputs: Mapping[str, Mapping[str, Any]]) -> list[Dict[str, Any]]:
    rows = {
        row.get("campaign_id"): row
        for row in inputs["early_mae_discriminator"].get("campaign_physics_rows", [])
        if isinstance(row, Mapping)
    }
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    packets = []
    for campaign in inputs["campaign_dataset"].get("campaigns", []):
        row = rows.get(campaign.get("campaign_id"), {})
        metrics = campaign.get("metrics", {}) if isinstance(campaign.get("metrics"), Mapping) else {}
        packets.append(
            {
                "schema_version": inputs["campaign_contract"].get("contract_version", CAMPAIGN_CONTRACT_VERSION),
                "campaign_id": campaign.get("campaign_id"),
                "signal_id": campaign.get("source_sample_id") or campaign.get("source_case_id"),
                "symbol": campaign.get("symbol"),
                "timeframe": "15m",
                "outcome": campaign.get("outcome"),
                "early_mae": first_present(row.get("early_mae"), metrics.get("early_mae")),
                "recovery_ratio": row.get("recovery_ratio"),
                "initial_drawdown_velocity": row.get("initial_drawdown_velocity"),
                "campaign_duration": first_present(row.get("campaign_duration"), metrics.get("campaign_duration"), campaign.get("duration")),
                "confidence": 1.0,
                "created_at": created_at,
            }
        )
    return packets


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def type_matches(value: Any, expected: Any) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "object":
        return isinstance(value, Mapping)
    return True


def build_engine_report(
    inputs: Mapping[str, Mapping[str, Any]],
    campaign_packets: Sequence[Mapping[str, Any]],
    mirror_packets: Sequence[Mapping[str, Any]],
    packet_validation: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "mirror_engine_report_schema_version": "mirror_engine_report_v1",
        "engine_mode": "offline_replay_only",
        "pipeline": list(PIPELINE),
        "campaign_physics_packet_count": len(campaign_packets),
        "mirror_packet_count": len(mirror_packets),
        "contract_validation": "PASS" if campaign_packets and all(packet.get("schema_version") for packet in campaign_packets) else "FAIL",
        "registry_validation": "PASS" if inputs["readiness"].get("readiness_verdict") == "READY" else "FAIL",
        "mirror_packet_validation": "PASS" if all(row.get("valid") for row in packet_validation) else "FAIL",
        "temporary_engineering_confidence": True,
        "temporary_engineering_confidence_note": "Confidence is temporary engineering confidence; it is not statistically validated.",
        "forbidden_actions_confirmed": [
            "No ML training",
            "No threshold change",
            "No gate change",
            "No score change",
            "No replay logic change",
            "No Campaign Physics change",
            "No Production change",
            "No realtime Hellhound Shadow connection",
        ],
        "is_trade_command": False,
    }


def distribution_report(schema_version: str, packets: Sequence[Mapping[str, Any]], field: str) -> Dict[str, Any]:
    counts = Counter(packet.get(field) for packet in packets)
    total = len(packets)
    return {
        schema_version.replace("_v1", "_schema_version"): schema_version,
        "total": total,
        "counts": dict(sorted(counts.items())),
        "rates": {key: round(value / total, 6) if total else 0.0 for key, value in sorted(counts.items())},
        "is_trade_command": False,
    }


def reason_report(packets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = Counter(code for packet in packets for code in packet.get("reason_code", []))
    return {
        "mirror_reason_statistics_schema_version": "mirror_reason_statistics_v1",
        "reason_counts": dict(sorted(counts.items())),
        "is_trade_command": False,
    }


def confidence_report(packets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    values = [float(packet.get("confidence", 0.0)) for packet in packets]
    values_sorted = sorted(values)
    total = len(values)
    return {
        "mirror_confidence_distribution_schema_version": "mirror_confidence_distribution_v1",
        "count": total,
        "min": values_sorted[0] if values_sorted else None,
        "max": values_sorted[-1] if values_sorted else None,
        "mean": round(sum(values) / total, 6) if total else None,
        "temporary_engineering_confidence": True,
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


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    result = run_mirror_pattern_engine()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
