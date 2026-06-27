from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_dataset_split_layer as split_layer
except ImportError:
    from . import mirror_dataset_split_layer as split_layer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _row(
    sample_id: str,
    packet_hash: str = None,
    label_encoded: int = 1,
    decision_encoded: int = 1,
) -> dict:
    if packet_hash is None:
        packet_hash = sample_id * 4  # 64-char approximation for tests
    return {
        "sample_id": sample_id,
        "packet_hash": packet_hash[:64].ljust(64, "0"),
        "features": {"decision_encoded": decision_encoded},
        "label_encoded": label_encoded,
        "label_original": "POSITIVE_MARKET_OUTCOME" if label_encoded == 1 else "NEGATIVE_MARKET_OUTCOME",
    }


def _make_rows(n: int) -> list:
    rows = []
    for i in range(n):
        label = 1 if i < n // 2 else 0
        decision = 1 if i < n // 2 else 0
        rows.append(_row(f"ds-{i:04d}", packet_hash=f"{i:064d}", label_encoded=label, decision_encoded=decision))
    return rows


_APPROVED_FEAT_VAL = {"feature_validation_result": "PASS"}
_REJECTED_FEAT_VAL = {"feature_validation_result": "FAIL"}


def _make_matrix(n: int = 20) -> dict:
    return {
        "feature_contract_version": "mirror_ml_feature_matrix_v1",
        "rows": _make_rows(n),
        "sample_count": n,
    }


def _run(n: int = 20, approved: bool = True) -> tuple:
    matrix = _make_matrix(n)
    feat_val = _APPROVED_FEAT_VAL if approved else _REJECTED_FEAT_VAL
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        result = split_layer.run_mirror_dataset_split_layer(
            output_dir=base,
            source_matrix=matrix,
            source_feature_validation=feat_val,
        )
        files = {}
        for fname in (
            "mirror_train_dataset.json",
            "mirror_validation_dataset.json",
            "mirror_test_dataset.json",
            "mirror_dataset_split_report.json",
            "mirror_dataset_split_statistics.json",
            "mirror_dataset_split_validation.json",
        ):
            p = base / fname
            if p.exists():
                files[fname] = json.loads(p.read_text(encoding="utf-8"))
        return result, files


# ---------------------------------------------------------------------------
# Feature Validation Gate
# ---------------------------------------------------------------------------

class FeatureValidationGateTest(unittest.TestCase):
    def test_pass_allowed(self) -> None:
        self.assertTrue(split_layer.check_feature_validation({"feature_validation_result": "PASS"}))

    def test_fail_blocked(self) -> None:
        self.assertFalse(split_layer.check_feature_validation({"feature_validation_result": "FAIL"}))

    def test_missing_key_blocked(self) -> None:
        self.assertFalse(split_layer.check_feature_validation({}))

    def test_case_sensitive(self) -> None:
        self.assertFalse(split_layer.check_feature_validation({"feature_validation_result": "pass"}))


# ---------------------------------------------------------------------------
# Split Count Calculation
# ---------------------------------------------------------------------------

class SplitCountTest(unittest.TestCase):
    def test_n20_exact(self) -> None:
        train, val, test = split_layer.compute_split_counts(20)
        self.assertEqual(val, 3)    # floor(20 * 0.15) = 3
        self.assertEqual(test, 3)   # floor(20 * 0.15) = 3
        self.assertEqual(train, 14)  # 20 - 3 - 3 = 14

    def test_total_preserved(self) -> None:
        for n in (10, 20, 30, 50, 100):
            tr, va, te = split_layer.compute_split_counts(n)
            self.assertEqual(tr + va + te, n, f"total mismatch for n={n}")

    def test_remainder_goes_to_train(self) -> None:
        # N=21: floor(21*0.15)=3, floor(21*0.15)=3, train=21-3-3=15
        tr, va, te = split_layer.compute_split_counts(21)
        self.assertEqual(va, 3)
        self.assertEqual(te, 3)
        self.assertEqual(tr, 15)

    def test_floor_not_round(self) -> None:
        # N=7: floor(7*0.15)=floor(1.05)=1
        tr, va, te = split_layer.compute_split_counts(7)
        self.assertEqual(va, 1)
        self.assertEqual(te, 1)
        self.assertEqual(tr, 5)

    def test_validation_uses_floor(self) -> None:
        for n in range(5, 30):
            tr, va, te = split_layer.compute_split_counts(n)
            self.assertEqual(va, math.floor(n * 0.15))
            self.assertEqual(te, math.floor(n * 0.15))


# ---------------------------------------------------------------------------
# Deterministic Split
# ---------------------------------------------------------------------------

class DeterministicSplitTest(unittest.TestCase):
    def test_n20_correct_counts(self) -> None:
        rows = _make_rows(20)
        train, val, test = split_layer.split_rows(rows, seed=42)
        self.assertEqual(len(train), 14)
        self.assertEqual(len(val), 3)
        self.assertEqual(len(test), 3)

    def test_same_seed_same_result(self) -> None:
        rows = _make_rows(20)
        tr1, va1, te1 = split_layer.split_rows(rows, seed=42)
        tr2, va2, te2 = split_layer.split_rows(rows, seed=42)
        self.assertEqual([r["sample_id"] for r in tr1], [r["sample_id"] for r in tr2])
        self.assertEqual([r["sample_id"] for r in va1], [r["sample_id"] for r in va2])
        self.assertEqual([r["sample_id"] for r in te1], [r["sample_id"] for r in te2])

    def test_different_seed_different_result(self) -> None:
        rows = _make_rows(20)
        tr1, _, _ = split_layer.split_rows(rows, seed=42)
        tr2, _, _ = split_layer.split_rows(rows, seed=99)
        ids1 = [r["sample_id"] for r in tr1]
        ids2 = [r["sample_id"] for r in tr2]
        self.assertNotEqual(ids1, ids2)

    def test_original_rows_not_mutated(self) -> None:
        rows = _make_rows(20)
        original_ids = [r["sample_id"] for r in rows]
        split_layer.split_rows(rows, seed=42)
        self.assertEqual([r["sample_id"] for r in rows], original_ids)

    def test_all_rows_covered(self) -> None:
        rows = _make_rows(20)
        train, val, test = split_layer.split_rows(rows, seed=42)
        all_ids = {r["sample_id"] for r in rows}
        used_ids = (
            {r["sample_id"] for r in train}
            | {r["sample_id"] for r in val}
            | {r["sample_id"] for r in test}
        )
        self.assertEqual(all_ids, used_ids)


# ---------------------------------------------------------------------------
# Split Contract
# ---------------------------------------------------------------------------

class SplitContractTest(unittest.TestCase):
    def _contract(self, n=20) -> dict:
        tr, va, te = split_layer.compute_split_counts(n)
        return split_layer.build_split_contract(
            source_feature_matrix="mirror_ml_feature_matrix.json",
            train_count=tr,
            validation_count=va,
            test_count=te,
        )

    def test_contract_version_correct(self) -> None:
        c = self._contract()
        self.assertEqual(c["split_contract_version"], split_layer.SPLIT_CONTRACT_VERSION)

    def test_random_seed_42(self) -> None:
        c = self._contract()
        self.assertEqual(c["random_seed"], 42)

    def test_required_fields_present(self) -> None:
        c = self._contract()
        for field in split_layer._REQUIRED_SPLIT_CONTRACT_FIELDS:
            self.assertIn(field, c)

    def test_counts_match_n20(self) -> None:
        c = self._contract(20)
        self.assertEqual(c["train_count"], 14)
        self.assertEqual(c["validation_count"], 3)
        self.assertEqual(c["test_count"], 3)

    def test_total_count_preserved(self) -> None:
        c = self._contract(20)
        self.assertEqual(c["total_count"], 20)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self._contract()["is_trade_command"])


# ---------------------------------------------------------------------------
# Leakage Validation
# ---------------------------------------------------------------------------

class LeakageValidationTest(unittest.TestCase):
    def _clean_split(self, n=20):
        rows = _make_rows(n)
        return split_layer.split_rows(rows, seed=42)

    def test_clean_split_passes(self) -> None:
        tr, va, te = self._clean_split()
        result = split_layer.validate_leakage(tr, va, te)
        self.assertEqual(result["leakage_validation_result"], "PASS")
        self.assertEqual(result["leakage_count"], 0)

    def test_train_val_overlap_fails(self) -> None:
        tr, va, te = self._clean_split()
        va_contaminated = [tr[0]] + va  # inject train row into val
        result = split_layer.validate_leakage(tr, va_contaminated, te)
        self.assertEqual(result["leakage_validation_result"], "FAIL")

    def test_train_test_overlap_fails(self) -> None:
        tr, va, te = self._clean_split()
        te_contaminated = [tr[0]] + te
        result = split_layer.validate_leakage(tr, va, te_contaminated)
        self.assertEqual(result["leakage_validation_result"], "FAIL")

    def test_val_test_overlap_fails(self) -> None:
        tr, va, te = self._clean_split()
        te_contaminated = [va[0]] + te
        result = split_layer.validate_leakage(tr, va, te_contaminated)
        self.assertEqual(result["leakage_validation_result"], "FAIL")

    def test_duplicate_in_train_fails(self) -> None:
        tr, va, te = self._clean_split()
        tr_dup = [tr[0]] + tr  # duplicate first row
        result = split_layer.validate_leakage(tr_dup, va, te)
        self.assertEqual(result["leakage_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Coverage Validation
# ---------------------------------------------------------------------------

class CoverageValidationTest(unittest.TestCase):
    def test_full_coverage_passes(self) -> None:
        rows = _make_rows(20)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        result = split_layer.validate_coverage(rows, tr, va, te)
        self.assertEqual(result["coverage_validation_result"], "PASS")
        self.assertEqual(result["coverage_pct"], 100.0)

    def test_missing_row_fails(self) -> None:
        rows = _make_rows(20)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        tr_short = tr[:-1]  # drop last train row
        result = split_layer.validate_coverage(rows, tr_short, va, te)
        self.assertEqual(result["coverage_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Split Statistics
# ---------------------------------------------------------------------------

class SplitStatisticsTest(unittest.TestCase):
    def _stats(self, n=20) -> dict:
        rows = _make_rows(n)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        return split_layer.build_split_statistics(rows, tr, va, te)

    def test_reference_only_true(self) -> None:
        self.assertTrue(self._stats()["reference_only"])

    def test_reference_note_contains_n(self) -> None:
        self.assertIn("20", self._stats()["reference_note"])

    def test_observations_four_items(self) -> None:
        self.assertEqual(len(self._stats()["observations"]), 4)

    def test_observations_mention_small_dataset(self) -> None:
        obs = " ".join(self._stats()["observations"])
        self.assertIn("N=20", obs)

    def test_observations_mention_reference_only(self) -> None:
        obs = " ".join(self._stats()["observations"])
        self.assertIn("참고용", obs)

    def test_label_distribution_keys_present(self) -> None:
        s = self._stats()
        for k in ("train_label_distribution", "validation_label_distribution", "test_label_distribution"):
            self.assertIn(k, s)

    def test_total_in_stats(self) -> None:
        s = self._stats()
        self.assertEqual(s["total_count"], 20)
        self.assertEqual(s["train_count"], 14)
        self.assertEqual(s["validation_count"], 3)
        self.assertEqual(s["test_count"], 3)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self._stats()["is_trade_command"])


# ---------------------------------------------------------------------------
# Split Validation
# ---------------------------------------------------------------------------

class SplitValidationTest(unittest.TestCase):
    def _valid_val(self, n=20):
        rows = _make_rows(n)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        tr_c, va_c, te_c = split_layer.compute_split_counts(n)
        contract = split_layer.build_split_contract(
            source_feature_matrix="test.json",
            train_count=tr_c, validation_count=va_c, test_count=te_c,
        )
        leakage = split_layer.validate_leakage(tr, va, te)
        coverage = split_layer.validate_coverage(rows, tr, va, te)
        return split_layer.validate_split(contract, tr, va, te, leakage, coverage)

    def test_valid_split_passes(self) -> None:
        r = self._valid_val()
        self.assertEqual(r["split_validation_result"], "PASS")
        self.assertEqual(r["issue_count"], 0)

    def test_wrong_contract_version_fails(self) -> None:
        rows = _make_rows(20)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        bad_contract = split_layer.build_split_contract(
            source_feature_matrix="test.json", train_count=14, validation_count=3, test_count=3
        )
        bad_contract["split_contract_version"] = "wrong_version"
        leakage = split_layer.validate_leakage(tr, va, te)
        coverage = split_layer.validate_coverage(rows, tr, va, te)
        r = split_layer.validate_split(bad_contract, tr, va, te, leakage, coverage)
        self.assertEqual(r["split_validation_result"], "FAIL")

    def test_wrong_seed_fails(self) -> None:
        rows = _make_rows(20)
        tr, va, te = split_layer.split_rows(rows, seed=42)
        bad_contract = split_layer.build_split_contract(
            source_feature_matrix="test.json", train_count=14, validation_count=3, test_count=3
        )
        bad_contract["random_seed"] = 99
        leakage = split_layer.validate_leakage(tr, va, te)
        coverage = split_layer.validate_coverage(rows, tr, va, te)
        r = split_layer.validate_split(bad_contract, tr, va, te, leakage, coverage)
        self.assertEqual(r["split_validation_result"], "FAIL")


# ---------------------------------------------------------------------------
# Run Split Layer (end-to-end)
# ---------------------------------------------------------------------------

class RunSplitLayerTest(unittest.TestCase):
    def test_output_files_created(self) -> None:
        result, files = _run(20, approved=True)
        for fname in (
            "mirror_train_dataset.json",
            "mirror_validation_dataset.json",
            "mirror_test_dataset.json",
            "mirror_dataset_split_report.json",
            "mirror_dataset_split_statistics.json",
            "mirror_dataset_split_validation.json",
        ):
            self.assertIn(fname, files, f"missing {fname}")

    def test_approved_run_returns_pass(self) -> None:
        result, _ = _run(approved=True)
        self.assertEqual(result["split_layer_result"], "PASS")

    def test_not_approved_run_returns_blocked(self) -> None:
        result, _ = _run(approved=False)
        self.assertEqual(result["split_layer_result"], "BLOCKED")

    def test_split_validation_pass(self) -> None:
        result, _ = _run()
        self.assertEqual(result["split_validation_result"], "PASS")

    def test_leakage_pass(self) -> None:
        result, _ = _run()
        self.assertEqual(result["leakage_validation_result"], "PASS")

    def test_coverage_100pct(self) -> None:
        result, _ = _run()
        self.assertEqual(result["coverage_pct"], 100.0)

    def test_train_14_val_3_test_3(self) -> None:
        result, _ = _run(20)
        self.assertEqual(result["train_count"], 14)
        self.assertEqual(result["validation_count"], 3)
        self.assertEqual(result["test_count"], 3)

    def test_mutation_count_zero(self) -> None:
        result, _ = _run()
        self.assertEqual(result["mutation_count"], 0)

    def test_is_not_trade_command(self) -> None:
        result, _ = _run()
        self.assertFalse(result["is_trade_command"])

    def test_train_dataset_has_14_rows(self) -> None:
        _, files = _run(20)
        self.assertEqual(files["mirror_train_dataset.json"]["sample_count"], 14)
        self.assertEqual(len(files["mirror_train_dataset.json"]["rows"]), 14)

    def test_validation_dataset_has_3_rows(self) -> None:
        _, files = _run(20)
        self.assertEqual(files["mirror_validation_dataset.json"]["sample_count"], 3)

    def test_test_dataset_has_3_rows(self) -> None:
        _, files = _run(20)
        self.assertEqual(files["mirror_test_dataset.json"]["sample_count"], 3)

    def test_statistics_reference_only(self) -> None:
        _, files = _run(20)
        self.assertTrue(files["mirror_dataset_split_statistics.json"]["reference_only"])

    def test_split_report_is_contract(self) -> None:
        _, files = _run(20)
        self.assertEqual(
            files["mirror_dataset_split_report.json"]["split_contract_version"],
            split_layer.SPLIT_CONTRACT_VERSION,
        )

    def test_split_name_in_datasets(self) -> None:
        _, files = _run(20)
        self.assertEqual(files["mirror_train_dataset.json"]["split_name"], "train")
        self.assertEqual(files["mirror_validation_dataset.json"]["split_name"], "validation")
        self.assertEqual(files["mirror_test_dataset.json"]["split_name"], "test")


if __name__ == "__main__":
    unittest.main()
