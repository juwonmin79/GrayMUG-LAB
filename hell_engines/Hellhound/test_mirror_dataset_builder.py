from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_dataset_builder as builder
    import mirror_dataset_contract as contract
    import mirror_packet_contract
except ImportError:
    from . import mirror_dataset_builder as builder
    from . import mirror_dataset_contract as contract
    from . import mirror_packet_contract


class DatasetSampleBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = mirror_packet_contract.build_schema()
        self.reason_registry = mirror_packet_contract.load_reason_registry()

    def _build(self, decision: str = "REAL_WHALE_BACK") -> dict:
        return builder.build_dataset_sample(
            _packet(decision),
            schema=self.schema,
            reason_registry=self.reason_registry,
        )

    def test_sample_contains_all_required_fields(self) -> None:
        sample = self._build()
        for field in contract.REQUIRED_FIELDS:
            self.assertIn(field, sample, f"Missing required field: {field}")

    def test_outcome_placeholder_is_none(self) -> None:
        sample = self._build()
        self.assertIsNone(sample["outcome_placeholder"])

    def test_outcome_placeholder_is_not_zero(self) -> None:
        sample = self._build()
        self.assertIsNot(sample["outcome_placeholder"], 0)
        self.assertIsNot(sample["outcome_placeholder"], "")
        self.assertIsNot(sample["outcome_placeholder"], False)

    def test_label_placeholder_is_none(self) -> None:
        sample = self._build()
        self.assertIsNone(sample["label_placeholder"])

    def test_label_placeholder_is_not_zero(self) -> None:
        sample = self._build()
        self.assertIsNot(sample["label_placeholder"], 0)
        self.assertIsNot(sample["label_placeholder"], "")
        self.assertIsNot(sample["label_placeholder"], False)

    def test_packet_hash_matches_original(self) -> None:
        packet = _packet("REAL_WHALE_BACK")
        expected_hash = _canonical_hash(packet)
        sample = builder.build_dataset_sample(packet, schema=self.schema, reason_registry=self.reason_registry)
        self.assertEqual(sample["packet_hash"], expected_hash)

    def test_packet_hash_is_64_hex_chars(self) -> None:
        sample = self._build()
        h = sample["packet_hash"]
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_contract_version_is_frozen(self) -> None:
        sample = self._build()
        self.assertEqual(sample["contract_version"], mirror_packet_contract.CONTRACT_VERSION)

    def test_dataset_contract_version(self) -> None:
        sample = self._build()
        self.assertEqual(sample["dataset_contract_version"], contract.DATASET_CONTRACT_VERSION)

    def test_feature_fields_extracted(self) -> None:
        sample = self._build()
        feature = sample["feature"]
        for field in contract.FEATURE_FIELDS:
            self.assertIn(field, feature)

    def test_feature_values_correct(self) -> None:
        sample = self._build()
        self.assertEqual(sample["feature"]["early_mae"], -2.0)
        self.assertEqual(sample["feature"]["recovery_ratio"], 1.2)
        self.assertEqual(sample["feature"]["campaign_duration"], 24.0)
        self.assertEqual(sample["feature"]["confidence"], 1.0)

    def test_evidence_extracted(self) -> None:
        sample = self._build()
        self.assertIsInstance(sample["evidence"], list)
        self.assertIn("RECOVERY_STRONG", sample["evidence"])

    def test_reason_extracted(self) -> None:
        sample = self._build("REAL_WHALE_BACK")
        self.assertIsInstance(sample["reason"], list)
        self.assertIn("RECOVERY_SUPPORT", sample["reason"])

    def test_decision_extracted(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            if decision == "FAKE_WHALE_BACK":
                continue
            sample = builder.build_dataset_sample(
                _packet(decision),
                schema=self.schema,
                reason_registry=self.reason_registry,
            )
            self.assertEqual(sample["decision"], decision)

    def test_is_trade_command_always_false(self) -> None:
        for decision in ("REAL_WHALE_BACK", "INCONCLUSIVE"):
            sample = builder.build_dataset_sample(
                _packet(decision),
                schema=self.schema,
                reason_registry=self.reason_registry,
            )
            self.assertFalse(sample["is_trade_command"])

    def test_replay_metadata_replay_result_pass(self) -> None:
        sample = self._build()
        self.assertEqual(sample["replay_metadata"]["replay_result"], "PASS")
        self.assertFalse(sample["replay_metadata"]["packet_mutated"])

    def test_readback_status_hash_verified(self) -> None:
        sample = self._build()
        self.assertTrue(sample["readback_status"]["hash_verified"])
        self.assertEqual(sample["readback_status"]["encoding"], "utf-8_without_bom")

    def test_persistence_metadata_append_only(self) -> None:
        sample = self._build()
        self.assertTrue(sample["persistence_metadata"]["append_only"])
        self.assertEqual(sample["persistence_metadata"]["storage_type"], "jsonl_file")

    def test_sample_id_is_deterministic(self) -> None:
        packet = _packet("REAL_WHALE_BACK")
        s1 = builder.build_dataset_sample(packet, schema=self.schema, reason_registry=self.reason_registry)
        s2 = builder.build_dataset_sample(packet, schema=self.schema, reason_registry=self.reason_registry)
        self.assertEqual(s1["sample_id"], s2["sample_id"])

    def test_mutation_count_is_zero(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        samples = builder.build_dataset_samples(packets, schema=self.schema, reason_registry=self.reason_registry)
        mutation = sum(1 for s in samples if s["replay_metadata"].get("packet_mutated"))
        self.assertEqual(mutation, 0)


class DatasetContractValidationTest(unittest.TestCase):
    def _sample(self, decision: str = "REAL_WHALE_BACK") -> dict:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        return builder.build_dataset_sample(_packet(decision), schema=schema, reason_registry=reason_registry)

    def test_valid_sample_passes_validation(self) -> None:
        result = contract.validate_sample(self._sample())
        self.assertTrue(result["valid"])
        self.assertEqual(result["validation_result"], "PASS")

    def test_non_null_outcome_placeholder_fails(self) -> None:
        sample = self._sample()
        sample["outcome_placeholder"] = 0
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_string_outcome_placeholder_fails(self) -> None:
        sample = self._sample()
        sample["outcome_placeholder"] = "unknown"
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_non_null_label_placeholder_fails(self) -> None:
        sample = self._sample()
        sample["label_placeholder"] = False
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_wrong_contract_version_fails(self) -> None:
        sample = self._sample()
        sample["contract_version"] = "wrong_version_v99"
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_wrong_dataset_contract_version_fails(self) -> None:
        sample = self._sample()
        sample["dataset_contract_version"] = "wrong_dataset_v99"
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_invalid_decision_fails(self) -> None:
        sample = self._sample()
        sample["decision"] = "INVALID_DECISION"
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_is_trade_command_true_fails(self) -> None:
        sample = self._sample()
        sample["is_trade_command"] = True
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_missing_required_field_fails(self) -> None:
        sample = self._sample()
        del sample["packet_hash"]
        result = contract.validate_sample(sample)
        self.assertFalse(result["valid"])

    def test_validate_samples_batch(self) -> None:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(
            [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            schema=schema,
            reason_registry=reason_registry,
        )
        result = contract.validate_samples(samples)
        self.assertEqual(result["validation_result"], "PASS")
        self.assertEqual(result["pass_count"], 2)


class DatasetWriterTest(unittest.TestCase):
    def test_write_dataset_creates_jsonl(self) -> None:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(
            [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            schema=schema,
            reason_registry=reason_registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.jsonl"
            builder.write_dataset(samples, path)
            self.assertTrue(path.exists())
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)

    def test_write_dataset_each_line_is_valid_json(self) -> None:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(
            [_packet("REAL_WHALE_BACK")],
            schema=schema,
            reason_registry=reason_registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.jsonl"
            builder.write_dataset(samples, path)
            for line in path.read_text(encoding="utf-8").splitlines():
                parsed = json.loads(line)
                self.assertIsInstance(parsed, dict)

    def test_write_dataset_preserves_null_placeholders(self) -> None:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(
            [_packet("REAL_WHALE_BACK")],
            schema=schema,
            reason_registry=reason_registry,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.jsonl"
            builder.write_dataset(samples, path)
            loaded = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertIsNone(loaded["outcome_placeholder"])
            self.assertIsNone(loaded["label_placeholder"])

    def test_write_dataset_preserves_packet_hash(self) -> None:
        packet = _packet("REAL_WHALE_BACK")
        expected_hash = _canonical_hash(packet)
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = [builder.build_dataset_sample(packet, schema=schema, reason_registry=reason_registry)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.jsonl"
            builder.write_dataset(samples, path)
            loaded = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(loaded["packet_hash"], expected_hash)


class DatasetStatisticsTest(unittest.TestCase):
    def test_statistics_sample_count(self) -> None:
        schema = mirror_packet_contract.build_schema()
        reason_registry = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(
            [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            schema=schema,
            reason_registry=reason_registry,
        )
        stats = builder.build_dataset_statistics(samples)
        self.assertEqual(stats["sample_count"], 2)
        self.assertEqual(stats["mutation_count"], 0)
        self.assertEqual(stats["outcome_placeholder_null_count"], 2)
        self.assertEqual(stats["label_placeholder_null_count"], 2)
        self.assertEqual(stats["hash_verified_count"], 2)
        self.assertEqual(stats["validation_result"], "PASS")


class RunDatasetBuilderTest(unittest.TestCase):
    def test_run_creates_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = builder.run_mirror_dataset_builder(
                output_dir=base,
                source_packets=[_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            )
            self.assertEqual(result["validation_result"], "PASS")
            self.assertEqual(result["mutation_count"], 0)
            self.assertTrue((base / "mirror_dataset_sample.json").exists())
            self.assertTrue((base / "mirror_dataset_statistics.json").exists())
            self.assertTrue((base / "mirror_dataset_schema.json").exists())
            self.assertTrue((base / "mirror_dataset_validation.json").exists())

    def test_run_all_placeholders_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = builder.run_mirror_dataset_builder(
                output_dir=Path(directory),
                source_packets=[_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            )
            self.assertEqual(result["outcome_placeholder_null_count"], 2)
            self.assertEqual(result["label_placeholder_null_count"], 2)

    def test_run_hash_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = builder.run_mirror_dataset_builder(
                output_dir=Path(directory),
                source_packets=[_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            )
            self.assertEqual(result["hash_verified_count"], 2)

    def test_run_is_not_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = builder.run_mirror_dataset_builder(
                output_dir=Path(directory),
                source_packets=[_packet("REAL_WHALE_BACK")],
            )
            self.assertFalse(result["is_trade_command"])

    def test_run_contract_versions_in_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = builder.run_mirror_dataset_builder(
                output_dir=Path(directory),
                source_packets=[_packet("REAL_WHALE_BACK")],
            )
            self.assertEqual(result["contract_version"], mirror_packet_contract.CONTRACT_VERSION)
            self.assertEqual(result["dataset_contract_version"], contract.DATASET_CONTRACT_VERSION)

    def test_run_output_files_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            builder.run_mirror_dataset_builder(
                output_dir=base,
                source_packets=[_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            )
            for fname in (
                "mirror_dataset_sample.json",
                "mirror_dataset_statistics.json",
                "mirror_dataset_schema.json",
                "mirror_dataset_validation.json",
            ):
                parsed = json.loads((base / fname).read_text(encoding="utf-8"))
                self.assertIsInstance(parsed, dict)


def _canonical_hash(packet: dict) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-ds-{decision}",
        "campaign_id": f"campaign-ds-{decision}",
        "signal_id": f"signal-ds-{decision}",
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
