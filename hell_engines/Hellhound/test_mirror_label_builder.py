from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_label_builder as builder
    import mirror_packet_contract
except ImportError:
    from . import mirror_label_builder as builder
    from . import mirror_packet_contract


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample(decision: str, packet_hash: str = None) -> dict:
    if packet_hash is None:
        packet_hash = ("a" * 64) if decision == "REAL_WHALE_BACK" else ("b" * 64) if decision == "INCONCLUSIVE" else ("c" * 64)
    return {
        "sample_id": f"ds-{decision[:4].lower()}-test",
        "contract_version": "mirror_pattern_packet_v1",
        "dataset_contract_version": "mirror_dataset_v1",
        "packet_hash": packet_hash,
        "feature": {"early_mae": -2.0, "recovery_ratio": 1.2, "campaign_duration": 24.0},
        "evidence": ["RECOVERY_STRONG"],
        "reason": ["RECOVERY_SUPPORT"],
        "decision": decision,
        "replay_metadata": {},
        "persistence_metadata": {},
        "readback_status": {"status": "PASS"},
        "outcome_placeholder": None,
        "label_placeholder": None,
        "created_at": "2026-06-26T00:00:00+00:00",
        "is_trade_command": False,
    }


_POLICY_V1 = {
    "policy_version": "mirror_label_policy_v1",
    "decision_policy": {
        "REAL_WHALE_BACK": {
            "candidate_label": "POSITIVE_MARKET_OUTCOME",
            "class_data_status": "AVAILABLE",
            "observed_positive_ratio": 1.0,
            "confidence_basis": "distribution_observed",
        },
        "INCONCLUSIVE": {
            "candidate_label": "NEGATIVE_MARKET_OUTCOME",
            "class_data_status": "AVAILABLE",
            "observed_positive_ratio": 0.0,
            "confidence_basis": "distribution_observed",
        },
        "FAKE_WHALE_BACK": {
            "candidate_label": "INSUFFICIENT_CLASS_DATA",
            "class_data_status": "INSUFFICIENT_CLASS_DATA",
            "observed_positive_ratio": None,
            "confidence_basis": "no_samples",
        },
    },
    "label_candidates": list(builder.LABEL_CANDIDATES),
    "is_trade_command": False,
}

_POLICY_WRONG_VERSION = dict(_POLICY_V1)
_POLICY_WRONG_VERSION = {**_POLICY_V1, "policy_version": "mirror_label_policy_v0"}


# ---------------------------------------------------------------------------
# Policy reference validation
# ---------------------------------------------------------------------------

class PolicyReferenceTest(unittest.TestCase):
    def test_valid_policy_passes(self) -> None:
        result = builder.validate_policy_reference(_POLICY_V1)
        self.assertTrue(result["policy_reference_valid"])
        self.assertEqual(result["issue_count"], 0)

    def test_wrong_version_fails(self) -> None:
        result = builder.validate_policy_reference(_POLICY_WRONG_VERSION)
        self.assertFalse(result["policy_reference_valid"])
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("wrong_policy_version", issues)

    def test_missing_decision_policy_fails(self) -> None:
        policy = {"policy_version": "mirror_label_policy_v1"}
        result = builder.validate_policy_reference(policy)
        self.assertFalse(result["policy_reference_valid"])

    def test_policy_version_in_result(self) -> None:
        result = builder.validate_policy_reference(_POLICY_V1)
        self.assertEqual(result["policy_version"], "mirror_label_policy_v1")

    def test_load_policy_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(_POLICY_V1), encoding="utf-8")
            loaded = builder.load_policy(path)
            self.assertEqual(loaded["policy_version"], "mirror_label_policy_v1")


# ---------------------------------------------------------------------------
# Assign label
# ---------------------------------------------------------------------------

class AssignLabelTest(unittest.TestCase):
    def _dp(self):
        return _POLICY_V1["decision_policy"]

    def test_real_whale_back_assigned_positive(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        label = builder.assign_label(sample, self._dp())
        self.assertEqual(label, "POSITIVE_MARKET_OUTCOME")

    def test_inconclusive_assigned_negative(self) -> None:
        sample = _sample("INCONCLUSIVE")
        label = builder.assign_label(sample, self._dp())
        self.assertEqual(label, "NEGATIVE_MARKET_OUTCOME")

    def test_fake_whale_back_assigned_insufficient_class_data(self) -> None:
        """FAKE_WHALE_BACK mock — runtime code path must exist."""
        sample = _sample("FAKE_WHALE_BACK")
        label = builder.assign_label(sample, self._dp())
        self.assertEqual(label, "INSUFFICIENT_CLASS_DATA")

    def test_unknown_decision_returns_unresolved(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        sample = dict(sample)
        sample["decision"] = "UNKNOWN_DECISION"
        label = builder.assign_label(sample, self._dp())
        self.assertEqual(label, "UNRESOLVED")

    def test_empty_decision_policy_returns_unresolved(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        label = builder.assign_label(sample, {})
        self.assertEqual(label, "UNRESOLVED")

    def test_assigned_label_is_in_candidates(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            sample = _sample(decision)
            label = builder.assign_label(sample, self._dp())
            self.assertIn(label, builder.LABEL_CANDIDATES)


# ---------------------------------------------------------------------------
# Apply label
# ---------------------------------------------------------------------------

class ApplyLabelTest(unittest.TestCase):
    def test_apply_label_fills_label_placeholder(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        labeled = builder.apply_label(sample, "POSITIVE_MARKET_OUTCOME")
        self.assertEqual(labeled["label_placeholder"], "POSITIVE_MARKET_OUTCOME")

    def test_apply_label_does_not_mutate_original(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        builder.apply_label(sample, "POSITIVE_MARKET_OUTCOME")
        self.assertIsNone(sample["label_placeholder"])

    def test_apply_label_preserves_packet_hash(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        labeled = builder.apply_label(sample, "POSITIVE_MARKET_OUTCOME")
        self.assertEqual(labeled["packet_hash"], sample["packet_hash"])

    def test_apply_label_preserves_decision(self) -> None:
        sample = _sample("INCONCLUSIVE")
        labeled = builder.apply_label(sample, "NEGATIVE_MARKET_OUTCOME")
        self.assertEqual(labeled["decision"], "INCONCLUSIVE")

    def test_apply_label_preserves_feature(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        labeled = builder.apply_label(sample, "POSITIVE_MARKET_OUTCOME")
        self.assertEqual(labeled["feature"], sample["feature"])

    def test_apply_label_deep_copy_independence(self) -> None:
        sample = _sample("REAL_WHALE_BACK")
        labeled = builder.apply_label(sample, "POSITIVE_MARKET_OUTCOME")
        # Mutate labeled's feature — original must not change
        labeled["feature"]["early_mae"] = 999.0
        self.assertNotEqual(sample["feature"].get("early_mae"), 999.0)

    def test_fake_whale_back_apply_label(self) -> None:
        """FAKE_WHALE_BACK mock — apply_label path must work."""
        sample = _sample("FAKE_WHALE_BACK")
        labeled = builder.apply_label(sample, "INSUFFICIENT_CLASS_DATA")
        self.assertEqual(labeled["label_placeholder"], "INSUFFICIENT_CLASS_DATA")
        self.assertIsNone(sample["label_placeholder"])  # original unchanged


# ---------------------------------------------------------------------------
# Batch assignment
# ---------------------------------------------------------------------------

class BatchAssignmentTest(unittest.TestCase):
    def _samples(self):
        return [_sample("REAL_WHALE_BACK"), _sample("INCONCLUSIVE")]

    def test_all_samples_labeled(self) -> None:
        samples = self._samples()
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        self.assertEqual(len(labeled), 2)

    def test_originals_unchanged_after_batch(self) -> None:
        samples = self._samples()
        builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        for s in samples:
            self.assertIsNone(s["label_placeholder"])

    def test_assignment_rows_count(self) -> None:
        samples = self._samples()
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        rows = builder.build_assignment_rows(samples, labeled)
        self.assertEqual(len(rows), 2)

    def test_assignment_rows_original_placeholder_null(self) -> None:
        samples = self._samples()
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        rows = builder.build_assignment_rows(samples, labeled)
        self.assertTrue(all(r["original_label_placeholder_null"] for r in rows))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationTest(unittest.TestCase):
    def _labeled_pair(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        samples = [_sample(d) for d in decisions]
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        return labeled, samples

    def test_valid_assignment_passes(self) -> None:
        labeled, samples = self._labeled_pair()
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "PASS")
        self.assertEqual(result["mutation_count"], 0)

    def test_packet_hash_mutation_detected(self) -> None:
        labeled, samples = self._labeled_pair()
        labeled[0]["packet_hash"] = "0" * 64
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")
        self.assertGreater(result["mutation_count"], 0)

    def test_feature_mutation_detected(self) -> None:
        labeled, samples = self._labeled_pair()
        labeled[0]["feature"]["early_mae"] = 999.0
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")

    def test_wrong_policy_version_detected(self) -> None:
        labeled, samples = self._labeled_pair()
        bad_policy = {**_POLICY_V1, "policy_version": "wrong_version"}
        result = builder.validate_assignments(labeled, samples, bad_policy)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")

    def test_deferred_label_insufficient_market_data_fails(self) -> None:
        labeled, samples = self._labeled_pair()
        labeled[0]["label_placeholder"] = "INSUFFICIENT_MARKET_DATA"
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("deferred_label_applied", issues)

    def test_deferred_label_unresolved_fails(self) -> None:
        labeled, samples = self._labeled_pair()
        labeled[0]["label_placeholder"] = "UNRESOLVED"
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("deferred_label_applied", issues)

    def test_null_label_after_assignment_fails(self) -> None:
        labeled, samples = self._labeled_pair()
        labeled[0]["label_placeholder"] = None
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "FAIL")

    def test_fake_whale_back_passes_validation(self) -> None:
        """Mock FAKE_WHALE_BACK — validation of INSUFFICIENT_CLASS_DATA assignment."""
        sample = _sample("FAKE_WHALE_BACK")
        samples = [sample]
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        result = builder.validate_assignments(labeled, samples, _POLICY_V1)
        self.assertEqual(result["label_assignment_validation_result"], "PASS")
        self.assertEqual(labeled[0]["label_placeholder"], "INSUFFICIENT_CLASS_DATA")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class StatisticsTest(unittest.TestCase):
    def _run_stats(self, decisions):
        samples = [_sample(d) for d in decisions]
        labeled = builder.assign_labels_batch(samples, _POLICY_V1["decision_policy"])
        rows = builder.build_assignment_rows(samples, labeled)
        return builder.build_assignment_statistics(labeled, rows)

    def test_total_count_correct(self) -> None:
        stats = self._run_stats(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        self.assertEqual(stats["total_count"], 2)

    def test_null_label_count_zero(self) -> None:
        stats = self._run_stats(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        self.assertEqual(stats["null_label_count"], 0)

    def test_assigned_count_correct(self) -> None:
        stats = self._run_stats(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        self.assertEqual(stats["assigned_count"], 2)

    def test_label_distribution_positive(self) -> None:
        stats = self._run_stats(["REAL_WHALE_BACK", "REAL_WHALE_BACK"])
        self.assertEqual(stats["label_distribution"]["POSITIVE_MARKET_OUTCOME"], 2)
        self.assertEqual(stats["label_distribution"]["NEGATIVE_MARKET_OUTCOME"], 0)

    def test_label_distribution_negative(self) -> None:
        stats = self._run_stats(["INCONCLUSIVE"])
        self.assertEqual(stats["label_distribution"]["NEGATIVE_MARKET_OUTCOME"], 1)

    def test_fake_whale_back_in_label_distribution(self) -> None:
        stats = self._run_stats(["FAKE_WHALE_BACK"])
        self.assertEqual(stats["label_distribution"]["INSUFFICIENT_CLASS_DATA"], 1)

    def test_is_not_trade_command(self) -> None:
        stats = self._run_stats(["REAL_WHALE_BACK"])
        self.assertFalse(stats["is_trade_command"])


# ---------------------------------------------------------------------------
# Run builder (end-to-end)
# ---------------------------------------------------------------------------

class RunBuilderTest(unittest.TestCase):
    def _run(self, decisions=None):
        if decisions is None:
            decisions = ["REAL_WHALE_BACK", "INCONCLUSIVE"]
        samples = [_sample(d) for d in decisions]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = builder.run_mirror_label_builder(
                output_dir=base,
                source_samples=samples,
                source_policy=_POLICY_V1,
            )
            files = {
                "report": base / "mirror_label_assignment_report.json",
                "statistics": base / "mirror_label_assignment_statistics.json",
                "validation": base / "mirror_label_assignment_validation.json",
                "dataset": base / "mirror_labeled_dataset.jsonl",
            }
            contents = {}
            for k, f in files.items():
                if k == "dataset":
                    contents[k] = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()]
                else:
                    contents[k] = json.loads(f.read_text(encoding="utf-8"))
            return result, contents

    def test_output_files_created(self) -> None:
        samples = [_sample("REAL_WHALE_BACK"), _sample("INCONCLUSIVE")]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            builder.run_mirror_label_builder(
                output_dir=base, source_samples=samples, source_policy=_POLICY_V1
            )
            self.assertTrue((base / "mirror_labeled_dataset.jsonl").exists())
            self.assertTrue((base / "mirror_label_assignment_report.json").exists())
            self.assertTrue((base / "mirror_label_assignment_statistics.json").exists())
            self.assertTrue((base / "mirror_label_assignment_validation.json").exists())

    def test_output_files_valid_json(self) -> None:
        _, contents = self._run()
        for name in ("report", "statistics", "validation"):
            self.assertIsInstance(contents[name], dict, f"{name} not a dict")

    def test_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["label_assignment_validation_result"], "PASS")

    def test_mutation_count_zero(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["mutation_count"], 0)

    def test_original_dataset_unchanged(self) -> None:
        result, _ = self._run()
        self.assertTrue(result["original_dataset_unchanged"])

    def test_labeled_dataset_has_correct_count(self) -> None:
        _, contents = self._run()
        self.assertEqual(len(contents["dataset"]), 2)

    def test_labeled_dataset_label_placeholder_filled(self) -> None:
        _, contents = self._run()
        for sample in contents["dataset"]:
            self.assertIsNotNone(sample["label_placeholder"])
            self.assertIn(sample["label_placeholder"], builder.LABEL_CANDIDATES)

    def test_real_whale_back_labeled_positive(self) -> None:
        _, contents = self._run(["REAL_WHALE_BACK"])
        self.assertEqual(contents["dataset"][0]["label_placeholder"], "POSITIVE_MARKET_OUTCOME")

    def test_inconclusive_labeled_negative(self) -> None:
        _, contents = self._run(["INCONCLUSIVE"])
        self.assertEqual(contents["dataset"][0]["label_placeholder"], "NEGATIVE_MARKET_OUTCOME")

    def test_fake_whale_back_labeled_insufficient_mock(self) -> None:
        """Mock FAKE_WHALE_BACK — full run path with INSUFFICIENT_CLASS_DATA."""
        _, contents = self._run(["FAKE_WHALE_BACK"])
        self.assertEqual(contents["dataset"][0]["label_placeholder"], "INSUFFICIENT_CLASS_DATA")

    def test_policy_version_in_report(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["policy_version_applied"], "mirror_label_policy_v1")

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_null_label_count_zero_in_report(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["null_label_count"], 0)

    def test_insufficient_market_data_not_applied(self) -> None:
        _, contents = self._run(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        labels = [s["label_placeholder"] for s in contents["dataset"]]
        self.assertNotIn("INSUFFICIENT_MARKET_DATA", labels)

    def test_unresolved_not_applied(self) -> None:
        _, contents = self._run(["REAL_WHALE_BACK", "INCONCLUSIVE"])
        labels = [s["label_placeholder"] for s in contents["dataset"]]
        self.assertNotIn("UNRESOLVED", labels)


if __name__ == "__main__":
    unittest.main()
