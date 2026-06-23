from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from signal_lineage_audit import audit_lineage_files, audit_signal_lineage, lineage_link_table
except ImportError:
    from .signal_lineage_audit import audit_lineage_files, audit_signal_lineage, lineage_link_table


class SignalLineageAuditTest(unittest.TestCase):
    def test_audit_signal_lineage_reports_complete_and_broken_links(self) -> None:
        report = audit_signal_lineage(
            signal_rows=[
                {"signal_id": "signal-1", "symbol": "BELUSDT", "mtf_snapshot": {"timeframes": {}}},
                {"signal_id": "signal-2", "symbol": "ACTUSDT", "mtf_snapshot": {"timeframes": {}}},
                {"symbol": "NOIDUSDT"},
            ],
            wave_rows=[
                {
                    "signal_id": "signal-1",
                    "snapshot_t0": {},
                    "outcome_mfe_24h": 12.0,
                    "outcome_mae_24h": -3.0,
                    "outcome_time_to_peak_24h": 6.0,
                },
                {"signal_id": "signal-2", "snapshot_t0": {}},
            ],
            outcome_rows=[{"shadow_signal_id": "signal-1", "result": "SUCCESS"}],
            mfe_mae_rows=[
                {
                    "signal_id": "signal-1",
                    "mfe_pct": 12.0,
                    "mae_pct": -3.0,
                    "time_to_peak_hours": 6.0,
                    "time_to_stop_hours": 2.0,
                }
            ],
        )

        self.assertEqual(report["signal_count"], 3)
        self.assertEqual(report["complete_count"], 1)
        self.assertEqual(report["broken_count"], 2)
        self.assertEqual(report["lineage_coverage_pct"], 33.33)
        self.assertFalse(report["is_trade_command"])

    def test_missing_signal_file_returns_zero_coverage_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = audit_lineage_files(signal_path=Path(directory) / "missing.jsonl")

        self.assertFalse(report["signal_path_exists"])
        self.assertEqual(report["signal_count"], 0)
        self.assertEqual(report["lineage_coverage_pct"], 0.0)

    def test_file_audit_uses_recent_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            signal_path = base / "production_hellhound_shadow.jsonl"
            wave_path = base / "wave.jsonl"
            outcome_path = base / "outcome.jsonl"
            mfe_path = base / "mfe.jsonl"
            signal_rows = [
                {"signal_id": "old", "symbol": "OLDUSDT", "mtf_snapshot": {}},
                {"signal_id": "signal-1", "symbol": "BELUSDT", "mtf_snapshot": {}},
            ]
            signal_path.write_text("\n".join(json.dumps(row) for row in signal_rows), encoding="utf-8")
            wave_path.write_text(json.dumps({"signal_id": "signal-1", "snapshot_t0": {}, "outcome_mfe_24h": 1}) + "\n", encoding="utf-8")
            outcome_path.write_text(json.dumps({"shadow_signal_id": "signal-1"}) + "\n", encoding="utf-8")
            mfe_path.write_text(
                json.dumps(
                    {
                        "signal_id": "signal-1",
                        "mfe_pct": 1,
                        "mae_pct": -1,
                        "time_to_peak_hours": 1,
                        "time_to_stop_hours": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = audit_lineage_files(
                signal_path=signal_path,
                wave_path=wave_path,
                outcome_path=outcome_path,
                mfe_mae_path=mfe_path,
                limit=1,
            )

        self.assertEqual(report["signal_count"], 1)
        self.assertEqual(report["complete_count"], 1)
        self.assertEqual(report["lineage_coverage_pct"], 100.0)

    def test_lineage_link_table_documents_required_fields(self) -> None:
        rows = lineage_link_table()

        self.assertEqual(rows[0]["stage"], "Signal -> Snapshot")
        self.assertIn("signal_id", rows[0]["field"])


if __name__ == "__main__":
    unittest.main()
