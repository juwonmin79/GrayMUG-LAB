from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_label_policy_builder as builder
    import mirror_packet_contract
except ImportError:
    from . import mirror_label_policy_builder as builder
    from . import mirror_packet_contract


# ---------------------------------------------------------------------------
# Synthetic distribution fixtures
# ---------------------------------------------------------------------------

_DISTRIBUTION_ALL_DATA = {
    "REAL_WHALE_BACK": {
        "sample_count": 10,
        "completed_count": 10,
        "incomplete_count": 0,
        "positive_return_count": 10,
        "negative_return_count": 0,
        "mfe": {"mean": 8.52539},
        "return_pct": {"mean": 8.52539},
    },
    "FAKE_WHALE_BACK": {
        "sample_count": 0,
        "completed_count": 0,
        "incomplete_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
        "mfe": {"mean": None},
        "return_pct": {"mean": None},
    },
    "INCONCLUSIVE": {
        "sample_count": 10,
        "completed_count": 10,
        "incomplete_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 10,
        "mfe": {"mean": 0.0},
        "return_pct": {"mean": -5.056651},
    },
    "overall": {
        "sample_count": 20,
        "completed_count": 20,
        "positive_return_count": 10,
        "negative_return_count": 10,
    },
}

_DISTRIBUTION_EMPTY = {
    "REAL_WHALE_BACK": {
        "sample_count": 0,
        "completed_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
    },
    "FAKE_WHALE_BACK": {
        "sample_count": 0,
        "completed_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
    },
    "INCONCLUSIVE": {
        "sample_count": 0,
        "completed_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
    },
}

_DISTRIBUTION_MIXED = {
    "REAL_WHALE_BACK": {
        "sample_count": 4,
        "completed_count": 4,
        "positive_return_count": 2,
        "negative_return_count": 2,
    },
    "FAKE_WHALE_BACK": {
        "sample_count": 0,
        "completed_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
    },
    "INCONCLUSIVE": {
        "sample_count": 4,
        "completed_count": 4,
        "positive_return_count": 2,
        "negative_return_count": 2,
    },
}


# ---------------------------------------------------------------------------
# Class data status
# ---------------------------------------------------------------------------

class ClassDataStatusTest(unittest.TestCase):
    def test_real_whale_back_available(self) -> None:
        status = builder.build_class_data_status(_DISTRIBUTION_ALL_DATA)
        self.assertEqual(status["REAL_WHALE_BACK"], "AVAILABLE")

    def test_fake_whale_back_insufficient(self) -> None:
        status = builder.build_class_data_status(_DISTRIBUTION_ALL_DATA)
        self.assertEqual(status["FAKE_WHALE_BACK"], "INSUFFICIENT_CLASS_DATA")

    def test_inconclusive_available(self) -> None:
        status = builder.build_class_data_status(_DISTRIBUTION_ALL_DATA)
        self.assertEqual(status["INCONCLUSIVE"], "AVAILABLE")

    def test_all_empty_all_insufficient(self) -> None:
        status = builder.build_class_data_status(_DISTRIBUTION_EMPTY)
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertEqual(status[decision], "INSUFFICIENT_CLASS_DATA")

    def test_covers_all_decision_keys(self) -> None:
        status = builder.build_class_data_status(_DISTRIBUTION_ALL_DATA)
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, status)


# ---------------------------------------------------------------------------
# Decision policy draft
# ---------------------------------------------------------------------------

class DecisionPolicyDraftTest(unittest.TestCase):
    def setUp(self) -> None:
        self.draft = builder.build_decision_policy_draft(_DISTRIBUTION_ALL_DATA)

    def test_real_whale_back_candidate_positive(self) -> None:
        self.assertEqual(
            self.draft["REAL_WHALE_BACK"]["candidate_label"],
            "POSITIVE_MARKET_OUTCOME",
        )

    def test_inconclusive_candidate_negative(self) -> None:
        self.assertEqual(
            self.draft["INCONCLUSIVE"]["candidate_label"],
            "NEGATIVE_MARKET_OUTCOME",
        )

    def test_fake_whale_back_candidate_insufficient(self) -> None:
        self.assertEqual(
            self.draft["FAKE_WHALE_BACK"]["candidate_label"],
            "INSUFFICIENT_CLASS_DATA",
        )

    def test_real_whale_back_observed_positive_ratio_one(self) -> None:
        self.assertAlmostEqual(
            self.draft["REAL_WHALE_BACK"]["observed_positive_ratio"], 1.0, places=4
        )

    def test_inconclusive_observed_positive_ratio_zero(self) -> None:
        self.assertAlmostEqual(
            self.draft["INCONCLUSIVE"]["observed_positive_ratio"], 0.0, places=4
        )

    def test_fake_whale_back_observed_positive_ratio_none(self) -> None:
        self.assertIsNone(self.draft["FAKE_WHALE_BACK"]["observed_positive_ratio"])

    def test_real_whale_back_confidence_basis(self) -> None:
        self.assertEqual(
            self.draft["REAL_WHALE_BACK"]["confidence_basis"],
            "distribution_observed",
        )

    def test_fake_whale_back_confidence_basis_no_samples(self) -> None:
        self.assertEqual(
            self.draft["FAKE_WHALE_BACK"]["confidence_basis"],
            "no_samples",
        )

    def test_mixed_distribution_produces_unresolved(self) -> None:
        draft = builder.build_decision_policy_draft(_DISTRIBUTION_MIXED)
        self.assertEqual(draft["REAL_WHALE_BACK"]["candidate_label"], "UNRESOLVED")

    def test_all_decision_keys_present(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, self.draft)

    def test_draft_has_sample_count(self) -> None:
        self.assertEqual(self.draft["REAL_WHALE_BACK"]["sample_count"], 10)
        self.assertEqual(self.draft["INCONCLUSIVE"]["sample_count"], 10)
        self.assertEqual(self.draft["FAKE_WHALE_BACK"]["sample_count"], 0)


# ---------------------------------------------------------------------------
# Unresolved policy cases
# ---------------------------------------------------------------------------

class UnresolvedPolicyCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = builder.build_unresolved_policy_cases()

    def test_returns_list(self) -> None:
        self.assertIsInstance(self.cases, list)

    def test_contains_five_cases(self) -> None:
        self.assertEqual(len(self.cases), 5)

    def test_insufficient_market_data_case_present(self) -> None:
        ids = [c["case_id"] for c in self.cases]
        self.assertIn("insufficient_market_data_issuance_condition", ids)

    def test_completed_false_case_present(self) -> None:
        ids = [c["case_id"] for c in self.cases]
        self.assertIn("completed_false_handling", ids)

    def test_live_outcome_case_present(self) -> None:
        ids = [c["case_id"] for c in self.cases]
        self.assertIn("live_outcome_insufficient_handling", ids)

    def test_all_cases_have_status_unresolved(self) -> None:
        for case in self.cases:
            self.assertEqual(case["status"], "UNRESOLVED")

    def test_all_cases_have_description(self) -> None:
        for case in self.cases:
            self.assertIn("description", case)
            self.assertIsInstance(case["description"], str)


# ---------------------------------------------------------------------------
# Label candidates
# ---------------------------------------------------------------------------

class LabelCandidatesTest(unittest.TestCase):
    def test_all_five_candidates_defined(self) -> None:
        for candidate in (
            "POSITIVE_MARKET_OUTCOME",
            "NEGATIVE_MARKET_OUTCOME",
            "INSUFFICIENT_CLASS_DATA",
            "INSUFFICIENT_MARKET_DATA",
            "UNRESOLVED",
        ):
            self.assertIn(candidate, builder.LABEL_CANDIDATES)

    def test_candidate_count_is_five(self) -> None:
        self.assertEqual(len(builder.LABEL_CANDIDATES), 5)


# ---------------------------------------------------------------------------
# Policy contract
# ---------------------------------------------------------------------------

class PolicyContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = builder.build_label_policy_contract(_DISTRIBUTION_ALL_DATA)

    def test_policy_version_correct(self) -> None:
        self.assertEqual(self.policy["policy_version"], builder.LABEL_POLICY_VERSION)

    def test_all_required_fields_present(self) -> None:
        for field in builder.REQUIRED_POLICY_FIELDS:
            self.assertIn(field, self.policy, f"missing required field: {field}")

    def test_label_candidates_all_present(self) -> None:
        for candidate in builder.LABEL_CANDIDATES:
            self.assertIn(candidate, self.policy["label_candidates"])

    def test_decision_policy_has_all_decisions(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, self.policy["decision_policy"])

    def test_class_data_status_has_all_decisions(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, self.policy["class_data_status"])

    def test_source_distribution_files_present(self) -> None:
        self.assertIsInstance(self.policy["source_distribution_files"], list)
        self.assertGreater(len(self.policy["source_distribution_files"]), 0)

    def test_unresolved_policy_cases_present(self) -> None:
        self.assertIsInstance(self.policy["unresolved_policy_cases"], list)
        self.assertGreater(len(self.policy["unresolved_policy_cases"]), 0)

    def test_observations_present(self) -> None:
        self.assertIsInstance(self.policy["observations"], list)
        self.assertGreater(len(self.policy["observations"]), 0)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self.policy["is_trade_command"])

    def test_created_at_present(self) -> None:
        self.assertIn("created_at", self.policy)
        self.assertIsNotNone(self.policy["created_at"])

    def test_label_placeholder_not_in_policy(self) -> None:
        self.assertNotIn("label_placeholder", self.policy)


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------

class PolicyValidationTest(unittest.TestCase):
    def _valid_policy(self):
        return builder.build_label_policy_contract(_DISTRIBUTION_ALL_DATA)

    def test_valid_policy_passes(self) -> None:
        policy = self._valid_policy()
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_wrong_policy_version_fails(self) -> None:
        policy = dict(self._valid_policy())
        policy["policy_version"] = "wrong_version_v0"
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("wrong_policy_version", issues)

    def test_missing_required_field_fails(self) -> None:
        policy = dict(self._valid_policy())
        del policy["unresolved_policy_cases"]
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")

    def test_fake_whale_back_wrong_candidate_fails(self) -> None:
        policy = self._valid_policy()
        policy["decision_policy"]["FAKE_WHALE_BACK"]["candidate_label"] = "POSITIVE_MARKET_OUTCOME"
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("fake_whale_back_candidate_label_wrong", issues)

    def test_empty_unresolved_cases_fails(self) -> None:
        policy = dict(self._valid_policy())
        policy["unresolved_policy_cases"] = []
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")

    def test_invalid_candidate_label_fails(self) -> None:
        policy = self._valid_policy()
        policy["decision_policy"]["REAL_WHALE_BACK"]["candidate_label"] = "MADE_UP_LABEL"
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("invalid_candidate_label", issues)

    def test_missing_label_candidate_fails(self) -> None:
        policy = dict(self._valid_policy())
        policy["label_candidates"] = ["POSITIVE_MARKET_OUTCOME"]  # missing rest
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")

    def test_is_trade_command_true_fails(self) -> None:
        policy = dict(self._valid_policy())
        policy["is_trade_command"] = True
        result = builder.validate_policy(policy)
        self.assertEqual(result["policy_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Run builder (end-to-end)
# ---------------------------------------------------------------------------

class RunBuilderTest(unittest.TestCase):
    def _run(self, distribution=None):
        if distribution is None:
            distribution = _DISTRIBUTION_ALL_DATA
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = builder.run_mirror_label_policy_builder(
                output_dir=base,
                source_distribution=distribution,
            )
            files = {
                "policy": (base / "mirror_label_policy.json"),
                "report": (base / "mirror_label_policy_report.json"),
                "validation": (base / "mirror_label_policy_validation.json"),
            }
            contents = {k: json.loads(v.read_text(encoding="utf-8")) for k, v in files.items()}
            return result, contents

    def test_output_files_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            builder.run_mirror_label_policy_builder(
                output_dir=base, source_distribution=_DISTRIBUTION_ALL_DATA
            )
            self.assertTrue((base / "mirror_label_policy.json").exists())
            self.assertTrue((base / "mirror_label_policy_report.json").exists())
            self.assertTrue((base / "mirror_label_policy_validation.json").exists())

    def test_output_files_valid_json(self) -> None:
        _, contents = self._run()
        for name, data in contents.items():
            self.assertIsInstance(data, dict, f"{name} is not a dict")

    def test_policy_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["policy_validation_result"], "PASS")

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_policy_version_in_report(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["policy_version"], builder.LABEL_POLICY_VERSION)

    def test_policy_file_has_required_fields(self) -> None:
        _, contents = self._run()
        for field in builder.REQUIRED_POLICY_FIELDS:
            self.assertIn(field, contents["policy"])

    def test_policy_file_has_all_decisions(self) -> None:
        _, contents = self._run()
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, contents["policy"]["decision_policy"])

    def test_validation_file_pass(self) -> None:
        _, contents = self._run()
        self.assertEqual(
            contents["validation"]["policy_validation_result"], "PASS"
        )

    def test_report_decision_summary_present(self) -> None:
        result, _ = self._run()
        self.assertIn("decision_summary", result)
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, result["decision_summary"])

    def test_unresolved_case_count_five(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["unresolved_case_count"], 5)

    def test_label_placeholder_state_null(self) -> None:
        result, _ = self._run()
        self.assertIn("null", result["label_placeholder_state"])


if __name__ == "__main__":
    unittest.main()
