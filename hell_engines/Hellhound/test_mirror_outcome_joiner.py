from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_dataset_builder as builder
    import mirror_dataset_contract as contract
    import mirror_outcome_joiner as joiner
    import mirror_packet_contract
except ImportError:
    from . import mirror_dataset_builder as builder
    from . import mirror_dataset_contract as contract
    from . import mirror_outcome_joiner as joiner
    from . import mirror_packet_contract


class OutcomePlaceholderBuildTest(unittest.TestCase):
    """build_outcome_placeholder structure and live_outcome=null rules."""

    def test_valid_replay_row_produces_valid_status(self) -> None:
        row = _replay_row("PASS", False)
        op = joiner.build_outcome_placeholder(row)
        self.assertEqual(op["replay_outcome"]["status"], "VALID")

    def test_mutated_packet_produces_mutated_status(self) -> None:
        row = _replay_row("PASS", True)
        op = joiner.build_outcome_placeholder(row)
        self.assertEqual(op["replay_outcome"]["status"], "MUTATED")

    def test_invalid_contract_produces_invalid_status(self) -> None:
        row = _replay_row("FAIL", False)
        op = joiner.build_outcome_placeholder(row)
        self.assertEqual(op["replay_outcome"]["status"], "INVALID")

    def test_no_replay_row_produces_no_match_status(self) -> None:
        op = joiner.build_outcome_placeholder(None)
        self.assertEqual(op["replay_outcome"]["status"], "NO_MATCH")

    def test_empty_dict_produces_no_match_status(self) -> None:
        op = joiner.build_outcome_placeholder({})
        self.assertEqual(op["replay_outcome"]["status"], "NO_MATCH")

    def test_live_outcome_is_always_null(self) -> None:
        for row in (_replay_row("PASS", False), _replay_row("FAIL", True), None):
            op = joiner.build_outcome_placeholder(row)
            self.assertIsNone(op["live_outcome"], f"live_outcome not null for row={row}")

    def test_live_outcome_is_not_zero_or_empty(self) -> None:
        op = joiner.build_outcome_placeholder(_replay_row("PASS", False))
        self.assertIsNot(op["live_outcome"], 0)
        self.assertIsNot(op["live_outcome"], "")
        self.assertIsNot(op["live_outcome"], False)

    def test_replay_outcome_has_required_keys(self) -> None:
        op = joiner.build_outcome_placeholder(_replay_row("PASS", False))
        self.assertIn("status", op["replay_outcome"])
        self.assertIn("metadata", op["replay_outcome"])

    def test_metadata_contains_contract_validation(self) -> None:
        op = joiner.build_outcome_placeholder(_replay_row("PASS", False))
        self.assertEqual(op["replay_outcome"]["metadata"]["contract_validation"], "PASS")

    def test_metadata_contains_packet_mutated(self) -> None:
        op = joiner.build_outcome_placeholder(_replay_row("PASS", False))
        self.assertFalse(op["replay_outcome"]["metadata"]["packet_mutated"])

    def test_no_match_metadata_is_empty(self) -> None:
        op = joiner.build_outcome_placeholder(None)
        self.assertEqual(op["replay_outcome"]["metadata"], {})


class JoinSampleWithOutcomeTest(unittest.TestCase):
    """join_sample_with_outcome — immutability and correctness."""

    def _sample(self) -> dict:
        return _make_sample("REAL_WHALE_BACK")

    def test_join_does_not_mutate_original_sample(self) -> None:
        sample = self._sample()
        original_hash = sample["packet_hash"]
        joiner.join_sample_with_outcome(sample, _replay_row("PASS", False))
        self.assertEqual(sample["packet_hash"], original_hash)
        self.assertIsNone(sample["outcome_placeholder"])  # original unchanged

    def test_joined_sample_has_outcome_placeholder_filled(self) -> None:
        joined = joiner.join_sample_with_outcome(self._sample(), _replay_row("PASS", False))
        self.assertIsNotNone(joined["outcome_placeholder"])
        self.assertIsInstance(joined["outcome_placeholder"], dict)

    def test_label_placeholder_stays_null_after_join(self) -> None:
        joined = joiner.join_sample_with_outcome(self._sample(), _replay_row("PASS", False))
        self.assertIsNone(joined["label_placeholder"])

    def test_packet_hash_unchanged_after_join(self) -> None:
        sample = self._sample()
        original_hash = sample["packet_hash"]
        joined = joiner.join_sample_with_outcome(sample, _replay_row("PASS", False))
        self.assertEqual(joined["packet_hash"], original_hash)

    def test_feature_unchanged_after_join(self) -> None:
        sample = self._sample()
        original_feature = dict(sample["feature"])
        joined = joiner.join_sample_with_outcome(sample, _replay_row("PASS", False))
        self.assertEqual(joined["feature"], original_feature)

    def test_decision_unchanged_after_join(self) -> None:
        sample = self._sample()
        joined = joiner.join_sample_with_outcome(sample, _replay_row("PASS", False))
        self.assertEqual(joined["decision"], sample["decision"])

    def test_contract_version_unchanged_after_join(self) -> None:
        sample = self._sample()
        joined = joiner.join_sample_with_outcome(sample, _replay_row("PASS", False))
        self.assertEqual(joined["contract_version"], mirror_packet_contract.CONTRACT_VERSION)

    def test_live_outcome_null_after_join(self) -> None:
        joined = joiner.join_sample_with_outcome(self._sample(), _replay_row("PASS", False))
        self.assertIsNone(joined["outcome_placeholder"]["live_outcome"])

    def test_no_match_join_still_produces_valid_structure(self) -> None:
        joined = joiner.join_sample_with_outcome(self._sample(), None)
        self.assertIn("replay_outcome", joined["outcome_placeholder"])
        self.assertIn("live_outcome", joined["outcome_placeholder"])
        self.assertEqual(joined["outcome_placeholder"]["replay_outcome"]["status"], "NO_MATCH")


class JoinDatasetWithReplayTest(unittest.TestCase):
    """join_dataset_with_replay — batch join with replay harness."""

    def _samples_and_packets(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        packets = [_packet(d) for d in decisions]
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reason_registry)
        return samples, packets, schema, reason_registry

    def test_all_samples_joined(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        joined, mapping = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        self.assertEqual(len(joined), len(samples))

    def test_all_mapping_rows_matched(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        _, mapping = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        self.assertTrue(all(m["matched"] for m in mapping))

    def test_outcome_status_valid_for_valid_packets(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        joined, mapping = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        self.assertTrue(all(m["outcome_status"] == "VALID" for m in mapping))

    def test_live_outcome_null_in_all_joined(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        joined, _ = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        self.assertTrue(all(s["outcome_placeholder"]["live_outcome"] is None for s in joined))

    def test_label_placeholder_null_in_all_joined(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        joined, _ = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        self.assertTrue(all(s["label_placeholder"] is None for s in joined))

    def test_packet_hash_unchanged_in_all_joined(self) -> None:
        samples, packets, schema, reg = self._samples_and_packets()
        joined, _ = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        for original, joined_s in zip(samples, joined):
            self.assertEqual(joined_s["packet_hash"], original["packet_hash"])

    def test_unmatched_packet_produces_no_match(self) -> None:
        samples, _, schema, reg = self._samples_and_packets()
        # Pass no packets → no matches
        joined, mapping = joiner.join_dataset_with_replay(samples, [], schema=schema, reason_registry=reg)
        self.assertTrue(all(m["outcome_status"] == "NO_MATCH" for m in mapping))
        self.assertTrue(all(not m["matched"] for m in mapping))


class JoinValidationTest(unittest.TestCase):
    """validate_join — detects mutations and structural violations."""

    def _joined_pair(self, decision="REAL_WHALE_BACK"):
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        packet = _packet(decision)
        packets = [packet]
        samples = builder.build_dataset_samples([packet], schema=schema, reason_registry=reg)
        joined, _ = joiner.join_dataset_with_replay(samples, packets, schema=schema, reason_registry=reg)
        return joined, samples

    def test_valid_join_passes_validation(self) -> None:
        joined, original = self._joined_pair()
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "PASS")
        self.assertEqual(result["mutation_count"], 0)

    def test_packet_hash_mutation_detected(self) -> None:
        joined, original = self._joined_pair()
        joined[0]["packet_hash"] = "0" * 64
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "FAIL")
        self.assertGreater(result["mutation_count"], 0)

    def test_feature_mutation_detected(self) -> None:
        joined, original = self._joined_pair()
        joined[0]["feature"]["early_mae"] = 999.0
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "FAIL")

    def test_label_placeholder_filled_detected(self) -> None:
        joined, original = self._joined_pair()
        joined[0]["label_placeholder"] = "BUY"
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "FAIL")

    def test_missing_live_outcome_detected(self) -> None:
        joined, original = self._joined_pair()
        del joined[0]["outcome_placeholder"]["live_outcome"]
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "FAIL")

    def test_non_null_live_outcome_detected(self) -> None:
        joined, original = self._joined_pair()
        joined[0]["outcome_placeholder"]["live_outcome"] = "something"
        result = joiner.validate_join(joined, original)
        self.assertEqual(result["join_validation_result"], "FAIL")


class RunOutcomeJoinerTest(unittest.TestCase):
    """run_mirror_outcome_joiner — full run, output files, contract."""

    def _run(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        packets = [_packet(d) for d in decisions]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = joiner.run_mirror_outcome_joiner(
                output_dir=base,
                source_samples=samples,
                source_packets=packets,
            )
            return result, base

    def test_run_creates_output_files(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            joiner.run_mirror_outcome_joiner(
                output_dir=base, source_samples=samples, source_packets=packets
            )
            self.assertTrue((base / "mirror_outcome_join_report.json").exists())
            self.assertTrue((base / "mirror_outcome_mapping.json").exists())
            self.assertTrue((base / "mirror_outcome_statistics.json").exists())

    def test_run_join_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["join_validation_result"], "PASS")

    def test_run_join_result_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["join_result"], "PASS")

    def test_run_mutation_count_zero(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["mutation_count"], 0)

    def test_run_live_outcome_null_count(self) -> None:
        result, _ = self._run(("REAL_WHALE_BACK", "INCONCLUSIVE"))
        self.assertEqual(result["live_outcome_null_count"], 2)

    def test_run_label_placeholder_null_count(self) -> None:
        result, _ = self._run(("REAL_WHALE_BACK", "INCONCLUSIVE"))
        self.assertEqual(result["label_placeholder_null_count"], 2)

    def test_run_contract_versions_correct(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["contract_version"], mirror_packet_contract.CONTRACT_VERSION)
        self.assertEqual(result["dataset_contract_version"], contract.DATASET_CONTRACT_VERSION)

    def test_run_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_run_output_files_valid_json(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            joiner.run_mirror_outcome_joiner(
                output_dir=base, source_samples=samples, source_packets=packets
            )
            for fname in (
                "mirror_outcome_join_report.json",
                "mirror_outcome_mapping.json",
                "mirror_outcome_statistics.json",
            ):
                parsed = json.loads((base / fname).read_text(encoding="utf-8"))
                self.assertIsInstance(parsed, dict)


def _replay_row(contract_validation: str, packet_mutated: bool) -> dict:
    return {
        "contract_validation": contract_validation,
        "packet_mutated": packet_mutated,
        "decision": "REAL_WHALE_BACK",
        "confidence": 0.9,
        "validation_state": "ACCEPT",
        "processing_time_ms": 0.123,
    }


def _make_sample(decision: str) -> dict:
    schema = mirror_packet_contract.build_schema()
    reg = mirror_packet_contract.load_reason_registry()
    return builder.build_dataset_sample(_packet(decision), schema=schema, reason_registry=reg)


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-an-{decision}",
        "campaign_id": f"campaign-an-{decision}",
        "signal_id": f"signal-an-{decision}",
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
