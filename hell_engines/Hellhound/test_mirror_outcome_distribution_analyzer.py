from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_outcome_distribution_analyzer as analyzer
    import mirror_packet_contract
except ImportError:
    from . import mirror_outcome_distribution_analyzer as analyzer
    from . import mirror_packet_contract


# ---------------------------------------------------------------------------
# Shared synthetic evaluation fixtures
# ---------------------------------------------------------------------------

def _eval(
    decision: str,
    mfe: float,
    mae: float,
    return_pct: float,
    window_duration: float,
    completed: bool = True,
    sample_id_suffix: str = "",
) -> dict:
    return {
        "sample_id": f"ds-{decision[:4].lower()}{sample_id_suffix}",
        "packet_hash": "a" * 64,
        "decision": decision,
        "window_start": "2026-06-25T00:00:00+00:00",
        "market_outcome": {
            "mfe": mfe,
            "mae": mae,
            "return_pct": return_pct,
            "time_to_peak": None,
            "time_to_trough": None,
            "window_duration": window_duration,
            "status": "COMPLETED" if completed else "INSUFFICIENT_REPLAY_DATA",
            "completed": completed,
        },
    }


REAL_EVALS = [
    _eval("REAL_WHALE_BACK", 0.4, 2.0, 0.4, 20.0, sample_id_suffix="-1"),
    _eval("REAL_WHALE_BACK", 0.8, 4.0, 0.8, 24.0, sample_id_suffix="-2"),
    _eval("REAL_WHALE_BACK", 1.2, 6.0, 1.2, 28.0, sample_id_suffix="-3"),
]
INC_EVALS = [
    _eval("INCONCLUSIVE", 0.0, 2.0, -0.4, 24.0, sample_id_suffix="-1"),
    _eval("INCONCLUSIVE", 0.2, 2.0, 0.2, 24.0, sample_id_suffix="-2"),
]
ALL_EVALS = REAL_EVALS + INC_EVALS  # 5 total, 0 FAKE_WHALE_BACK


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

class PercentileTest(unittest.TestCase):
    def test_empty_list_returns_none(self) -> None:
        self.assertIsNone(analyzer._percentile([], 50))

    def test_single_value_returns_that_value(self) -> None:
        self.assertEqual(analyzer._percentile([5.0], 50), 5.0)

    def test_p50_of_three_is_middle(self) -> None:
        self.assertAlmostEqual(analyzer._percentile([1.0, 2.0, 3.0], 50), 2.0, places=5)

    def test_p25_interpolation(self) -> None:
        # [0.4, 0.8, 1.2]: idx=0.25*2=0.5 → 0.4 + 0.5*0.4 = 0.6
        self.assertAlmostEqual(analyzer._percentile([0.4, 0.8, 1.2], 25), 0.6, places=5)

    def test_p75_interpolation(self) -> None:
        # [0.4, 0.8, 1.2]: idx=0.75*2=1.5 → 0.8 + 0.5*0.4 = 1.0
        self.assertAlmostEqual(analyzer._percentile([0.4, 0.8, 1.2], 75), 1.0, places=5)

    def test_p90_interpolation(self) -> None:
        # [0.4, 0.8, 1.2]: idx=0.9*2=1.8 → 0.8 + 0.8*0.4 = 1.12
        self.assertAlmostEqual(analyzer._percentile([0.4, 0.8, 1.2], 90), 1.12, places=5)

    def test_p100_returns_maximum(self) -> None:
        self.assertAlmostEqual(analyzer._percentile([1.0, 2.0, 3.0], 100), 3.0, places=5)

    def test_p0_returns_minimum(self) -> None:
        self.assertAlmostEqual(analyzer._percentile([1.0, 2.0, 3.0], 0), 1.0, places=5)


# ---------------------------------------------------------------------------
# Field stats
# ---------------------------------------------------------------------------

class FieldStatsTest(unittest.TestCase):
    def test_empty_returns_all_none(self) -> None:
        fs = analyzer._field_stats([])
        for key in ("mean", "median", "minimum", "maximum", "standard_deviation",
                    "percentile_25", "percentile_75", "percentile_90"):
            self.assertIsNone(fs[key], f"expected None for {key}")

    def test_single_value_stdev_is_none(self) -> None:
        fs = analyzer._field_stats([3.0])
        self.assertIsNone(fs["standard_deviation"])

    def test_single_value_mean_equals_value(self) -> None:
        fs = analyzer._field_stats([7.5])
        self.assertAlmostEqual(fs["mean"], 7.5, places=5)

    def test_multi_value_mean(self) -> None:
        fs = analyzer._field_stats([0.4, 0.8, 1.2])
        self.assertAlmostEqual(fs["mean"], 0.8, places=5)

    def test_multi_value_median(self) -> None:
        fs = analyzer._field_stats([0.4, 0.8, 1.2])
        self.assertAlmostEqual(fs["median"], 0.8, places=5)

    def test_multi_value_minimum(self) -> None:
        fs = analyzer._field_stats([0.4, 0.8, 1.2])
        self.assertAlmostEqual(fs["minimum"], 0.4, places=5)

    def test_multi_value_maximum(self) -> None:
        fs = analyzer._field_stats([0.4, 0.8, 1.2])
        self.assertAlmostEqual(fs["maximum"], 1.2, places=5)

    def test_multi_value_stdev(self) -> None:
        fs = analyzer._field_stats([0.4, 0.8, 1.2])
        self.assertAlmostEqual(fs["standard_deviation"], 0.4, places=5)

    def test_all_keys_present(self) -> None:
        fs = analyzer._field_stats([1.0, 2.0])
        for key in ("mean", "median", "minimum", "maximum", "standard_deviation",
                    "percentile_25", "percentile_75", "percentile_90"):
            self.assertIn(key, fs)


# ---------------------------------------------------------------------------
# Group stats
# ---------------------------------------------------------------------------

class GroupStatsTest(unittest.TestCase):
    def test_empty_group_all_zero_counts(self) -> None:
        gs = analyzer._group_stats([])
        self.assertEqual(gs["sample_count"], 0)
        self.assertEqual(gs["completed_count"], 0)
        self.assertEqual(gs["incomplete_count"], 0)
        self.assertEqual(gs["positive_return_count"], 0)
        self.assertEqual(gs["negative_return_count"], 0)

    def test_empty_group_field_stats_all_none(self) -> None:
        gs = analyzer._group_stats([])
        for field in ("mfe", "mae", "return_pct", "window_duration"):
            self.assertIsNone(gs[field]["mean"])

    def test_completed_count_correct(self) -> None:
        gs = analyzer._group_stats(REAL_EVALS)
        self.assertEqual(gs["completed_count"], 3)
        self.assertEqual(gs["incomplete_count"], 0)
        self.assertEqual(gs["sample_count"], 3)

    def test_incomplete_counted_separately(self) -> None:
        inc_eval = _eval("REAL_WHALE_BACK", None, None, None, None, completed=False)
        inc_eval["market_outcome"]["return_pct"] = None
        gs = analyzer._group_stats(REAL_EVALS + [inc_eval])
        self.assertEqual(gs["incomplete_count"], 1)
        self.assertEqual(gs["completed_count"], 3)

    def test_positive_return_count(self) -> None:
        gs = analyzer._group_stats(REAL_EVALS)
        # All 3 REAL_WHALE_BACK have positive return_pct
        self.assertEqual(gs["positive_return_count"], 3)
        self.assertEqual(gs["negative_return_count"], 0)

    def test_negative_return_counted(self) -> None:
        gs = analyzer._group_stats(INC_EVALS)
        # INCONCLUSIVE: return_pct = [-0.4, 0.2]
        self.assertEqual(gs["negative_return_count"], 1)
        self.assertEqual(gs["positive_return_count"], 1)

    def test_mfe_mean_correct(self) -> None:
        gs = analyzer._group_stats(REAL_EVALS)
        # mfe = [0.4, 0.8, 1.2] → mean = 0.8
        self.assertAlmostEqual(gs["mfe"]["mean"], 0.8, places=5)

    def test_return_pct_mean_inconclusive(self) -> None:
        gs = analyzer._group_stats(INC_EVALS)
        # [-0.4, 0.2] → mean = -0.1
        self.assertAlmostEqual(gs["return_pct"]["mean"], -0.1, places=5)


# ---------------------------------------------------------------------------
# Build distribution by decision
# ---------------------------------------------------------------------------

class BuildDistributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dist = analyzer.build_distribution_by_decision(ALL_EVALS)

    def test_all_decision_keys_present(self) -> None:
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, self.dist)

    def test_overall_key_present(self) -> None:
        self.assertIn("overall", self.dist)

    def test_fake_whale_back_zero_samples(self) -> None:
        self.assertEqual(self.dist["FAKE_WHALE_BACK"]["sample_count"], 0)

    def test_real_whale_back_sample_count(self) -> None:
        self.assertEqual(self.dist["REAL_WHALE_BACK"]["sample_count"], 3)

    def test_inconclusive_sample_count(self) -> None:
        self.assertEqual(self.dist["INCONCLUSIVE"]["sample_count"], 2)

    def test_overall_sample_count(self) -> None:
        self.assertEqual(self.dist["overall"]["sample_count"], len(ALL_EVALS))

    def test_overall_positive_return_count(self) -> None:
        # REAL: 3 positive + INCONCLUSIVE: 1 positive = 4
        self.assertEqual(self.dist["overall"]["positive_return_count"], 4)

    def test_overall_negative_return_count(self) -> None:
        # INCONCLUSIVE: 1 negative
        self.assertEqual(self.dist["overall"]["negative_return_count"], 1)


# ---------------------------------------------------------------------------
# Extreme cases
# ---------------------------------------------------------------------------

class ExtremeCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extremes = analyzer.build_extreme_cases(ALL_EVALS)

    def test_max_mfe_is_real_whale_back(self) -> None:
        # max mfe = 1.2 (REAL_WHALE_BACK-3)
        self.assertIsNotNone(self.extremes["max_mfe"])
        self.assertEqual(self.extremes["max_mfe"]["market_outcome"]["mfe"], 1.2)

    def test_max_mae_is_real_whale_back(self) -> None:
        # max mae = 6.0 (REAL_WHALE_BACK-3)
        self.assertIsNotNone(self.extremes["max_mae"])
        self.assertEqual(self.extremes["max_mae"]["market_outcome"]["mae"], 6.0)

    def test_max_return_is_real_whale_back(self) -> None:
        # max return_pct = 1.2
        self.assertIsNotNone(self.extremes["max_return"])
        self.assertEqual(self.extremes["max_return"]["market_outcome"]["return_pct"], 1.2)

    def test_min_return_is_inconclusive(self) -> None:
        # min return_pct = -0.4
        self.assertIsNotNone(self.extremes["min_return"])
        self.assertEqual(self.extremes["min_return"]["market_outcome"]["return_pct"], -0.4)

    def test_max_window_duration(self) -> None:
        # max window_duration = 28.0
        self.assertEqual(self.extremes["max_window_duration"]["market_outcome"]["window_duration"], 28.0)

    def test_min_window_duration(self) -> None:
        # min window_duration = 20.0
        self.assertEqual(self.extremes["min_window_duration"]["market_outcome"]["window_duration"], 20.0)

    def test_extreme_case_has_required_keys(self) -> None:
        case = self.extremes["max_mfe"]
        for key in ("sample_id", "decision", "packet_hash", "market_outcome", "created_at"):
            self.assertIn(key, case)

    def test_empty_evaluations_returns_all_none(self) -> None:
        ext = analyzer.build_extreme_cases([])
        for key in ("max_mfe", "max_mae", "max_return", "min_return",
                    "max_window_duration", "min_window_duration"):
            self.assertIsNone(ext[key], f"expected None for {key}")

    def test_only_incomplete_returns_all_none(self) -> None:
        inc_only = [_eval("INCONCLUSIVE", None, None, None, None, completed=False)]
        ext = analyzer.build_extreme_cases(inc_only)
        self.assertIsNone(ext["max_mfe"])


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class ObservationsTest(unittest.TestCase):
    def test_no_incomplete_no_warning_key(self) -> None:
        obs = analyzer.build_observations(ALL_EVALS)
        self.assertNotIn("incomplete_warning", obs)

    def test_incomplete_adds_warning_key(self) -> None:
        incomplete = [_eval("INCONCLUSIVE", None, None, None, None, completed=False)]
        obs = analyzer.build_observations(ALL_EVALS + incomplete)
        self.assertIn("incomplete_warning", obs)

    def test_incomplete_ratio_correct(self) -> None:
        incomplete = [_eval("INCONCLUSIVE", None, None, None, None, completed=False)]
        obs = analyzer.build_observations(ALL_EVALS + incomplete)
        # 1 incomplete out of 6 total = 0.1667
        self.assertAlmostEqual(obs["incomplete_ratio"], round(1 / 6, 4), places=4)

    def test_window_duration_basis_text(self) -> None:
        obs = analyzer.build_observations(ALL_EVALS)
        self.assertIn("campaign_duration", obs["window_duration_basis"])

    def test_time_to_peak_not_available(self) -> None:
        obs = analyzer.build_observations(ALL_EVALS)
        self.assertFalse(obs["time_to_peak_available"])

    def test_time_to_trough_not_available(self) -> None:
        obs = analyzer.build_observations(ALL_EVALS)
        self.assertFalse(obs["time_to_trough_available"])

    def test_empty_evaluations_ratio_zero(self) -> None:
        obs = analyzer.build_observations([])
        self.assertEqual(obs["incomplete_ratio"], 0.0)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationTest(unittest.TestCase):
    def test_valid_distribution_passes(self) -> None:
        dist = analyzer.build_distribution_by_decision(ALL_EVALS)
        result = analyzer.validate_distribution(dist)
        self.assertEqual(result["distribution_validation_result"], "PASS")
        self.assertEqual(result["issue_count"], 0)

    def test_count_mismatch_fails(self) -> None:
        dist = analyzer.build_distribution_by_decision(ALL_EVALS)
        # Corrupt a count to trigger mismatch
        dist["REAL_WHALE_BACK"]["sample_count"] = 99
        result = analyzer.validate_distribution(dist)
        self.assertEqual(result["distribution_validation_result"], "FAIL")
        self.assertGreater(result["issue_count"], 0)

    def test_negative_mfe_minimum_fails(self) -> None:
        dist = analyzer.build_distribution_by_decision(ALL_EVALS)
        dist["REAL_WHALE_BACK"]["mfe"]["minimum"] = -0.1
        result = analyzer.validate_distribution(dist)
        self.assertEqual(result["distribution_validation_result"], "FAIL")

    def test_mean_out_of_range_fails(self) -> None:
        dist = analyzer.build_distribution_by_decision(ALL_EVALS)
        # Set mean above maximum to trigger out-of-range
        dist["REAL_WHALE_BACK"]["mfe"]["mean"] = 99.0
        result = analyzer.validate_distribution(dist)
        self.assertEqual(result["distribution_validation_result"], "FAIL")

    def test_overall_not_validated_separately(self) -> None:
        # overall key must not cause phantom issues
        dist = analyzer.build_distribution_by_decision([])
        result = analyzer.validate_distribution(dist)
        self.assertEqual(result["distribution_validation_result"], "PASS")


# ---------------------------------------------------------------------------
# Run analyzer (end-to-end with synthetic evaluations)
# ---------------------------------------------------------------------------

class RunAnalyzerTest(unittest.TestCase):
    def _run(self, evals=None):
        if evals is None:
            evals = ALL_EVALS
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = analyzer.run_mirror_outcome_distribution_analyzer(
                output_dir=base,
                source_evaluations=evals,
            )
            files = {
                "report": (base / "mirror_outcome_distribution_report.json"),
                "by_decision": (base / "mirror_outcome_distribution_by_decision.json"),
                "extremes": (base / "mirror_outcome_extreme_cases.json"),
                "statistics": (base / "mirror_outcome_distribution_statistics.json"),
            }
            contents = {k: json.loads(v.read_text(encoding="utf-8")) for k, v in files.items()}
            return result, contents

    def test_output_files_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            analyzer.run_mirror_outcome_distribution_analyzer(
                output_dir=base, source_evaluations=ALL_EVALS
            )
            self.assertTrue((base / "mirror_outcome_distribution_report.json").exists())
            self.assertTrue((base / "mirror_outcome_distribution_by_decision.json").exists())
            self.assertTrue((base / "mirror_outcome_extreme_cases.json").exists())
            self.assertTrue((base / "mirror_outcome_distribution_statistics.json").exists())

    def test_output_files_valid_json(self) -> None:
        _, contents = self._run()
        for name, data in contents.items():
            self.assertIsInstance(data, dict, f"{name} is not a dict")

    def test_distribution_validation_pass(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["distribution_validation_result"], "PASS")

    def test_sample_count_correct(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["sample_count"], len(ALL_EVALS))

    def test_completed_count_correct(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["completed_count"], len(ALL_EVALS))

    def test_incomplete_count_zero(self) -> None:
        result, _ = self._run()
        self.assertEqual(result["incomplete_count"], 0)

    def test_is_not_trade_command(self) -> None:
        result, _ = self._run()
        self.assertFalse(result["is_trade_command"])

    def test_by_decision_has_all_groups(self) -> None:
        _, contents = self._run()
        for decision in mirror_packet_contract.DECISION_ENUM:
            self.assertIn(decision, contents["by_decision"])
        self.assertIn("overall", contents["by_decision"])

    def test_extremes_file_has_all_keys(self) -> None:
        _, contents = self._run()
        for key in ("max_mfe", "max_mae", "max_return", "min_return",
                    "max_window_duration", "min_window_duration"):
            self.assertIn(key, contents["extremes"])

    def test_statistics_file_has_schema_version(self) -> None:
        _, contents = self._run()
        self.assertIn("statistics_schema_version", contents["statistics"])

    def test_run_with_incomplete_evals_notes_observation(self) -> None:
        incomplete = _eval("INCONCLUSIVE", None, None, None, None, completed=False)
        result, _ = self._run(ALL_EVALS + [incomplete])
        self.assertEqual(result["incomplete_count"], 1)
        self.assertIn("incomplete_warning", result["observations"])

    def test_label_placeholder_not_in_evaluations(self) -> None:
        # Evaluations from window_evaluator never carry label_placeholder
        for ev in ALL_EVALS:
            self.assertNotIn("label_placeholder", ev)

    def test_decision_groups_listed_in_report(self) -> None:
        result, _ = self._run()
        self.assertIn("decision_groups", result)
        self.assertIn("REAL_WHALE_BACK", result["decision_groups"])


if __name__ == "__main__":
    unittest.main()
