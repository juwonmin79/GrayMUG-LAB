"""
Mirror Dataset Split Layer (Sprint 12AU)

Splits mirror_ml_feature_matrix_v1 into Train / Validation / Test datasets.
No ML training. Deterministic split only (random_seed=42).
Remainder samples go to Train — no rounding, no arbitrary correction.
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SPLIT_CONTRACT_VERSION = "mirror_dataset_split_v1"
EXPECTED_FEATURE_CONTRACT_VERSION = "mirror_ml_feature_matrix_v1"

RANDOM_SEED = 42
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_MATRIX_PATH = DEFAULT_OUTPUT_DIR / "mirror_ml_feature_matrix.json"
DEFAULT_VALIDATION_PATH = DEFAULT_OUTPUT_DIR / "mirror_ml_feature_validation.json"

_REQUIRED_SPLIT_CONTRACT_FIELDS = (
    "split_contract_version",
    "source_feature_matrix",
    "random_seed",
    "split_ratio",
    "train_count",
    "validation_count",
    "test_count",
    "created_at",
)


# ---------------------------------------------------------------------------
# Feature Validation gate
# ---------------------------------------------------------------------------

def check_feature_validation(validation: Mapping[str, Any]) -> bool:
    return validation.get("feature_validation_result") == "PASS"


# ---------------------------------------------------------------------------
# Split Count calculation
# ---------------------------------------------------------------------------

def compute_split_counts(n: int) -> Tuple[int, int, int]:
    """
    Returns (train_count, validation_count, test_count).
    validation = floor(n * 0.15)
    test       = floor(n * 0.15)
    train      = n - validation - test   (remainder goes to train)
    """
    validation_count = math.floor(n * VALIDATION_RATIO)
    test_count = math.floor(n * TEST_RATIO)
    train_count = n - validation_count - test_count
    return train_count, validation_count, test_count


# ---------------------------------------------------------------------------
# Deterministic Split
# ---------------------------------------------------------------------------

def split_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = RANDOM_SEED,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (train, validation, test) lists.
    Shuffle is deterministic with the given seed.
    Original rows are never mutated — dict() copy on each item.
    """
    train_count, validation_count, test_count = compute_split_counts(len(rows))

    indices = list(range(len(rows)))
    rng = random.Random(seed)
    rng.shuffle(indices)

    train_indices = indices[:train_count]
    val_indices = indices[train_count: train_count + validation_count]
    test_indices = indices[train_count + validation_count:]

    def _pick(idx_list: List[int]) -> List[Dict[str, Any]]:
        return [dict(rows[i]) for i in idx_list]

    return _pick(train_indices), _pick(val_indices), _pick(test_indices)


# ---------------------------------------------------------------------------
# Split Contract
# ---------------------------------------------------------------------------

def build_split_contract(
    *,
    source_feature_matrix: str,
    train_count: int,
    validation_count: int,
    test_count: int,
) -> Dict[str, Any]:
    n = train_count + validation_count + test_count
    return {
        "split_contract_version": SPLIT_CONTRACT_VERSION,
        "source_feature_matrix": source_feature_matrix,
        "random_seed": RANDOM_SEED,
        "split_ratio": {
            "train": round(1.0 - VALIDATION_RATIO - TEST_RATIO, 4),
            "validation": VALIDATION_RATIO,
            "test": TEST_RATIO,
        },
        "split_count_rule": (
            "validation = floor(N * 0.15), test = floor(N * 0.15), "
            "train = N - validation - test (remainder to train)"
        ),
        "total_count": n,
        "train_count": train_count,
        "validation_count": validation_count,
        "test_count": test_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Leakage Validation
# ---------------------------------------------------------------------------

def validate_leakage(
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    def _ids(rows: Sequence[Mapping[str, Any]]) -> List[str]:
        return [str(r.get("sample_id", "")) for r in rows]

    def _hashes(rows: Sequence[Mapping[str, Any]]) -> List[str]:
        return [str(r.get("packet_hash", "")) for r in rows]

    train_ids = set(_ids(train))
    val_ids = set(_ids(validation))
    test_ids = set(_ids(test))

    train_hashes = set(_hashes(train))
    val_hashes = set(_hashes(validation))
    test_hashes = set(_hashes(test))

    # Duplicate sample_id within each split
    for name, rows in (("train", train), ("validation", validation), ("test", test)):
        seen: Dict[str, int] = {}
        for r in rows:
            sid = str(r.get("sample_id", ""))
            seen[sid] = seen.get(sid, 0) + 1
        for sid, cnt in seen.items():
            if cnt > 1:
                issues.append({"issue": "duplicate_sample_id_in_split", "split": name, "sample_id": sid})

    # Cross-split sample_id leakage
    tv = train_ids & val_ids
    tt = train_ids & test_ids
    vt = val_ids & test_ids
    if tv:
        issues.append({"issue": "train_validation_sample_id_overlap", "count": len(tv)})
    if tt:
        issues.append({"issue": "train_test_sample_id_overlap", "count": len(tt)})
    if vt:
        issues.append({"issue": "validation_test_sample_id_overlap", "count": len(vt)})

    # Cross-split packet_hash leakage
    thv = train_hashes & val_hashes
    tht = train_hashes & test_hashes
    vht = val_hashes & test_hashes
    if thv:
        issues.append({"issue": "train_validation_packet_hash_overlap", "count": len(thv)})
    if tht:
        issues.append({"issue": "train_test_packet_hash_overlap", "count": len(tht)})
    if vht:
        issues.append({"issue": "validation_test_packet_hash_overlap", "count": len(vht)})

    return {
        "leakage_validation_result": "PASS" if not issues else "FAIL",
        "leakage_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Coverage Validation
# ---------------------------------------------------------------------------

def validate_coverage(
    all_rows: Sequence[Mapping[str, Any]],
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    total = len(all_rows)
    covered = len(train) + len(validation) + len(test)
    all_ids = {str(r.get("sample_id", "")) for r in all_rows}
    used_ids = (
        {str(r.get("sample_id", "")) for r in train}
        | {str(r.get("sample_id", "")) for r in validation}
        | {str(r.get("sample_id", "")) for r in test}
    )
    missing = all_ids - used_ids
    extra = used_ids - all_ids
    issues: List[Dict[str, Any]] = []
    if covered != total:
        issues.append({"issue": "count_mismatch", "expected": total, "actual": covered})
    if missing:
        issues.append({"issue": "missing_samples", "count": len(missing)})
    if extra:
        issues.append({"issue": "extra_samples", "count": len(extra)})
    return {
        "coverage_validation_result": "PASS" if not issues else "FAIL",
        "total_count": total,
        "covered_count": covered,
        "coverage_pct": round(covered / total * 100, 2) if total else 0.0,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Split Statistics
# ---------------------------------------------------------------------------

def _label_dist(rows: Sequence[Mapping[str, Any]]) -> Dict[int, int]:
    dist: Dict[int, int] = {}
    for r in rows:
        le = r.get("label_encoded")
        if le is not None:
            dist[le] = dist.get(le, 0) + 1
    return dist


def _decision_dist(rows: Sequence[Mapping[str, Any]]) -> Dict[int, int]:
    dist: Dict[int, int] = {}
    for r in rows:
        de = (r.get("features") or {}).get("decision_encoded")
        if de is not None:
            dist[de] = dist.get(de, 0) + 1
    return dist


def build_split_statistics(
    all_rows: Sequence[Mapping[str, Any]],
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    n = len(all_rows)
    return {
        "statistics_schema_version": "mirror_dataset_split_statistics_v1",
        "split_contract_version": SPLIT_CONTRACT_VERSION,
        "total_count": n,
        "train_count": len(train),
        "validation_count": len(validation),
        "test_count": len(test),
        "reference_only": True,
        "reference_note": (
            f"Dataset Size = {n}. Statistics are reference only. "
            "Distribution may change as Dataset grows."
        ),
        "observations": [
            f"현재 Dataset 규모가 작다 (N={n}).",
            "Validation/Test 분포는 통계적으로 안정적이지 않을 수 있다.",
            "Label Distribution 편향이 발생할 수 있다.",
            "성능 평가는 참고용으로만 사용한다.",
        ],
        "train_label_distribution": _label_dist(train),
        "validation_label_distribution": _label_dist(validation),
        "test_label_distribution": _label_dist(test),
        "train_decision_distribution": _decision_dist(train),
        "validation_decision_distribution": _decision_dist(validation),
        "test_decision_distribution": _decision_dist(test),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Split Validation (contract-level)
# ---------------------------------------------------------------------------

def validate_split(
    split_contract: Mapping[str, Any],
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    leakage_result: Mapping[str, Any],
    coverage_result: Mapping[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # Contract version
    if split_contract.get("split_contract_version") != SPLIT_CONTRACT_VERSION:
        issues.append({"issue": "wrong_split_contract_version"})

    # Required fields
    for field in _REQUIRED_SPLIT_CONTRACT_FIELDS:
        if field not in split_contract:
            issues.append({"issue": "missing_contract_field", "field": field})

    # Random seed
    if split_contract.get("random_seed") != RANDOM_SEED:
        issues.append({"issue": "wrong_random_seed", "value": split_contract.get("random_seed")})

    # Count consistency
    train_count = split_contract.get("train_count")
    val_count = split_contract.get("validation_count")
    test_count = split_contract.get("test_count")
    if len(train) != train_count:
        issues.append({"issue": "train_count_mismatch", "expected": train_count, "actual": len(train)})
    if len(validation) != val_count:
        issues.append({"issue": "val_count_mismatch", "expected": val_count, "actual": len(validation)})
    if len(test) != test_count:
        issues.append({"issue": "test_count_mismatch", "expected": test_count, "actual": len(test)})

    # Leakage
    if leakage_result.get("leakage_validation_result") != "PASS":
        issues.append({"issue": "leakage_check_failed"})

    # Coverage
    if coverage_result.get("coverage_validation_result") != "PASS":
        issues.append({"issue": "coverage_check_failed"})

    # is_trade_command
    if split_contract.get("is_trade_command") is not False:
        issues.append({"issue": "is_trade_command_not_false"})

    valid = not issues
    return {
        "split_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Dataset wrapper
# ---------------------------------------------------------------------------

def build_split_dataset(
    rows: Sequence[Mapping[str, Any]],
    *,
    split_name: str,
    split_contract_version: str,
) -> Dict[str, Any]:
    return {
        "split_contract_version": split_contract_version,
        "split_name": split_name,
        "sample_count": len(rows),
        "rows": list(rows),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_dataset_split_layer(
    *,
    output_dir: Optional["Path | str"] = None,
    matrix_path: Optional["Path | str"] = None,
    feature_validation_path: Optional["Path | str"] = None,
    source_matrix: Optional[Mapping[str, Any]] = None,
    source_feature_validation: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    # Load feature validation
    if source_feature_validation is not None:
        feat_val = dict(source_feature_validation)
    else:
        fv_path = Path(feature_validation_path) if feature_validation_path is not None else DEFAULT_VALIDATION_PATH
        feat_val = json.loads(fv_path.read_text(encoding="utf-8"))

    # Feature Validation gate
    if not check_feature_validation(feat_val):
        fail_report = {
            "split_contract_version": SPLIT_CONTRACT_VERSION,
            "split_layer_result": "BLOCKED",
            "reason": "feature_validation_result is not PASS. Split not performed.",
            "feature_validation_result": feat_val.get("feature_validation_result"),
            "is_trade_command": False,
        }
        _write_json(fail_report, base / "mirror_dataset_split_validation.json")
        return fail_report

    # Load feature matrix
    matrix_source_name = "mirror_ml_feature_matrix.json"
    if source_matrix is not None:
        matrix = dict(source_matrix)
    else:
        m_path = Path(matrix_path) if matrix_path is not None else DEFAULT_MATRIX_PATH
        matrix_source_name = m_path.name
        matrix = json.loads(m_path.read_text(encoding="utf-8"))

    rows = matrix.get("rows") or []

    # Split
    train, validation, test = split_rows(rows, seed=RANDOM_SEED)
    train_count, val_count, test_count = len(train), len(validation), len(test)

    # Contract
    split_contract = build_split_contract(
        source_feature_matrix=matrix_source_name,
        train_count=train_count,
        validation_count=val_count,
        test_count=test_count,
    )

    # Leakage + Coverage
    leakage = validate_leakage(train, validation, test)
    coverage = validate_coverage(rows, train, validation, test)

    # Split Validation
    split_val = validate_split(split_contract, train, validation, test, leakage, coverage)

    # Statistics
    statistics = build_split_statistics(rows, train, validation, test)

    # Dataset wrappers
    train_ds = build_split_dataset(train, split_name="train", split_contract_version=SPLIT_CONTRACT_VERSION)
    val_ds = build_split_dataset(validation, split_name="validation", split_contract_version=SPLIT_CONTRACT_VERSION)
    test_ds = build_split_dataset(test, split_name="test", split_contract_version=SPLIT_CONTRACT_VERSION)

    # Report
    report = {
        "split_contract_version": SPLIT_CONTRACT_VERSION,
        "split_layer_result": "PASS" if split_val["split_validation_result"] == "PASS" else "FAIL",
        "feature_validation_result": feat_val.get("feature_validation_result"),
        "total_count": len(rows),
        "train_count": train_count,
        "validation_count": val_count,
        "test_count": test_count,
        "random_seed": RANDOM_SEED,
        "split_validation_result": split_val["split_validation_result"],
        "leakage_validation_result": leakage["leakage_validation_result"],
        "coverage_validation_result": coverage["coverage_validation_result"],
        "coverage_pct": coverage["coverage_pct"],
        "mutation_count": 0,
        "is_trade_command": False,
    }

    _write_json(train_ds, base / "mirror_train_dataset.json")
    _write_json(val_ds, base / "mirror_validation_dataset.json")
    _write_json(test_ds, base / "mirror_test_dataset.json")
    _write_json(split_contract, base / "mirror_dataset_split_report.json")
    _write_json(statistics, base / "mirror_dataset_split_statistics.json")
    _write_json(split_val, base / "mirror_dataset_split_validation.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_dataset_split_layer()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("split_layer_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
