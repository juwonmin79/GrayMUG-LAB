from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_live_evidence_accumulator as accumulator
except ImportError:
    from . import mirror_live_evidence_accumulator as accumulator


class MirrorLiveEvidenceAccumulatorTest(unittest.TestCase):
    def test_decision_reason_and_processing_stats(self) -> None:
        rows = [_row("BTCUSDT", "REAL_WHALE_BACK", 0.9, ["RECOVERY_SUPPORT"], 1.0), _row("ETHUSDT", "INCONCLUSIVE", 0.35, ["CONFLICTING_EVIDENCE"], 3.0)]

        decisions = accumulator.build_decision_distribution(rows)
        reasons = accumulator.build_reason_distribution(rows)
        processing = accumulator.build_processing_stats(rows)

        self.assertEqual(decisions["counts"]["REAL_WHALE_BACK"], 1)
        self.assertEqual(decisions["counts"]["INCONCLUSIVE"], 1)
        self.assertEqual(decisions["rates"]["INCONCLUSIVE"], 0.5)
        self.assertEqual(decisions["inconclusive_drift_check"]["level"], "WATCH")
        self.assertEqual(reasons["reason_counts"]["RECOVERY_SUPPORT"], 1)
        self.assertEqual(processing["average_processing_time_ms"], 2.0)
        self.assertEqual(processing["p90_processing_time_ms"], 2.8)
        self.assertEqual(processing["max_processing_time_ms"], 3.0)

    def test_schema_stability_passes_valid_shadow_rows(self) -> None:
        rows = [_row("BTCUSDT", "REAL_WHALE_BACK", 0.9, ["RECOVERY_SUPPORT"], 1.0)]

        result = accumulator.build_schema_stability(rows, {"RECOVERY_SUPPORT"})

        self.assertEqual(result["schema_stability"], "PASS")
        self.assertEqual(result["missing_field"], {})
        self.assertEqual(result["invalid_confidence"], 0)
        self.assertEqual(result["invalid_reason_code"], {})

    def test_schema_stability_rejects_invalid_rows(self) -> None:
        row = _row("BTCUSDT", "REAL_WHALE_BACK", 0.9, ["RECOVERY_SUPPORT"], 1.0)
        row.pop("timestamp")
        row["mirror_decision"] = "UNKNOWN"
        row["confidence"] = 2.0
        row["reason_code"] = ["UNKNOWN_REASON"]
        row["unexpected"] = True

        result = accumulator.build_schema_stability([row], {"RECOVERY_SUPPORT"})

        self.assertEqual(result["schema_stability"], "FAIL")
        self.assertEqual(result["missing_field"]["timestamp"], 1)
        self.assertEqual(result["invalid_enum"]["UNKNOWN"], 1)
        self.assertEqual(result["invalid_confidence"], 1)
        self.assertEqual(result["invalid_reason_code"]["UNKNOWN_REASON"], 1)
        self.assertEqual(result["unknown_field"]["unexpected"], 1)

    def test_replay_compatibility_checks_append_only_shadow_rows(self) -> None:
        valid = _row("BTCUSDT", "REAL_WHALE_BACK", 0.9, ["RECOVERY_SUPPORT"], 1.0)
        invalid = _row("ETHUSDT", "INCONCLUSIVE", 0.35, ["CONFLICTING_EVIDENCE"], 2.0)
        invalid["is_trade_command"] = True

        result = accumulator.build_replay_compatibility([valid, invalid])

        self.assertEqual(result["replay_compatibility"], "FAIL")
        self.assertEqual(result["incompatible_count"], 1)
        self.assertFalse(result["db_created"])
        self.assertFalse(result["supabase_connected"])

    def test_run_writes_live_evidence_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            log_path = base / "mirror_shadow_log.jsonl"
            rows = [_row("BTCUSDT", "REAL_WHALE_BACK", 0.9, ["RECOVERY_SUPPORT"], 1.0)]
            log_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

            result = accumulator.run_mirror_live_evidence_accumulation(output_dir=base, shadow_log_path=log_path)

            self.assertEqual(result["packet_count"], 1)
            self.assertEqual(result["schema_stability"], "PASS")
            self.assertEqual(result["replay_compatibility"], "PASS")
            self.assertEqual(result["json_validation"], "PASS")
            self.assertTrue((base / "mirror_live_evidence_report.json").exists())
            self.assertTrue((base / "mirror_live_decision_distribution.json").exists())
            self.assertTrue((base / "mirror_live_reason_distribution.json").exists())
            self.assertTrue((base / "mirror_live_schema_stability.json").exists())
            self.assertTrue((base / "mirror_live_replay_compatibility.json").exists())
            self.assertTrue((base / "mirror_live_processing_stats.json").exists())


def _row(symbol: str, decision: str, confidence: float, reasons: list[str], processing_time_ms: float) -> dict:
    mirror_packet = {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-{symbol}",
        "campaign_id": f"campaign-{symbol}",
        "signal_id": f"signal-{symbol}",
        "symbol": symbol,
        "mirror_decision": decision,
        "confidence": confidence,
        "reason_code": list(reasons),
        "supporting_features": {},
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }
    return {
        "mirror_shadow_schema_version": "mirror_shadow_adapter_v1",
        "timestamp": "2026-06-25T00:00:00+00:00",
        "campaign_id": f"campaign-{symbol}",
        "signal_id": f"signal-{symbol}",
        "symbol": symbol,
        "mirror_pattern_id": f"mirror-{symbol}",
        "mirror_decision": decision,
        "decision": decision,
        "confidence": confidence,
        "reason_code": list(reasons),
        "validation_state": "ACCEPT",
        "processing_time_ms": processing_time_ms,
        "mirror_packet": mirror_packet,
        "audit": {
            "timestamp": "2026-06-25T00:00:00+00:00",
            "campaign_id": f"campaign-{symbol}",
            "mirror_pattern_id": f"mirror-{symbol}",
            "decision": decision,
            "confidence": confidence,
            "reason_code": list(reasons),
            "processing_time_ms": processing_time_ms,
            "validation_state": "ACCEPT",
            "is_trade_command": False,
        },
        "telegram": None,
        "telegram_enabled": False,
        "shadow_mode": True,
        "replay_storage_compatible": True,
        "is_trade_command": False,
        "forbidden_actions_confirmed": [],
        "mirror_packet_validation": "PASS",
        "validation_issues": [],
    }


if __name__ == "__main__":
    unittest.main()
