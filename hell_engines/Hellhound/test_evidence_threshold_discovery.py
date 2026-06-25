from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import evidence_threshold_discovery as discovery
except ImportError:
    from . import evidence_threshold_discovery as discovery


class EvidenceThresholdDiscoveryTest(unittest.TestCase):
    def test_percentile_uses_linear_interpolation(self) -> None:
        self.assertEqual(discovery.percentile([1.0, 2.0, 3.0, 4.0], 50), 2.5)
        self.assertEqual(discovery.percentile([1.0, 2.0, 3.0, 4.0], 25), 1.75)

    def test_classification_metrics_support_both_directions(self) -> None:
        values = [(0.9, "success"), (0.8, "success"), (0.2, "failure"), (0.1, "failure")]

        metrics = discovery.classification_metrics(values, 0.5, "success_higher")

        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1"], 1.0)
        self.assertEqual(metrics["balanced_accuracy"], 1.0)

    def test_run_writes_threshold_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            validation = base / "mirror_candidate_validation.json"
            statistics = base / "mirror_candidate_statistics.json"
            ranking = base / "mirror_discriminator_ranking.json"
            expansion = base / "replay_expansion_report.json"
            contrast = base / "mirror_contrast_dataset.json"
            validation.write_text(json.dumps({"samples": _samples()}), encoding="utf-8")
            statistics.write_text(json.dumps({"candidates": []}), encoding="utf-8")
            ranking.write_text(json.dumps({"ranking": []}), encoding="utf-8")
            expansion.write_text(json.dumps({"replay_count": 20}), encoding="utf-8")
            contrast.write_text(json.dumps({"cases": []}), encoding="utf-8")

            result = discovery.run_evidence_threshold_discovery(
                output_dir=base,
                validation_path=validation,
                statistics_path=statistics,
                ranking_path=ranking,
                expansion_report_path=expansion,
                contrast_dataset_path=contrast,
            )

            self.assertEqual(result["candidate_count"], 3)
            self.assertEqual(set(result["verdicts"]), set(discovery.CANDIDATES))
            self.assertTrue((base / "evidence_threshold_candidates.json").exists())
            self.assertTrue((base / "candidate_distribution_report.json").exists())
            self.assertTrue((base / "candidate_threshold_scan.json").exists())
            self.assertTrue((base / "candidate_best_threshold.json").exists())
            self.assertTrue((base / "candidate_threshold_confidence.json").exists())


def _samples() -> list[dict[str, object]]:
    rows = []
    for index in range(10):
        rows.append(
            {
                "case_type": "success",
                "candidate_metrics": {
                    "score_slope": {"primary_value": 0.7 + index * 0.01},
                    "rsi_persistence": {"primary_value": 7 + index % 2},
                    "volume_delay": {"primary_value": 1},
                },
            }
        )
        rows.append(
            {
                "case_type": "failure",
                "candidate_metrics": {
                    "score_slope": {"primary_value": 0.2 + index * 0.01},
                    "rsi_persistence": {"primary_value": 3 + index % 2},
                    "volume_delay": {"primary_value": -1},
                },
            }
        )
    return rows


if __name__ == "__main__":
    unittest.main()
