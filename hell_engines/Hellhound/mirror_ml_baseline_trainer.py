"""
Mirror ML Baseline Trainer (Sprint 12AW)

Train → Save → Load → Predict → Report pipeline verification.
JSON serialization only. No pickle/joblib/binary formats.
Pipeline reproducibility is the goal, not model accuracy.
All evaluation results are REFERENCE_ONLY (N=20).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

TRAINER_VERSION = "mirror_ml_baseline_trainer_v1"
EXPECTED_TRAINING_CONTRACT_VERSION = "mirror_ml_training_v1"
EXPECTED_SPLIT_CONTRACT_VERSION = "mirror_dataset_split_v1"
EXPECTED_FEATURE_CONTRACT_VERSION = "mirror_ml_feature_matrix_v1"

# Fixed order — must match mirror_ml_feature_matrix_v1 FEATURE_COLUMNS
FEATURE_COLUMNS = ("early_mae", "recovery_ratio", "campaign_duration", "confidence", "decision_encoded")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_TRAIN_PATH = DEFAULT_OUTPUT_DIR / "mirror_train_dataset.json"
DEFAULT_VAL_PATH = DEFAULT_OUTPUT_DIR / "mirror_validation_dataset.json"
DEFAULT_TEST_PATH = DEFAULT_OUTPUT_DIR / "mirror_test_dataset.json"
DEFAULT_CONTRACT_PATH = DEFAULT_OUTPUT_DIR / "mirror_ml_training_contract.json"
DEFAULT_MODEL_PATH = DEFAULT_OUTPUT_DIR / "mirror_ml_baseline_model.json"

_REQUIRED_ARTIFACT_FIELDS = (
    "model_type", "model_version", "coef_", "intercept_",
    "classes_", "n_features_in_", "random_seed",
    "feature_columns", "feature_contract_version",
    "training_contract_version", "created_at",
)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_X_y(rows: Sequence[Mapping[str, Any]]) -> tuple:
    """Returns (X: list[list[float]], y: list[int]) in FEATURE_COLUMNS order."""
    X = [[row["features"][col] for col in FEATURE_COLUMNS] for row in rows]
    y = [int(row["label_encoded"]) for row in rows]
    return X, y


def extract_X(rows: Sequence[Mapping[str, Any]]) -> list:
    return [[row["features"][col] for col in FEATURE_COLUMNS] for row in rows]


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------

def train_baseline_model(
    X_train: Sequence,
    y_train: Sequence,
    *,
    seed: int = 42,
) -> LogisticRegression:
    model = LogisticRegression(random_state=seed, max_iter=1000)
    model.fit(np.array(X_train), np.array(y_train))
    return model


# ---------------------------------------------------------------------------
# JSON Serialization
# ---------------------------------------------------------------------------

def serialize_model(
    model: LogisticRegression,
    *,
    seed: int = 42,
    feature_contract_version: str = EXPECTED_FEATURE_CONTRACT_VERSION,
    training_contract_version: str = EXPECTED_TRAINING_CONTRACT_VERSION,
) -> Dict[str, Any]:
    return {
        "model_type": "LogisticRegression",
        "model_version": TRAINER_VERSION,
        "coef_": model.coef_.tolist(),
        "intercept_": model.intercept_.tolist(),
        "classes_": model.classes_.tolist(),
        "n_features_in_": int(model.n_features_in_),
        "feature_columns": list(FEATURE_COLUMNS),
        "random_seed": seed,
        "feature_contract_version": feature_contract_version,
        "training_contract_version": training_contract_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_trade_command": False,
    }


def deserialize_model(artifact: Mapping[str, Any]) -> LogisticRegression:
    """Reconstruct LogisticRegression from JSON artifact. No pickle used."""
    model = LogisticRegression(random_state=artifact["random_seed"])
    model.coef_ = np.array(artifact["coef_"])
    model.intercept_ = np.array(artifact["intercept_"])
    model.classes_ = np.array(artifact["classes_"])
    model.n_features_in_ = int(artifact["n_features_in_"])
    return model


def validate_artifact(artifact: Mapping[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    if artifact.get("model_type") != "LogisticRegression":
        issues.append({"issue": "wrong_model_type", "value": artifact.get("model_type")})

    for field in _REQUIRED_ARTIFACT_FIELDS:
        if field not in artifact:
            issues.append({"issue": "missing_artifact_field", "field": field})

    if artifact.get("feature_columns") != list(FEATURE_COLUMNS):
        issues.append({"issue": "wrong_feature_columns", "value": artifact.get("feature_columns")})

    if artifact.get("is_trade_command") is not False:
        issues.append({"issue": "is_trade_command_not_false"})

    return {
        "artifact_validation_result": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------

def predict_rows(
    model: LogisticRegression,
    rows: Sequence[Mapping[str, Any]],
    *,
    model_version: str,
) -> List[Dict[str, Any]]:
    X = np.array(extract_X(rows))
    raw_predictions = model.predict(X)
    probas = model.predict_proba(X)
    classes = list(model.classes_)
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for i, row in enumerate(rows):
        pred = int(raw_predictions[i])
        class_idx = classes.index(pred)
        prob = round(float(probas[i][class_idx]), 6)
        results.append({
            "sample_id": row.get("sample_id"),
            "packet_hash": row.get("packet_hash"),
            "prediction": pred,
            "probability": prob,
            "prediction_time": now,
            "model_version": model_version,
            "label_encoded": row.get("label_encoded"),
        })
    return results


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

def evaluate_predictions(
    predictions: Sequence[Mapping[str, Any]],
    *,
    split_name: str,
) -> Dict[str, Any]:
    y_true = [int(p["label_encoded"]) for p in predictions]
    y_pred = [int(p["prediction"]) for p in predictions]

    labels = sorted(set(y_true) | set(y_pred))

    acc = round(float(accuracy_score(y_true, y_pred)), 6)
    prec = round(float(precision_score(y_true, y_pred, average="weighted", zero_division=0)), 6)
    rec = round(float(recall_score(y_true, y_pred, average="weighted", zero_division=0)), 6)
    f1 = round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 6)
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    return {
        "evaluation_schema_version": "mirror_evaluation_schema_v1",
        "split_name": split_name,
        "dataset_size": len(predictions),
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "confusion_matrix": cm,
        "confusion_matrix_labels": labels,
        "reference_only": True,
        "reference_note": (
            f"Dataset Size = {len(predictions)} ({split_name}). "
            "REFERENCE_ONLY. Do not use as production criteria."
        ),
        "is_trade_command": False,
    }


# ---------------------------------------------------------------------------
# Save / Load Validation
# ---------------------------------------------------------------------------

def validate_save_load(
    predictions_before: Sequence[Mapping[str, Any]],
    predictions_after: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    if len(predictions_before) != len(predictions_after):
        issues.append({"issue": "prediction_count_mismatch"})
        return {"save_load_validation_result": "FAIL", "issue_count": len(issues), "issues": issues}

    for i, (b, a) in enumerate(zip(predictions_before, predictions_after)):
        if b["prediction"] != a["prediction"]:
            issues.append({"index": i, "issue": "prediction_mismatch",
                           "before": b["prediction"], "after": a["prediction"]})
        if b["probability"] != a["probability"]:
            issues.append({"index": i, "issue": "probability_mismatch",
                           "before": b["probability"], "after": a["probability"]})

    return {
        "save_load_validation_result": "PASS" if not issues else "FAIL",
        "prediction_count": len(predictions_before),
        "mismatch_count": len(issues),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run_mirror_ml_baseline_trainer(
    *,
    output_dir: Optional["Path | str"] = None,
    train_path: Optional["Path | str"] = None,
    val_path: Optional["Path | str"] = None,
    test_path: Optional["Path | str"] = None,
    contract_path: Optional["Path | str"] = None,
    source_train: Optional[Mapping[str, Any]] = None,
    source_val: Optional[Mapping[str, Any]] = None,
    source_test: Optional[Mapping[str, Any]] = None,
    source_contract: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    def _load(source, path, default):
        if source is not None:
            return dict(source)
        p = Path(path) if path is not None else default
        return json.loads(p.read_text(encoding="utf-8"))

    contract = _load(source_contract, contract_path, DEFAULT_CONTRACT_PATH)
    train_ds = _load(source_train, train_path, DEFAULT_TRAIN_PATH)
    val_ds = _load(source_val, val_path, DEFAULT_VAL_PATH)
    test_ds = _load(source_test, test_path, DEFAULT_TEST_PATH)

    train_rows = train_ds.get("rows") or []
    val_rows = val_ds.get("rows") or []
    test_rows = test_ds.get("rows") or []

    X_train, y_train = extract_X_y(train_rows)

    # --- Train ---
    model = train_baseline_model(X_train, y_train, seed=42)

    # --- Predict before save (for save/load validation) ---
    all_rows = val_rows + test_rows
    preds_before = predict_rows(model, all_rows, model_version=TRAINER_VERSION)

    # --- Serialize ---
    artifact = serialize_model(
        model,
        seed=42,
        feature_contract_version=EXPECTED_FEATURE_CONTRACT_VERSION,
        training_contract_version=EXPECTED_TRAINING_CONTRACT_VERSION,
    )
    artifact_validation = validate_artifact(artifact)

    # --- Save ---
    model_path = base / "mirror_ml_baseline_model.json"
    _write_json(artifact, model_path)

    # --- Load ---
    loaded_artifact = json.loads(model_path.read_text(encoding="utf-8"))
    loaded_model = deserialize_model(loaded_artifact)

    # --- Predict after load ---
    preds_after = predict_rows(loaded_model, all_rows, model_version=TRAINER_VERSION)

    # --- Save/Load Validation ---
    save_load_val = validate_save_load(preds_before, preds_after)

    # --- Final Predictions (using loaded model) ---
    val_preds = predict_rows(loaded_model, val_rows, model_version=TRAINER_VERSION)
    test_preds = predict_rows(loaded_model, test_rows, model_version=TRAINER_VERSION)

    # --- Evaluate ---
    val_eval = evaluate_predictions(val_preds, split_name="validation")
    test_eval = evaluate_predictions(test_preds, split_name="test")

    prediction_report = {
        "trainer_version": TRAINER_VERSION,
        "model_version": TRAINER_VERSION,
        "validation_predictions": val_preds,
        "test_predictions": test_preds,
        "reference_only": True,
        "is_trade_command": False,
    }

    evaluation_report = {
        "trainer_version": TRAINER_VERSION,
        "validation_evaluation": val_eval,
        "test_evaluation": test_eval,
        "reference_only": True,
        "reference_note": (
            "All evaluation metrics are REFERENCE_ONLY. "
            "N=20 dataset is too small for statistically reliable evaluation."
        ),
        "is_trade_command": False,
    }

    baseline_validation = {
        "trainer_version": TRAINER_VERSION,
        "training_result": "PASS",
        "artifact_validation_result": artifact_validation["artifact_validation_result"],
        "save_load_validation_result": save_load_val["save_load_validation_result"],
        "json_serialization": "PASS",
        "pickle_used": False,
        "joblib_used": False,
        "random_seed": 42,
        "train_count": len(train_rows),
        "validation_count": len(val_rows),
        "test_count": len(test_rows),
        "mutation_count": 0,
        "reference_only": True,
        "is_trade_command": False,
    }

    _write_json(prediction_report, base / "mirror_prediction_report.json")
    _write_json(evaluation_report, base / "mirror_evaluation_report.json")
    _write_json(baseline_validation, base / "mirror_ml_baseline_validation.json")

    overall = (
        artifact_validation["artifact_validation_result"] == "PASS"
        and save_load_val["save_load_validation_result"] == "PASS"
    )

    return {
        "trainer_version": TRAINER_VERSION,
        "pipeline_result": "PASS" if overall else "FAIL",
        "training_result": "PASS",
        "artifact_validation_result": artifact_validation["artifact_validation_result"],
        "save_load_validation_result": save_load_val["save_load_validation_result"],
        "validation_accuracy": val_eval["accuracy"],
        "test_accuracy": test_eval["accuracy"],
        "model_artifact": str(model_path),
        "mutation_count": 0,
        "reference_only": True,
        "is_trade_command": False,
    }


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    result = run_mirror_ml_baseline_trainer()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("pipeline_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
