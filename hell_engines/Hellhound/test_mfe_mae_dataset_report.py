from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from mfe_mae_dataset_report import build_mfe_mae_report, build_mfe_mae_report_file, load_mfe_mae_dataset
except ImportError:
    from .mfe_mae_dataset_report import build_mfe_mae_report, build_mfe_mae_report_file, load_mfe_mae_dataset


class MfeMaeDatasetReportTest(unittest.TestCase):
    def test_report_calculates_overall_quantiles(self) -> None:
        report = build_mfe_mae_report(
            [
                _row("BEL", 10.0, -4.0, 1.0, None),
                _row("BEL", 20.0, -8.0, 4.0, 2.0),
                _row("ACT", 30.0, -2.0, 24.0, 4.0),
            ]
        )

        self.assertEqual(report["record_count"], 3)
        self.assertEqual(report["overall"]["mfe"]["average"], 20.0)
        self.assertEqual(report["overall"]["mfe"]["median"], 20.0)
        self.assertEqual(report["profit_zones"]["p75"], 25.0)
        self.assertEqual(report["loss_zones"]["p50"], -4.0)
        self.assertEqual(report["peak_time"]["p90"], 20.0)
        self.assertEqual(report["stop_time"]["count"], 2)
        self.assertEqual(report["stop_time"]["average"], 3.0)
        self.assertFalse(report["is_trade_command"])

    def test_report_tracks_required_structures_even_when_empty(self) -> None:
        report = build_mfe_mae_report([_row("BEL", 10.0, -4.0, 1.0, None)])

        self.assertEqual(report["by_structure"]["BEL"]["count"], 1)
        self.assertEqual(report["by_structure"]["ACT"]["count"], 0)
        self.assertEqual(report["by_structure"]["NIGHT"]["count"], 0)

    def test_file_builder_writes_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "mfe.jsonl"
            output_path = Path(directory) / "report.json"
            input_path.write_text(json.dumps(_row("MET", 5.0, -1.0, 4.0, None)) + "\n", encoding="utf-8")

            result = build_mfe_mae_report_file(input_path=input_path, output_path=output_path)
            loaded = load_mfe_mae_dataset(input_path)
            exists = output_path.exists()

        self.assertEqual(result["record_count"], 1)
        self.assertEqual(len(loaded), 1)
        self.assertTrue(exists)


def _row(structure: str, mfe: float, mae: float, peak: float, stop: float | None) -> dict[str, object]:
    return {
        "structure_type": structure,
        "promotion_status": "WATCH",
        "signal_hour": 9,
        "mfe_pct": mfe,
        "mae_pct": mae,
        "time_to_peak_hours": peak,
        "time_to_stop_hours": stop,
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
