"""
Mirror Label Builder (Sprint 12AR)

Applies mirror_label_policy_v1 to Dataset Samples.
No new Policy. No Threshold. No Rule. No Score. Apply Policy Only.
Original mirror_dataset.jsonl is never modified.
Output: mirror_labeled_dataset.jsonl (new file).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_dataset_contract as dataset_contract
except ImportError:
    from . import mirror_dataset_contract as dataset_contract


LABEL_BUILDER_VERSION = "mirror_label_builder_v1"
EXPECTED_POLICY_VERSION = "mirror_label_policy_v1"

LABEL_CANDIDATES = (
    "POSITIVE_MARKET_OUTCOME",
    "NEGATIVE_MARKET_OUTCOME",
    "INSUFFICIENT_CLASS_DATA",
    "INSUFFICIENT_MARKET_DATA",
    "UNRESOLVED",
)

# Labels whose issuance conditions are undefined in this Sprint
_DEFERRED_LABELS = ("INSUFFICIENT_MARKET_DATA", "UNRESOLVED")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"
DEFAULT_POLICY_PATH = DEFAULT_OUTPUT_DIR / "mirror_label_policy.json"


# ---------------------------------------------------------------------------
# Policy reference
# ---------------------------------------------------------------------------

def load_policy(path: "Path | str") -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_policy_reference(policy: Mapping[str, Any]) -> Dict[str, Any]:
    """Verify the loaded policy is the expected version and is structurally sound."""
    issues: List[Dict[str, Any]] = []

    if policy.get("policy_version") != EXPECTED_POLICY_VERSION:
        issues.append({
            "issue": "wrong_policy_version",
            "value": policy.get("policy_version"),
            "expected": EXPECTED_POLICY_VERSION,
        })

    if not policy.get("decision_policy"):
        issues.append({"issue": "decision_policy_missing"})

    valid = not issues
    return {
        "policy_reference_valid": valid,
        "policy_version": policy.get("policy_version"),
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Label assignment
# ---------------------------------------------------------------------------

def assign_label(
    sample: Mapping[str, Any],
    decision_policy: Mapping[str, Any],
) -> str:
    """
    Map sample.decision → candidate_label from policy.
    Returns "UNRESOLVED" if no match found.
    No new judgment. Policy only.
    """
    decision = sample.get("decision")
    dp = decision_policy.get(decision) or {}
    candidate = dp.get("candidate_label")
    if candidate not in LABEL_CANDIDATES:
        return "UNRESOLVED"
    return candidate


def apply_label(
    sample: Mapping[str, Any],
    label: str,
) -> Dict[str, Any]:
    """Return a new labeled sample dict. Never mutates input."""
    labeled = copy.deepcopy(dict(sample))
    labeled["label_placeholder"] = label
    return labeled


# ---------------------------------------------------------------------------
# Batch assignment
# ---------------------------------------------------------------------------

def assign_labels_batch(
    samples: Sequence[Mapping[str, Any]],
    decision_policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """
    Assign and apply labels to all samples.
    Returns (labeled_samples, assignment_rows).
    """
    labeled_samples = []
    for sample in samples:
        label = assign_label(sample, decision_policy)
        labeled = apply_label(sample, label)
        labeled_samples.append(labeled)
    return labeled_samples


def build_assignment_rows(
    original_samples: Sequence[Mapping[str, Any]],
    labeled_samples: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    for orig, labeled in zip(original_samples, labeled_samples):
        rows.append({
            "sample_id": orig.get("sample_id"),
            "decision": orig.get("decision"),
            "assigned_label": labeled.get("label_placeholder"),
            "packet_hash": orig.get("packet_hash"),
            "original_label_placeholder_null": orig.get("label_placeholder") is None,
        })
    return rows


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_assignments(
    labeled_samples: Sequence[Mapping[str, Any]],
    original_samples: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # Policy version
    if policy.get("policy_version") != EXPECTED_POLICY_VERSION:
        issues.append({"issue": "wrong_policy_version", "value": policy.get("policy_version")})

    for i, (labeled, original) in enumerate(zip(labeled_samples, original_samples)):
        sample_id = labeled.get("sample_id")

        # Original must remain unmodified
        if original.get("label_placeholder") is not None:
            issues.append({"index": i, "sample_id": sample_id, "issue": "original_label_placeholder_mutated"})

        # Core data fields unchanged
        for field in ("packet_hash", "feature", "decision", "contract_version", "dataset_contract_version"):
            if labeled.get(field) != original.get(field):
                issues.append({"index": i, "sample_id": sample_id, "issue": f"{field}_mutated"})

        # label_placeholder must now be filled (not None)
        label = labeled.get("label_placeholder")
        if label is None:
            issues.append({"index": i, "sample_id": sample_id, "issue": "label_placeholder_still_null"})

        # label must be a valid candidate
        elif label not in LABEL_CANDIDATES:
            issues.append({"index": i, "sample_id": sample_id, "issue": "invalid_label", "value": label})

        # Deferred labels must not appear in this Sprint's dataset
        elif label in _DEFERRED_LABELS:
            issues.append({
                "index": i,
                "sample_id": sample_id,
                "issue": f"deferred_label_applied",
                "value": label,
            })

    mutation_count = sum(1 for iss in issues if "mutated" in iss.get("issue", ""))
    valid = not issues
    return {
        "label_assignment_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "mutation_count": mutation_count,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def build_assignment_statistics(
    labeled_samples: Sequence[Mapping[str, Any]],
    assignment_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    label_dist: Dict[str, int] = {c: 0 for c in LABEL_CANDIDATES}
    decision_dist: Dict[str, int] = {}
    null_count = 0

    for s in labeled_samples:
        label = s.get("label_placeholder")
        if label is None:
            null_count += 1
        elif label in label_dist:
            label_dist[label] += 1

    for row in assignment_rows:
        decision = row.get("decision") or "UNKNOWN"
        decision_dist[decision] = decision_dist.get(decision, 0) + 1

    return {
        "statistics_schema_version": "mirror_label_assignment_statistics_v1",
        "label_builder_version": LABEL_BUILDER_VERSION,
        "total_count": len(labeled_samples),
        "null_label_count": null_count,
        "assigned_count": len(labeled_samples) - null_count,
        "label_distribution": label_dist,
        "decision_distribution": decision_dist,
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# JSONL writer (new file — never appends to original dataset)
# ---------------------------------------------------------------------------

def write_labeled_dataset(labeled_samples: Sequence[Mapping[str, Any]], path: Path) -> None:
    """Write all labeled samples as a new JSONL file. Overwrites if exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(dict(s), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for s in labeled_samples
    ]
    path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_label_builder(
    *,
    output_dir: Optional["Path | str"] = None,
    dataset_path: Optional["Path | str"] = None,
    policy_path: Optional["Path | str"] = None,
    source_samples: Optional[Sequence[Mapping[str, Any]]] = None,
    source_policy: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    # Load samples (original — read-only)
    if source_samples is not None:
        samples = list(source_samples)
    else:
        ds_path = Path(dataset_path) if dataset_path is not None else DEFAULT_DATASET_PATH
        samples = dataset_contract.load_dataset(ds_path)

    # Load policy
    if source_policy is not None:
        policy = dict(source_policy)
    else:
        p_path = Path(policy_path) if policy_path is not None else DEFAULT_POLICY_PATH
        policy = load_policy(p_path)

    # Validate policy reference
    policy_ref = validate_policy_reference(policy)
    decision_policy = policy.get("decision_policy") or {}

    started = perf_counter()

    # Assign labels (original samples untouched — deep copy inside apply_label)
    labeled_samples = assign_labels_batch(samples, decision_policy)
    assignment_rows = build_assignment_rows(samples, labeled_samples)

    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    # Confirm original samples are unmodified
    original_unchanged = all(s.get("label_placeholder") is None for s in samples)

    # Validate
    validation = validate_assignments(labeled_samples, samples, policy)

    # Statistics
    statistics = build_assignment_statistics(labeled_samples, assignment_rows)

    # Write labeled dataset (new file)
    write_labeled_dataset(labeled_samples, base / "mirror_labeled_dataset.jsonl")

    report = {
        "label_builder_version": LABEL_BUILDER_VERSION,
        "policy_version_applied": policy.get("policy_version"),
        "policy_reference_valid": policy_ref["policy_reference_valid"],
        "sample_count": len(samples),
        "labeled_count": len(labeled_samples),
        "label_assignment_validation_result": validation["label_assignment_validation_result"],
        "mutation_count": validation["mutation_count"],
        "original_dataset_unchanged": original_unchanged,
        "null_label_count": statistics["null_label_count"],
        "label_distribution": statistics["label_distribution"],
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }

    _write_json(report, base / "mirror_label_assignment_report.json")
    _write_json(statistics, base / "mirror_label_assignment_statistics.json")
    _write_json(validation, base / "mirror_label_assignment_validation.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_label_builder()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("label_assignment_validation_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
