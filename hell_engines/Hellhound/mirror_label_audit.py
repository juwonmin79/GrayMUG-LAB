"""
Mirror Label Audit (Sprint 12AS)

Read-only quality gate for mirror_labeled_dataset.jsonl before ML input.
No Label modification. No Policy modification. No Dataset modification.
ML_INPUT_APPROVED is issued only when all audit checks PASS.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_dataset_contract as dataset_contract
except ImportError:
    from . import mirror_dataset_contract as dataset_contract


AUDIT_VERSION = "mirror_label_audit_v1"
EXPECTED_POLICY_VERSION = "mirror_label_policy_v1"

LABEL_CANDIDATES = (
    "POSITIVE_MARKET_OUTCOME",
    "NEGATIVE_MARKET_OUTCOME",
    "INSUFFICIENT_CLASS_DATA",
    "INSUFFICIENT_MARKET_DATA",
    "UNRESOLVED",
)

_DEFERRED_LABELS = ("INSUFFICIENT_MARKET_DATA", "UNRESOLVED")

_ML_APPROVAL_BASIS = (
    "Label Audit PASS",
    "Dataset Integrity PASS",
    "Original Dataset Protection PASS",
    "packet_hash Consistency PASS",
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_LABELED_PATH = DEFAULT_OUTPUT_DIR / "mirror_labeled_dataset.jsonl"
DEFAULT_ORIGINAL_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"
DEFAULT_POLICY_PATH = DEFAULT_OUTPUT_DIR / "mirror_label_policy.json"


# ---------------------------------------------------------------------------
# 1. Decision ↔ Label Consistency
# ---------------------------------------------------------------------------

def audit_decision_label_consistency(
    labeled_samples: Sequence[Mapping[str, Any]],
    decision_policy: Mapping[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, s in enumerate(labeled_samples):
        decision = s.get("decision")
        label = s.get("label_placeholder")
        dp = decision_policy.get(decision) or {}
        expected = dp.get("candidate_label")
        if label != expected:
            issues.append({
                "index": i,
                "sample_id": s.get("sample_id"),
                "decision": decision,
                "assigned_label": label,
                "expected_label": expected,
                "issue": "decision_label_mismatch",
            })
    return {
        "decision_label_consistency_result": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 2. Policy Version
# ---------------------------------------------------------------------------

def audit_policy_version(policy: Mapping[str, Any]) -> Dict[str, Any]:
    version = policy.get("policy_version")
    valid = version == EXPECTED_POLICY_VERSION
    return {
        "policy_version_audit_result": "PASS" if valid else "FAIL",
        "policy_version": version,
        "expected": EXPECTED_POLICY_VERSION,
        "issue_count": 0 if valid else 1,
        "issues": [] if valid else [{"issue": "wrong_policy_version", "value": version}],
    }


# ---------------------------------------------------------------------------
# 3. Label Candidate Validation
# ---------------------------------------------------------------------------

def audit_label_candidates(
    labeled_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, s in enumerate(labeled_samples):
        label = s.get("label_placeholder")
        if label not in LABEL_CANDIDATES:
            issues.append({
                "index": i,
                "sample_id": s.get("sample_id"),
                "issue": "invalid_label_candidate",
                "value": label,
            })
    return {
        "label_candidate_audit_result": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 4a. Dataset Integrity — sample level
# ---------------------------------------------------------------------------

def audit_dataset_integrity(
    labeled_samples: Sequence[Mapping[str, Any]],
    original_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # No duplicate sample_id
    seen_ids: Dict[str, int] = {}
    for i, s in enumerate(labeled_samples):
        sid = s.get("sample_id")
        if sid in seen_ids:
            issues.append({
                "index": i,
                "sample_id": sid,
                "issue": "duplicate_sample_id",
                "first_seen_at": seen_ids[sid],
            })
        else:
            seen_ids[sid] = i

    # packet_hash preserved vs original
    for i, (labeled, original) in enumerate(zip(labeled_samples, original_samples)):
        if labeled.get("packet_hash") != original.get("packet_hash"):
            issues.append({
                "index": i,
                "sample_id": labeled.get("sample_id"),
                "issue": "packet_hash_changed",
                "labeled": labeled.get("packet_hash"),
                "original": original.get("packet_hash"),
            })

    # Dataset order: sample_ids must match original order
    for i, (labeled, original) in enumerate(zip(labeled_samples, original_samples)):
        if labeled.get("sample_id") != original.get("sample_id"):
            issues.append({
                "index": i,
                "issue": "order_mismatch",
                "labeled_sample_id": labeled.get("sample_id"),
                "original_sample_id": original.get("sample_id"),
            })

    # Count consistency
    if len(labeled_samples) != len(original_samples):
        issues.append({
            "issue": "sample_count_mismatch",
            "labeled_count": len(labeled_samples),
            "original_count": len(original_samples),
        })

    return {
        "dataset_integrity_result": "PASS" if not issues else "FAIL",
        "sample_count": len(labeled_samples),
        "duplicate_sample_id_count": sum(1 for iss in issues if iss.get("issue") == "duplicate_sample_id"),
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 4b. BOM check
# ---------------------------------------------------------------------------

def audit_bom(path: Path) -> Dict[str, Any]:
    """Check that the JSONL file does NOT have a UTF-8 BOM."""
    try:
        with path.open("rb") as f:
            header = f.read(3)
        bom_detected = header == b"\xef\xbb\xbf"
        return {
            "bom_audit_result": "FAIL" if bom_detected else "PASS",
            "bom_detected": bom_detected,
        }
    except OSError as exc:
        return {
            "bom_audit_result": "FAIL",
            "bom_detected": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# 5. packet_hash Consistency
# ---------------------------------------------------------------------------

def audit_packet_hash_consistency(
    labeled_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Same packet_hash must have same Decision and same Label.
    Different Decision or Label on same hash → Audit Failure.
    """
    hash_map: Dict[str, Dict[str, set]] = {}
    for s in labeled_samples:
        ph = s.get("packet_hash") or ""
        if ph not in hash_map:
            hash_map[ph] = {"decisions": set(), "labels": set()}
        hash_map[ph]["decisions"].add(s.get("decision"))
        hash_map[ph]["labels"].add(s.get("label_placeholder"))

    issues: List[Dict[str, Any]] = []
    for ph, data in hash_map.items():
        if len(data["decisions"]) > 1:
            issues.append({
                "packet_hash": ph[:16] + "…",
                "issue": "multiple_decisions_on_same_hash",
                "decisions": sorted(data["decisions"]),
            })
        if len(data["labels"]) > 1:
            issues.append({
                "packet_hash": ph[:16] + "…",
                "issue": "multiple_labels_on_same_hash",
                "labels": sorted(data["labels"]),
            })

    return {
        "packet_hash_consistency_result": "PASS" if not issues else "FAIL",
        "unique_packet_hash_count": len(hash_map),
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 6. Original Dataset Protection
# ---------------------------------------------------------------------------

def audit_original_dataset_protection(
    original_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, s in enumerate(original_samples):
        if s.get("label_placeholder") is not None:
            issues.append({
                "index": i,
                "sample_id": s.get("sample_id"),
                "issue": "original_label_placeholder_not_null",
                "value": s.get("label_placeholder"),
            })
    mutation_count = len(issues)
    return {
        "original_dataset_protection_result": "PASS" if not issues else "FAIL",
        "mutation_count": mutation_count,
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 7. Deferred Label Validation (Warning only — not FAIL)
# ---------------------------------------------------------------------------

def audit_deferred_labels(
    labeled_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    found: Dict[str, List[str]] = {label: [] for label in _DEFERRED_LABELS}
    for s in labeled_samples:
        label = s.get("label_placeholder")
        if label in _DEFERRED_LABELS:
            found[label].append(s.get("sample_id") or "")

    total_found = sum(len(v) for v in found.values())
    return {
        "deferred_label_audit_result": "WARNING" if total_found > 0 else "PASS",
        "deferred_labels_found_count": total_found,
        "deferred_label_breakdown": {k: len(v) for k, v in found.items()},
        "note": (
            "Deferred labels found — issuance conditions not yet defined."
            if total_found > 0
            else "No deferred labels found."
        ),
    }


# ---------------------------------------------------------------------------
# ML Input Readiness
# ---------------------------------------------------------------------------

def build_ml_input_readiness(
    consistency: Mapping[str, Any],
    policy_audit: Mapping[str, Any],
    candidate_audit: Mapping[str, Any],
    integrity: Mapping[str, Any],
    bom: Mapping[str, Any],
    hash_consistency: Mapping[str, Any],
    original_protection: Mapping[str, Any],
) -> Dict[str, Any]:
    label_audit_pass = (
        consistency.get("decision_label_consistency_result") == "PASS"
        and policy_audit.get("policy_version_audit_result") == "PASS"
        and candidate_audit.get("label_candidate_audit_result") == "PASS"
    )
    dataset_integrity_pass = (
        integrity.get("dataset_integrity_result") == "PASS"
        and bom.get("bom_audit_result") == "PASS"
    )
    original_protection_pass = original_protection.get("original_dataset_protection_result") == "PASS"
    hash_consistency_pass = hash_consistency.get("packet_hash_consistency_result") == "PASS"

    approved = (
        label_audit_pass
        and dataset_integrity_pass
        and original_protection_pass
        and hash_consistency_pass
    )

    rejection_reasons: List[str] = []
    if not label_audit_pass:
        rejection_reasons.append("Label Audit FAIL")
    if not dataset_integrity_pass:
        rejection_reasons.append("Dataset Integrity FAIL")
    if not original_protection_pass:
        rejection_reasons.append("Original Dataset Protection FAIL")
    if not hash_consistency_pass:
        rejection_reasons.append("packet_hash Consistency FAIL")

    result: Dict[str, Any] = {
        "ML_INPUT_APPROVED": approved,
        "label_audit_pass": label_audit_pass,
        "dataset_integrity_pass": dataset_integrity_pass,
        "original_dataset_protection_pass": original_protection_pass,
        "packet_hash_consistency_pass": hash_consistency_pass,
    }
    if approved:
        result["approval_basis"] = list(_ML_APPROVAL_BASIS)
    else:
        result["rejection_reasons"] = rejection_reasons

    return result


# ---------------------------------------------------------------------------
# Audit Statistics
# ---------------------------------------------------------------------------

def build_audit_statistics(
    labeled_samples: Sequence[Mapping[str, Any]],
    audit_results: Mapping[str, Any],
) -> Dict[str, Any]:
    label_dist: Dict[str, int] = {c: 0 for c in LABEL_CANDIDATES}
    decision_dist: Dict[str, int] = {}
    for s in labeled_samples:
        label = s.get("label_placeholder")
        if label in label_dist:
            label_dist[label] += 1
        decision = s.get("decision") or "UNKNOWN"
        decision_dist[decision] = decision_dist.get(decision, 0) + 1

    return {
        "audit_statistics_schema_version": "mirror_label_audit_statistics_v1",
        "audit_version": AUDIT_VERSION,
        "sample_count": len(labeled_samples),
        "label_distribution": label_dist,
        "decision_distribution": decision_dist,
        "ml_input_approved": audit_results.get("ml_input_readiness", {}).get("ML_INPUT_APPROVED"),
        "mutation_count": audit_results.get("original_protection", {}).get("mutation_count", 0),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_label_audit(
    *,
    output_dir: Optional["Path | str"] = None,
    labeled_path: Optional["Path | str"] = None,
    original_path: Optional["Path | str"] = None,
    policy_path: Optional["Path | str"] = None,
    source_labeled: Optional[Sequence[Mapping[str, Any]]] = None,
    source_original: Optional[Sequence[Mapping[str, Any]]] = None,
    source_policy: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    # Load labeled dataset
    if source_labeled is not None:
        labeled_samples = list(source_labeled)
        lpath = Path(labeled_path) if labeled_path is not None else DEFAULT_LABELED_PATH
    else:
        lpath = Path(labeled_path) if labeled_path is not None else DEFAULT_LABELED_PATH
        labeled_samples = [
            json.loads(line) for line in lpath.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    # Load original dataset
    if source_original is not None:
        original_samples = list(source_original)
    else:
        opath = Path(original_path) if original_path is not None else DEFAULT_ORIGINAL_PATH
        original_samples = dataset_contract.load_dataset(opath)

    # Load policy
    if source_policy is not None:
        policy = dict(source_policy)
    else:
        p_path = Path(policy_path) if policy_path is not None else DEFAULT_POLICY_PATH
        policy = json.loads(p_path.read_text(encoding="utf-8"))

    decision_policy = policy.get("decision_policy") or {}

    # --- Run all audits ---
    consistency = audit_decision_label_consistency(labeled_samples, decision_policy)
    policy_audit = audit_policy_version(policy)
    candidate_audit = audit_label_candidates(labeled_samples)
    integrity = audit_dataset_integrity(labeled_samples, original_samples)
    bom = audit_bom(lpath)
    hash_consistency = audit_packet_hash_consistency(labeled_samples)
    original_protection = audit_original_dataset_protection(original_samples)
    deferred = audit_deferred_labels(labeled_samples)

    # ML Readiness
    ml_readiness = build_ml_input_readiness(
        consistency, policy_audit, candidate_audit,
        integrity, bom, hash_consistency, original_protection,
    )

    all_results = {
        "consistency": consistency,
        "policy_audit": policy_audit,
        "candidate_audit": candidate_audit,
        "integrity": integrity,
        "bom": bom,
        "hash_consistency": hash_consistency,
        "original_protection": original_protection,
        "deferred": deferred,
        "ml_input_readiness": ml_readiness,
    }
    statistics = build_audit_statistics(labeled_samples, all_results)

    # Audit report
    label_audit_result = (
        "PASS"
        if all(
            r == "PASS"
            for r in (
                consistency["decision_label_consistency_result"],
                policy_audit["policy_version_audit_result"],
                candidate_audit["label_candidate_audit_result"],
                integrity["dataset_integrity_result"],
                bom["bom_audit_result"],
                hash_consistency["packet_hash_consistency_result"],
                original_protection["original_dataset_protection_result"],
            )
        )
        else "FAIL"
    )

    audit_report = {
        "audit_version": AUDIT_VERSION,
        "sample_count": len(labeled_samples),
        "label_audit_result": label_audit_result,
        "decision_label_consistency_result": consistency["decision_label_consistency_result"],
        "policy_version_audit_result": policy_audit["policy_version_audit_result"],
        "label_candidate_audit_result": candidate_audit["label_candidate_audit_result"],
        "dataset_integrity_result": integrity["dataset_integrity_result"],
        "bom_audit_result": bom["bom_audit_result"],
        "packet_hash_consistency_result": hash_consistency["packet_hash_consistency_result"],
        "original_dataset_protection_result": original_protection["original_dataset_protection_result"],
        "deferred_label_audit_result": deferred["deferred_label_audit_result"],
        "mutation_count": original_protection["mutation_count"],
        "ML_INPUT_APPROVED": ml_readiness["ML_INPUT_APPROVED"],
        "is_trade_command": False,
    }

    consistency_report = {
        "consistency_schema_version": "mirror_label_consistency_v1",
        "audit_version": AUDIT_VERSION,
        "decision_label_consistency_result": consistency["decision_label_consistency_result"],
        "packet_hash_consistency_result": hash_consistency["packet_hash_consistency_result"],
        "policy_version_applied": policy.get("policy_version"),
        "consistency_issues": consistency["issues"],
        "hash_consistency_issues": hash_consistency["issues"],
        "is_trade_command": False,
    }

    integrity_report = {
        "integrity_schema_version": "mirror_label_integrity_v1",
        "audit_version": AUDIT_VERSION,
        "dataset_integrity_result": integrity["dataset_integrity_result"],
        "bom_audit_result": bom["bom_audit_result"],
        "original_dataset_protection_result": original_protection["original_dataset_protection_result"],
        "deferred_label_audit_result": deferred["deferred_label_audit_result"],
        "mutation_count": original_protection["mutation_count"],
        "duplicate_sample_id_count": integrity["duplicate_sample_id_count"],
        "deferred_label_breakdown": deferred["deferred_label_breakdown"],
        "is_trade_command": False,
    }

    _write_json(audit_report, base / "mirror_label_audit_report.json")
    _write_json(consistency_report, base / "mirror_label_consistency_report.json")
    _write_json(integrity_report, base / "mirror_label_integrity_report.json")
    _write_json(ml_readiness, base / "mirror_ml_input_readiness.json")
    _write_json(statistics, base / "mirror_label_audit_statistics.json")

    return audit_report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_label_audit()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("label_audit_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
