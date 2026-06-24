from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import feature_lineage_audit as feature_lineage_audit_module
except ImportError:
    from . import feature_lineage_audit as feature_lineage_audit_module

audit_feature_lineage = feature_lineage_audit_module.audit_feature_lineage


class FeatureLineageAuditTest(unittest.TestCase):
    def test_audit_reports_complete_feature_lineage(self) -> None:
        signal_id = "33333333-3333-4333-8333-000000000001"
        signals = [
            {
                "id": signal_id,
                "symbol": "BELUSDT",
                "created_at": "2026-06-24T00:00:00+00:00",
                "payload": {
                    "hellhound_score": 0.42,
                    "decision_source": "decision_api",
                    "btc_weather": 0.0,
                    "volume_ratio_ma5": 1.2,
                    "volume_ratio_ma20": 1.1,
                    "rsi_15m": 61.0,
                    "macd_hist_15m": 0.04,
                },
            }
        ]
        outcomes = {
            signal_id: [
                {"shadow_signal_id": signal_id, "evaluation_window": "1h", "result": "SUCCESS"}
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            mfe_path = Path(directory) / "mfe.jsonl"
            feature_path = Path(directory) / "features.jsonl"
            mfe_path.write_text(
                _jsonl(
                    {
                        "signal_id": signal_id,
                        "shadow_signal_id": signal_id,
                        "mfe_pct": 6.0,
                        "mae_pct": -1.0,
                        "is_trade_command": False,
                    }
                ),
                encoding="utf-8",
            )
            feature_path.write_text(
                _jsonl(
                    {
                        "signal_id": signal_id,
                        "shadow_signal_id": signal_id,
                        "mfe_pct": 6.0,
                        "mae_pct": -1.0,
                        "mfe_bucket": "HIGH",
                        "hellhound_score": 0.42,
                        "decision_source": "decision_api",
                        "btc_weather": 0.0,
                        "volume_ratio_ma5": 1.2,
                        "volume_ratio_ma20": 1.1,
                        "rsi_15m": 61.0,
                        "macd_hist_15m": 0.04,
                        "is_trade_command": False,
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                f"{feature_lineage_audit_module.__name__}._load_recent_feature_signals",
                return_value=signals,
            ), patch(
                f"{feature_lineage_audit_module.__name__}._load_outcomes",
                return_value=outcomes,
            ):
                report = audit_feature_lineage(limit=1, mfe_path=mfe_path, feature_path=feature_path)

        self.assertEqual(report["signal_count"], 1)
        self.assertEqual(report["complete_lineage_count"], 1)
        self.assertEqual(report["lineage_coverage_pct"], 100.0)
        self.assertEqual(report["loss_audit"]["mfe_to_feature_dataset_loss_pct"], 0.0)
        self.assertEqual(report["feature_coverage"]["hellhound_score"]["coverage_pct"], 100.0)
        self.assertEqual(report["high_mfe_vs_loss"]["high_extreme"]["average_score"], 0.42)


def _jsonl(row: dict) -> str:
    import json

    return json.dumps(row, sort_keys=True) + "\n"


if __name__ == "__main__":
    unittest.main()
