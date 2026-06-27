from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_label_audit as audit
except ImportError:
    from . import mirror_label_audit as audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_POLICY_V1 = {
    "policy_version": "mirror_label_policy_v1",
    "decision_policy": {
        "REAL_WHALE_BACK": {"candidate_label": "POSITIVE_MARKET_OUTCOME"},
        "INCONCLUSIVE": {"candidate_label": "NEGATIVE_MARKET_OUTCOME"},
        "FAKE_WHALE_BACK": {"candidate_label": "INSUFFICIENT_CLASS_DATA"},
    },
}


def _orig(decision: str, sample_id: str = None, ph: str = None) -> dict:
    if ph is None:
        ph = ("a" * 64) if decision == "REAL_WHALE_BACK" else ("b" * 64) if decision == "INCONCLUSIVE" else ("c" * 64)
    if sample_id is None:
        sample_id = f"ds-{decision[:4].lower()}-0000"
    return {
        "sample_id": sample_id,
        "contract_version": "mirror_pattern_packet_v1",
        "dataset_contract_version": "mirror_dataset_v1",
        "packet_hash": ph,
        "decision": decision,
        "feature": {"early_mae": -2.0},
        "evidence": [],
        "reason": [],
        "replay_metadata": {},
        "persistence_metadata": {},
        "readback_status": {"status": "PASS"},
        "outcome_placeholder": None,
        "label_placeholder": None,
        "created_at": "2026-06-26T00:00:00+00:00",
        "is_trade_command": False,
    }


def _label_map():
    return {"REAL_WHALE_BACK": "POSITIVE_MARKET_OUTCOME",
            "INCONCLUSIVE": "NEGATIVE_MARKET_OUTCOME",
            "FAKE_WHALE_BACK": "INSUFFICIENT_CLASS_DATA"}


def _labeled(decision: str, label: str = None, sample_id: str = None, ph: str = None) -> dict:
    s = dict(_orig(decision, sample_id, ph))
    s["label_placeholder"] = label if label is not None else _label_map().get(decision)
    return s


def _standard_pair():
    decisions = ["REAL_WHALE_BACK", "REAL_WHALE_BACK",
                 "INCONCLUSIVE", "INCONCLUSIVE"]
    phs = ["a" * 63 + "1", "a" * 63 + "2", "b" * 63 + "1", "b" * 63 + "2"]
    orig = [_orig(d, f"ds-orig-{i}", ph) for i, (d, ph) in enumerate(zip(decisions, phs))]
    labs = [_labeled(d, None, f"ds-orig-{i}", ph) for i, (d, ph) in enumerate(zip(decisions, phs))]
    return orig, labs


# ---------------------------------------------------------------------------
# Decision ↔ Label Consistency
# ---------------------------------------------------------------------------

class DecisionLabelConsistencyTest(unittest.TestCase):
    def _dp(self):
        return _POLICY_V1["decision_policy"]

    def test_correct_labels_pass(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK"), _labeled("INCONCLUSIVE")]
        result = audit.audit_decision_label_consistency(samples, self._dp())
        self.assertEqual(result["decision_label_consistency_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_wrong_label_fails(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK", label="NEGATIVE_MARKET_OUTCOME")]
        result = audit.audit_decision_label_consistency(samples, self._dp())
        self.assertEqual(result["decision_label_consistency_result"], "FAIL")
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(result["issues"][0]["issue"], "decision_label_mismatch")

    def test_fake_whale_back_correct(self) -> None:
        samples = [_labeled("FAKE_WHALE_BACK", "INSUFFICIENT_CLASS_DATA")]
        result = audit.audit_decision_label_consistency(samples, self._dp())
        self.assertEqual(result["decision_label_consistency_result"], "PASS")

    def test_empty_dataset_passes(self) -> None:
        result = audit.audit_decision_label_consistency([], self._dp())
        self.assertEqual(result["decision_label_consistency_result"], "PASS")

    def test_mismatch_reports_expected_and_actual(self) -> None:
        samples = [_labeled("INCONCLUSIVE", label="POSITIVE_MARKET_OUTCOME")]
        result = audit.audit_decision_label_consistency(samples, self._dp())
        issue = result["issues"][0]
        self.assertEqual(issue["assigned_label"], "POSITIVE_MARKET_OUTCOME")
        self.assertEqual(issue["expected_label"], "NEGATIVE_MARKET_OUTCOME")


# ---------------------------------------------------------------------------
# Policy Version
# ---------------------------------------------------------------------------

class PolicyVersionAuditTest(unittest.TestCase):
    def test_correct_version_passes(self) -> None:
        result = audit.audit_policy_version(_POLICY_V1)
        self.assertEqual(result["policy_version_audit_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_wrong_version_fails(self) -> None:
        policy = {**_POLICY_V1, "policy_version": "mirror_label_policy_v0"}
        result = audit.audit_policy_version(policy)
        self.assertEqual(result["policy_version_audit_result"], "FAIL")

    def test_result_includes_version_value(self) -> None:
        result = audit.audit_policy_version(_POLICY_V1)
        self.assertEqual(result["policy_version"], "mirror_label_policy_v1")


# ---------------------------------------------------------------------------
# Label Candidate Validation
# ---------------------------------------------------------------------------

class LabelCandidateAuditTest(unittest.TestCase):
    def test_valid_labels_pass(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK"), _labeled("INCONCLUSIVE")]
        result = audit.audit_label_candidates(samples)
        self.assertEqual(result["label_candidate_audit_result"], "PASS")

    def test_invalid_label_fails(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK", label="MADE_UP")]
        result = audit.audit_label_candidates(samples)
        self.assertEqual(result["label_candidate_audit_result"], "FAIL")
        self.assertEqual(result["issues"][0]["issue"], "invalid_label_candidate")

    def test_null_label_fails(self) -> None:
        # _orig creates samples with label_placeholder=None (not yet labeled)
        samples = [_orig("REAL_WHALE_BACK")]
        result = audit.audit_label_candidates(samples)
        self.assertEqual(result["label_candidate_audit_result"], "FAIL")

    def test_all_five_candidates_individually_pass(self) -> None:
        for candidate in audit.LABEL_CANDIDATES:
            sample = _labeled("REAL_WHALE_BACK", label=candidate)
            result = audit.audit_label_candidates([sample])
            self.assertEqual(result["label_candidate_audit_result"], "PASS",
                             f"Expected PASS for {candidate}")


# ---------------------------------------------------------------------------
# Dataset Integrity
# ---------------------------------------------------------------------------

class DatasetIntegrityTest(unittest.TestCase):
    def test_clean_dataset_passes(self) -> None:
        orig, labs = _standard_pair()
        result = audit.audit_dataset_integrity(labs, orig)
        self.assertEqual(result["dataset_integrity_result"], "PASS")

    def test_duplicate_sample_id_fails(self) -> None:
        orig, labs = _standard_pair()
        labs[1] = dict(labs[0])  # same sample_id
        result = audit.audit_dataset_integrity(labs, orig)
        self.assertEqual(result["dataset_integrity_result"], "FAIL")
        self.assertGreater(result["duplicate_sample_id_count"], 0)

    def test_packet_hash_changed_fails(self) -> None:
        orig, labs = _standard_pair()
        labs[0] = dict(labs[0])
        labs[0]["packet_hash"] = "0" * 64
        result = audit.audit_dataset_integrity(labs, orig)
        self.assertEqual(result["dataset_integrity_result"], "FAIL")

    def test_order_mismatch_fails(self) -> None:
        orig, labs = _standard_pair()
        labs[0], labs[1] = labs[1], labs[0]  # swap
        result = audit.audit_dataset_integrity(labs, orig)
        self.assertEqual(result["dataset_integrity_result"], "FAIL")

    def test_count_mismatch_fails(self) -> None:
        orig, labs = _standard_pair()
        result = audit.audit_dataset_integrity(labs[:2], orig)
        self.assertEqual(result["dataset_integrity_result"], "FAIL")


# ---------------------------------------------------------------------------
# BOM
# ---------------------------------------------------------------------------

class BomAuditTest(unittest.TestCase):
    def test_no_bom_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labeled.jsonl"
            path.write_bytes(b'{"label_placeholder": "POSITIVE_MARKET_OUTCOME"}\n')
            result = audit.audit_bom(path)
            self.assertEqual(result["bom_audit_result"], "PASS")
            self.assertFalse(result["bom_detected"])

    def test_bom_detected_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labeled.jsonl"
            path.write_bytes(b"\xef\xbb\xbf" + b'{"label_placeholder": "POSITIVE_MARKET_OUTCOME"}\n')
            result = audit.audit_bom(path)
            self.assertEqual(result["bom_audit_result"], "FAIL")
            self.assertTrue(result["bom_detected"])

    def test_missing_file_returns_fail(self) -> None:
        result = audit.audit_bom(Path("/nonexistent/path/file.jsonl"))
        self.assertEqual(result["bom_audit_result"], "FAIL")


# ---------------------------------------------------------------------------
# packet_hash Consistency
# ---------------------------------------------------------------------------

class PacketHashConsistencyTest(unittest.TestCase):
    def test_unique_hashes_pass(self) -> None:
        samples = [
            _labeled("REAL_WHALE_BACK", ph="a" * 64),
            _labeled("INCONCLUSIVE", ph="b" * 64),
        ]
        result = audit.audit_packet_hash_consistency(samples)
        self.assertEqual(result["packet_hash_consistency_result"], "PASS")

    def test_same_hash_same_decision_same_label_passes(self) -> None:
        """Same packet_hash appearing twice with identical decision+label is fine."""
        ph = "a" * 64
        samples = [
            _labeled("REAL_WHALE_BACK", ph=ph, sample_id="ds-a-1"),
            _labeled("REAL_WHALE_BACK", ph=ph, sample_id="ds-a-2"),
        ]
        result = audit.audit_packet_hash_consistency(samples)
        self.assertEqual(result["packet_hash_consistency_result"], "PASS")

    def test_same_hash_different_decision_fails(self) -> None:
        ph = "a" * 64
        samples = [
            _labeled("REAL_WHALE_BACK", label="POSITIVE_MARKET_OUTCOME", ph=ph),
            _labeled("INCONCLUSIVE", label="POSITIVE_MARKET_OUTCOME", ph=ph),
        ]
        result = audit.audit_packet_hash_consistency(samples)
        self.assertEqual(result["packet_hash_consistency_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("multiple_decisions_on_same_hash", issues)

    def test_same_hash_different_label_fails(self) -> None:
        ph = "a" * 64
        samples = [
            _labeled("REAL_WHALE_BACK", label="POSITIVE_MARKET_OUTCOME", ph=ph),
            _labeled("REAL_WHALE_BACK", label="NEGATIVE_MARKET_OUTCOME", ph=ph),
        ]
        result = audit.audit_packet_hash_consistency(samples)
        self.assertEqual(result["packet_hash_consistency_result"], "FAIL")
        issues = [i["issue"] for i in result["issues"]]
        self.assertIn("multiple_labels_on_same_hash", issues)

    def test_unique_hash_count_reported(self) -> None:
        samples = [
            _labeled("REAL_WHALE_BACK", ph="a" * 64),
            _labeled("INCONCLUSIVE", ph="b" * 64),
        ]
        result = audit.audit_packet_hash_consistency(samples)
        self.assertEqual(result["unique_packet_hash_count"], 2)


# ---------------------------------------------------------------------------
# Original Dataset Protection
# ---------------------------------------------------------------------------

class OriginalDatasetProtectionTest(unittest.TestCase):
    def test_all_null_passes(self) -> None:
        orig = [_orig("REAL_WHALE_BACK"), _orig("INCONCLUSIVE")]
        result = audit.audit_original_dataset_protection(orig)
        self.assertEqual(result["original_dataset_protection_result"], "PASS")
        self.assertEqual(result["mutation_count"], 0)

    def test_non_null_label_fails(self) -> None:
        orig = [_orig("REAL_WHALE_BACK")]
        orig[0]["label_placeholder"] = "POSITIVE_MARKET_OUTCOME"
        result = audit.audit_original_dataset_protection(orig)
        self.assertEqual(result["original_dataset_protection_result"], "FAIL")
        self.assertEqual(result["mutation_count"], 1)

    def test_empty_dataset_passes(self) -> None:
        result = audit.audit_original_dataset_protection([])
        self.assertEqual(result["original_dataset_protection_result"], "PASS")


# ---------------------------------------------------------------------------
# Deferred Label Warning
# ---------------------------------------------------------------------------

class DeferredLabelWarningTest(unittest.TestCase):
    def test_no_deferred_returns_pass(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK"), _labeled("INCONCLUSIVE")]
        result = audit.audit_deferred_labels(samples)
        self.assertEqual(result["deferred_label_audit_result"], "PASS")
        self.assertEqual(result["deferred_labels_found_count"], 0)

    def test_insufficient_market_data_returns_warning(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK", label="INSUFFICIENT_MARKET_DATA")]
        result = audit.audit_deferred_labels(samples)
        self.assertEqual(result["deferred_label_audit_result"], "WARNING")
        self.assertEqual(result["deferred_labels_found_count"], 1)

    def test_unresolved_returns_warning(self) -> None:
        samples = [_labeled("REAL_WHALE_BACK", label="UNRESOLVED")]
        result = audit.audit_deferred_labels(samples)
        self.assertEqual(result["deferred_label_audit_result"], "WARNING")

    def test_warning_is_not_fail(self) -> None:
        # WARNING != FAIL — must not block ML approval by itself
        samples = [_labeled("REAL_WHALE_BACK", label="UNRESOLVED")]
        result = audit.audit_deferred_labels(samples)
        self.assertNotEqual(result["deferred_label_audit_result"], "FAIL")


# ---------------------------------------------------------------------------
# ML Input Readiness
# ---------------------------------------------------------------------------

class MLInputReadinessTest(unittest.TestCase):
    def _all_pass(self):
        return {
            "decision_label_consistency_result": "PASS",
            "policy_version_audit_result": "PASS",
            "label_candidate_audit_result": "PASS",
            "dataset_integrity_result": "PASS",
            "bom_audit_result": "PASS",
            "packet_hash_consistency_result": "PASS",
            "original_dataset_protection_result": "PASS",
        }

    def _build(self, overrides=None):
        d = self._all_pass()
        if overrides:
            d.update(overrides)
        consistency = {"decision_label_consistency_result": d["decision_label_consistency_result"], "issues": []}
        policy_audit = {"policy_version_audit_result": d["policy_version_audit_result"]}
        candidate_audit = {"label_candidate_audit_result": d["label_candidate_audit_result"]}
        integrity = {"dataset_integrity_result": d["dataset_integrity_result"]}
        bom = {"bom_audit_result": d["bom_audit_result"]}
        hash_cons = {"packet_hash_consistency_result": d["packet_hash_consistency_result"]}
        orig_prot = {"original_dataset_protection_result": d["original_dataset_protection_result"], "mutation_count": 0}
        return audit.build_ml_input_readiness(consistency, policy_audit, candidate_audit, integrity, bom, hash_cons, orig_prot)

    def test_all_pass_approved(self) -> None:
        result = self._build()
        self.assertTrue(result["ML_INPUT_APPROVED"])
        self.assertIn("approval_basis", result)

    def test_label_audit_fail_not_approved(self) -> None:
        result = self._build({"decision_label_consistency_result": "FAIL"})
        self.assertFalse(result["ML_INPUT_APPROVED"])
        self.assertIn("rejection_reasons", result)

    def test_dataset_integrity_fail_not_approved(self) -> None:
        result = self._build({"dataset_integrity_result": "FAIL"})
        self.assertFalse(result["ML_INPUT_APPROVED"])

    def test_original_protection_fail_not_approved(self) -> None:
        result = self._build({"original_dataset_protection_result": "FAIL"})
        self.assertFalse(result["ML_INPUT_APPROVED"])

    def test_hash_consistency_fail_not_approved(self) -> None:
        result = self._build({"packet_hash_consistency_result": "FAIL"})
        self.assertFalse(result["ML_INPUT_APPROVED"])

    def test_approval_basis_has_four_items(self) -> None:
        result = self._build()
        self.assertEqual(len(result["approval_basis"]), 4)

    def test_rejection_reasons_listed(self) -> None:
        result = self._build({"dataset_integrity_result": "FAIL", "bom_audit_result": "FAIL"})
        self.assertIn("Dataset Integrity FAIL", result["rejection_reasons"])


# ---------------------------------------------------------------------------
# Run Audit (end-to-end)
# ---------------------------------------------------------------------------

class RunAuditTest(unittest.TestCase):
    def _make_labeled_jsonl(self, directory, samples):
        path = Path(directory) / "mirror_labeled_dataset.jsonl"
        lines = [json.dumps(s, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for s in samples]
        path.write_text("".join(lines), encoding="utf-8")
        return path

    def _run(self, decisions=None):
        if decisions is None:
            decisions = ["REAL_WHALE_BACK", "INCONCLUSIVE"]
        orig = [_orig(d, f"ds-{i}", "a" * 63 + str(i) if "REAL" in d else "b" * 63 + str(i))
                for i, d in enumerate(decisions)]
        labs = [_labeled(d, None, f"ds-{i}", "a" * 63 + str(i) if "REAL" in d else "b" * 63 + str(i))
                for i, d in enumerate(decisions)]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            lpath = self._make_labeled_jsonl(directory, labs)
            result = audit.run_mirror_label_audit(
                output_dir=base,
                labeled_path=lpath,
                source_original=orig,
                source_policy=_POLICY_V1,
            )
            files = {
                "audit_report": base / "mirror_label_audit_report.json",
                "consistency": base / "mirror_label_consistency_report.json",
                "integrity": base / "mirror_label_integrity_report.json",
                "readiness": base / "mirror_ml_input_readiness.json",
                "statistics": base / "mirror_label_audit_statistics.json",
            }
            contents = {k: json.loads(v.read_text(encoding="utf-8")) for k, v in files.items()}
            return result, contents

    def test_output_files_created(self) -> None:
        orig = [_orig("REAL_WHALE_BACK", "ds-0")]
        labs = [_labeled("REAL_WHALE_BACK", sample_id="ds-0")]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            lpath = self._make_labeled_jsonl(directory, labs)
            audit.run_mirror_label_audit(
                output_dir=base, labeled_path=lpath,
                source_original=orig, source_policy=_POLICY_V1
            )
            for fname in (
                "mirror_label_audit_report.json",
                "mirror_label_consistency_report.json",
                "mirror_label_integrity_report.json",
                "mirror_ml_input_readiness.json",
                "mirror_label_audit_statistics.json",
            ):
                self.assertTrue((base / fname).exists(), f"missing {fname}")

    def test_output_files_valid_json(self) -> None:
        _, contents = self._run()
        for name, data in contents.items():
            self.assertIsInstance(data, dict, f"{name} not a dict")

    def test_clean_dataset_label_audit_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["label_audit_result"], "PASS")

    def test_clean_dataset_ml_approved(self) -> None:
        result, _ = self._run()
        self.assertTrue(result["ML_INPUT_APPROVED"])

    def test_mutation_count_zero(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["mutation_count"], 0)

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_ml_readiness_file_has_approval_basis(self) -> None:
        _, contents = self._run()
        self.assertIn("approval_basis", contents["readiness"])

    def test_ml_approved_key_present(self) -> None:
        _, contents = self._run()
        self.assertIn("ML_INPUT_APPROVED", contents["readiness"])


if __name__ == "__main__":
    unittest.main()
