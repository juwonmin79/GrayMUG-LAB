from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_packet_contract as contract
except ImportError:
    from . import mirror_packet_contract as contract


class MirrorPacketContractTest(unittest.TestCase):
    def test_valid_packet_passes_frozen_contract(self) -> None:
        schema = contract.build_schema()
        result = contract.validate_packet(_packet(), schema=schema, reason_registry={"RECOVERY_SUPPORT"})

        self.assertTrue(result["valid"])
        self.assertEqual(result["validation_result"], "PASS")
        self.assertEqual(result["issues"], [])

    def test_required_field_validation_detects_missing_field(self) -> None:
        packet = _packet()
        packet.pop("campaign_id")

        result = contract.validate_packet(packet, schema=contract.build_schema(), reason_registry={"RECOVERY_SUPPORT"})

        self.assertFalse(result["valid"])
        self.assertEqual(result["validation_result"], "REJECT")
        self.assertIn({"code": "missing_field", "field": "campaign_id", "severity": "REJECT"}, result["issues"])

    def test_enum_numeric_timestamp_null_and_reason_validation(self) -> None:
        packet = _packet()
        packet["mirror_decision"] = "UNKNOWN"
        packet["confidence"] = 1.1234567
        packet["created_at"] = "not-a-date"
        packet["symbol"] = None
        packet["reason_code"] = ["UNKNOWN_REASON"]

        result = contract.validate_packet(packet, schema=contract.build_schema(), reason_registry={"RECOVERY_SUPPORT"})
        codes = {issue["code"] for issue in result["issues"]}

        self.assertFalse(result["valid"])
        self.assertIn("invalid_enum", codes)
        self.assertIn("numeric_out_of_range", codes)
        self.assertIn("numeric_precision_exceeded", codes)
        self.assertIn("invalid_timestamp", codes)
        self.assertIn("null_not_allowed", codes)
        self.assertIn("invalid_reason_code", codes)

    def test_unknown_field_is_warning_not_pass(self) -> None:
        packet = _packet()
        packet["future_field"] = "reserved"

        result = contract.validate_packet(packet, schema=contract.build_schema(), reason_registry={"RECOVERY_SUPPORT"})

        self.assertFalse(result["valid"])
        self.assertEqual(result["validation_result"], "WARNING")
        self.assertIn({"code": "unknown_field", "field": "future_field", "severity": "WARNING"}, result["issues"])

    def test_golden_samples_are_actual_packets_and_do_not_synthesize_missing_fake(self) -> None:
        samples = contract.build_golden_samples([_packet(), _packet(decision="INCONCLUSIVE", reasons=["CONFLICTING_EVIDENCE"])])

        self.assertEqual(samples["golden_sample_validation"], "PASS")
        self.assertIn("REAL_WHALE_BACK", samples["available_decision_types"])
        self.assertIn("INCONCLUSIVE", samples["available_decision_types"])
        self.assertEqual(samples["samples"]["FAKE_WHALE_BACK"]["status"], "absent_in_source")

    def test_run_writes_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            log_path = base / "mirror_shadow_log.jsonl"
            rows = [{"mirror_packet": _packet()}, {"mirror_packet": _packet(decision="INCONCLUSIVE", reasons=["CONFLICTING_EVIDENCE"])}]
            log_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

            result = contract.run_mirror_packet_contract_freeze(output_dir=base, shadow_log_path=log_path)

            self.assertEqual(result["contract_validation"], "PASS")
            self.assertEqual(result["freeze_status"], "FROZEN")
            self.assertEqual(result["golden_sample_validation"], "PASS")
            self.assertTrue((base / "mirror_packet_schema_v1.json").exists())
            self.assertTrue((base / "mirror_packet_contract_report.json").exists())
            self.assertTrue((base / "mirror_packet_validation_report.json").exists())
            self.assertTrue((base / "mirror_packet_golden_samples.json").exists())


def _packet(decision: str = "REAL_WHALE_BACK", reasons: list[str] | None = None) -> dict:
    reason_code = list(reasons or ["RECOVERY_SUPPORT"])
    policy = "INCONCLUSIVE" if decision == "INCONCLUSIVE" else "DECIDE"
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-campaign-{decision}",
        "campaign_id": f"campaign-{decision}",
        "signal_id": f"signal-{decision}",
        "symbol": "BTCUSDT",
        "mirror_decision": decision,
        "confidence": 0.9 if decision != "INCONCLUSIVE" else 0.35,
        "reason_code": reason_code,
        "supporting_features": {
            "early_mae": -2.123456,
            "recovery_ratio": 1.234567,
            "campaign_duration": 24.0,
            "confidence": 1.0,
            "evidence": ["RECOVERY_STRONG"] if decision != "INCONCLUSIVE" else ["RECOVERY_WEAK"],
            "conflict_resolution": {
                "conflict_detected": decision == "INCONCLUSIVE",
                "decision_targets": [decision] if decision != "INCONCLUSIVE" else ["FAKE_WHALE_BACK", "INCONCLUSIVE"],
                "policy": policy,
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
