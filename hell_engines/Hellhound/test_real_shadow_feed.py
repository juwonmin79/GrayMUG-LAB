from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional

try:
    from real_shadow_feed import (
        build_real_shadow_decision,
        detect_daily_open_clusters,
        join_outcomes,
        load_recent_signals,
        mock_signal_rows,
        process_recent_signals,
        write_shadow_feed_log,
    )
except ImportError:
    from .real_shadow_feed import (
        build_real_shadow_decision,
        detect_daily_open_clusters,
        join_outcomes,
        load_recent_signals,
        mock_signal_rows,
        process_recent_signals,
        write_shadow_feed_log,
    )


class RealShadowFeedTest(unittest.TestCase):
    def test_load_recent_signals_missing_env_is_fail_safe_skip(self) -> None:
        old_url = os.environ.pop("SUPABASE_URL", None)
        old_service = os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        old_anon = os.environ.pop("SUPABASE_ANON_KEY", None)
        try:
            result = load_recent_signals(limit=3)
        finally:
            _restore_env("SUPABASE_URL", old_url)
            _restore_env("SUPABASE_SERVICE_ROLE_KEY", old_service)
            _restore_env("SUPABASE_ANON_KEY", old_anon)

        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["signals"], [])

    def test_build_real_shadow_decision_from_mock_row(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        signal = mock_signal_rows(1)[0]

        decision = build_real_shadow_decision(signal)

        self.assertEqual(decision["signal_id"], signal["id"])
        self.assertEqual(decision["shadow_signal_id"], signal["id"])
        self.assertEqual(decision["symbol"], signal["symbol"])
        self.assertEqual(decision["entry_bias"], "neutral")
        self.assertFalse(decision["is_trade_command"])
        self.assertIn("promotion_status", decision)

    def test_build_real_shadow_decision_preserves_signal_features(self) -> None:
        signal = {
            "id": "signal-1",
            "symbol": "BELUSDT",
            "source_time": "2026-01-01T00:00:00+00:00",
            "payload": {
                "btc_weather": 0.2,
                "volume_ratio_ma5": 1.9,
                "volume_ratio_ma20": 1.3,
                "rsi_15m": 63.0,
                "macd_hist_15m": 0.05,
            },
        }

        decision = build_real_shadow_decision(signal, decision_enabled=False)

        self.assertEqual(decision["btc_weather"], 0.2)
        self.assertEqual(decision["volume_ratio_ma5"], 1.9)
        self.assertEqual(decision["volume_ratio_ma20"], 1.3)
        self.assertEqual(decision["rsi_15m"], 63.0)
        self.assertEqual(decision["macd_hist_15m"], 0.05)

    def test_build_real_shadow_decision_generates_signal_id_when_missing(self) -> None:
        signal = {
            "symbol": "BELUSDT",
            "source_time": "2026-01-01T00:00:00+00:00",
            "pattern": "NO_ID_FIXTURE",
        }

        decision = build_real_shadow_decision(signal)

        self.assertTrue(decision["signal_id"])
        self.assertEqual(decision["shadow_signal_id"], decision["signal_id"])
        self.assertFalse(decision["is_trade_command"])

    def test_outcome_join_attaches_available_windows(self) -> None:
        signal = mock_signal_rows(1)[0]
        outcomes = [
            {
                "shadow_signal_id": signal["id"],
                "symbol": signal["symbol"],
                "evaluation_window": "1h",
                "result": "SUCCESS",
            },
            {
                "shadow_signal_id": signal["id"],
                "symbol": signal["symbol"],
                "evaluation_window": "24h",
                "result": "FAIL",
            },
        ]

        joined = join_outcomes(signal, outcomes)

        self.assertEqual(joined["actual_1h_outcome"], "SUCCESS")
        self.assertIsNone(joined["actual_4h_outcome"])
        self.assertEqual(joined["actual_24h_outcome"], "FAIL")

    def test_process_recent_signals_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "hellhound_shadow_decisions.jsonl"
            result = process_recent_signals(
                mock_signal_rows(2),
                output_path=output_path,
                dry_run=True,
            )

            self.assertFalse(output_path.exists())

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["decision_count"], 2)
        self.assertFalse(result["is_trade_command"])

    def test_write_shadow_feed_log_jsonl(self) -> None:
        decisions = [
            {
                "symbol": "BELUSDT",
                "signal_time": "2026-01-01T00:00:00+00:00",
                "event_id": "event-1",
                "hellhound_score": 0.6,
                "promotion_status": "PROMOTE",
                "structure_type": "ACCUMULATION_BASE",
                "setup_type": "BEL",
                "distribution_risk": 0.2,
                "reasons": ["test"],
                "is_trade_command": False,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "hellhound_shadow_decisions.jsonl"
            result = write_shadow_feed_log(decisions, output_path=output_path)
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["written_count"], 1)
        self.assertIn("signal_id", rows[0])
        self.assertEqual(rows[0]["symbol"], "BELUSDT")
        self.assertFalse(rows[0]["is_trade_command"])

    def test_daily_open_alert_cluster_detection(self) -> None:
        signals = [
            _cluster_signal("BELUSDT", "2026-01-01T23:50:00+00:00", 2.1),
            _cluster_signal("ACTUSDT", "2026-01-02T00:00:00+00:00", 1.7),
            _cluster_signal("METUSDT", "2026-01-02T00:14:00+00:00", 2.6),
            _cluster_signal("LATEUSDT", "2026-01-02T00:20:00+00:00", 4.0),
        ]

        clusters = detect_daily_open_clusters(signals)

        self.assertEqual(len(clusters), 1)
        self.assertTrue(clusters[0]["daily_open_cluster"])
        self.assertTrue(clusters[0]["detection_delay_candidate"])
        self.assertEqual(clusters[0]["alert_count"], 3)
        self.assertEqual(clusters[0]["symbols"], ["ACTUSDT", "BELUSDT", "METUSDT"])
        self.assertEqual(clusters[0]["avg_vol_ratio"], 2.133333)
        self.assertEqual(clusters[0]["max_vol_ratio"], 2.6)

    def test_process_recent_signals_writes_cluster_to_shadow_log(self) -> None:
        signals = [
            _cluster_signal("BELUSDT", "2026-01-02T00:00:00+00:00", 2.0),
            _cluster_signal("ACTUSDT", "2026-01-02T00:10:00+00:00", 3.0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "hellhound_shadow_decisions.jsonl"
            result = process_recent_signals(
                signals,
                output_path=output_path,
                dry_run=False,
            )
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        cluster_rows = [row for row in rows if row.get("record_type") == "daily_open_alert_cluster"]
        self.assertEqual(result["cluster_count"], 1)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(cluster_rows), 1)
        self.assertEqual(cluster_rows[0]["alert_count"], 2)
        self.assertFalse(cluster_rows[0]["is_trade_command"])


def _restore_env(name: str, value: Optional[str]) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _cluster_signal(symbol: str, source_time: str, vol_ratio: float) -> dict[str, object]:
    return {
        "id": f"44444444-4444-4444-8444-{symbol[:3].lower():0<12}",
        "symbol": symbol,
        "source_time": source_time,
        "hypothesis": {"name": "daily-open-cluster-test"},
        "shadow_action": "WATCH",
        "pattern": "DAILY_OPEN_ALERT",
        "vol_ratio": vol_ratio,
    }


if __name__ == "__main__":
    unittest.main()
