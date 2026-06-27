"""
Mirror Label Policy Builder (Sprint 12AQ)

Builds a verifiable Label Policy Contract from Outcome Distribution data.
No Labels are generated. label_placeholder stays JSON null.
No Threshold. No Rule. No Score. Policy Contract only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_packet_contract
except ImportError:
    from . import mirror_packet_contract


LABEL_POLICY_VERSION = "mirror_label_policy_v1"

LABEL_CANDIDATES = (
    "POSITIVE_MARKET_OUTCOME",
    "NEGATIVE_MARKET_OUTCOME",
    "INSUFFICIENT_CLASS_DATA",
    "INSUFFICIENT_MARKET_DATA",
    "UNRESOLVED",
)

REQUIRED_POLICY_FIELDS = (
    "policy_version",
    "source_distribution_files",
    "decision_policy",
    "class_data_status",
    "required_fields",
    "label_candidates",
    "unresolved_policy_cases",
    "observations",
    "created_at",
)

CLASS_DATA_STATUS_AVAILABLE = "AVAILABLE"
CLASS_DATA_STATUS_INSUFFICIENT = "INSUFFICIENT_CLASS_DATA"

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DISTRIBUTION_PATH = DEFAULT_OUTPUT_DIR / "mirror_outcome_distribution_by_decision.json"

_SOURCE_DISTRIBUTION_FILES = [
    "outputs/mirror_outcome_distribution_report.json",
    "outputs/mirror_outcome_distribution_by_decision.json",
    "outputs/mirror_outcome_extreme_cases.json",
    "outputs/mirror_outcome_distribution_statistics.json",
]


def build_class_data_status(
    distribution_by_decision: Mapping[str, Any],
) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for decision in mirror_packet_contract.DECISION_ENUM:
        stats = distribution_by_decision.get(decision) or {}
        if stats.get("sample_count", 0) == 0:
            result[decision] = CLASS_DATA_STATUS_INSUFFICIENT
        else:
            result[decision] = CLASS_DATA_STATUS_AVAILABLE
    return result


def _candidate_label_from_distribution(
    positive_count: int,
    negative_count: int,
    completed_count: int,
) -> str:
    """
    Derive candidate label from observed distribution.
    This is a distribution observation — not a rule or threshold.
    """
    if completed_count == 0:
        return "INSUFFICIENT_CLASS_DATA"
    if positive_count == completed_count and negative_count == 0:
        return "POSITIVE_MARKET_OUTCOME"
    if negative_count == completed_count and positive_count == 0:
        return "NEGATIVE_MARKET_OUTCOME"
    return "UNRESOLVED"


def build_decision_policy_draft(
    distribution_by_decision: Mapping[str, Any],
) -> Dict[str, Any]:
    class_data_status = build_class_data_status(distribution_by_decision)
    draft: Dict[str, Any] = {}

    for decision in mirror_packet_contract.DECISION_ENUM:
        stats = distribution_by_decision.get(decision) or {}
        status = class_data_status[decision]

        if status == CLASS_DATA_STATUS_INSUFFICIENT:
            draft[decision] = {
                "class_data_status": CLASS_DATA_STATUS_INSUFFICIENT,
                "candidate_label": "INSUFFICIENT_CLASS_DATA",
                "confidence_basis": "no_samples",
                "sample_count": 0,
                "completed_count": 0,
                "positive_return_count": 0,
                "negative_return_count": 0,
                "observed_positive_ratio": None,
            }
        else:
            sample_count = stats.get("sample_count", 0)
            completed = stats.get("completed_count", 0)
            positive = stats.get("positive_return_count", 0)
            negative = stats.get("negative_return_count", 0)
            obs_pos_ratio = round(positive / completed, 4) if completed > 0 else None

            candidate = _candidate_label_from_distribution(positive, negative, completed)

            draft[decision] = {
                "class_data_status": CLASS_DATA_STATUS_AVAILABLE,
                "candidate_label": candidate,
                "confidence_basis": "distribution_observed",
                "sample_count": sample_count,
                "completed_count": completed,
                "positive_return_count": positive,
                "negative_return_count": negative,
                "observed_positive_ratio": obs_pos_ratio,
            }

    return draft


def build_unresolved_policy_cases() -> List[Dict[str, Any]]:
    """
    List of policy cases that require resolution in a future Sprint.
    INSUFFICIENT_MARKET_DATA issuance conditions are not defined in this Sprint.
    """
    return [
        {
            "case_id": "insufficient_market_data_issuance_condition",
            "description": "INSUFFICIENT_MARKET_DATA 발급 조건 정의 예정",
            "sprint": "TBD",
            "status": "UNRESOLVED",
        },
        {
            "case_id": "completed_false_handling",
            "description": "completed=false Sample 처리 여부",
            "sprint": "TBD",
            "status": "UNRESOLVED",
        },
        {
            "case_id": "replay_insufficient_handling",
            "description": "Replay 부족 처리 여부",
            "sprint": "TBD",
            "status": "UNRESOLVED",
        },
        {
            "case_id": "live_outcome_insufficient_handling",
            "description": "Live Outcome 부족 처리 여부",
            "sprint": "TBD",
            "status": "UNRESOLVED",
        },
        {
            "case_id": "market_observation_insufficient_handling",
            "description": "Market Observation 부족 처리 여부",
            "sprint": "TBD",
            "status": "UNRESOLVED",
        },
    ]


def build_policy_observations() -> List[str]:
    return [
        "현재 결과는 Sample 10개 기반이다.",
        "현재 Distribution만을 반영한 관찰 결과이다.",
        "향후 Dataset 증가 시 Policy 변경 가능성이 있다.",
        "observed_positive_ratio=0.0을 영구 Rule로 해석하지 않는다.",
        "INCONCLUSIVE의 Negative Return은 현재 10개 Sample에서의 관찰이다.",
        "FAKE_WHALE_BACK은 현재 데이터 없음. 데이터 확보 후 Policy 재정의 필요.",
    ]


def build_label_policy_contract(
    distribution_by_decision: Mapping[str, Any],
    *,
    source_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    class_data_status = build_class_data_status(distribution_by_decision)
    decision_policy = build_decision_policy_draft(distribution_by_decision)
    unresolved_cases = build_unresolved_policy_cases()
    observations = build_policy_observations()

    if source_files is None:
        source_files = _SOURCE_DISTRIBUTION_FILES

    return {
        "policy_version": LABEL_POLICY_VERSION,
        "source_distribution_files": source_files,
        "decision_policy": decision_policy,
        "class_data_status": class_data_status,
        "required_fields": list(REQUIRED_POLICY_FIELDS),
        "label_candidates": list(LABEL_CANDIDATES),
        "unresolved_policy_cases": unresolved_cases,
        "observations": observations,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_trade_command": False,
    }


def validate_policy(policy: Mapping[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # Policy version
    if policy.get("policy_version") != LABEL_POLICY_VERSION:
        issues.append({
            "issue": "wrong_policy_version",
            "value": policy.get("policy_version"),
            "expected": LABEL_POLICY_VERSION,
        })

    # Required fields
    for field in REQUIRED_POLICY_FIELDS:
        if field not in policy:
            issues.append({"issue": f"missing_required_field", "field": field})

    # Label candidates — all 5 must be present
    candidates = policy.get("label_candidates") or []
    for candidate in LABEL_CANDIDATES:
        if candidate not in candidates:
            issues.append({"issue": "missing_label_candidate", "candidate": candidate})

    # FAKE_WHALE_BACK must be INSUFFICIENT_CLASS_DATA
    decision_policy = policy.get("decision_policy") or {}
    fw = decision_policy.get("FAKE_WHALE_BACK") or {}
    if fw.get("candidate_label") != "INSUFFICIENT_CLASS_DATA":
        issues.append({
            "issue": "fake_whale_back_candidate_label_wrong",
            "value": fw.get("candidate_label"),
        })
    if fw.get("class_data_status") != CLASS_DATA_STATUS_INSUFFICIENT:
        issues.append({
            "issue": "fake_whale_back_class_data_status_wrong",
            "value": fw.get("class_data_status"),
        })

    # Unresolved cases must be present
    unresolved = policy.get("unresolved_policy_cases") or []
    if not unresolved:
        issues.append({"issue": "unresolved_policy_cases_empty"})

    # Observations must be present
    observations = policy.get("observations") or []
    if not observations:
        issues.append({"issue": "observations_empty"})

    # is_trade_command must be False
    if policy.get("is_trade_command") is not False:
        issues.append({"issue": "is_trade_command_not_false"})

    # Decision policy must cover all three decisions
    for decision in mirror_packet_contract.DECISION_ENUM:
        if decision not in decision_policy:
            issues.append({"issue": "decision_policy_missing", "decision": decision})

    # Each decision policy must have a valid candidate_label
    for decision, dp in decision_policy.items():
        if not isinstance(dp, dict):
            continue
        candidate = dp.get("candidate_label")
        if candidate not in LABEL_CANDIDATES:
            issues.append({
                "issue": "invalid_candidate_label",
                "decision": decision,
                "value": candidate,
            })

    valid = not issues
    return {
        "policy_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


def build_policy_report(
    policy: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    decision_policy = policy.get("decision_policy") or {}
    return {
        "policy_builder_version": "mirror_label_policy_builder_v1",
        "policy_version": policy.get("policy_version"),
        "policy_validation_result": validation.get("policy_validation_result"),
        "issue_count": validation.get("issue_count", 0),
        "decision_summary": {
            d: {
                "candidate_label": dp.get("candidate_label"),
                "class_data_status": dp.get("class_data_status"),
                "observed_positive_ratio": dp.get("observed_positive_ratio"),
                "sample_count": dp.get("sample_count"),
            }
            for d, dp in decision_policy.items()
            if isinstance(dp, dict)
        },
        "label_candidates": policy.get("label_candidates"),
        "unresolved_case_count": len(policy.get("unresolved_policy_cases") or []),
        "observations": policy.get("observations"),
        "label_placeholder_state": "null (JSON null — not modified in this Sprint)",
        "is_trade_command": False,
    }


def run_mirror_label_policy_builder(
    *,
    output_dir: Optional["Path | str"] = None,
    distribution_path: Optional["Path | str"] = None,
    source_distribution: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    if source_distribution is not None:
        distribution = dict(source_distribution)
    else:
        dist_path = Path(distribution_path) if distribution_path is not None else DEFAULT_DISTRIBUTION_PATH
        distribution = json.loads(dist_path.read_text(encoding="utf-8"))

    policy = build_label_policy_contract(distribution)
    validation = validate_policy(policy)
    report = build_policy_report(policy, validation)

    _write_json(policy, base / "mirror_label_policy.json")
    _write_json(report, base / "mirror_label_policy_report.json")
    _write_json(validation, base / "mirror_label_policy_validation.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_label_policy_builder()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("policy_validation_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
