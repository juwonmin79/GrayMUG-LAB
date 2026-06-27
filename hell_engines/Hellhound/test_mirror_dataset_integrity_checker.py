from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_dataset_builder as builder
    import mirror_dataset_contract as contract
    import mirror_dataset_integrity_checker as checker
    import mirror_packet_contract
except ImportError:
    from . import mirror_dataset_builder as builder
    from . import mirror_dataset_contract as contract
    from . import mirror_dataset_integrity_checker as checker
    from . import mirror_packet_contract


class IntegrityCheckerPassTest(unittest.TestCase):
    """Valid dataset passes every integrity check."""

    def _run(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, list(decisions))
            return checker.check_dataset_integrity(dataset_path)

    def test_integrity_result_pass(self) -> None:
        self.assertEqual(self._run()["integrity_result"], "PASS")

    def test_no_bom_detected(self) -> None:
        self.assertFalse(self._run()["utf8_bom_detected"])
        self.assertEqual(self._run()["encoding_result"], "PASS")

    def test_no_parse_errors(self) -> None:
        self.assertEqual(self._run()["parse_error_count"], 0)

    def test_contract_consistency_pass(self) -> None:
        self.assertEqual(self._run()["contract_consistency_result"], "PASS")
        self.assertEqual(self._run()["contract_issue_count"], 0)

    def test_hash_format_pass(self) -> None:
        self.assertEqual(self._run()["hash_format_result"], "PASS")
        self.assertEqual(self._run()["invalid_hash_count"], 0)

    def test_no_duplicates(self) -> None:
        result = self._run()
        self.assertEqual(result["duplicate_result"], "PASS")
        self.assertEqual(result["duplicate_packet_hash_count"], 0)
        self.assertEqual(result["duplicate_sample_id_count"], 0)

    def test_canonical_roundtrip_pass(self) -> None:
        self.assertEqual(self._run()["canonical_roundtrip_result"], "PASS")
        self.assertEqual(self._run()["roundtrip_failure_count"], 0)

    def test_append_order_pass(self) -> None:
        self.assertEqual(self._run()["append_order_result"], "PASS")
        self.assertEqual(self._run()["time_reversal_count"], 0)

    def test_placeholder_integrity_pass(self) -> None:
        self.assertEqual(self._run()["placeholder_integrity_result"], "PASS")
        self.assertEqual(self._run()["placeholder_issue_count"], 0)

    def test_is_not_trade_command(self) -> None:
        self.assertFalse(self._run()["is_trade_command"])

    def test_sample_count_correct(self) -> None:
        self.assertEqual(self._run(("REAL_WHALE_BACK", "INCONCLUSIVE"))["sample_count"], 2)


class BOMDetectionTest(unittest.TestCase):
    def test_bom_detected_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.jsonl"
            sample = _make_sample("REAL_WHALE_BACK")
            content_bytes = (json.dumps(sample, sort_keys=True) + "\n").encode("utf-8")
            path.write_bytes(b"\xef\xbb\xbf" + content_bytes)
            result = checker._check_utf8_bom(path)
            self.assertTrue(result["utf8_bom_detected"])
            self.assertEqual(result["encoding_result"], "FAIL")

    def test_no_bom_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.jsonl"
            sample = _make_sample("REAL_WHALE_BACK")
            path.write_text(json.dumps(sample, sort_keys=True) + "\n", encoding="utf-8")
            result = checker._check_utf8_bom(path)
            self.assertFalse(result["utf8_bom_detected"])
            self.assertEqual(result["encoding_result"], "PASS")


class ParseErrorTest(unittest.TestCase):
    def test_invalid_json_line_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.jsonl"
            path.write_text(
                json.dumps(_make_sample("REAL_WHALE_BACK"), sort_keys=True) + "\n"
                + "not_valid_json\n",
                encoding="utf-8",
            )
            _, errors = checker._parse_jsonl(path)
            self.assertEqual(len(errors), 1)
            self.assertIn("line_index", errors[0])
            self.assertIn("error", errors[0])

    def test_valid_lines_still_parsed_after_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.jsonl"
            path.write_text(
                json.dumps(_make_sample("REAL_WHALE_BACK"), sort_keys=True) + "\n"
                + "BROKEN\n"
                + json.dumps(_make_sample("INCONCLUSIVE"), sort_keys=True) + "\n",
                encoding="utf-8",
            )
            rows, errors = checker._parse_jsonl(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(errors), 1)

    def test_parse_error_causes_integrity_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.jsonl"
            path.write_text("not_valid_json\n", encoding="utf-8")
            result = checker.check_dataset_integrity(path)
            self.assertEqual(result["integrity_result"], "FAIL")
            self.assertGreater(result["parse_error_count"], 0)


class ContractConsistencyTest(unittest.TestCase):
    def test_wrong_contract_version_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["contract_version"] = "wrong_version_v99"
        rows = [(0, sample)]
        result = checker._check_contract_consistency(rows)
        self.assertEqual(result["contract_consistency_result"], "FAIL")
        self.assertGreater(result["issue_count"], 0)

    def test_wrong_dataset_contract_version_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["dataset_contract_version"] = "wrong_dataset_v99"
        rows = [(0, sample)]
        result = checker._check_contract_consistency(rows)
        self.assertEqual(result["contract_consistency_result"], "FAIL")
        self.assertGreater(result["issue_count"], 0)

    def test_correct_versions_pass(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK"))]
        result = checker._check_contract_consistency(rows)
        self.assertEqual(result["contract_consistency_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)


class HashFormatTest(unittest.TestCase):
    def test_short_hash_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["packet_hash"] = "abc123"
        rows = [(0, sample)]
        result = checker._check_hash_format(rows)
        self.assertEqual(result["hash_format_result"], "FAIL")
        self.assertEqual(result["invalid_hash_count"], 1)

    def test_non_hex_hash_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["packet_hash"] = "z" * 64
        rows = [(0, sample)]
        result = checker._check_hash_format(rows)
        self.assertEqual(result["hash_format_result"], "FAIL")

    def test_valid_hash_passes(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK"))]
        result = checker._check_hash_format(rows)
        self.assertEqual(result["hash_format_result"], "PASS")
        self.assertEqual(result["invalid_hash_count"], 0)

    def test_missing_hash_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        del sample["packet_hash"]
        rows = [(0, sample)]
        result = checker._check_hash_format(rows)
        self.assertEqual(result["hash_format_result"], "FAIL")


class DuplicateDetectionTest(unittest.TestCase):
    def test_duplicate_packet_hash_detected(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s2 = _make_sample("REAL_WHALE_BACK")
        s2["sample_id"] = "ds-different-id"
        # Same packet_hash (same packet), different sample_id
        rows = [(0, s1), (1, s2)]
        result = checker._check_duplicates(rows)
        self.assertEqual(result["duplicate_result"], "FAIL")
        self.assertGreater(result["duplicate_packet_hash_count"], 0)

    def test_duplicate_sample_id_detected(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s2 = _make_sample("INCONCLUSIVE")
        s2["sample_id"] = s1["sample_id"]  # Force same sample_id
        rows = [(0, s1), (1, s2)]
        result = checker._check_duplicates(rows)
        self.assertEqual(result["duplicate_result"], "FAIL")
        self.assertGreater(result["duplicate_sample_id_count"], 0)

    def test_no_duplicates_pass(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK")), (1, _make_sample("INCONCLUSIVE"))]
        result = checker._check_duplicates(rows)
        self.assertEqual(result["duplicate_result"], "PASS")
        self.assertEqual(result["duplicate_packet_hash_count"], 0)
        self.assertEqual(result["duplicate_sample_id_count"], 0)


class CanonicalRoundtripTest(unittest.TestCase):
    def test_valid_rows_pass_roundtrip(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK")), (1, _make_sample("INCONCLUSIVE"))]
        result = checker._check_canonical_roundtrip(rows)
        self.assertEqual(result["canonical_roundtrip_result"], "PASS")
        self.assertEqual(result["failure_count"], 0)

    def test_nan_value_causes_failure(self) -> None:
        row = _make_sample("REAL_WHALE_BACK")
        row["feature"]["early_mae"] = float("nan")
        rows = [(0, row)]
        result = checker._check_canonical_roundtrip(rows)
        self.assertEqual(result["canonical_roundtrip_result"], "FAIL")
        self.assertGreater(result["failure_count"], 0)


class AppendOrderTest(unittest.TestCase):
    def test_time_reversal_detected(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s1["created_at"] = "2026-06-25T12:00:00+00:00"
        s2 = _make_sample("INCONCLUSIVE")
        s2["created_at"] = "2026-06-25T06:00:00+00:00"  # earlier than s1
        rows = [(0, s1), (1, s2)]
        result = checker._check_append_order(rows)
        self.assertEqual(result["append_order_result"], "FAIL")
        self.assertGreater(result["time_reversal_count"], 0)

    def test_monotonic_timestamps_pass(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s1["created_at"] = "2026-06-25T06:00:00+00:00"
        s2 = _make_sample("INCONCLUSIVE")
        s2["created_at"] = "2026-06-25T12:00:00+00:00"
        rows = [(0, s1), (1, s2)]
        result = checker._check_append_order(rows)
        self.assertEqual(result["append_order_result"], "PASS")
        self.assertEqual(result["time_reversal_count"], 0)

    def test_equal_timestamps_are_not_reversal(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s1["created_at"] = "2026-06-25T00:00:00+00:00"
        s2 = _make_sample("INCONCLUSIVE")
        s2["created_at"] = "2026-06-25T00:00:00+00:00"
        rows = [(0, s1), (1, s2)]
        result = checker._check_append_order(rows)
        self.assertEqual(result["append_order_result"], "PASS")

    def test_null_timestamps_skipped(self) -> None:
        s1 = _make_sample("REAL_WHALE_BACK")
        s1["created_at"] = None
        s2 = _make_sample("INCONCLUSIVE")
        s2["created_at"] = None
        rows = [(0, s1), (1, s2)]
        result = checker._check_append_order(rows)
        self.assertEqual(result["append_order_result"], "PASS")
        self.assertEqual(result["time_reversal_count"], 0)


class PlaceholderIntegrityTest(unittest.TestCase):
    def test_non_null_outcome_placeholder_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["outcome_placeholder"] = 0
        rows = [(0, sample)]
        result = checker._check_placeholders(rows)
        self.assertEqual(result["placeholder_integrity_result"], "FAIL")
        self.assertGreater(result["issue_count"], 0)

    def test_string_outcome_placeholder_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["outcome_placeholder"] = "unknown"
        rows = [(0, sample)]
        result = checker._check_placeholders(rows)
        self.assertEqual(result["placeholder_integrity_result"], "FAIL")

    def test_non_null_label_placeholder_detected(self) -> None:
        sample = _make_sample("REAL_WHALE_BACK")
        sample["label_placeholder"] = False
        rows = [(0, sample)]
        result = checker._check_placeholders(rows)
        self.assertEqual(result["placeholder_integrity_result"], "FAIL")

    def test_null_placeholders_pass(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK"))]
        result = checker._check_placeholders(rows)
        self.assertEqual(result["placeholder_integrity_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)


class HashAuditTest(unittest.TestCase):
    def test_hash_audit_all_valid(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK")), (1, _make_sample("INCONCLUSIVE"))]
        audit = checker._build_hash_audit(rows)
        self.assertEqual(audit["hash_audit_result"], "PASS")
        self.assertEqual(audit["sample_count"], 2)
        self.assertTrue(all(r["hash_format_valid"] for r in audit["rows"]))

    def test_hash_audit_includes_sample_canonical_hash(self) -> None:
        rows = [(0, _make_sample("REAL_WHALE_BACK"))]
        audit = checker._build_hash_audit(rows)
        self.assertIn("sample_canonical_hash", audit["rows"][0])
        h = audit["rows"][0]["sample_canonical_hash"]
        self.assertEqual(len(h), 64)


class DatasetNotFoundTest(unittest.TestCase):
    def test_missing_dataset_returns_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nonexistent.jsonl"
            result = checker.check_dataset_integrity(path)
            self.assertEqual(result["integrity_result"], "FAIL")
            self.assertEqual(result["error"], "dataset_not_found")


class RunIntegrityCheckerTest(unittest.TestCase):
    def test_creates_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, ["REAL_WHALE_BACK", "INCONCLUSIVE"])
            checker.run_mirror_dataset_integrity_checker(dataset_path=dataset_path, output_dir=base)
            self.assertTrue((base / "mirror_dataset_integrity_report.json").exists())
            self.assertTrue((base / "mirror_dataset_hash_audit.json").exists())
            self.assertTrue((base / "mirror_dataset_duplicate_report.json").exists())

    def test_output_files_are_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, ["REAL_WHALE_BACK", "INCONCLUSIVE"])
            checker.run_mirror_dataset_integrity_checker(dataset_path=dataset_path, output_dir=base)
            for fname in (
                "mirror_dataset_integrity_report.json",
                "mirror_dataset_hash_audit.json",
                "mirror_dataset_duplicate_report.json",
            ):
                parsed = json.loads((base / fname).read_text(encoding="utf-8"))
                self.assertIsInstance(parsed, dict)

    def test_run_result_integrity_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, ["REAL_WHALE_BACK", "INCONCLUSIVE"])
            result = checker.run_mirror_dataset_integrity_checker(dataset_path=dataset_path, output_dir=base)
            self.assertEqual(result["integrity_result"], "PASS")

    def test_run_is_not_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, ["REAL_WHALE_BACK"])
            result = checker.run_mirror_dataset_integrity_checker(dataset_path=dataset_path, output_dir=base)
            self.assertFalse(result["is_trade_command"])

    def test_corrupt_sample_causes_fail_safe_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            # One valid sample, one bad JSON line
            valid = json.dumps(_make_sample("REAL_WHALE_BACK"), sort_keys=True)
            dataset_path.write_text(valid + "\n" + "CORRUPTED LINE\n", encoding="utf-8")
            result = checker.check_dataset_integrity(dataset_path)
            # Fail-safe: result is returned (no crash), integrity_result is FAIL
            self.assertEqual(result["integrity_result"], "FAIL")
            self.assertGreater(result["parse_error_count"], 0)

    def test_full_integrity_all_checks_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset_path = base / "dataset.jsonl"
            _write_valid_dataset(dataset_path, ["REAL_WHALE_BACK"])
            result = checker.check_dataset_integrity(dataset_path)
            expected_keys = (
                "integrity_result", "sample_count", "parse_error_count",
                "encoding_result", "contract_consistency_result", "hash_format_result",
                "duplicate_result", "canonical_roundtrip_result",
                "append_order_result", "placeholder_integrity_result",
            )
            for key in expected_keys:
                self.assertIn(key, result, f"Missing key: {key}")


def _make_sample(decision: str) -> dict:
    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()
    return builder.build_dataset_sample(
        _packet(decision),
        schema=schema,
        reason_registry=reason_registry,
    )


def _write_valid_dataset(path: Path, decisions: list) -> None:
    samples = [_make_sample(d) for d in decisions]
    with path.open("w", encoding="utf-8") as file:
        for sample in samples:
            file.write(json.dumps(sample, sort_keys=True) + "\n")


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-am-{decision}",
        "campaign_id": f"campaign-am-{decision}",
        "signal_id": f"signal-am-{decision}",
        "symbol": "BTCUSDT",
        "mirror_decision": decision,
        "confidence": 0.9 if decision == "REAL_WHALE_BACK" else 0.35,
        "reason_code": reasons,
        "supporting_features": {
            "early_mae": -2.0,
            "recovery_ratio": 1.2,
            "campaign_duration": 24.0,
            "confidence": 1.0,
            "evidence": ["RECOVERY_STRONG"],
            "conflict_resolution": {
                "conflict_detected": decision == "INCONCLUSIVE",
                "decision_targets": [decision] if decision == "REAL_WHALE_BACK" else ["FAKE_WHALE_BACK", "INCONCLUSIVE"],
                "policy": "DECIDE" if decision == "REAL_WHALE_BACK" else "INCONCLUSIVE",
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
