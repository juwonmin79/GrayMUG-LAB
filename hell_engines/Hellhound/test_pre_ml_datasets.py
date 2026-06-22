from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from detection_delay_report import summarize_detection_delays, build_detection_delay_report
    from production_feedback_dataset import build_feedback_dataset, create_feedback_record
    from structure_outcome_ranking import aggregate_structure_outcomes, build_structure_stats
except ImportError:
    from .detection_delay_report import summarize_detection_delays, build_detection_delay_report
    from .production_feedback_dataset import build_feedback_dataset, create_feedback_record
    from .structure_outcome_ranking import aggregate_structure_outcomes, build_structure_stats


class PreMlDatasetsTest(unittest.TestCase):
    def test_structure_outcome_ranking_tracks_required_structures(self) -> None:
        result = aggregate_structure_outcomes(
            [
                _mfe_row("BEL", "VALIDATED", 20.0, -4.0, 8.0),
                _mfe_row("BEL", "REJECTED", 10.0, -6.0, 12.0),
                _mfe_row("ACT", "VALIDATED", 3.0, -8.0, 2.0),
            ]
        )

        self.assertEqual(result["structures"]["BEL"]["count"], 2)
        self.assertEqual(result["structures"]["BEL"]["validated_ratio"], 0.5)
        self.assertEqual(result["structures"]["BEL"]["average_mfe"], 15.0)
        self.assertEqual(result["structures"]["ACT"]["average_mae"], -8.0)
        self.assertIsNone(result["structures"]["ACE"]["validated_ratio"])
        self.assertFalse(result["is_trade_command"])

    def test_detection_delay_summary(self) -> None:
        result = summarize_detection_delays(
            [
                _lead_line_row("lead-1", "2026-06-23T00:00:00+00:00", 24),
                _lead_line_row("lead-2", "2026-06-23T00:00:00+00:00", 48),
            ]
        )

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["average_delay_hours"], 36.0)
        self.assertEqual(result["median_delay_hours"], 36.0)
        self.assertEqual(result["min_delay_hours"], 24.0)
        self.assertEqual(result["max_delay_hours"], 48.0)
        self.assertFalse(result["is_trade_command"])

    def test_feedback_record_normalizes_production_shadow_row(self) -> None:
        record = create_feedback_record(
            {
                "event_id": "event-1",
                "event_time": "2026-06-23T00:00:00+00:00",
                "payload": {
                    "symbol": "btcusdt",
                    "hellhound_score": 0.42,
                    "promotion_status": "WATCH",
                    "setup_type": "MET",
                },
            }
        )

        self.assertEqual(record["symbol"], "BTCUSDT")
        self.assertEqual(record["hellhound_score"], 0.42)
        self.assertEqual(record["structure_type"], "MET")
        self.assertFalse(record["is_trade_command"])

    def test_builders_write_expected_jsonl_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mfe_path = base / "mfe.jsonl"
            lead_path = base / "lead.jsonl"
            shadow_path = base / "production_hellhound_shadow.jsonl"
            stats_path = base / "stats.jsonl"
            delay_path = base / "delay.jsonl"
            feedback_path = base / "feedback.jsonl"
            mfe_path.write_text(json.dumps(_mfe_row("BEL", "VALIDATED", 20.0, -4.0, 8.0)) + "\n", encoding="utf-8")
            lead_path.write_text(json.dumps(_lead_line_row("lead-1", "2026-06-23T00:00:00+00:00", 24)) + "\n", encoding="utf-8")
            shadow_path.write_text(
                json.dumps({"symbol": "BTCUSDT", "event_id": "event-1", "hellhound_score": 0.5}) + "\n",
                encoding="utf-8",
            )

            stats = build_structure_stats(input_path=mfe_path, output_path=stats_path, append=True)
            delay = build_detection_delay_report(input_path=lead_path, output_path=delay_path, append=True)
            feedback = build_feedback_dataset(input_path=shadow_path, output_path=feedback_path, append=True)

        self.assertEqual(stats["structure_count"], 5)
        self.assertEqual(delay["record_count"], 1)
        self.assertEqual(feedback["written_count"], 1)


def _mfe_row(structure: str, status: str, mfe: float, mae: float, time_to_peak: float) -> dict[str, object]:
    return {
        "structure_type": structure,
        "validation_status": status,
        "mfe_pct": mfe,
        "mae_pct": mae,
        "time_to_peak_hours": time_to_peak,
        "is_trade_command": False,
    }


def _lead_line_row(lead_line_id: str, outcome_time: str, hours_before_outcome: int) -> dict[str, object]:
    return {
        "lead_line_id": lead_line_id,
        "symbol": "BTCUSDT",
        "outcome_time": outcome_time,
        "hours_before_outcome": hours_before_outcome,
        "promotion_status": "WATCH",
        "structure_type": "MET",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
