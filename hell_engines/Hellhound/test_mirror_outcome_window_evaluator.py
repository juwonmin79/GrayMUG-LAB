from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_dataset_builder as builder
    import mirror_dataset_contract as contract
    import mirror_outcome_window_evaluator as evaluator
    import mirror_packet_contract
except ImportError:
    from . import mirror_dataset_builder as builder
    from . import mirror_dataset_contract as contract
    from . import mirror_outcome_window_evaluator as evaluator
    from . import mirror_packet_contract

_FEATURES_FULL = {
    "early_mae": -2.0,
    "recovery_ratio": 1.2,
    "campaign_duration": 24.0,
    "confidence": 1.0,
    "evidence": ["RECOVERY_STRONG"],
}
_FEATURES_NO_RECOVERY = {
    "early_mae": -2.0,
    "recovery_ratio": 0.8,
    "campaign_duration": 24.0,
    "confidence": 0.4,
    "evidence": [],
}


class ComputeOutcomeWindowTest(unittest.TestCase):
    """compute_outcome_window — calculation correctness."""

    def test_completed_status_when_all_features_present(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertTrue(result["completed"])
        self.assertEqual(result["status"], "COMPLETED")

    def test_mae_equals_abs_early_mae(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertAlmostEqual(result["mae"], 2.0)

    def test_mae_is_non_negative(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertGreaterEqual(result["mae"], 0.0)

    def test_mfe_is_non_negative(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertGreaterEqual(result["mfe"], 0.0)

    def test_mfe_positive_when_recovery_above_one(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        # recovery_ratio=1.2, early_mae=-2.0 → return=(1.2-1)*2=0.4, mfe=0.4
        self.assertAlmostEqual(result["mfe"], 0.4)

    def test_mfe_zero_when_recovery_below_one(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_NO_RECOVERY)
        self.assertEqual(result["mfe"], 0.0)

    def test_return_pct_positive_when_recovery_above_one(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertAlmostEqual(result["return_pct"], 0.4)

    def test_return_pct_negative_when_recovery_below_one(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_NO_RECOVERY)
        # (0.8 - 1) * 2 = -0.4
        self.assertAlmostEqual(result["return_pct"], -0.4)

    def test_window_duration_equals_campaign_duration(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertAlmostEqual(result["window_duration"], 24.0)

    def test_time_to_peak_always_null(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertIsNone(result["time_to_peak"])

    def test_time_to_trough_always_null(self) -> None:
        result = evaluator.compute_outcome_window(_FEATURES_FULL)
        self.assertIsNone(result["time_to_trough"])

    def test_zero_mae_produces_zero_returns(self) -> None:
        features = {**_FEATURES_FULL, "early_mae": 0.0}
        result = evaluator.compute_outcome_window(features)
        self.assertEqual(result["mae"], 0.0)
        self.assertEqual(result["mfe"], 0.0)
        self.assertEqual(result["return_pct"], 0.0)


class InsufficientDataTest(unittest.TestCase):
    """compute_outcome_window — INSUFFICIENT_REPLAY_DATA cases."""

    def test_none_early_mae_causes_insufficient(self) -> None:
        features = {**_FEATURES_FULL, "early_mae": None}
        result = evaluator.compute_outcome_window(features)
        self.assertFalse(result["completed"])
        self.assertEqual(result["status"], "INSUFFICIENT_REPLAY_DATA")

    def test_none_recovery_ratio_causes_insufficient(self) -> None:
        features = {**_FEATURES_FULL, "recovery_ratio": None}
        result = evaluator.compute_outcome_window(features)
        self.assertFalse(result["completed"])
        self.assertEqual(result["status"], "INSUFFICIENT_REPLAY_DATA")

    def test_none_campaign_duration_causes_insufficient(self) -> None:
        features = {**_FEATURES_FULL, "campaign_duration": None}
        result = evaluator.compute_outcome_window(features)
        self.assertFalse(result["completed"])
        self.assertEqual(result["status"], "INSUFFICIENT_REPLAY_DATA")

    def test_all_nulls_when_insufficient(self) -> None:
        features = {**_FEATURES_FULL, "early_mae": None}
        result = evaluator.compute_outcome_window(features)
        for field in ("mfe", "mae", "return_pct", "time_to_peak", "time_to_trough", "window_duration"):
            self.assertIsNone(result[field], f"{field} should be null")

    def test_empty_features_causes_insufficient(self) -> None:
        result = evaluator.compute_outcome_window({})
        self.assertEqual(result["status"], "INSUFFICIENT_REPLAY_DATA")
        self.assertFalse(result["completed"])


class EvaluateSampleWindowTest(unittest.TestCase):
    """evaluate_sample_window — per-sample evaluation."""

    def _sample(self, decision="REAL_WHALE_BACK"):
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        return builder.build_dataset_sample(_packet(decision), schema=schema, reason_registry=reg)

    def test_completed_window_for_full_packet(self) -> None:
        sample = self._sample()
        packet = _packet("REAL_WHALE_BACK")
        ev = evaluator.evaluate_sample_window(sample, packet)
        self.assertTrue(ev["market_outcome"]["completed"])
        self.assertEqual(ev["market_outcome"]["status"], "COMPLETED")

    def test_no_packet_match_status(self) -> None:
        sample = self._sample()
        ev = evaluator.evaluate_sample_window(sample, None)
        self.assertEqual(ev["market_outcome"]["status"], "NO_PACKET_MATCH")
        self.assertFalse(ev["market_outcome"]["completed"])

    def test_sample_id_preserved(self) -> None:
        sample = self._sample()
        ev = evaluator.evaluate_sample_window(sample, _packet("REAL_WHALE_BACK"))
        self.assertEqual(ev["sample_id"], sample["sample_id"])

    def test_packet_hash_preserved(self) -> None:
        sample = self._sample()
        ev = evaluator.evaluate_sample_window(sample, _packet("REAL_WHALE_BACK"))
        self.assertEqual(ev["packet_hash"], sample["packet_hash"])

    def test_decision_preserved(self) -> None:
        sample = self._sample()
        ev = evaluator.evaluate_sample_window(sample, _packet("REAL_WHALE_BACK"))
        self.assertEqual(ev["decision"], "REAL_WHALE_BACK")

    def test_window_start_from_created_at(self) -> None:
        sample = self._sample()
        ev = evaluator.evaluate_sample_window(sample, _packet("REAL_WHALE_BACK"))
        self.assertEqual(ev["window_start"], sample.get("created_at"))

    def test_original_sample_not_mutated(self) -> None:
        sample = self._sample()
        original_hash = sample["packet_hash"]
        original_feature = dict(sample["feature"])
        evaluator.evaluate_sample_window(sample, _packet("REAL_WHALE_BACK"))
        self.assertEqual(sample["packet_hash"], original_hash)
        self.assertEqual(sample["feature"], original_feature)


class EvaluateDatasetWindowsTest(unittest.TestCase):
    """evaluate_dataset_windows — batch matching and evaluation."""

    def _batch(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        packets = [_packet(d) for d in decisions]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        return samples, packets

    def test_all_samples_evaluated(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        self.assertEqual(len(evals), len(samples))

    def test_all_completed_when_all_matched(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        self.assertTrue(all(e["market_outcome"]["completed"] for e in evals))

    def test_no_match_when_no_packets(self) -> None:
        samples, _ = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, [])
        self.assertTrue(all(e["market_outcome"]["status"] == "NO_PACKET_MATCH" for e in evals))

    def test_mfe_non_negative_for_all(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        completed = [e for e in evals if e["market_outcome"]["completed"]]
        self.assertTrue(all(e["market_outcome"]["mfe"] >= 0 for e in completed))

    def test_mae_non_negative_for_all(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        completed = [e for e in evals if e["market_outcome"]["completed"]]
        self.assertTrue(all(e["market_outcome"]["mae"] >= 0 for e in completed))

    def test_time_to_peak_always_null(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        self.assertTrue(all(e["market_outcome"]["time_to_peak"] is None for e in evals))

    def test_time_to_trough_always_null(self) -> None:
        samples, packets = self._batch()
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        self.assertTrue(all(e["market_outcome"]["time_to_trough"] is None for e in evals))


class ValidationTest(unittest.TestCase):
    """validate_windows."""

    def _evals(self):
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        return evaluator.evaluate_dataset_windows(samples, packets)

    def test_valid_windows_pass_validation(self) -> None:
        result = evaluator.validate_windows(self._evals())
        self.assertEqual(result["window_validation_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_negative_mfe_fails_validation(self) -> None:
        evals = self._evals()
        evals[0]["market_outcome"]["mfe"] = -0.5
        result = evaluator.validate_windows(evals)
        self.assertEqual(result["window_validation_result"], "FAIL")

    def test_negative_mae_fails_validation(self) -> None:
        evals = self._evals()
        evals[0]["market_outcome"]["mae"] = -1.0
        result = evaluator.validate_windows(evals)
        self.assertEqual(result["window_validation_result"], "FAIL")

    def test_invalid_status_fails_validation(self) -> None:
        evals = self._evals()
        evals[0]["market_outcome"]["status"] = "UNKNOWN_STATUS"
        result = evaluator.validate_windows(evals)
        self.assertEqual(result["window_validation_result"], "FAIL")

    def test_completed_with_null_mfe_fails(self) -> None:
        evals = self._evals()
        evals[0]["market_outcome"]["mfe"] = None
        result = evaluator.validate_windows(evals)
        self.assertEqual(result["window_validation_result"], "FAIL")


class StatisticsTest(unittest.TestCase):
    def test_statistics_counts(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        stats = evaluator.build_window_statistics(evals)
        self.assertEqual(stats["total_count"], 2)
        self.assertEqual(stats["completed_count"], 2)
        self.assertEqual(stats["no_match_count"], 0)
        self.assertFalse(stats["is_trade_command"])

    def test_statistics_mfe_mean_non_negative(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        evals = evaluator.evaluate_dataset_windows(samples, packets)
        stats = evaluator.build_window_statistics(evals)
        if stats["mfe_mean"] is not None:
            self.assertGreaterEqual(stats["mfe_mean"], 0.0)

    def test_statistics_time_flags_false(self) -> None:
        evals = evaluator.evaluate_dataset_windows([], [])
        stats = evaluator.build_window_statistics(evals)
        self.assertFalse(stats["time_to_peak_available"])
        self.assertFalse(stats["time_to_trough_available"])
        self.assertTrue(stats["candle_level_data_required"])


class RunEvaluatorTest(unittest.TestCase):
    def _packets_and_samples(self, decisions=("REAL_WHALE_BACK", "INCONCLUSIVE")):
        packets = [_packet(d) for d in decisions]
        schema = mirror_packet_contract.build_schema()
        reg = mirror_packet_contract.load_reason_registry()
        samples = builder.build_dataset_samples(packets, schema=schema, reason_registry=reg)
        return packets, samples

    def test_creates_output_files(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            evaluator.run_mirror_outcome_window_evaluator(
                output_dir=base, source_samples=samples, source_packets=packets
            )
            self.assertTrue((base / "mirror_market_outcome_report.json").exists())
            self.assertTrue((base / "mirror_market_outcome_statistics.json").exists())
            self.assertTrue((base / "mirror_outcome_window_examples.json").exists())

    def test_run_validation_pass(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            self.assertEqual(result["window_validation_result"], "PASS")

    def test_run_completed_count_matches_sample_count(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            self.assertEqual(result["completed_count"], result["sample_count"])

    def test_run_mfe_mae_non_negative(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            if result["mfe_mean"] is not None:
                self.assertGreaterEqual(result["mfe_mean"], 0.0)
            if result["mae_mean"] is not None:
                self.assertGreaterEqual(result["mae_mean"], 0.0)

    def test_run_time_flags_false(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            self.assertFalse(result["time_to_peak_available"])
            self.assertFalse(result["time_to_trough_available"])

    def test_run_contract_versions(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            self.assertEqual(result["contract_version"], mirror_packet_contract.CONTRACT_VERSION)
            self.assertEqual(result["dataset_contract_version"], contract.DATASET_CONTRACT_VERSION)

    def test_run_is_not_trade_command(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            result = evaluator.run_mirror_outcome_window_evaluator(
                output_dir=Path(directory), source_samples=samples, source_packets=packets
            )
            self.assertFalse(result["is_trade_command"])

    def test_output_files_are_valid_json(self) -> None:
        packets, samples = self._packets_and_samples()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            evaluator.run_mirror_outcome_window_evaluator(
                output_dir=base, source_samples=samples, source_packets=packets
            )
            for fname in (
                "mirror_market_outcome_report.json",
                "mirror_market_outcome_statistics.json",
                "mirror_outcome_window_examples.json",
            ):
                parsed = json.loads((base / fname).read_text(encoding="utf-8"))
                self.assertIsInstance(parsed, dict)


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-ao-{decision}",
        "campaign_id": f"campaign-ao-{decision}",
        "signal_id": f"signal-ao-{decision}",
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
