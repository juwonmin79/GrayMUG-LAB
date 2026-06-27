from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

try:
    import mirror_ml_baseline_trainer as trainer
except ImportError:
    from . import mirror_ml_baseline_trainer as trainer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _row(
    idx: int,
    label: int = 1,
    decision: int = 1,
    early_mae: float = -2.0,
    recovery_ratio: float = 1.2,
    campaign_duration: float = 20.0,
    confidence: float = 0.9,
) -> dict:
    ph = f"{idx:064d}"
    return {
        "sample_id": f"ds-{idx:04d}",
        "packet_hash": ph,
        "features": {
            "early_mae": early_mae,
            "recovery_ratio": recovery_ratio,
            "campaign_duration": campaign_duration,
            "confidence": confidence,
            "decision_encoded": decision,
        },
        "label_encoded": label,
        "label_original": "POSITIVE_MARKET_OUTCOME" if label == 1 else "NEGATIVE_MARKET_OUTCOME",
    }


def _make_rows(n: int, half_positive: bool = True) -> list:
    rows = []
    for i in range(n):
        if half_positive:
            label = 1 if i < n // 2 else 0
            decision = 1 if i < n // 2 else 0
            mae = -2.0 if i < n // 2 else -8.0
            rec = 1.5 if i < n // 2 else 0.5
        else:
            label = 0
            decision = 0
            mae = -8.0
            rec = 0.5
        rows.append(_row(i, label=label, decision=decision, early_mae=mae, recovery_ratio=rec))
    return rows


def _train_model(n: int = 14) -> "trainer.LogisticRegression":
    rows = _make_rows(n)
    X, y = trainer.extract_X_y(rows)
    return trainer.train_baseline_model(X, y, seed=42)


def _make_ds(rows: list, split_name: str) -> dict:
    return {"split_name": split_name, "sample_count": len(rows), "rows": rows}


def _make_contract() -> dict:
    return {"training_contract_version": "mirror_ml_training_v1"}


def _run_pipeline(train_n=14, val_n=3, test_n=3) -> tuple:
    train_rows = _make_rows(train_n)
    val_rows = _make_rows(val_n)
    test_rows = _make_rows(test_n)
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        result = trainer.run_mirror_ml_baseline_trainer(
            output_dir=base,
            source_train=_make_ds(train_rows, "train"),
            source_val=_make_ds(val_rows, "validation"),
            source_test=_make_ds(test_rows, "test"),
            source_contract=_make_contract(),
        )
        files = {}
        for fname in (
            "mirror_ml_baseline_model.json",
            "mirror_prediction_report.json",
            "mirror_evaluation_report.json",
            "mirror_ml_baseline_validation.json",
        ):
            p = base / fname
            if p.exists():
                files[fname] = json.loads(p.read_text(encoding="utf-8"))
        return result, files


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------

class FeatureExtractionTest(unittest.TestCase):
    def test_extract_X_y_correct_shape(self) -> None:
        rows = _make_rows(5)
        X, y = trainer.extract_X_y(rows)
        self.assertEqual(len(X), 5)
        self.assertEqual(len(y), 5)
        self.assertEqual(len(X[0]), len(trainer.FEATURE_COLUMNS))

    def test_feature_column_order_preserved(self) -> None:
        row = _row(0, early_mae=-3.0, recovery_ratio=1.5, campaign_duration=22.0, confidence=0.8, decision=1)
        X, _ = trainer.extract_X_y([row])
        self.assertEqual(X[0][0], -3.0)   # early_mae
        self.assertEqual(X[0][1], 1.5)    # recovery_ratio
        self.assertEqual(X[0][2], 22.0)   # campaign_duration
        self.assertEqual(X[0][3], 0.8)    # confidence
        self.assertEqual(X[0][4], 1)      # decision_encoded

    def test_label_extracted_as_int(self) -> None:
        rows = [_row(0, label=1), _row(1, label=0)]
        _, y = trainer.extract_X_y(rows)
        self.assertEqual(y, [1, 0])

    def test_extract_X_no_labels(self) -> None:
        rows = _make_rows(3)
        X = trainer.extract_X(rows)
        self.assertEqual(len(X), 3)
        self.assertEqual(len(X[0]), len(trainer.FEATURE_COLUMNS))


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

class TrainingTest(unittest.TestCase):
    def test_model_trains_without_error(self) -> None:
        model = _train_model(14)
        self.assertIsNotNone(model)

    def test_model_has_coef(self) -> None:
        model = _train_model()
        self.assertIsNotNone(model.coef_)

    def test_model_has_intercept(self) -> None:
        model = _train_model()
        self.assertIsNotNone(model.intercept_)

    def test_model_has_classes(self) -> None:
        model = _train_model()
        self.assertIsNotNone(model.classes_)

    def test_model_has_n_features_in(self) -> None:
        model = _train_model()
        self.assertEqual(model.n_features_in_, len(trainer.FEATURE_COLUMNS))

    def test_same_seed_same_model(self) -> None:
        rows = _make_rows(14)
        X, y = trainer.extract_X_y(rows)
        m1 = trainer.train_baseline_model(X, y, seed=42)
        m2 = trainer.train_baseline_model(X, y, seed=42)
        np.testing.assert_array_equal(m1.coef_, m2.coef_)


# ---------------------------------------------------------------------------
# JSON Serialization
# ---------------------------------------------------------------------------

class SerializationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = _train_model()
        self.artifact = trainer.serialize_model(self.model, seed=42)

    def test_artifact_is_dict(self) -> None:
        self.assertIsInstance(self.artifact, dict)

    def test_model_type_correct(self) -> None:
        self.assertEqual(self.artifact["model_type"], "LogisticRegression")

    def test_coef_is_list(self) -> None:
        self.assertIsInstance(self.artifact["coef_"], list)

    def test_intercept_is_list(self) -> None:
        self.assertIsInstance(self.artifact["intercept_"], list)

    def test_classes_is_list(self) -> None:
        self.assertIsInstance(self.artifact["classes_"], list)

    def test_n_features_in_correct(self) -> None:
        self.assertEqual(self.artifact["n_features_in_"], len(trainer.FEATURE_COLUMNS))

    def test_feature_columns_in_artifact(self) -> None:
        self.assertEqual(self.artifact["feature_columns"], list(trainer.FEATURE_COLUMNS))

    def test_random_seed_in_artifact(self) -> None:
        self.assertEqual(self.artifact["random_seed"], 42)

    def test_all_required_fields_present(self) -> None:
        for field in trainer._REQUIRED_ARTIFACT_FIELDS:
            self.assertIn(field, self.artifact, f"missing: {field}")

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self.artifact["is_trade_command"])

    def test_artifact_is_json_serializable(self) -> None:
        serialized = json.dumps(self.artifact)
        loaded = json.loads(serialized)
        self.assertEqual(loaded["model_type"], "LogisticRegression")

    def test_no_binary_types_in_artifact(self) -> None:
        # Verify numpy arrays are converted to Python lists
        serialized = json.dumps(self.artifact)  # would raise if numpy types present
        self.assertIsInstance(serialized, str)


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------

class DeserializationTest(unittest.TestCase):
    def _roundtrip(self):
        model = _train_model()
        artifact = trainer.serialize_model(model, seed=42)
        json_str = json.dumps(artifact)
        loaded_artifact = json.loads(json_str)
        return model, trainer.deserialize_model(loaded_artifact)

    def test_loaded_model_can_predict(self) -> None:
        _, loaded = self._roundtrip()
        rows = _make_rows(3)
        preds = trainer.predict_rows(loaded, rows, model_version=trainer.TRAINER_VERSION)
        self.assertEqual(len(preds), 3)

    def test_coef_preserved_after_roundtrip(self) -> None:
        original, loaded = self._roundtrip()
        np.testing.assert_array_almost_equal(original.coef_, loaded.coef_, decimal=10)

    def test_intercept_preserved_after_roundtrip(self) -> None:
        original, loaded = self._roundtrip()
        np.testing.assert_array_almost_equal(original.intercept_, loaded.intercept_, decimal=10)

    def test_classes_preserved_after_roundtrip(self) -> None:
        original, loaded = self._roundtrip()
        np.testing.assert_array_equal(original.classes_, loaded.classes_)


# ---------------------------------------------------------------------------
# Artifact Validation
# ---------------------------------------------------------------------------

class ArtifactValidationTest(unittest.TestCase):
    def _artifact(self):
        return trainer.serialize_model(_train_model(), seed=42)

    def test_valid_artifact_passes(self) -> None:
        result = trainer.validate_artifact(self._artifact())
        self.assertEqual(result["artifact_validation_result"], "PASS")

    def test_wrong_model_type_fails(self) -> None:
        a = self._artifact()
        a["model_type"] = "XGBoost"
        result = trainer.validate_artifact(a)
        self.assertEqual(result["artifact_validation_result"], "FAIL")

    def test_missing_coef_fails(self) -> None:
        a = self._artifact()
        del a["coef_"]
        result = trainer.validate_artifact(a)
        self.assertEqual(result["artifact_validation_result"], "FAIL")

    def test_wrong_feature_columns_fails(self) -> None:
        a = self._artifact()
        a["feature_columns"] = ["wrong_col"]
        result = trainer.validate_artifact(a)
        self.assertEqual(result["artifact_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

class PredictionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = _train_model()
        self.rows = _make_rows(3)
        self.preds = trainer.predict_rows(self.model, self.rows, model_version=trainer.TRAINER_VERSION)

    def test_prediction_count_matches_rows(self) -> None:
        self.assertEqual(len(self.preds), len(self.rows))

    def test_required_prediction_fields_present(self) -> None:
        for field in ("sample_id", "packet_hash", "prediction", "probability", "prediction_time", "model_version"):
            self.assertIn(field, self.preds[0], f"missing: {field}")

    def test_prediction_is_int(self) -> None:
        for p in self.preds:
            self.assertIsInstance(p["prediction"], int)

    def test_probability_between_0_and_1(self) -> None:
        for p in self.preds:
            self.assertGreaterEqual(p["probability"], 0.0)
            self.assertLessEqual(p["probability"], 1.0)

    def test_model_version_in_prediction(self) -> None:
        for p in self.preds:
            self.assertEqual(p["model_version"], trainer.TRAINER_VERSION)

    def test_sample_id_preserved(self) -> None:
        for pred, row in zip(self.preds, self.rows):
            self.assertEqual(pred["sample_id"], row["sample_id"])

    def test_packet_hash_preserved(self) -> None:
        for pred, row in zip(self.preds, self.rows):
            self.assertEqual(pred["packet_hash"], row["packet_hash"])


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class EvaluationTest(unittest.TestCase):
    def _eval(self):
        model = _train_model(14)
        rows = _make_rows(3)
        preds = trainer.predict_rows(model, rows, model_version=trainer.TRAINER_VERSION)
        return trainer.evaluate_predictions(preds, split_name="validation")

    def test_required_evaluation_fields_present(self) -> None:
        ev = self._eval()
        for field in ("accuracy", "precision", "recall", "f1_score", "confusion_matrix", "dataset_size", "reference_only"):
            self.assertIn(field, ev)

    def test_reference_only_true(self) -> None:
        self.assertTrue(self._eval()["reference_only"])

    def test_reference_note_contains_reference_only(self) -> None:
        self.assertIn("REFERENCE_ONLY", self._eval()["reference_note"])

    def test_accuracy_between_0_and_1(self) -> None:
        acc = self._eval()["accuracy"]
        self.assertGreaterEqual(acc, 0.0)
        self.assertLessEqual(acc, 1.0)

    def test_confusion_matrix_is_list(self) -> None:
        cm = self._eval()["confusion_matrix"]
        self.assertIsInstance(cm, list)

    def test_dataset_size_correct(self) -> None:
        self.assertEqual(self._eval()["dataset_size"], 3)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self._eval()["is_trade_command"])


# ---------------------------------------------------------------------------
# Save / Load Validation
# ---------------------------------------------------------------------------

class SaveLoadValidationTest(unittest.TestCase):
    def _save_load_preds(self):
        model = _train_model()
        rows = _make_rows(5)
        preds_before = trainer.predict_rows(model, rows, model_version=trainer.TRAINER_VERSION)
        artifact = trainer.serialize_model(model, seed=42)
        json_str = json.dumps(artifact)
        loaded = trainer.deserialize_model(json.loads(json_str))
        preds_after = trainer.predict_rows(loaded, rows, model_version=trainer.TRAINER_VERSION)
        return preds_before, preds_after

    def test_save_load_predictions_identical(self) -> None:
        before, after = self._save_load_preds()
        result = trainer.validate_save_load(before, after)
        self.assertEqual(result["save_load_validation_result"], "PASS")
        self.assertEqual(result["mismatch_count"], 0)

    def test_save_load_probabilities_identical(self) -> None:
        before, after = self._save_load_preds()
        for b, a in zip(before, after):
            self.assertEqual(b["probability"], a["probability"])

    def test_mismatched_prediction_fails(self) -> None:
        before, after = self._save_load_preds()
        tampered = [dict(p) for p in after]
        # flip one prediction to force mismatch
        tampered[0]["prediction"] = 1 - tampered[0]["prediction"]
        result = trainer.validate_save_load(before, tampered)
        self.assertEqual(result["save_load_validation_result"], "FAIL")
        self.assertGreater(result["mismatch_count"], 0)

    def test_different_count_fails(self) -> None:
        before, after = self._save_load_preds()
        result = trainer.validate_save_load(before, after[:-1])
        self.assertEqual(result["save_load_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Run Pipeline (end-to-end)
# ---------------------------------------------------------------------------

class RunPipelineTest(unittest.TestCase):
    def test_output_files_created(self) -> None:
        _, files = _run_pipeline()
        for fname in (
            "mirror_ml_baseline_model.json",
            "mirror_prediction_report.json",
            "mirror_evaluation_report.json",
            "mirror_ml_baseline_validation.json",
        ):
            self.assertIn(fname, files, f"missing {fname}")

    def test_pipeline_result_pass(self) -> None:
        result, _ = _run_pipeline()
        self.assertEqual(result["pipeline_result"], "PASS")

    def test_artifact_validation_pass(self) -> None:
        result, _ = _run_pipeline()
        self.assertEqual(result["artifact_validation_result"], "PASS")

    def test_save_load_validation_pass(self) -> None:
        result, _ = _run_pipeline()
        self.assertEqual(result["save_load_validation_result"], "PASS")

    def test_mutation_count_zero(self) -> None:
        result, _ = _run_pipeline()
        self.assertEqual(result["mutation_count"], 0)

    def test_reference_only_true(self) -> None:
        result, _ = _run_pipeline()
        self.assertTrue(result["reference_only"])

    def test_is_not_trade_command(self) -> None:
        result, _ = _run_pipeline()
        self.assertFalse(result["is_trade_command"])

    def test_model_json_has_required_fields(self) -> None:
        _, files = _run_pipeline()
        model_json = files["mirror_ml_baseline_model.json"]
        for field in trainer._REQUIRED_ARTIFACT_FIELDS:
            self.assertIn(field, model_json)

    def test_model_json_no_pickle(self) -> None:
        # JSON model file must not contain binary markers
        _, files = _run_pipeline()
        model_str = json.dumps(files["mirror_ml_baseline_model.json"])
        self.assertNotIn("pickle", model_str.lower())
        self.assertNotIn("joblib", model_str.lower())

    def test_evaluation_report_reference_only(self) -> None:
        _, files = _run_pipeline()
        self.assertTrue(files["mirror_evaluation_report.json"]["reference_only"])

    def test_baseline_validation_json_no_pickle(self) -> None:
        _, files = _run_pipeline()
        val = files["mirror_ml_baseline_validation.json"]
        self.assertFalse(val["pickle_used"])
        self.assertFalse(val["joblib_used"])

    def test_prediction_report_has_both_splits(self) -> None:
        _, files = _run_pipeline()
        report = files["mirror_prediction_report.json"]
        self.assertIn("validation_predictions", report)
        self.assertIn("test_predictions", report)

    def test_model_artifact_path_in_result(self) -> None:
        result, _ = _run_pipeline()
        self.assertIn("model_artifact", result)


if __name__ == "__main__":
    unittest.main()
