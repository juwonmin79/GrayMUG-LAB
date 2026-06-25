from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import mirror_pattern_engine as engine
except ImportError:
    from . import mirror_pattern_engine as engine


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
PACKETS_PATH = DEFAULT_OUTPUT_DIR / "mirror_pattern_packets.jsonl"
ENGINE_REPORT_PATH = DEFAULT_OUTPUT_DIR / "mirror_engine_report.json"
DECISION_DISTRIBUTION_PATH = DEFAULT_OUTPUT_DIR / "mirror_decision_distribution.json"
REASON_STATISTICS_PATH = DEFAULT_OUTPUT_DIR / "mirror_reason_statistics.json"
CONFIDENCE_DISTRIBUTION_PATH = DEFAULT_OUTPUT_DIR / "mirror_confidence_distribution.json"
REGISTRY_DEPENDENCY_PATH = DEFAULT_OUTPUT_DIR / "mirror_registry_dependency.json"
REASON_REGISTRY_PATH = DEFAULT_OUTPUT_DIR / "mirror_reason_registry.json"


def run_mirror_decision_calibration(
    *,
    output_dir: Optional[Path | str] = None,
    packets_path: Path | str = PACKETS_PATH,
    engine_report_path: Path | str = ENGINE_REPORT_PATH,
    decision_distribution_path: Path | str = DECISION_DISTRIBUTION_PATH,
    reason_statistics_path: Path | str = REASON_STATISTICS_PATH,
    confidence_distribution_path: Path | str = CONFIDENCE_DISTRIBUTION_PATH,
    registry_dependency_path: Path | str = REGISTRY_DEPENDENCY_PATH,
    reason_registry_path: Path | str = REASON_REGISTRY_PATH,
) -> Dict[str, Any]:
    inputs = {
        "packets": load_jsonl(packets_path),
        "engine_report": load_json(engine_report_path),
        "decision_distribution": load_json(decision_distribution_path),
        "reason_statistics": load_json(reason_statistics_path),
        "confidence_distribution": load_json(confidence_distribution_path),
        "registry_dependency": load_json(registry_dependency_path),
        "reason_registry": load_json(reason_registry_path),
    }
    decision_audit = build_decision_distribution_audit(inputs)
    conflict = build_conflict_analysis(inputs)
    sufficiency = build_evidence_sufficiency(inputs, conflict)
    confidence = build_confidence_calibration(inputs, conflict)
    stability = build_decision_stability(inputs)
    inconclusive = build_inconclusive_analysis(inputs, conflict, sufficiency)
    calibration = build_calibration(inputs, decision_audit, conflict, sufficiency, confidence, stability, inconclusive)
    report = build_calibration_report(decision_audit, conflict, sufficiency, confidence, stability, inconclusive)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "calibration_path": base / "mirror_decision_calibration.json",
        "stability_path": base / "mirror_decision_stability.json",
        "conflict_analysis_path": base / "mirror_conflict_analysis.json",
        "evidence_sufficiency_path": base / "mirror_evidence_sufficiency.json",
        "confidence_calibration_path": base / "mirror_confidence_calibration.json",
        "inconclusive_analysis_path": base / "mirror_inconclusive_analysis.json",
        "calibration_report_path": base / "mirror_decision_calibration_report.json",
    }
    write_json(calibration, paths["calibration_path"])
    write_json(stability, paths["stability_path"])
    write_json(conflict, paths["conflict_analysis_path"])
    write_json(sufficiency, paths["evidence_sufficiency_path"])
    write_json(confidence, paths["confidence_calibration_path"])
    write_json(inconclusive, paths["inconclusive_analysis_path"])
    write_json(report, paths["calibration_report_path"])
    return {
        "mirror_decision_calibration_run_schema_version": "mirror_decision_calibration_run_v1",
        "packet_count": len(inputs["packets"]),
        "deterministic": stability["deterministic"],
        "inconclusive_count": decision_audit["counts"].get("INCONCLUSIVE", 0),
        "calibration_verdict": report["calibration_verdict"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_decision_distribution_audit(inputs: Mapping[str, Any]) -> Dict[str, Any]:
    packets = inputs["packets"]
    counts = Counter(packet.get("mirror_decision") for packet in packets)
    for decision in engine.DECISIONS:
        counts.setdefault(decision, 0)
    current = inputs.get("decision_distribution", {}).get("counts", {})
    return {
        "mirror_decision_distribution_audit_schema_version": "mirror_decision_distribution_audit_v1",
        "counts": dict(sorted(counts.items())),
        "current_engine_counts": current,
        "matches_current_output": dict(sorted(counts.items())) == {key: current.get(key, 0) for key in sorted(counts)},
        "inconclusive_count": counts.get("INCONCLUSIVE", 0),
        "is_trade_command": False,
    }


def build_conflict_analysis(inputs: Mapping[str, Any]) -> Dict[str, Any]:
    reason_to_decision = {edge["from"]: edge["to"] for edge in inputs["registry_dependency"].get("reason_to_decision", [])}
    inconclusive_reasons = {reason for reason, decision in reason_to_decision.items() if decision == "INCONCLUSIVE"}
    rows = []
    for packet in inputs["packets"]:
        reasons = list(packet.get("reason_code", []))
        decision_targets = sorted({reason_to_decision.get(reason) for reason in reasons if reason_to_decision.get(reason)})
        conflict_reasons = sorted(set(reasons) & inconclusive_reasons)
        conflict = len(decision_targets) > 1 or bool(conflict_reasons)
        rows.append(
            {
                "campaign_id": packet.get("campaign_id"),
                "mirror_decision": packet.get("mirror_decision"),
                "reason_code": reasons,
                "decision_targets": decision_targets,
                "conflict_reasons": conflict_reasons,
                "conflict_detected": conflict,
                "inconclusive_candidate": conflict,
            }
        )
    return {
        "mirror_conflict_analysis_schema_version": "mirror_conflict_analysis_v1",
        "packet_count": len(rows),
        "conflict_count": sum(1 for row in rows if row["conflict_detected"]),
        "inconclusive_candidate_count": sum(1 for row in rows if row["inconclusive_candidate"]),
        "conflicts": rows,
        "is_trade_command": False,
    }


def build_evidence_sufficiency(inputs: Mapping[str, Any], conflict: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    conflict_by_campaign = {row["campaign_id"]: row for row in conflict["conflicts"]}
    for packet in inputs["packets"]:
        evidence = list(packet.get("supporting_features", {}).get("evidence", []))
        reasons = list(packet.get("reason_code", []))
        conflict_row = conflict_by_campaign.get(packet.get("campaign_id"), {})
        issues = []
        if not evidence:
            issues.append("evidence_missing")
        if not reasons:
            issues.append("reason_missing")
        if conflict_row.get("conflict_detected"):
            issues.append("reason_conflict")
        rows.append(
            {
                "campaign_id": packet.get("campaign_id"),
                "evidence_count": len(evidence),
                "reason_count": len(reasons),
                "issues": issues,
                "sufficient_for_decision": bool(evidence) and bool(reasons) and not conflict_row.get("conflict_detected"),
            }
        )
    issue_counts = Counter(issue for row in rows for issue in row["issues"])
    return {
        "mirror_evidence_sufficiency_schema_version": "mirror_evidence_sufficiency_v1",
        "packet_count": len(rows),
        "sufficient_count": sum(1 for row in rows if row["sufficient_for_decision"]),
        "issue_counts": dict(sorted(issue_counts.items())),
        "rows": rows,
        "is_trade_command": False,
    }


def build_confidence_calibration(inputs: Mapping[str, Any], conflict: Mapping[str, Any]) -> Dict[str, Any]:
    conflict_ids = {row["campaign_id"] for row in conflict["conflicts"] if row["conflict_detected"]}
    rows = []
    for packet in inputs["packets"]:
        confidence = float(packet.get("confidence", 0.0))
        conflicted = packet.get("campaign_id") in conflict_ids
        rows.append(
            {
                "campaign_id": packet.get("campaign_id"),
                "mirror_decision": packet.get("mirror_decision"),
                "confidence": confidence,
                "conflict_detected": conflicted,
                "confidence_consistency": "OVERCONFIDENT_CONFLICT" if conflicted and confidence >= 0.9 else "CONSISTENT",
            }
        )
    consistency = Counter(row["confidence_consistency"] for row in rows)
    return {
        "mirror_confidence_calibration_schema_version": "mirror_confidence_calibration_v1",
        "temporary_engineering_confidence": True,
        "confidence_is_modified": False,
        "consistency_counts": dict(sorted(consistency.items())),
        "rows": rows,
        "is_trade_command": False,
    }


def build_decision_stability(inputs: Mapping[str, Any]) -> Dict[str, Any]:
    first = inputs["packets"]
    second_result = engine.run_mirror_pattern_engine(output_dir=Path("/tmp") / "graymug_mirror_calibration_stability")
    second = load_jsonl(second_result["packets_path"])
    first_by_id = {packet["campaign_id"]: packet for packet in first}
    mismatches = []
    for packet in second:
        original = first_by_id.get(packet["campaign_id"])
        if not original:
            mismatches.append({"campaign_id": packet["campaign_id"], "issue": "missing_original"})
            continue
        if original["mirror_decision"] != packet["mirror_decision"] or original["reason_code"] != packet["reason_code"]:
            mismatches.append(
                {
                    "campaign_id": packet["campaign_id"],
                    "original_decision": original["mirror_decision"],
                    "replayed_decision": packet["mirror_decision"],
                    "original_reason": original["reason_code"],
                    "replayed_reason": packet["reason_code"],
                }
            )
    return {
        "mirror_decision_stability_schema_version": "mirror_decision_stability_v1",
        "deterministic": not mismatches,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "is_trade_command": False,
    }


def build_inconclusive_analysis(inputs: Mapping[str, Any], conflict: Mapping[str, Any], sufficiency: Mapping[str, Any]) -> Dict[str, Any]:
    counts = Counter(packet.get("mirror_decision") for packet in inputs["packets"])
    rule_gaps = []
    if counts.get("INCONCLUSIVE", 0) == 0:
        rule_gaps.append("INCONCLUSIVE is reachable in registry but not selected by current engine output.")
    if conflict["inconclusive_candidate_count"] > 0:
        rule_gaps.append("Conflict handling does not route conflict candidates to INCONCLUSIVE.")
    issue_counts = sufficiency.get("issue_counts", {})
    if not issue_counts.get("evidence_missing") and not issue_counts.get("reason_missing"):
        rule_gaps.append("No evidence or reason missing in current packets; INCONCLUSIVE absence is not caused by missing evidence.")
    return {
        "mirror_inconclusive_analysis_schema_version": "mirror_inconclusive_analysis_v1",
        "inconclusive_count": counts.get("INCONCLUSIVE", 0),
        "rule_gap_evidence": rule_gaps,
        "root_cause_candidates": {
            "rule_gap": bool(rule_gaps),
            "evidence_gap": bool(issue_counts.get("evidence_missing")),
            "conflict_handling_gap": conflict["inconclusive_candidate_count"] > 0,
            "registry_gap": False,
        },
        "is_trade_command": False,
    }


def build_calibration(
    inputs: Mapping[str, Any],
    decision: Mapping[str, Any],
    conflict: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    confidence: Mapping[str, Any],
    stability: Mapping[str, Any],
    inconclusive: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "mirror_decision_calibration_schema_version": "mirror_decision_calibration_v1",
        "packet_count": len(inputs["packets"]),
        "decision_distribution": decision["counts"],
        "conflict_count": conflict["conflict_count"],
        "evidence_sufficient_count": sufficiency["sufficient_count"],
        "confidence_consistency_counts": confidence["consistency_counts"],
        "deterministic": stability["deterministic"],
        "inconclusive_analysis": inconclusive["root_cause_candidates"],
        "is_trade_command": False,
    }


def build_calibration_report(
    decision: Mapping[str, Any],
    conflict: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    confidence: Mapping[str, Any],
    stability: Mapping[str, Any],
    inconclusive: Mapping[str, Any],
) -> Dict[str, Any]:
    calibration_needed = (
        decision["inconclusive_count"] == 0
        and (conflict["inconclusive_candidate_count"] > 0 or confidence["consistency_counts"].get("OVERCONFIDENT_CONFLICT", 0) > 0)
    )
    return {
        "mirror_decision_calibration_report_schema_version": "mirror_decision_calibration_report_v1",
        "calibration_verdict": "CALIBRATION_NEEDED" if calibration_needed else "NO_CALIBRATION_BLOCKER",
        "decision_distribution": decision["counts"],
        "conflict_count": conflict["conflict_count"],
        "inconclusive_candidate_count": conflict["inconclusive_candidate_count"],
        "evidence_sufficiency_issue_counts": sufficiency["issue_counts"],
        "confidence_consistency_counts": confidence["consistency_counts"],
        "deterministic": stability["deterministic"],
        "inconclusive_root_cause_candidates": inconclusive["root_cause_candidates"],
        "next_sprint_recommendation": "12AC Mirror Decision Refinement" if calibration_needed else "12AC Shadow Integration",
        "forbidden_actions_confirmed": [
            "No Mirror Engine logic change",
            "No Decision Rule change",
            "No Registry change",
            "No Threshold change",
            "No Gate change",
            "No Score change",
            "No Replay change",
            "No Campaign Physics change",
            "No Production change",
            "No Shadow Integration",
            "No ML training",
        ],
        "is_trade_command": False,
    }


def load_json(path: Path | str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_decision_calibration()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
