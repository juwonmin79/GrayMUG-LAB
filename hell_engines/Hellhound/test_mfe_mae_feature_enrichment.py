from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import mfe_mae_feature_enrichment as mfe_mae_feature_enrichment_module
    from mfe_mae_feature_enrichment import (
        build_feature_dataset,
        build_feature_dataset_file,
        build_feature_report,
        mae_bucket,
        mfe_bucket,
    )
except ImportError:
    from . import mfe_mae_feature_enrichment as mfe_mae_feature_enrichment_module
    from .mfe_mae_feature_enrichment import (
        build_feature_dataset,
        build_feature_dataset_file,
        build_feature_report,
        mae_bucket,
        mfe_bucket,
    )


class MfeMaeFeatureEnrichmentTest(unittest.TestCase):
    def test_buckets(self) -> None:
        self.assertEqual(mfe_bucket(-1), "LOSS")
        self.assertEqual(mfe_bucket(1), "LOW")
        self.assertEqual(mfe_bucket(3), "MID")
        self.assertEqual(mfe_bucket(7), "HIGH")
        self.assertEqual(mfe_bucket(12), "EXTREME")
        self.assertEqual(mae_bucket(0), "SAFE")
        self.assertEqual(mae_bucket(-3), "NORMAL")
        self.assertEqual(mae_bucket(-7), "RISK")
        self.assertEqual(mae_bucket(-12), "DANGER")

    def test_build_feature_dataset_joins_signal_features(self) -> None:
        enriched = build_feature_dataset([_mfe_row("signal-1", 7.0, -3.0)], {"signal-1": _signal()})

        row = enriched[0]
        self.assertEqual(row["mfe_bucket"], "HIGH")
        self.assertEqual(row["mae_bucket"], "NORMAL")
        self.assertEqual(row["signal_hour"], 9)
        self.assertEqual(row["signal_day_of_week"], 2)
        self.assertEqual(row["rsi_15m"], 62.5)
        self.assertEqual(row["volume_ratio_ma5"], 1.8)
        self.assertEqual(row["btc_weather"], 0.4)
        self.assertTrue(row["feature_join_success"])
        self.assertFalse(row["is_trade_command"])

    def test_report_compares_high_mfe_vs_loss(self) -> None:
        rows = build_feature_dataset(
            [_mfe_row("signal-1", 7.0, -3.0), _mfe_row("signal-2", -1.0, -8.0)],
            {"signal-1": _signal(), "signal-2": {**_signal(), "id": "signal-2", "source_time": "2026-06-24T10:00:00+00:00"}},
        )
        report = build_feature_report(rows)

        self.assertEqual(report["mfe_bucket_counts"]["HIGH"], 1)
        self.assertEqual(report["mfe_bucket_counts"]["LOSS"], 1)
        self.assertEqual(report["feature_coverage"]["signal_hour"]["present_count"], 2)
        self.assertEqual(report["high_mfe_vs_loss"]["high_group"]["count"], 1)

    def test_file_builder_writes_dataset_and_report_without_supabase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            input_path = base / "mfe.jsonl"
            output_path = base / "feature.jsonl"
            report_path = base / "report.json"
            input_path.write_text(json.dumps(_mfe_row("missing", 0.0, -1.0)) + "\n", encoding="utf-8")
            with patch.object(mfe_mae_feature_enrichment_module, "load_shadow_signals_for_rows", return_value={}):
                result = build_feature_dataset_file(input_path=input_path, output_path=output_path, report_path=report_path)
            output_exists = output_path.exists()
            report_exists = report_path.exists()

        self.assertEqual(result["record_count"], 1)
        self.assertTrue(output_exists)
        self.assertTrue(report_exists)


def _mfe_row(signal_id: str, mfe: float, mae: float) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "shadow_signal_id": signal_id,
        "structure_type": "SLOW_CREEP",
        "mfe_pct": mfe,
        "mae_pct": mae,
        "time_to_peak_hours": 4.0,
        "time_to_stop_hours": None,
        "is_trade_command": False,
    }


def _signal() -> dict[str, object]:
    return {
        "id": "signal-1",
        "source_time": "2026-06-24T09:15:00+00:00",
        "pattern": "SLOW_CREEP",
        "shadow_action": "WATCH",
        "payload": {"rsi_15m": 62.5, "volume_ratio_ma5": 1.8},
        "target_feed": {"btc_weather": 0.4},
    }


if __name__ == "__main__":
    unittest.main()
