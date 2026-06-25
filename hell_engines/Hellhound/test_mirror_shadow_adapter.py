from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_shadow_adapter as adapter
except ImportError:
    from . import mirror_shadow_adapter as adapter


class MirrorShadowAdapterTest(unittest.TestCase):
    def test_shadow_adapter_processes_campaign_physics_packet_only(self) -> None:
        shadow = adapter.MirrorShadowAdapter(_inputs())
        row = shadow.process_campaign_physics_packet(_packet("campaign-real", recovery_ratio=2.0))

        self.assertEqual(row["mirror_decision"], "REAL_WHALE_BACK")
        self.assertEqual(row["reason_code"], ["RECOVERY_SUPPORT"])
        self.assertEqual(row["validation_state"], "ACCEPT")
        self.assertEqual(row["mirror_packet_validation"], "PASS")
        self.assertFalse(row["is_trade_command"])
        self.assertTrue(row["shadow_mode"])
        self.assertTrue(row["replay_storage_compatible"])
        self.assertIn("processing_time_ms", row)
        self.assertIsNone(row["telegram"])

    def test_invalid_campaign_physics_packet_is_logged_without_trade_action(self) -> None:
        shadow = adapter.MirrorShadowAdapter(_inputs())
        packet = _packet("campaign-invalid", recovery_ratio=2.0)
        packet.pop("campaign_id")

        row = shadow.process_campaign_physics_packet(packet)

        self.assertEqual(row["mirror_decision"], "INCONCLUSIVE")
        self.assertEqual(row["validation_state"], "REJECT")
        self.assertFalse(row["is_trade_command"])
        self.assertEqual(row["audit"]["validation_state"], "REJECT")

    def test_statistics_include_shadow_decision_distribution(self) -> None:
        rows = [
            {"mirror_decision": "REAL_WHALE_BACK", "confidence": 0.9, "processing_time_ms": 1.0},
            {"mirror_decision": "INCONCLUSIVE", "confidence": 0.35, "processing_time_ms": 3.0},
        ]

        statistics = adapter.build_shadow_statistics(rows)
        processing = adapter.build_processing_time_report(rows)

        self.assertEqual(statistics["decision_counts"]["REAL_WHALE_BACK"], 1)
        self.assertEqual(statistics["decision_counts"]["FAKE_WHALE_BACK"], 0)
        self.assertEqual(statistics["decision_counts"]["INCONCLUSIVE"], 1)
        self.assertEqual(statistics["average_confidence"], 0.625)
        self.assertEqual(processing["average_processing_time_ms"], 2.0)

    def test_run_writes_shadow_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = adapter.run_mirror_shadow_integration(
                output_dir=base,
                campaign_packets=[_packet("campaign-real", recovery_ratio=2.0), _packet("campaign-fake", recovery_ratio=0.5)],
                telegram_enabled=False,
            )

            self.assertEqual(result["packet_count"], 2)
            self.assertEqual(result["contract_validation"], "PASS")
            self.assertEqual(result["json_validation"], "PASS")
            self.assertTrue((base / "mirror_shadow_log.jsonl").exists())
            self.assertTrue((base / "mirror_shadow_statistics.json").exists())
            self.assertTrue((base / "mirror_shadow_processing_time.json").exists())
            self.assertTrue((base / "mirror_shadow_integration_report.json").exists())
            rows = [
                json.loads(line)
                for line in (base / "mirror_shadow_log.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["is_trade_command"] is False for row in rows))


def _packet(campaign_id: str, *, recovery_ratio: float) -> dict:
    return {
        "schema_version": "campaign_physics_contract_v1",
        "campaign_id": campaign_id,
        "signal_id": f"signal-{campaign_id}",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "outcome": "SUCCESS",
        "early_mae": -2.0,
        "recovery_ratio": recovery_ratio,
        "initial_drawdown_velocity": None,
        "campaign_duration": 10.0,
        "confidence": 1.0,
        "created_at": "2026-06-25T00:00:00+00:00",
    }


def _inputs() -> dict:
    fields = [
        {"field": "schema_version", "type": "string", "required": True, "nullable": False},
        {"field": "campaign_id", "type": "string", "required": True, "nullable": False},
        {"field": "signal_id", "type": "string", "required": True, "nullable": True},
        {"field": "symbol", "type": "string", "required": True, "nullable": False},
        {"field": "timeframe", "type": "string", "required": True, "nullable": False},
        {"field": "outcome", "type": "string", "required": True, "nullable": False},
        {"field": "early_mae", "type": "number", "required": True, "nullable": False},
        {"field": "recovery_ratio", "type": "number", "required": True, "nullable": False},
        {"field": "initial_drawdown_velocity", "type": "number", "required": True, "nullable": True},
        {"field": "campaign_duration", "type": "number", "required": True, "nullable": True},
        {"field": "confidence", "type": "number", "required": True, "nullable": False},
        {"field": "created_at", "type": "string", "required": True, "nullable": False},
    ]
    return {
        "campaign_dataset": {"campaigns": []},
        "early_mae_discriminator": {"campaign_physics_rows": []},
        "campaign_contract": {"contract_version": "campaign_physics_contract_v1", "fields": fields},
        "mirror_output_schema": {"fields": [], "decision_enum": ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"]},
        "feature_registry": {
            "features": [
                {"feature_id": "early_mae", "status": "ACTIVE"},
                {"feature_id": "recovery_ratio", "status": "ACTIVE"},
                {"feature_id": "campaign_duration", "status": "ACTIVE"},
                {"feature_id": "initial_drawdown_velocity", "status": "RESERVED"},
                {"feature_id": "confidence", "status": "ACTIVE"},
            ]
        },
        "evidence_registry": {
            "evidence": [
                {"evidence_id": "RECOVERY_STRONG"},
                {"evidence_id": "RECOVERY_WEAK"},
                {"evidence_id": "INSUFFICIENT_EVIDENCE"},
            ]
        },
        "reason_registry": {
            "reasons": [
                {"reason_code": "RECOVERY_SUPPORT"},
                {"reason_code": "RECOVERY_FAILURE"},
                {"reason_code": "INSUFFICIENT_EVIDENCE"},
            ]
        },
        "registry_dependency": {
            "feature_to_evidence": [
                {"from": "recovery_ratio", "to": "RECOVERY_STRONG"},
                {"from": "recovery_ratio", "to": "RECOVERY_WEAK"},
            ],
            "evidence_to_reason": [
                {"from": "RECOVERY_STRONG", "to": "RECOVERY_SUPPORT"},
                {"from": "RECOVERY_WEAK", "to": "RECOVERY_FAILURE"},
                {"from": "INSUFFICIENT_EVIDENCE", "to": "INSUFFICIENT_EVIDENCE"},
            ],
            "reason_to_decision": [
                {"from": "RECOVERY_SUPPORT", "to": "REAL_WHALE_BACK"},
                {"from": "RECOVERY_FAILURE", "to": "FAKE_WHALE_BACK"},
                {"from": "INSUFFICIENT_EVIDENCE", "to": "INCONCLUSIVE"},
            ],
        },
        "validation_rules": {"rules": [{"validation_error_code": "valid_packet", "verdict": "ACCEPT", "actions": ["PASS"]}]},
        "readiness": {"readiness_verdict": "READY"},
    }


if __name__ == "__main__":
    unittest.main()
