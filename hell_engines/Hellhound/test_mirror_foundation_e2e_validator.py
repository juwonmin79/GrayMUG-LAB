from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_foundation_e2e_validator as e2e
    import mirror_packet_contract
    import mirror_storage_failure_policy as failure_policy
except ImportError:
    from . import mirror_foundation_e2e_validator as e2e
    from . import mirror_packet_contract
    from . import mirror_storage_failure_policy as failure_policy


class E2EPipelineTest(unittest.TestCase):
    def test_pipeline_pass_with_valid_packets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            self.assertEqual(result["pipeline_result"], "PASS")

    def test_pipeline_total_mutation_count_is_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            self.assertEqual(result["total_mutation_count"], 0)

    def test_pipeline_contains_all_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            stage_names = {s["stage"] for s in result["stage_results"]}
            for expected in e2e.E2E_PIPELINE_STAGES:
                self.assertIn(expected, stage_names)

    def test_replay_stage_no_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            replay_stage = _get_stage(result, "replay")
            self.assertEqual(replay_stage["stage_result"], "PASS")
            self.assertEqual(replay_stage["mutation_count"], 0)
            self.assertTrue(replay_stage["content_unchanged"])

    def test_persistence_stage_saves_all_packets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            packets = _packets()
            result = e2e.run_e2e_pipeline(packets, storage_path=storage_path)
            persistence_stage = _get_stage(result, "persistence")
            self.assertEqual(persistence_stage["stage_result"], "PASS")
            self.assertEqual(persistence_stage["save_count"], len(packets))
            self.assertEqual(persistence_stage["mutation_count"], 0)

    def test_readback_stage_hash_matches_original(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            packets = _packets()
            result = e2e.run_e2e_pipeline(packets, storage_path=storage_path)
            readback_stage = _get_stage(result, "readback_audit")
            self.assertEqual(readback_stage["stage_result"], "PASS")
            self.assertEqual(readback_stage["hash_mismatch_count"], 0)
            self.assertEqual(readback_stage["mutation_count"], 0)
            self.assertEqual(readback_stage["hash_match_count"], len(packets))

    def test_readback_replay_after_readback_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            readback_stage = _get_stage(result, "readback_audit")
            self.assertEqual(readback_stage["replay_after_readback"], "PASS")

    def test_failure_policy_stage_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            fp_stage = _get_stage(result, "failure_policy")
            self.assertEqual(fp_stage["stage_result"], "PASS")
            self.assertTrue(fp_stage["all_fail_safe"])
            self.assertTrue(fp_stage["all_no_auto_recovery"])

    def test_pipeline_timing_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            self.assertIsNotNone(result["total_elapsed_ms"])
            self.assertGreater(result["total_elapsed_ms"], 0)
            for stage in result["stage_results"]:
                self.assertIn("elapsed_ms", stage)

    def test_contract_version_in_pipeline_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            self.assertEqual(result["contract_version"], mirror_packet_contract.CONTRACT_VERSION)

    def test_pipeline_is_not_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            result = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            self.assertFalse(result["is_trade_command"])


class E2EFailureInjectionTest(unittest.TestCase):
    def test_write_failure_injection_is_fail_safe(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        write_case = _get_injection_case(result, "write_failure")
        self.assertEqual(write_case["injection_result"], "PASS")
        self.assertTrue(write_case["all_fail_safe"])
        self.assertTrue(write_case["none_saved"])

    def test_write_failure_no_bad_packets_downstream(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        write_case = _get_injection_case(result, "write_failure")
        self.assertTrue(write_case["no_bad_packets_downstream"])
        self.assertEqual(write_case["downstream_packet_count"], 0)

    def test_read_failure_injection_is_fail_safe(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        read_case = _get_injection_case(result, "read_failure")
        self.assertEqual(read_case["injection_result"], "PASS")
        self.assertTrue(read_case["all_fail_safe"])

    def test_read_failure_no_bad_packets_downstream(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        read_case = _get_injection_case(result, "read_failure")
        self.assertTrue(read_case["no_bad_packets_downstream"])
        self.assertEqual(read_case["downstream_packet_count"], 0)

    def test_corrupt_data_read_classified_correctly(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        corrupt_case = _get_injection_case(result, "corrupt_data_read")
        self.assertEqual(corrupt_case["injection_result"], "PASS")
        self.assertEqual(corrupt_case["failure_code"], failure_policy.FAILURE_CODE_CORRUPT_DATA)
        self.assertTrue(corrupt_case["correct_classification"])

    def test_all_failure_injections_pass(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        self.assertEqual(result["failure_injection_result"], "PASS")
        self.assertTrue(result["all_fail_safe"])
        self.assertTrue(result["all_no_bad_packets_downstream"])

    def test_failure_injection_is_not_trade_command(self) -> None:
        result = e2e.run_e2e_failure_injection(_packets())
        self.assertFalse(result["is_trade_command"])
        for case in result["cases"]:
            self.assertFalse(case["is_trade_command"])


class E2EReportTest(unittest.TestCase):
    def test_e2e_report_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            pipeline = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            injection = e2e.run_e2e_failure_injection(_packets())
            report = e2e.build_e2e_report(pipeline, injection)
            self.assertEqual(report["e2e_result"], "PASS")
            self.assertIn("contract_version", report)
            self.assertIn("total_mutation_count", report)
            self.assertIn("hash_match_count", report)
            self.assertIn("hash_mismatch_count", report)
            self.assertIn("replay_after_readback", report)
            self.assertIn("total_elapsed_ms", report)
            self.assertIn("forbidden_actions_confirmed", report)

    def test_e2e_timing_report_contains_all_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "e2e_storage.jsonl"
            pipeline = e2e.run_e2e_pipeline(_packets(), storage_path=storage_path)
            timing = e2e.build_e2e_timing_report(pipeline)
            self.assertIn("total_elapsed_ms", timing)
            for stage in e2e.E2E_PIPELINE_STAGES:
                self.assertIn(stage, timing["stage_timings_ms"])


class RunE2EValidatorTest(unittest.TestCase):
    def test_run_creates_all_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = e2e.run_mirror_foundation_e2e_validator(
                output_dir=base,
                source_packets=_packets(),
            )
            self.assertEqual(result["e2e_result"], "PASS")
            self.assertTrue((base / "mirror_foundation_e2e_report.json").exists())
            self.assertTrue((base / "mirror_foundation_e2e_failure_report.json").exists())
            self.assertTrue((base / "mirror_foundation_e2e_timing.json").exists())

    def test_run_e2e_result_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = e2e.run_mirror_foundation_e2e_validator(
                output_dir=Path(directory),
                source_packets=_packets(),
            )
            self.assertEqual(result["e2e_result"], "PASS")
            self.assertEqual(result["pipeline_result"], "PASS")
            self.assertEqual(result["failure_injection_result"], "PASS")
            self.assertEqual(result["total_mutation_count"], 0)

    def test_run_e2e_failure_injection_all_fail_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = e2e.run_mirror_foundation_e2e_validator(
                output_dir=Path(directory),
                source_packets=_packets(),
            )
            self.assertTrue(result["all_fail_safe_on_injection"])
            self.assertTrue(result["all_no_bad_packets_downstream"])

    def test_run_e2e_contract_version_correct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = e2e.run_mirror_foundation_e2e_validator(
                output_dir=Path(directory),
                source_packets=_packets(),
            )
            self.assertEqual(result["contract_version"], mirror_packet_contract.CONTRACT_VERSION)

    def test_run_e2e_is_not_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = e2e.run_mirror_foundation_e2e_validator(
                output_dir=Path(directory),
                source_packets=_packets(),
            )
            self.assertFalse(result["is_trade_command"])

    def test_run_e2e_output_files_are_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            e2e.run_mirror_foundation_e2e_validator(
                output_dir=base,
                source_packets=_packets(),
            )
            for fname in (
                "mirror_foundation_e2e_report.json",
                "mirror_foundation_e2e_failure_report.json",
                "mirror_foundation_e2e_timing.json",
            ):
                content = (base / fname).read_text(encoding="utf-8")
                parsed = json.loads(content)
                self.assertIsInstance(parsed, dict)


def _get_stage(pipeline_result: dict, stage_name: str) -> dict:
    for stage in pipeline_result.get("stage_results", []):
        if stage.get("stage") == stage_name:
            return stage
    raise KeyError(f"Stage not found: {stage_name}")


def _get_injection_case(injection_result: dict, case_name: str) -> dict:
    for case in injection_result.get("cases", []):
        if case.get("case") == case_name:
            return case
    raise KeyError(f"Injection case not found: {case_name}")


def _packets() -> list:
    return [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-e2e-{decision}",
        "campaign_id": f"campaign-e2e-{decision}",
        "signal_id": f"signal-e2e-{decision}",
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
