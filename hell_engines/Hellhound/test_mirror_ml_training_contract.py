from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_ml_training_contract as tc
except ImportError:
    from . import mirror_ml_training_contract as tc


# ---------------------------------------------------------------------------
# Prediction Schema
# ---------------------------------------------------------------------------

class PredictionSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = tc.build_prediction_schema()

    def test_schema_has_all_required_fields(self) -> None:
        for field in tc._REQUIRED_PREDICTION_SCHEMA_FIELDS:
            self.assertIn(field, self.schema["fields"], f"missing: {field}")

    def test_sample_id_field_present(self) -> None:
        self.assertIn("sample_id", self.schema["fields"])

    def test_packet_hash_field_present(self) -> None:
        self.assertIn("packet_hash", self.schema["fields"])

    def test_prediction_field_present(self) -> None:
        self.assertIn("prediction", self.schema["fields"])

    def test_probability_field_present(self) -> None:
        self.assertIn("probability", self.schema["fields"])

    def test_model_version_field_present(self) -> None:
        self.assertIn("model_version", self.schema["fields"])

    def test_prediction_time_field_present(self) -> None:
        self.assertIn("prediction_time", self.schema["fields"])

    def test_prediction_values_map_has_three_classes(self) -> None:
        self.assertEqual(len(self.schema["prediction_values"]), 3)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self.schema["is_trade_command"])

    def test_training_contract_version_referenced(self) -> None:
        self.assertEqual(self.schema["training_contract_version"], tc.TRAINING_CONTRACT_VERSION)


# ---------------------------------------------------------------------------
# Evaluation Schema
# ---------------------------------------------------------------------------

class EvaluationSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = tc.build_evaluation_schema()

    def test_schema_has_all_required_fields(self) -> None:
        for field in tc._REQUIRED_EVALUATION_SCHEMA_FIELDS:
            self.assertIn(field, self.schema["fields"], f"missing: {field}")

    def test_accuracy_field_present(self) -> None:
        self.assertIn("accuracy", self.schema["fields"])

    def test_precision_field_present(self) -> None:
        self.assertIn("precision", self.schema["fields"])

    def test_recall_field_present(self) -> None:
        self.assertIn("recall", self.schema["fields"])

    def test_f1_score_field_present(self) -> None:
        self.assertIn("f1_score", self.schema["fields"])

    def test_confusion_matrix_field_present(self) -> None:
        self.assertIn("confusion_matrix", self.schema["fields"])

    def test_dataset_size_field_present(self) -> None:
        self.assertIn("dataset_size", self.schema["fields"])

    def test_reference_only_field_present(self) -> None:
        self.assertIn("reference_only", self.schema["fields"])

    def test_reference_only_is_true(self) -> None:
        self.assertTrue(self.schema["reference_only"])

    def test_reference_note_mentions_n20(self) -> None:
        self.assertIn("N=20", self.schema["reference_note"])

    def test_reference_note_mentions_reference_only(self) -> None:
        self.assertIn("REFERENCE_ONLY", self.schema["reference_note"])

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self.schema["is_trade_command"])


# ---------------------------------------------------------------------------
# Training Contract
# ---------------------------------------------------------------------------

class TrainingContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = tc.build_training_contract()

    def test_contract_version_correct(self) -> None:
        self.assertEqual(self.contract["training_contract_version"], tc.TRAINING_CONTRACT_VERSION)

    def test_feature_contract_version_correct(self) -> None:
        self.assertEqual(self.contract["feature_contract_version"], tc.EXPECTED_FEATURE_CONTRACT_VERSION)

    def test_split_contract_version_correct(self) -> None:
        self.assertEqual(self.contract["split_contract_version"], tc.EXPECTED_SPLIT_CONTRACT_VERSION)

    def test_all_required_fields_present(self) -> None:
        for field in tc._REQUIRED_TRAINING_CONTRACT_FIELDS:
            self.assertIn(field, self.contract, f"missing: {field}")

    def test_model_type_is_logistic_regression(self) -> None:
        self.assertEqual(self.contract["model_type"], "LogisticRegression")

    def test_model_type_in_allowed_list(self) -> None:
        self.assertIn(self.contract["model_type"], tc.ALLOWED_MODEL_TYPES)

    def test_model_artifact_path_set(self) -> None:
        self.assertEqual(self.contract["model_artifact"], tc.MODEL_ARTIFACT_PATH)

    def test_model_artifact_path_contains_json(self) -> None:
        self.assertTrue(self.contract["model_artifact"].endswith(".json"))

    def test_random_seed_42(self) -> None:
        self.assertEqual(self.contract["random_seed"], 42)

    def test_prediction_schema_embedded(self) -> None:
        self.assertIsInstance(self.contract["prediction_schema"], dict)

    def test_evaluation_schema_embedded(self) -> None:
        self.assertIsInstance(self.contract["evaluation_schema"], dict)

    def test_reference_only_true(self) -> None:
        self.assertTrue(self.contract["reference_only"])

    def test_pipeline_stages_defined(self) -> None:
        stages = self.contract["pipeline_stages"]
        for stage in ("Train", "Save", "Load", "Predict", "Report"):
            self.assertIn(stage, stages)

    def test_training_dataset_path_set(self) -> None:
        self.assertIn("train", self.contract["training_dataset"])

    def test_validation_dataset_path_set(self) -> None:
        self.assertIn("validation", self.contract["validation_dataset"])

    def test_test_dataset_path_set(self) -> None:
        self.assertIn("test", self.contract["test_dataset"])

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self.contract["is_trade_command"])


# ---------------------------------------------------------------------------
# Contract Validation
# ---------------------------------------------------------------------------

class ContractValidationTest(unittest.TestCase):
    def _valid(self) -> dict:
        return tc.build_training_contract()

    def test_valid_contract_passes(self) -> None:
        result = tc.validate_training_contract(self._valid())
        self.assertEqual(result["contract_validation_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_wrong_contract_version_fails(self) -> None:
        c = self._valid()
        c["training_contract_version"] = "wrong"
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_wrong_feature_contract_version_fails(self) -> None:
        c = self._valid()
        c["feature_contract_version"] = "old_version"
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_wrong_split_contract_version_fails(self) -> None:
        c = self._valid()
        c["split_contract_version"] = "old_version"
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_disallowed_model_type_fails(self) -> None:
        c = self._valid()
        c["model_type"] = "XGBoost"
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_missing_model_artifact_fails(self) -> None:
        c = self._valid()
        c["model_artifact"] = ""
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_wrong_random_seed_fails(self) -> None:
        c = self._valid()
        c["random_seed"] = 99
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_evaluation_schema_without_reference_only_fails(self) -> None:
        c = self._valid()
        c["evaluation_schema"]["reference_only"] = False
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_missing_prediction_field_fails(self) -> None:
        c = self._valid()
        c["prediction_schema"]["fields"].remove("probability")
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")

    def test_missing_evaluation_field_fails(self) -> None:
        c = self._valid()
        c["evaluation_schema"]["fields"].remove("f1_score")
        result = tc.validate_training_contract(c)
        self.assertEqual(result["contract_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Run Contract Layer (end-to-end)
# ---------------------------------------------------------------------------

class RunContractLayerTest(unittest.TestCase):
    def _run(self) -> tuple:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = tc.run_mirror_ml_training_contract(output_dir=base)
            files = {}
            for fname in (
                "mirror_ml_training_contract.json",
                "mirror_prediction_contract.json",
                "mirror_evaluation_contract.json",
                "mirror_ml_contract_validation.json",
            ):
                p = base / fname
                if p.exists():
                    files[fname] = json.loads(p.read_text(encoding="utf-8"))
            return result, files

    def test_output_files_created(self) -> None:
        _, files = self._run()
        for fname in (
            "mirror_ml_training_contract.json",
            "mirror_prediction_contract.json",
            "mirror_evaluation_contract.json",
            "mirror_ml_contract_validation.json",
        ):
            self.assertIn(fname, files, f"missing {fname}")

    def test_contract_layer_result_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["contract_layer_result"], "PASS")

    def test_contract_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["contract_validation_result"], "PASS")

    def test_model_type_logistic_regression(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["model_type"], "LogisticRegression")

    def test_model_artifact_in_result(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["model_artifact"], tc.MODEL_ARTIFACT_PATH)

    def test_random_seed_42_in_result(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["random_seed"], 42)

    def test_reference_only_true_in_result(self) -> None:
        result, _ = self._run()
        self.assertTrue(result["reference_only"])

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_prediction_schema_fields_in_result(self) -> None:
        result, _ = self._run()
        for field in tc._REQUIRED_PREDICTION_SCHEMA_FIELDS:
            self.assertIn(field, result["prediction_schema_fields"])

    def test_evaluation_schema_fields_in_result(self) -> None:
        result, _ = self._run()
        for field in tc._REQUIRED_EVALUATION_SCHEMA_FIELDS:
            self.assertIn(field, result["evaluation_schema_fields"])

    def test_training_contract_json_has_model_artifact(self) -> None:
        _, files = self._run()
        contract = files["mirror_ml_training_contract.json"]
        self.assertEqual(contract["model_artifact"], tc.MODEL_ARTIFACT_PATH)

    def test_evaluation_contract_reference_only_true(self) -> None:
        _, files = self._run()
        self.assertTrue(files["mirror_evaluation_contract.json"]["reference_only"])

    def test_contract_validation_json_passes(self) -> None:
        _, files = self._run()
        self.assertEqual(files["mirror_ml_contract_validation.json"]["contract_validation_result"], "PASS")


if __name__ == "__main__":
    unittest.main()
