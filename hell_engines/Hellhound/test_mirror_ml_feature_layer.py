from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_ml_feature_layer as feature_layer
except ImportError:
    from . import mirror_ml_feature_layer as feature_layer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _labeled(
    decision: str,
    label: str = None,
    sample_id: str = None,
    ph: str = None,
    early_mae: float = -2.0,
    recovery_ratio: float = 1.2,
    campaign_duration: float = 24.0,
    confidence: float = 0.9,
) -> dict:
    if label is None:
        label = {
            "REAL_WHALE_BACK": "POSITIVE_MARKET_OUTCOME",
            "INCONCLUSIVE": "NEGATIVE_MARKET_OUTCOME",
            "FAKE_WHALE_BACK": "INSUFFICIENT_CLASS_DATA",
        }.get(decision, "UNRESOLVED")
    if ph is None:
        ph = {"REAL_WHALE_BACK": "a", "INCONCLUSIVE": "b", "FAKE_WHALE_BACK": "c"}.get(decision, "d") * 64
    if sample_id is None:
        sample_id = f"ds-{decision[:4].lower()}-test"
    return {
        "sample_id": sample_id,
        "packet_hash": ph,
        "decision": decision,
        "label_placeholder": label,
        "feature": {
            "early_mae": early_mae,
            "recovery_ratio": recovery_ratio,
            "campaign_duration": campaign_duration,
            "confidence": confidence,
        },
        "is_trade_command": False,
    }


_READINESS_APPROVED = {"ML_INPUT_APPROVED": True}
_READINESS_REJECTED = {"ML_INPUT_APPROVED": False}


# ---------------------------------------------------------------------------
# ML Approval gate
# ---------------------------------------------------------------------------

class MLApprovalCheckTest(unittest.TestCase):
    def test_true_approved(self) -> None:
        self.assertTrue(feature_layer.check_ml_approval({"ML_INPUT_APPROVED": True}))

    def test_false_not_approved(self) -> None:
        self.assertFalse(feature_layer.check_ml_approval({"ML_INPUT_APPROVED": False}))

    def test_missing_key_not_approved(self) -> None:
        self.assertFalse(feature_layer.check_ml_approval({}))

    def test_string_true_not_approved(self) -> None:
        # Only boolean True counts
        self.assertFalse(feature_layer.check_ml_approval({"ML_INPUT_APPROVED": "true"}))


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

class EncodingTest(unittest.TestCase):
    def test_real_whale_back_encoded_1(self) -> None:
        self.assertEqual(feature_layer.encode_decision("REAL_WHALE_BACK"), 1)

    def test_inconclusive_encoded_0(self) -> None:
        self.assertEqual(feature_layer.encode_decision("INCONCLUSIVE"), 0)

    def test_fake_whale_back_encoded_minus1(self) -> None:
        """FAKE_WHALE_BACK mock — decision encoding must be -1."""
        self.assertEqual(feature_layer.encode_decision("FAKE_WHALE_BACK"), -1)

    def test_unknown_decision_returns_none(self) -> None:
        self.assertIsNone(feature_layer.encode_decision("UNKNOWN"))

    def test_positive_label_encoded_1(self) -> None:
        self.assertEqual(feature_layer.encode_label("POSITIVE_MARKET_OUTCOME"), 1)

    def test_negative_label_encoded_0(self) -> None:
        self.assertEqual(feature_layer.encode_label("NEGATIVE_MARKET_OUTCOME"), 0)

    def test_insufficient_class_data_encoded_minus1(self) -> None:
        """FAKE_WHALE_BACK mock — label encoding must be -1."""
        self.assertEqual(feature_layer.encode_label("INSUFFICIENT_CLASS_DATA"), -1)

    def test_unknown_label_returns_none(self) -> None:
        self.assertIsNone(feature_layer.encode_label("MADE_UP"))

    def test_decision_encoding_map_has_three_entries(self) -> None:
        self.assertEqual(len(feature_layer.DECISION_ENCODING), 3)

    def test_label_encoding_map_has_three_entries(self) -> None:
        self.assertEqual(len(feature_layer.LABEL_ENCODING), 3)


# ---------------------------------------------------------------------------
# Feature Row
# ---------------------------------------------------------------------------

class FeatureRowTest(unittest.TestCase):
    def test_real_whale_back_row_structure(self) -> None:
        sample = _labeled("REAL_WHALE_BACK")
        row = feature_layer.build_feature_row(sample)
        self.assertEqual(row["sample_id"], sample["sample_id"])
        self.assertEqual(row["packet_hash"], sample["packet_hash"])
        self.assertEqual(row["label_encoded"], 1)
        self.assertEqual(row["label_original"], "POSITIVE_MARKET_OUTCOME")
        self.assertEqual(row["features"]["decision_encoded"], 1)

    def test_inconclusive_row_encoding(self) -> None:
        sample = _labeled("INCONCLUSIVE")
        row = feature_layer.build_feature_row(sample)
        self.assertEqual(row["label_encoded"], 0)
        self.assertEqual(row["features"]["decision_encoded"], 0)

    def test_fake_whale_back_row_encoding(self) -> None:
        """FAKE_WHALE_BACK mock — decision_encoded=-1, label_encoded=-1."""
        sample = _labeled("FAKE_WHALE_BACK")
        row = feature_layer.build_feature_row(sample)
        self.assertEqual(row["features"]["decision_encoded"], -1)
        self.assertEqual(row["label_encoded"], -1)
        self.assertEqual(row["label_original"], "INSUFFICIENT_CLASS_DATA")

    def test_feature_values_extracted(self) -> None:
        sample = _labeled("REAL_WHALE_BACK", early_mae=-3.5, recovery_ratio=1.4, campaign_duration=20.0, confidence=0.85)
        row = feature_layer.build_feature_row(sample)
        self.assertAlmostEqual(row["features"]["early_mae"], -3.5)
        self.assertAlmostEqual(row["features"]["recovery_ratio"], 1.4)
        self.assertAlmostEqual(row["features"]["campaign_duration"], 20.0)
        self.assertAlmostEqual(row["features"]["confidence"], 0.85)

    def test_original_sample_not_mutated(self) -> None:
        sample = _labeled("REAL_WHALE_BACK")
        original_ph = sample["packet_hash"]
        feature_layer.build_feature_row(sample)
        self.assertEqual(sample["packet_hash"], original_ph)
        self.assertEqual(sample["label_placeholder"], "POSITIVE_MARKET_OUTCOME")

    def test_required_row_fields_present(self) -> None:
        row = feature_layer.build_feature_row(_labeled("INCONCLUSIVE"))
        for field in ("sample_id", "packet_hash", "features", "label_encoded", "label_original"):
            self.assertIn(field, row)

    def test_all_feature_columns_in_features(self) -> None:
        row = feature_layer.build_feature_row(_labeled("REAL_WHALE_BACK"))
        for col in feature_layer.FEATURE_COLUMNS:
            self.assertIn(col, row["features"], f"missing feature column: {col}")


# ---------------------------------------------------------------------------
# Feature Matrix
# ---------------------------------------------------------------------------

class FeatureMatrixTest(unittest.TestCase):
    def _matrix(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        samples = [_labeled(d) for d in decisions]
        return feature_layer.build_feature_matrix(samples), samples

    def test_contract_version_correct(self) -> None:
        matrix, _ = self._matrix()
        self.assertEqual(matrix["feature_contract_version"], feature_layer.FEATURE_CONTRACT_VERSION)

    def test_required_fields_present(self) -> None:
        matrix, _ = self._matrix()
        for field in ("feature_contract_version", "source_dataset", "sample_count",
                      "feature_columns", "label_column", "rows", "encoding_map", "created_at"):
            self.assertIn(field, matrix)

    def test_feature_column_order_fixed(self) -> None:
        matrix, _ = self._matrix()
        self.assertEqual(matrix["feature_columns"], list(feature_layer.FEATURE_COLUMNS))

    def test_sample_count_correct(self) -> None:
        matrix, samples = self._matrix()
        self.assertEqual(matrix["sample_count"], len(samples))

    def test_encoding_map_has_both_encodings(self) -> None:
        matrix, _ = self._matrix()
        self.assertIn("decision_encoding", matrix["encoding_map"])
        self.assertIn("label_encoding", matrix["encoding_map"])

    def test_is_not_trade_command(self) -> None:
        matrix, _ = self._matrix()
        self.assertFalse(matrix["is_trade_command"])

    def test_fake_whale_back_in_matrix(self) -> None:
        """FAKE_WHALE_BACK mock — full Feature Matrix row with -1 encoding."""
        matrix, _ = self._matrix(("FAKE_WHALE_BACK",))
        row = matrix["rows"][0]
        self.assertEqual(row["features"]["decision_encoded"], -1)
        self.assertEqual(row["label_encoded"], -1)


# ---------------------------------------------------------------------------
# Feature Schema
# ---------------------------------------------------------------------------

class FeatureSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = feature_layer.build_feature_schema()

    def test_schema_has_feature_columns(self) -> None:
        self.assertEqual(self.schema["feature_columns"], list(feature_layer.FEATURE_COLUMNS))

    def test_schema_has_decision_encoding(self) -> None:
        self.assertIn("decision_encoding", self.schema)
        self.assertEqual(self.schema["decision_encoding"]["FAKE_WHALE_BACK"], -1)

    def test_schema_has_label_encoding(self) -> None:
        self.assertIn("label_encoding", self.schema)
        self.assertEqual(self.schema["label_encoding"]["INSUFFICIENT_CLASS_DATA"], -1)

    def test_schema_is_not_trade_command(self) -> None:
        self.assertFalse(self.schema["is_trade_command"])


# ---------------------------------------------------------------------------
# Feature Statistics
# ---------------------------------------------------------------------------

class FeatureStatisticsTest(unittest.TestCase):
    def _rows(self):
        samples = [
            _labeled("REAL_WHALE_BACK", early_mae=-2.0, recovery_ratio=1.2, campaign_duration=20.0, confidence=0.9),
            _labeled("REAL_WHALE_BACK", early_mae=-4.0, recovery_ratio=1.4, campaign_duration=24.0, confidence=0.8),
            _labeled("INCONCLUSIVE", early_mae=-3.0, recovery_ratio=0.8, campaign_duration=16.0, confidence=0.6),
        ]
        return feature_layer.build_feature_rows(samples)

    def test_reference_only_is_true(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        self.assertTrue(stats["reference_only"])

    def test_reference_note_contains_reference_only(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        self.assertIn("reference only", stats["reference_note"].lower())

    def test_reference_note_contains_dataset_size(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        self.assertIn("3", stats["reference_note"])

    def test_feature_stats_have_all_numeric_features(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        for feat in ("early_mae", "recovery_ratio", "campaign_duration", "confidence"):
            self.assertIn(feat, stats["feature_stats"])

    def test_early_mae_mean(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        # [-2.0, -4.0, -3.0] → mean = -3.0
        self.assertAlmostEqual(stats["feature_stats"]["early_mae"]["mean"], -3.0, places=5)

    def test_label_distribution_present(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        self.assertIn("label_distribution", stats)

    def test_is_not_trade_command(self) -> None:
        stats = feature_layer.build_feature_statistics(self._rows())
        self.assertFalse(stats["is_trade_command"])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationTest(unittest.TestCase):
    def _valid_matrix(self):
        samples = [_labeled("REAL_WHALE_BACK"), _labeled("INCONCLUSIVE")]
        return feature_layer.build_feature_matrix(samples), samples

    def test_valid_matrix_passes(self) -> None:
        matrix, samples = self._valid_matrix()
        result = feature_layer.validate_feature_matrix(matrix, original_samples=samples)
        self.assertEqual(result["feature_validation_result"], "PASS")
        self.assertEqual(result["mutation_count"], 0)

    def test_wrong_contract_version_fails(self) -> None:
        matrix, samples = self._valid_matrix()
        matrix["feature_contract_version"] = "wrong_version"
        result = feature_layer.validate_feature_matrix(matrix, original_samples=samples)
        self.assertEqual(result["feature_validation_result"], "FAIL")

    def test_wrong_feature_column_order_fails(self) -> None:
        matrix, samples = self._valid_matrix()
        matrix["feature_columns"] = list(reversed(feature_layer.FEATURE_COLUMNS))
        result = feature_layer.validate_feature_matrix(matrix, original_samples=samples)
        self.assertEqual(result["feature_validation_result"], "FAIL")

    def test_invalid_decision_encoding_fails(self) -> None:
        matrix, samples = self._valid_matrix()
        matrix["rows"][0]["features"]["decision_encoded"] = 99
        result = feature_layer.validate_feature_matrix(matrix)
        self.assertEqual(result["feature_validation_result"], "FAIL")

    def test_invalid_label_encoding_fails(self) -> None:
        matrix, samples = self._valid_matrix()
        matrix["rows"][0]["label_encoded"] = 99
        result = feature_layer.validate_feature_matrix(matrix)
        self.assertEqual(result["feature_validation_result"], "FAIL")

    def test_packet_hash_changed_detected(self) -> None:
        matrix, samples = self._valid_matrix()
        matrix["rows"][0]["packet_hash"] = "0" * 64
        result = feature_layer.validate_feature_matrix(matrix, original_samples=samples)
        self.assertEqual(result["feature_validation_result"], "FAIL")
        self.assertGreater(result["mutation_count"], 0)

    def test_fake_whale_back_valid_encoding_passes(self) -> None:
        """Mock FAKE_WHALE_BACK — -1 encoding passes validation."""
        samples = [_labeled("FAKE_WHALE_BACK")]
        matrix = feature_layer.build_feature_matrix(samples)
        result = feature_layer.validate_feature_matrix(matrix, original_samples=samples)
        self.assertEqual(result["feature_validation_result"], "PASS")


# ---------------------------------------------------------------------------
# Run Feature Layer (end-to-end)
# ---------------------------------------------------------------------------

class RunFeatureLayerTest(unittest.TestCase):
    def _run(self, decisions=None, approved=True):
        if decisions is None:
            decisions = ["REAL_WHALE_BACK", "INCONCLUSIVE"]
        samples = [_labeled(d) for d in decisions]
        readiness = {"ML_INPUT_APPROVED": approved}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = feature_layer.run_mirror_ml_feature_layer(
                output_dir=base,
                source_labeled=samples,
                source_readiness=readiness,
            )
            files = {
                "matrix": base / "mirror_ml_feature_matrix.json",
                "schema": base / "mirror_ml_feature_schema.json",
                "statistics": base / "mirror_ml_feature_statistics.json",
                "validation": base / "mirror_ml_feature_validation.json",
            }
            contents = {}
            for k, f in files.items():
                if f.exists():
                    contents[k] = json.loads(f.read_text(encoding="utf-8"))
            return result, contents

    def test_output_files_created(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK"), _labeled("INCONCLUSIVE")]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            feature_layer.run_mirror_ml_feature_layer(
                output_dir=base, source_labeled=samples,
                source_readiness=_READINESS_APPROVED,
            )
            for fname in (
                "mirror_ml_feature_matrix.json",
                "mirror_ml_feature_schema.json",
                "mirror_ml_feature_statistics.json",
                "mirror_ml_feature_validation.json",
            ):
                self.assertTrue((base / fname).exists(), f"missing {fname}")

    def test_approved_run_returns_pass(self) -> None:
        result, _ = self._run(approved=True)
        self.assertEqual(result["feature_layer_result"], "PASS")

    def test_not_approved_run_returns_blocked(self) -> None:
        result, _ = self._run(approved=False)
        self.assertEqual(result["feature_layer_result"], "BLOCKED")

    def test_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["feature_validation_result"], "PASS")

    def test_mutation_count_zero(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["mutation_count"], 0)

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_statistics_has_reference_only(self) -> None:
        _, contents = self._run()
        self.assertTrue(contents["statistics"]["reference_only"])

    def test_matrix_has_all_rows(self) -> None:
        _, contents = self._run(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        self.assertEqual(len(contents["matrix"]["rows"]), 2)

    def test_fake_whale_back_mock_full_run(self) -> None:
        """End-to-end FAKE_WHALE_BACK mock — decision_encoded=-1, label_encoded=-1."""
        _, contents = self._run(["FAKE_WHALE_BACK"])
        row = contents["matrix"]["rows"][0]
        self.assertEqual(row["features"]["decision_encoded"], -1)
        self.assertEqual(row["label_encoded"], -1)

    def test_ml_approved_flag_in_report(self) -> None:
        result, _ = self._run(approved=True)
        self.assertTrue(result["ML_INPUT_APPROVED"])

    def test_feature_columns_in_report(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["feature_columns"], list(feature_layer.FEATURE_COLUMNS))


if __name__ == "__main__":
    unittest.main()
