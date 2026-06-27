"""
Mirror ML Baseline Contract (Sprint 12AV)

Defines Training / Prediction / Evaluation Contracts for the Mirror ML Baseline.
No model training. No model files created. No predictions executed.
This is the Contract layer only — 12AW implements the actual pipeline.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

TRAINING_CONTRACT_VERSION = "mirror_ml_training_v1"
EXPECTED_FEATURE_CONTRACT_VERSION = "mirror_ml_feature_matrix_v1"
EXPECTED_SPLIT_CONTRACT_VERSION = "mirror_dataset_split_v1"

ALLOWED_MODEL_TYPES = ("LogisticRegression",)
DEFAULT_RANDOM_SEED = 42

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
MODEL_ARTIFACT_PATH = "outputs/mirror_ml_baseline_model.json"

_REQUIRED_TRAINING_CONTRACT_FIELDS = (
    "training_contract_version",
    "feature_contract_version",
    "split_contract_version",
    "training_dataset",
    "validation_dataset",
    "test_dataset",
    "model_type",
    "model_artifact",
    "random_seed",
    "prediction_schema",
    "evaluation_schema",
    "created_at",
)

_REQUIRED_PREDICTION_SCHEMA_FIELDS = (
    "sample_id",
    "packet_hash",
    "prediction",
    "probability",
    "model_version",
    "prediction_time",
)

_REQUIRED_EVALUATION_SCHEMA_FIELDS = (
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "confusion_matrix",
    "dataset_size",
    "reference_only",
)


# ---------------------------------------------------------------------------
# Prediction Schema
# ---------------------------------------------------------------------------

def build_prediction_schema() -> Dict[str, Any]:
    return {
        "prediction_schema_version": "mirror_prediction_schema_v1",
        "training_contract_version": TRAINING_CONTRACT_VERSION,
        "fields": list(_REQUIRED_PREDICTION_SCHEMA_FIELDS),
        "field_types": {
            "sample_id": "str",
            "packet_hash": "str",
            "prediction": "int",
            "probability": "float",
            "model_version": "str",
            "prediction_time": "str (ISO 8601)",
        },
        "prediction_values": {
            "1": "POSITIVE_MARKET_OUTCOME",
            "0": "NEGATIVE_MARKET_OUTCOME",
            "-1": "INSUFFICIENT_CLASS_DATA",
        },
        "notes": [
            "prediction mirrors label_encoding from mirror_ml_feature_matrix_v1.",
            "probability is the model confidence for the predicted class.",
            "model_version must match the training_contract_version that produced the model.",
        ],
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Evaluation Schema
# ---------------------------------------------------------------------------

def build_evaluation_schema() -> Dict[str, Any]:
    return {
        "evaluation_schema_version": "mirror_evaluation_schema_v1",
        "training_contract_version": TRAINING_CONTRACT_VERSION,
        "fields": list(_REQUIRED_EVALUATION_SCHEMA_FIELDS),
        "field_types": {
            "accuracy": "float",
            "precision": "float",
            "recall": "float",
            "f1_score": "float",
            "confusion_matrix": "dict",
            "dataset_size": "int",
            "reference_only": "bool",
        },
        "reference_only": True,
        "reference_note": (
            "All evaluation metrics are REFERENCE_ONLY. "
            "Current dataset N=20 is too small for statistically reliable evaluation. "
            "Do not use metrics as production criteria."
        ),
        "notes": [
            "현재 Dataset은 N=20 기반이다.",
            "성능 수치는 운영 기준으로 사용하지 않는다.",
            "Dataset이 충분히 커질 때까지 모든 평가 수치는 참고용이다.",
        ],
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Training Contract
# ---------------------------------------------------------------------------

def build_training_contract(
    *,
    training_dataset: str = "outputs/mirror_train_dataset.json",
    validation_dataset: str = "outputs/mirror_validation_dataset.json",
    test_dataset: str = "outputs/mirror_test_dataset.json",
    model_type: str = "LogisticRegression",
) -> Dict[str, Any]:
    prediction_schema = build_prediction_schema()
    evaluation_schema = build_evaluation_schema()

    return {
        "training_contract_version": TRAINING_CONTRACT_VERSION,
        "feature_contract_version": EXPECTED_FEATURE_CONTRACT_VERSION,
        "split_contract_version": EXPECTED_SPLIT_CONTRACT_VERSION,
        "training_dataset": training_dataset,
        "validation_dataset": validation_dataset,
        "test_dataset": test_dataset,
        "model_type": model_type,
        "model_artifact": MODEL_ARTIFACT_PATH,
        "random_seed": DEFAULT_RANDOM_SEED,
        "prediction_schema": prediction_schema,
        "evaluation_schema": evaluation_schema,
        "allowed_model_types": list(ALLOWED_MODEL_TYPES),
        "pipeline_stages": [
            "Train",
            "Save",
            "Load",
            "Predict",
            "Report",
        ],
        "reference_only": True,
        "reference_note": (
            "Current Dataset N=20. All evaluation metrics are REFERENCE_ONLY. "
            "Pipeline reproducibility is the goal of this contract, not accuracy."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Contract Validation
# ---------------------------------------------------------------------------

def validate_training_contract(contract: Mapping[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # Contract version
    if contract.get("training_contract_version") != TRAINING_CONTRACT_VERSION:
        issues.append({
            "issue": "wrong_training_contract_version",
            "value": contract.get("training_contract_version"),
        })

    # Required fields
    for field in _REQUIRED_TRAINING_CONTRACT_FIELDS:
        if field not in contract:
            issues.append({"issue": "missing_contract_field", "field": field})

    # Feature contract version
    if contract.get("feature_contract_version") != EXPECTED_FEATURE_CONTRACT_VERSION:
        issues.append({
            "issue": "wrong_feature_contract_version",
            "value": contract.get("feature_contract_version"),
        })

    # Split contract version
    if contract.get("split_contract_version") != EXPECTED_SPLIT_CONTRACT_VERSION:
        issues.append({
            "issue": "wrong_split_contract_version",
            "value": contract.get("split_contract_version"),
        })

    # Model type
    if contract.get("model_type") not in ALLOWED_MODEL_TYPES:
        issues.append({
            "issue": "disallowed_model_type",
            "value": contract.get("model_type"),
            "allowed": list(ALLOWED_MODEL_TYPES),
        })

    # Model artifact path
    if not contract.get("model_artifact"):
        issues.append({"issue": "missing_model_artifact_path"})

    # Random seed
    if contract.get("random_seed") != DEFAULT_RANDOM_SEED:
        issues.append({
            "issue": "wrong_random_seed",
            "value": contract.get("random_seed"),
        })

    # Prediction schema
    ps = contract.get("prediction_schema") or {}
    for field in _REQUIRED_PREDICTION_SCHEMA_FIELDS:
        if field not in (ps.get("fields") or []):
            issues.append({"issue": "missing_prediction_schema_field", "field": field})

    # Evaluation schema
    es = contract.get("evaluation_schema") or {}
    for field in _REQUIRED_EVALUATION_SCHEMA_FIELDS:
        if field not in (es.get("fields") or []):
            issues.append({"issue": "missing_evaluation_schema_field", "field": field})

    # REFERENCE_ONLY on evaluation schema
    if not (es.get("reference_only") is True):
        issues.append({"issue": "evaluation_schema_missing_reference_only"})

    # is_trade_command
    if contract.get("is_trade_command") is not False:
        issues.append({"issue": "is_trade_command_not_false"})

    valid = not issues
    return {
        "contract_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_ml_training_contract(
    *,
    output_dir: Optional["Path | str"] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    contract = build_training_contract()
    prediction_schema = build_prediction_schema()
    evaluation_schema = build_evaluation_schema()
    validation = validate_training_contract(contract)

    report = {
        "training_contract_version": TRAINING_CONTRACT_VERSION,
        "contract_layer_result": "PASS" if validation["contract_validation_result"] == "PASS" else "FAIL",
        "model_type": contract["model_type"],
        "model_artifact": contract["model_artifact"],
        "random_seed": contract["random_seed"],
        "contract_validation_result": validation["contract_validation_result"],
        "prediction_schema_fields": prediction_schema["fields"],
        "evaluation_schema_fields": evaluation_schema["fields"],
        "reference_only": True,
        "is_trade_command": False,
    }

    _write_json(contract, base / "mirror_ml_training_contract.json")
    _write_json(prediction_schema, base / "mirror_prediction_contract.json")
    _write_json(evaluation_schema, base / "mirror_evaluation_contract.json")
    _write_json(validation, base / "mirror_ml_contract_validation.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_ml_training_contract()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("contract_layer_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
