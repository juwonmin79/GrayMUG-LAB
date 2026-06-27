"""
Mirror ML Feature Layer (Sprint 12AT)

Converts ML_INPUT_APPROVED mirror_labeled_dataset.jsonl into a Feature Matrix.
No ML training. No Feature Engineering. No new features.
Existing Dataset features only. Deterministic encoding only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Mapping, Optional, Sequence

FEATURE_CONTRACT_VERSION = "mirror_ml_feature_matrix_v1"

# Feature column order is fixed — must not change without contract version bump
FEATURE_COLUMNS = ("early_mae", "recovery_ratio", "campaign_duration", "confidence", "decision_encoded")
LABEL_COLUMN = "label_encoded"

DECISION_ENCODING: Dict[str, int] = {
    "REAL_WHALE_BACK": 1,
    "INCONCLUSIVE": 0,
    "FAKE_WHALE_BACK": -1,
}

LABEL_ENCODING: Dict[str, int] = {
    "POSITIVE_MARKET_OUTCOME": 1,
    "NEGATIVE_MARKET_OUTCOME": 0,
    "INSUFFICIENT_CLASS_DATA": -1,
}

_NUMERIC_FEATURES = ("early_mae", "recovery_ratio", "campaign_duration", "confidence")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_LABELED_PATH = DEFAULT_OUTPUT_DIR / "mirror_labeled_dataset.jsonl"
DEFAULT_READINESS_PATH = DEFAULT_OUTPUT_DIR / "mirror_ml_input_readiness.json"


# ---------------------------------------------------------------------------
# ML Approval gate
# ---------------------------------------------------------------------------

def check_ml_approval(readiness: Mapping[str, Any]) -> bool:
    return readiness.get("ML_INPUT_APPROVED") is True


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def encode_decision(decision: Optional[str]) -> Optional[int]:
    """Map decision string to int. Returns None for unknown decisions."""
    return DECISION_ENCODING.get(decision)  # type: ignore[return-value]


def encode_label(label: Optional[str]) -> Optional[int]:
    """Map label string to int. Returns None for unknown labels."""
    return LABEL_ENCODING.get(label)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Feature row builder
# ---------------------------------------------------------------------------

def build_feature_row(sample: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Extract and encode one Dataset Sample into a Feature Row.
    Never mutates input. Returns None-safe values for unknown encodings.
    """
    feature = sample.get("feature") or {}
    decision = sample.get("decision")
    label = sample.get("label_placeholder")

    return {
        "sample_id": sample.get("sample_id"),
        "packet_hash": sample.get("packet_hash"),
        "features": {
            "early_mae": feature.get("early_mae"),
            "recovery_ratio": feature.get("recovery_ratio"),
            "campaign_duration": feature.get("campaign_duration"),
            "confidence": feature.get("confidence"),
            "decision_encoded": encode_decision(decision),
        },
        "label_encoded": encode_label(label),
        "label_original": label,
    }


def build_feature_rows(samples: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [build_feature_row(s) for s in samples]


# ---------------------------------------------------------------------------
# Feature Matrix
# ---------------------------------------------------------------------------

def build_feature_matrix(
    samples: Sequence[Mapping[str, Any]],
    *,
    source_dataset: str = "mirror_labeled_dataset.jsonl",
) -> Dict[str, Any]:
    rows = build_feature_rows(samples)
    return {
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "source_dataset": source_dataset,
        "sample_count": len(rows),
        "feature_columns": list(FEATURE_COLUMNS),
        "label_column": LABEL_COLUMN,
        "encoding_map": {
            "decision_encoding": DECISION_ENCODING,
            "label_encoding": LABEL_ENCODING,
        },
        "rows": rows,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Feature Schema
# ---------------------------------------------------------------------------

def build_feature_schema() -> Dict[str, Any]:
    return {
        "feature_schema_version": "mirror_ml_feature_schema_v1",
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "label_column": LABEL_COLUMN,
        "numeric_features": list(_NUMERIC_FEATURES),
        "categorical_features": ["decision_encoded"],
        "decision_encoding": DECISION_ENCODING,
        "label_encoding": LABEL_ENCODING,
        "feature_source": "mirror_dataset_v1 sample.feature (existing fields only)",
        "notes": [
            "Feature columns are in fixed order defined by FEATURE_COLUMNS.",
            "Encoding is deterministic — no learned encoding.",
            "No new features are added. Only existing Dataset fields are used.",
        ],
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Feature Statistics
# ---------------------------------------------------------------------------

def _field_stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {
            "mean": None, "median": None, "minimum": None,
            "maximum": None, "standard_deviation": None,
        }
    return {
        "mean": round(mean(values), 6),
        "median": round(median(values), 6),
        "minimum": round(min(values), 6),
        "maximum": round(max(values), 6),
        "standard_deviation": round(stdev(values), 6) if len(values) >= 2 else None,
    }


def build_feature_statistics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def _vals(field: str) -> List[float]:
        return [
            float(r["features"][field])
            for r in rows
            if r.get("features", {}).get(field) is not None
        ]

    label_dist: Dict[int, int] = {}
    decision_dist: Dict[int, int] = {}
    for r in rows:
        le = r.get("label_encoded")
        de = r.get("features", {}).get("decision_encoded")
        if le is not None:
            label_dist[le] = label_dist.get(le, 0) + 1
        if de is not None:
            decision_dist[de] = decision_dist.get(de, 0) + 1

    return {
        "statistics_schema_version": "mirror_ml_feature_statistics_v1",
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "sample_count": len(rows),
        "reference_only": True,
        "reference_note": (
            f"Dataset Size = {len(rows)}. "
            "Statistics are reference only. "
            "Distribution may change as Dataset grows."
        ),
        "feature_stats": {field: _field_stats(_vals(field)) for field in _NUMERIC_FEATURES},
        "label_distribution": label_dist,
        "decision_distribution": decision_dist,
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_MATRIX_FIELDS = (
    "feature_contract_version", "source_dataset", "sample_count",
    "feature_columns", "label_column", "rows", "encoding_map", "created_at",
)

_REQUIRED_ROW_FIELDS = ("sample_id", "packet_hash", "features", "label_encoded", "label_original")


def validate_feature_matrix(
    matrix: Mapping[str, Any],
    original_samples: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # Contract version
    if matrix.get("feature_contract_version") != FEATURE_CONTRACT_VERSION:
        issues.append({
            "issue": "wrong_contract_version",
            "value": matrix.get("feature_contract_version"),
        })

    # Required matrix fields
    for field in _REQUIRED_MATRIX_FIELDS:
        if field not in matrix:
            issues.append({"issue": "missing_matrix_field", "field": field})

    # Feature column order
    if matrix.get("feature_columns") != list(FEATURE_COLUMNS):
        issues.append({
            "issue": "wrong_feature_column_order",
            "value": matrix.get("feature_columns"),
            "expected": list(FEATURE_COLUMNS),
        })

    # Label column
    if matrix.get("label_column") != LABEL_COLUMN:
        issues.append({"issue": "wrong_label_column", "value": matrix.get("label_column")})

    # Rows
    rows = matrix.get("rows") or []
    for i, row in enumerate(rows):
        for field in _REQUIRED_ROW_FIELDS:
            if field not in row:
                issues.append({"index": i, "issue": f"missing_row_field: {field}"})

        # decision_encoded valid
        de = (row.get("features") or {}).get("decision_encoded")
        if de not in DECISION_ENCODING.values():
            issues.append({
                "index": i,
                "sample_id": row.get("sample_id"),
                "issue": "invalid_decision_encoding",
                "value": de,
            })

        # label_encoded valid
        le = row.get("label_encoded")
        if le not in LABEL_ENCODING.values():
            issues.append({
                "index": i,
                "sample_id": row.get("sample_id"),
                "issue": "invalid_label_encoding",
                "value": le,
            })

        # Numeric features present
        features = row.get("features") or {}
        for fname in _NUMERIC_FEATURES:
            if features.get(fname) is None:
                issues.append({
                    "index": i,
                    "sample_id": row.get("sample_id"),
                    "issue": f"missing_numeric_feature: {fname}",
                })

    # sample_id and packet_hash preservation vs originals
    if original_samples is not None:
        for i, (row, orig) in enumerate(zip(rows, original_samples)):
            if row.get("sample_id") != orig.get("sample_id"):
                issues.append({"index": i, "issue": "sample_id_changed"})
            if row.get("packet_hash") != orig.get("packet_hash"):
                issues.append({"index": i, "issue": "packet_hash_changed"})

    # Sample count matches
    if matrix.get("sample_count") != len(rows):
        issues.append({"issue": "sample_count_mismatch", "declared": matrix.get("sample_count"), "actual": len(rows)})

    # is_trade_command
    if matrix.get("is_trade_command") is not False:
        issues.append({"issue": "is_trade_command_not_false"})

    mutation_count = sum(1 for iss in issues if "changed" in iss.get("issue", ""))
    valid = not issues
    return {
        "feature_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "mutation_count": mutation_count,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_ml_feature_layer(
    *,
    output_dir: Optional["Path | str"] = None,
    labeled_path: Optional["Path | str"] = None,
    readiness_path: Optional["Path | str"] = None,
    source_labeled: Optional[Sequence[Mapping[str, Any]]] = None,
    source_readiness: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    # Load readiness
    if source_readiness is not None:
        readiness = dict(source_readiness)
    else:
        r_path = Path(readiness_path) if readiness_path is not None else DEFAULT_READINESS_PATH
        readiness = json.loads(r_path.read_text(encoding="utf-8"))

    # ML_INPUT_APPROVED gate
    if not check_ml_approval(readiness):
        fail_report = {
            "feature_contract_version": FEATURE_CONTRACT_VERSION,
            "feature_layer_result": "BLOCKED",
            "reason": "ML_INPUT_APPROVED is not true. Feature Matrix not generated.",
            "ML_INPUT_APPROVED": readiness.get("ML_INPUT_APPROVED"),
            "is_trade_command": False,
        }
        _write_json(fail_report, base / "mirror_ml_feature_validation.json")
        return fail_report

    # Load labeled samples
    lpath_str = "mirror_labeled_dataset.jsonl"
    if source_labeled is not None:
        labeled_samples = list(source_labeled)
    else:
        lpath = Path(labeled_path) if labeled_path is not None else DEFAULT_LABELED_PATH
        lpath_str = lpath.name
        labeled_samples = [
            json.loads(line) for line in lpath.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    matrix = build_feature_matrix(labeled_samples, source_dataset=lpath_str)
    schema = build_feature_schema()
    statistics = build_feature_statistics(matrix["rows"])
    validation = validate_feature_matrix(matrix, original_samples=labeled_samples)

    report = {
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_layer_result": "PASS" if validation["feature_validation_result"] == "PASS" else "FAIL",
        "ML_INPUT_APPROVED": True,
        "sample_count": matrix["sample_count"],
        "feature_columns": matrix["feature_columns"],
        "label_column": LABEL_COLUMN,
        "feature_validation_result": validation["feature_validation_result"],
        "mutation_count": validation["mutation_count"],
        "is_trade_command": False,
    }

    _write_json(matrix, base / "mirror_ml_feature_matrix.json")
    _write_json(schema, base / "mirror_ml_feature_schema.json")
    _write_json(statistics, base / "mirror_ml_feature_statistics.json")
    _write_json(validation, base / "mirror_ml_feature_validation.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_ml_feature_layer()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("feature_layer_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
