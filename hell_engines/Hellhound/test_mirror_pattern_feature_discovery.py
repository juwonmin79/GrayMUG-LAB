from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from mirror_pattern_feature_discovery import (
        build_sequence_report,
        build_temporal_report,
        run_mirror_pattern_feature_discovery,
        segment_rows,
        slope,
    )
except ImportError:
    from .mirror_pattern_feature_discovery import (
        build_sequence_report,
        build_temporal_report,
        run_mirror_pattern_feature_discovery,
        segment_rows,
        slope,
    )


class MirrorPatternFeatureDiscoveryTest(unittest.TestCase):
    def test_slope_uses_recent_window(self) -> None:
        self.assertEqual(slope([1.0, 2.0, 4.0, 8.0], 2), 3.0)

    def test_temporal_and_sequence_reports(self) -> None:
        rows = _rows()
        target = {
            "accumulation_start": rows[0]["timestamp"],
            "ignition_time": rows[4]["timestamp"],
            "local_peak_time": rows[-1]["timestamp"],
        }
        segmented = segment_rows(rows, target)
        temporal = build_temporal_report(segmented, target)
        sequence = build_sequence_report(segmented, target)

        self.assertEqual(temporal["row_counts"]["pre_ignition"], 4)
        self.assertIn("hellhound_score", temporal["features"])
        self.assertEqual(sequence["sequence_features"][0], "volume_ratio_ma20")
        self.assertFalse(sequence["is_trade_command"])

    def test_run_writes_outputs(self) -> None:
        rows = _rows()
        report = {
            "target": {
                "accumulation_start": rows[0]["timestamp"],
                "ignition_time": rows[4]["timestamp"],
                "local_peak_time": rows[-1]["timestamp"],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            dataset = base / "btc_replay_dataset.jsonl"
            replay_report = base / "btc_replay_report.json"
            dataset.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            replay_report.write_text(json.dumps(report), encoding="utf-8")
            result = run_mirror_pattern_feature_discovery(
                replay_dataset_path=dataset,
                replay_report_path=replay_report,
                output_dir=base,
            )

            self.assertEqual(result["row_count"], len(rows))
            self.assertTrue((base / "mirror_pattern_feature_candidates.json").exists())
            self.assertTrue((base / "mirror_pattern_sequence_report.json").exists())
            self.assertTrue((base / "pre_ignition_temporal_report.json").exists())
            self.assertTrue((base / "feature_transition_matrix.json").exists())


def _rows() -> list[dict[str, object]]:
    rows = []
    scores = [0.2, 0.2, 0.25, 0.3, 0.35, 0.4]
    rsi = [40, 40, 40, 41, 43, 45]
    volume = [1.0, 1.2, 1.4, 1.5, 1.6, 1.7]
    for index in range(6):
        rows.append(
            {
                "timestamp": f"2026-01-01T00:{index * 15:02d}:00+00:00",
                "hellhound_score": scores[index],
                "rsi_15m": rsi[index],
                "volume_ratio_ma20": volume[index],
                "mfe_pct": 3.0 if index < 3 else 0.0,
                "is_trade_command": False,
            }
        )
    return rows


if __name__ == "__main__":
    unittest.main()
