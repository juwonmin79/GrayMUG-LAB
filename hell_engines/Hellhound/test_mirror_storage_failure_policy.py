from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

try:
    import mirror_storage_failure_policy as policy
except ImportError:
    from . import mirror_storage_failure_policy as policy


class StorageFailurePolicyWriteTest(unittest.TestCase):
    def _mock_storage(self, *, append_exc: Exception = None) -> MagicMock:
        storage = MagicMock()
        if append_exc is not None:
            storage.append_packet.side_effect = append_exc
        storage.existing_hashes.return_value = set()
        return storage

    def test_write_io_error_is_fail_safe(self) -> None:
        storage = self._mock_storage(append_exc=IOError("disk full"))
        sut = policy.StorageFailurePolicy(storage)
        result = sut.save_with_policy(_packet())
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_FAIL_SAFE)
        self.assertFalse(result["saved"])
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_WRITE_FAILURE)

    def test_write_os_error_is_write_failure(self) -> None:
        storage = self._mock_storage(append_exc=OSError("permission denied"))
        sut = policy.StorageFailurePolicy(storage)
        result = sut.save_with_policy(_packet())
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_WRITE_FAILURE)

    def test_write_failure_records_are_appended(self) -> None:
        storage = self._mock_storage(append_exc=IOError("disk error"))
        sut = policy.StorageFailurePolicy(storage)
        sut.save_with_policy(_packet())
        sut.save_with_policy(_packet())
        self.assertEqual(len(sut.failure_records), 2)

    def test_write_failure_no_auto_recovery(self) -> None:
        storage = self._mock_storage(append_exc=IOError("disk error"))
        sut = policy.StorageFailurePolicy(storage)
        sut.save_with_policy(_packet())
        record = sut.failure_records[0]
        self.assertFalse(record["auto_recovery_attempted"])

    def test_successful_write_records_no_failure(self) -> None:
        storage = self._mock_storage()
        sut = policy.StorageFailurePolicy(storage)
        result = sut.save_with_policy(_packet())
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_PASS)
        self.assertTrue(result["saved"])
        self.assertEqual(len(sut.failure_records), 0)

    def test_write_failure_is_not_trade_command(self) -> None:
        storage = self._mock_storage(append_exc=IOError("error"))
        sut = policy.StorageFailurePolicy(storage)
        result = sut.save_with_policy(_packet())
        self.assertFalse(result["is_trade_command"])


class StorageFailurePolicyReadTest(unittest.TestCase):
    def test_read_io_error_is_fail_safe(self) -> None:
        storage = MagicMock()
        storage.load_packets.side_effect = IOError("file missing")
        sut = policy.StorageFailurePolicy(storage)
        result = sut.load_with_policy()
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_FAIL_SAFE)
        self.assertEqual(result["packets"], [])
        self.assertEqual(result["packet_count"], 0)
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_READ_FAILURE)

    def test_read_corrupt_json_is_corrupt_data(self) -> None:
        storage = MagicMock()
        storage.load_packets.side_effect = json.JSONDecodeError("bad json", "", 0)
        sut = policy.StorageFailurePolicy(storage)
        result = sut.load_with_policy()
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_CORRUPT_DATA)
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_FAIL_SAFE)

    def test_read_unicode_error_is_encoding_error(self) -> None:
        storage = MagicMock()
        storage.load_packets.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "bad encoding")
        sut = policy.StorageFailurePolicy(storage)
        result = sut.load_with_policy()
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_ENCODING_ERROR)

    def test_read_failure_no_auto_recovery(self) -> None:
        storage = MagicMock()
        storage.load_packets.side_effect = IOError("read error")
        sut = policy.StorageFailurePolicy(storage)
        sut.load_with_policy()
        record = sut.failure_records[0]
        self.assertFalse(record["auto_recovery_attempted"])

    def test_successful_read_records_no_failure(self) -> None:
        storage = MagicMock()
        storage.load_packets.return_value = [_packet()]
        sut = policy.StorageFailurePolicy(storage)
        result = sut.load_with_policy()
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_PASS)
        self.assertEqual(result["packet_count"], 1)
        self.assertEqual(len(sut.failure_records), 0)


class StorageFailurePolicyHashReadTest(unittest.TestCase):
    def test_hash_read_io_error_is_hash_read_failure(self) -> None:
        storage = MagicMock()
        storage.existing_hashes.side_effect = IOError("hash read failed")
        sut = policy.StorageFailurePolicy(storage)
        result = sut.hash_load_with_policy()
        self.assertEqual(result["policy_outcome"], policy.POLICY_OUTCOME_FAIL_SAFE)
        self.assertEqual(result["hashes"], set())
        self.assertEqual(result["hash_count"], 0)
        self.assertEqual(result["failure_code"], policy.FAILURE_CODE_HASH_READ_FAILURE)

    def test_hash_read_failure_no_auto_recovery(self) -> None:
        storage = MagicMock()
        storage.existing_hashes.side_effect = IOError("hash read error")
        sut = policy.StorageFailurePolicy(storage)
        sut.hash_load_with_policy()
        record = sut.failure_records[0]
        self.assertFalse(record["auto_recovery_attempted"])


class FailureClassificationTest(unittest.TestCase):
    def test_json_decode_error_is_corrupt_data(self) -> None:
        exc = json.JSONDecodeError("bad", "", 0)
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_READ), policy.FAILURE_CODE_CORRUPT_DATA)
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_WRITE), policy.FAILURE_CODE_CORRUPT_DATA)

    def test_unicode_error_is_encoding_error(self) -> None:
        exc = UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_READ), policy.FAILURE_CODE_ENCODING_ERROR)

    def test_io_error_write_is_write_failure(self) -> None:
        exc = IOError("disk full")
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_WRITE), policy.FAILURE_CODE_WRITE_FAILURE)

    def test_io_error_read_is_read_failure(self) -> None:
        exc = IOError("read error")
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_READ), policy.FAILURE_CODE_READ_FAILURE)

    def test_io_error_hash_read_is_hash_read_failure(self) -> None:
        exc = IOError("hash error")
        self.assertEqual(policy.classify_failure(exc, policy.OPERATION_HASH_READ), policy.FAILURE_CODE_HASH_READ_FAILURE)


class ReplaySafetyTest(unittest.TestCase):
    def test_replay_safe_after_read_failure(self) -> None:
        storage = MagicMock()
        storage.load_packets.side_effect = IOError("read error")
        sut = policy.StorageFailurePolicy(storage)
        result = sut.load_with_policy()
        self.assertEqual(result["packets"], [])
        simulation = {"cases": [{"operation": "READ", "policy_outcome": policy.POLICY_OUTCOME_FAIL_SAFE}]}
        report = policy.build_replay_safety_report(simulation)
        self.assertEqual(report["replay_safety_verdict"], "PASS")

    def test_replay_safe_after_write_failure(self) -> None:
        storage = MagicMock()
        storage.append_packet.side_effect = IOError("write error")
        sut = policy.StorageFailurePolicy(storage)
        sut.save_with_policy(_packet())
        simulation = {"cases": [{"operation": "WRITE", "policy_outcome": policy.POLICY_OUTCOME_FAIL_SAFE}]}
        report = policy.build_replay_safety_report(simulation)
        self.assertEqual(report["replay_safety_verdict"], "PASS")


class FailureReportTest(unittest.TestCase):
    def test_failure_report_counts_correctly(self) -> None:
        records = [
            policy.make_failure_record(
                failure_code=policy.FAILURE_CODE_WRITE_FAILURE,
                operation=policy.OPERATION_WRITE,
                exception_type="IOError",
                exception_message="disk full",
            ),
            policy.make_failure_record(
                failure_code=policy.FAILURE_CODE_READ_FAILURE,
                operation=policy.OPERATION_READ,
                exception_type="IOError",
                exception_message="read error",
            ),
        ]
        report = policy.build_failure_report(records)
        self.assertEqual(report["total_failures"], 2)
        self.assertEqual(report["fail_safe_count"], 2)
        self.assertEqual(report["auto_recovery_count"], 0)
        self.assertTrue(report["no_auto_recovery"])

    def test_empty_failure_report_is_pass(self) -> None:
        report = policy.build_failure_report([])
        self.assertEqual(report["total_failures"], 0)
        self.assertEqual(report["policy_outcome"], policy.POLICY_OUTCOME_PASS)
        self.assertTrue(report["no_auto_recovery"])

    def test_failure_report_code_distribution(self) -> None:
        records = [
            policy.make_failure_record(
                failure_code=policy.FAILURE_CODE_WRITE_FAILURE,
                operation=policy.OPERATION_WRITE,
                exception_type="IOError",
                exception_message="x",
            ),
            policy.make_failure_record(
                failure_code=policy.FAILURE_CODE_WRITE_FAILURE,
                operation=policy.OPERATION_WRITE,
                exception_type="OSError",
                exception_message="x",
            ),
            policy.make_failure_record(
                failure_code=policy.FAILURE_CODE_CORRUPT_DATA,
                operation=policy.OPERATION_READ,
                exception_type="JSONDecodeError",
                exception_message="x",
            ),
        ]
        report = policy.build_failure_report(records)
        self.assertEqual(report["failure_code_distribution"][policy.FAILURE_CODE_WRITE_FAILURE], 2)
        self.assertEqual(report["failure_code_distribution"][policy.FAILURE_CODE_CORRUPT_DATA], 1)
        self.assertEqual(report["failure_code_distribution"][policy.FAILURE_CODE_READ_FAILURE], 0)


class FailureSimulationTest(unittest.TestCase):
    def test_run_failure_simulation_all_pass(self) -> None:
        result = policy.run_failure_simulation()
        self.assertEqual(result["simulation_verdict"], "PASS")
        self.assertTrue(result["all_fail_safe"])
        self.assertTrue(result["all_no_auto_recovery"])
        self.assertTrue(result["all_correct_failure_codes"])

    def test_run_failure_simulation_covers_all_cases(self) -> None:
        result = policy.run_failure_simulation()
        self.assertEqual(result["simulation_count"], len(policy.SIMULATION_CASES))

    def test_simulation_contains_write_and_read_cases(self) -> None:
        result = policy.run_failure_simulation()
        operations = {c["operation"] for c in result["cases"]}
        self.assertIn(policy.OPERATION_WRITE, operations)
        self.assertIn(policy.OPERATION_READ, operations)
        self.assertIn(policy.OPERATION_HASH_READ, operations)

    def test_all_simulated_failures_are_not_trade_commands(self) -> None:
        result = policy.run_failure_simulation()
        for case in result["cases"]:
            self.assertFalse(case["is_trade_command"])


class RunPolicyTest(unittest.TestCase):
    def test_run_writes_all_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = policy.run_mirror_storage_failure_policy(output_dir=base)
            self.assertEqual(result["failure_policy"], "PASS")
            self.assertEqual(result["simulation_verdict"], "PASS")
            self.assertEqual(result["replay_safety_verdict"], "PASS")
            self.assertTrue(result["no_auto_recovery"])
            self.assertTrue((base / "mirror_failure_policy_report.json").exists())
            self.assertTrue((base / "mirror_failure_classification.json").exists())
            self.assertTrue((base / "mirror_replay_safety_report.json").exists())
            self.assertTrue((base / "mirror_failure_simulation.json").exists())
            self.assertTrue((base / "mirror_failure_report.json").exists())

    def test_run_policy_is_not_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = policy.run_mirror_storage_failure_policy(output_dir=Path(directory))
            self.assertFalse(result["is_trade_command"])


def _packet(decision: str = "REAL_WHALE_BACK") -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-{decision}",
        "campaign_id": f"campaign-{decision}",
        "signal_id": f"signal-{decision}",
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
                "conflict_detected": False,
                "decision_targets": [decision],
                "policy": "DECIDE",
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
