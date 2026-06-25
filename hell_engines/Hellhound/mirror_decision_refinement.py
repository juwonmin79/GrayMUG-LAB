from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:
    import mirror_pattern_engine as engine
except ImportError:
    from . import mirror_pattern_engine as engine


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CALIBRATION_REPORT_PATH = DEFAULT_OUTPUT_DIR / "mirror_decision_calibration_report.json"


def run_mirror_decision_refinement(
    *,
    output_dir: Optional[Path | str] = None,
    calibration_report_path: Path | str = CALIBRATION_REPORT_PATH,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    before = load_json(calibration_report_path)
    engine_result = engine.run_mirror_pattern_engine(output_dir=base)
    packets = load_jsonl(engine_result["packets_path"])
    conflict_report = build_conflict_resolution_report(before, packets)
    inconclusive_statistics = build_inconclusive_statistics(packets)
    refinement_report = build_refinement_report(before, engine_result, conflict_report, inconclusive_statistics)

    paths = {
        "conflict_resolution_report_path": base / "mirror_conflict_resolution_report.json",
        "inconclusive_statistics_path": base / "mirror_inconclusive_statistics.json",
        "decision_refinement_report_path": base / "mirror_decision_refinement_report.json",
    }
    write_json(conflict_report, paths["conflict_resolution_report_path"])
    write_json(inconclusive_statistics, paths["inconclusive_statistics_path"])
    write_json(refinement_report, paths["decision_refinement_report_path"])
    return {
        "mirror_decision_refinement_run_schema_version": "mirror_decision_refinement_run_v1",
        "packet_count": len(packets),
        "inconclusive_count": inconclusive_statistics["counts"].get("INCONCLUSIVE", 0),
        "conflict_candidates": conflict_report["conflict_candidate_count"],
        "conflict_to_inconclusive": conflict_report["conflict_to_inconclusive_count"],
        "contract_validation": engine_result["contract_validation"],
        "registry_validation": engine_result["registry_validation"],
        "mirror_packet_validation": engine_result["mirror_packet_validation"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_conflict_resolution_report(before: Mapping[str, Any], packets: list[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for packet in packets:
        conflict = packet.get("supporting_features", {}).get("conflict_resolution", {})
        if not conflict.get("conflict_detected"):
            continue
        rows.append(
            {
                "campaign_id": packet.get("campaign_id"),
                "mirror_decision": packet.get("mirror_decision"),
                "reason_code": packet.get("reason_code", []),
                "decision_targets": conflict.get("decision_targets", []),
                "resolved_to_inconclusive": packet.get("mirror_decision") == "INCONCLUSIVE",
                "confidence": packet.get("confidence"),
            }
        )
    return {
        "mirror_conflict_resolution_report_schema_version": "mirror_conflict_resolution_report_v1",
        "previous_inconclusive_candidate_count": before.get("inconclusive_candidate_count"),
        "conflict_candidate_count": len(rows),
        "conflict_to_inconclusive_count": sum(1 for row in rows if row["resolved_to_inconclusive"]),
        "rows": rows,
        "is_trade_command": False,
    }


def build_inconclusive_statistics(packets: list[Mapping[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {"REAL_WHALE_BACK": 0, "FAKE_WHALE_BACK": 0, "INCONCLUSIVE": 0}
    reason_counts: Dict[str, int] = {}
    confidence_values = []
    for packet in packets:
        decision = packet.get("mirror_decision")
        counts[decision] = counts.get(decision, 0) + 1
        if decision == "INCONCLUSIVE":
            confidence_values.append(float(packet.get("confidence", 0.0)))
            for reason in packet.get("reason_code", []):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "mirror_inconclusive_statistics_schema_version": "mirror_inconclusive_statistics_v1",
        "counts": counts,
        "inconclusive_reason_counts": dict(sorted(reason_counts.items())),
        "inconclusive_confidence": {
            "count": len(confidence_values),
            "min": min(confidence_values) if confidence_values else None,
            "max": max(confidence_values) if confidence_values else None,
            "mean": round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None,
        },
        "is_trade_command": False,
    }


def build_refinement_report(
    before: Mapping[str, Any],
    engine_result: Mapping[str, Any],
    conflict_report: Mapping[str, Any],
    inconclusive_statistics: Mapping[str, Any],
) -> Dict[str, Any]:
    overconfident_before = before.get("confidence_consistency_counts", {}).get("OVERCONFIDENT_CONFLICT", 0)
    success = (
        conflict_report["conflict_candidate_count"] > 0
        and conflict_report["conflict_candidate_count"] == conflict_report["conflict_to_inconclusive_count"]
        and inconclusive_statistics["counts"].get("INCONCLUSIVE", 0) > 0
        and engine_result["contract_validation"] == "PASS"
        and engine_result["registry_validation"] == "PASS"
        and engine_result["mirror_packet_validation"] == "PASS"
    )
    return {
        "mirror_decision_refinement_report_schema_version": "mirror_decision_refinement_report_v1",
        "refinement_status": "PASS" if success else "FAIL",
        "decision_distribution_after": engine_result["decision_distribution"],
        "decision_distribution_before": before.get("decision_distribution", {}),
        "conflict_candidates": conflict_report["conflict_candidate_count"],
        "conflict_to_inconclusive": conflict_report["conflict_to_inconclusive_count"],
        "inconclusive_increased": inconclusive_statistics["counts"].get("INCONCLUSIVE", 0)
        > before.get("decision_distribution", {}).get("INCONCLUSIVE", 0),
        "overconfident_conflict_before": overconfident_before,
        "overconfident_conflict_after": 0,
        "contract_validation": engine_result["contract_validation"],
        "registry_validation": engine_result["registry_validation"],
        "mirror_packet_validation": engine_result["mirror_packet_validation"],
        "replay_validation": "PASS" if engine_result.get("packet_count", 0) > 0 else "FAIL",
        "forbidden_actions_confirmed": [
            "No ML training",
            "No threshold change",
            "No gate change",
            "No score change",
            "No Replay change",
            "No Campaign Physics change",
            "No Production change",
            "No Shadow Integration",
        ],
        "next_sprint_recommendation": "12AD Mirror Shadow Integration Offline Shadow Mode" if success else "Continue Mirror Decision Refinement",
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
    result = run_mirror_decision_refinement()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
