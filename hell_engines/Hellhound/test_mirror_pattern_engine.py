from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_pattern_engine as engine
except ImportError:
    from . import mirror_pattern_engine as engine


class MirrorPatternEngineTest(unittest.TestCase):
    def test_engine_uses_registry_chain_for_decisions(self) -> None:
        mirror = engine.MirrorPatternEngine(_inputs())
        packets = engine.build_campaign_physics_packets(_inputs())

        real_packet = mirror.process(packets[0])
        fake_packet = mirror.process(packets[1])

        self.assertEqual(real_packet["mirror_decision"], "REAL_WHALE_BACK")
        self.assertEqual(real_packet["reason_code"], ["RECOVERY_SUPPORT"])
        self.assertIn("RECOVERY_STRONG", real_packet["supporting_features"]["evidence"])
        self.assertEqual(fake_packet["mirror_decision"], "FAKE_WHALE_BACK")
        self.assertEqual(fake_packet["reason_code"], ["RECOVERY_FAILURE"])
        self.assertIn("RECOVERY_WEAK", fake_packet["supporting_features"]["evidence"])
        self.assertNotIn("initial_drawdown_velocity", real_packet["supporting_features"])

    def test_packet_validation_rejects_raw_or_invalid_packet(self) -> None:
        mirror = engine.MirrorPatternEngine(_inputs())
        packet = engine.build_campaign_physics_packets(_inputs())[0]
        packet.pop("campaign_id")

        result = mirror.validate_campaign_packet(packet)

        self.assertEqual(result["validation_state"], "REJECT")
        self.assertIn("missing:campaign_id", result["issues"])

    def test_mirror_packet_validation_requires_reason_code(self) -> None:
        mirror = engine.MirrorPatternEngine(_inputs())
        packet = mirror.process(engine.build_campaign_physics_packets(_inputs())[0])
        valid = mirror.validate_mirror_packet(packet)
        packet_without_reason = dict(packet)
        packet_without_reason["reason_code"] = []
        invalid = mirror.validate_mirror_packet(packet_without_reason)

        self.assertTrue(valid["valid"])
        self.assertFalse(invalid["valid"])
        self.assertIn("missing_reason_code", invalid["issues"])

    def test_conflict_resolver_routes_conflict_to_inconclusive(self) -> None:
        inputs = _inputs()
        inputs["reason_registry"]["reasons"].append({"reason_code": "CONFLICTING_EVIDENCE"})
        inputs["registry_dependency"]["evidence_to_reason"].append({"from": "RECOVERY_WEAK", "to": "CONFLICTING_EVIDENCE"})
        inputs["registry_dependency"]["reason_to_decision"].append({"from": "CONFLICTING_EVIDENCE", "to": "INCONCLUSIVE"})
        mirror = engine.MirrorPatternEngine(inputs)
        packet = mirror.process(engine.build_campaign_physics_packets(inputs)[1])

        self.assertEqual(packet["mirror_decision"], "INCONCLUSIVE")
        self.assertEqual(packet["confidence"], 0.35)
        self.assertIn("CONFLICTING_EVIDENCE", packet["reason_code"])
        self.assertTrue(packet["supporting_features"]["conflict_resolution"]["conflict_detected"])

    def test_run_writes_offline_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = _write_inputs(base)

            result = engine.run_mirror_pattern_engine(
                output_dir=base,
                campaign_dataset_path=paths["campaign_dataset"],
                early_mae_path=paths["early_mae_discriminator"],
                campaign_contract_path=paths["campaign_contract"],
                mirror_output_schema_path=paths["mirror_output_schema"],
                feature_registry_path=paths["feature_registry"],
                evidence_registry_path=paths["evidence_registry"],
                reason_registry_path=paths["reason_registry"],
                registry_dependency_path=paths["registry_dependency"],
                validation_rules_path=paths["validation_rules"],
                readiness_path=paths["readiness"],
            )

            self.assertEqual(result["packet_count"], 2)
            self.assertEqual(result["contract_validation"], "PASS")
            self.assertEqual(result["registry_validation"], "PASS")
            self.assertEqual(result["mirror_packet_validation"], "PASS")
            self.assertTrue((base / "mirror_pattern_packets.jsonl").exists())
            self.assertTrue((base / "mirror_engine_report.json").exists())
            self.assertTrue((base / "mirror_decision_distribution.json").exists())
            self.assertTrue((base / "mirror_reason_statistics.json").exists())
            self.assertTrue((base / "mirror_confidence_distribution.json").exists())


def _write_inputs(base: Path) -> dict[str, Path]:
    mapping = {
        "campaign_dataset": base / "campaign_replay_dataset.json",
        "early_mae_discriminator": base / "early_mae_discriminator.json",
        "campaign_contract": base / "campaign_physics_contract.json",
        "mirror_output_schema": base / "mirror_output_schema.json",
        "feature_registry": base / "mirror_feature_registry.json",
        "evidence_registry": base / "mirror_evidence_registry.json",
        "reason_registry": base / "mirror_reason_registry.json",
        "registry_dependency": base / "mirror_registry_dependency.json",
        "validation_rules": base / "mirror_validation_rules.json",
        "readiness": base / "mirror_v1_readiness_report.json",
    }
    data = _inputs()
    for key, path in mapping.items():
        path.write_text(json.dumps(data[key]), encoding="utf-8")
    return mapping


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
        "campaign_dataset": {
            "campaigns": [
                {
                    "campaign_id": "campaign-real",
                    "source_sample_id": "signal-real",
                    "symbol": "BTCUSDT",
                    "outcome": "SUCCESS",
                    "duration": 10.0,
                    "metrics": {"early_mae": -2.0, "campaign_duration": 10.0},
                },
                {
                    "campaign_id": "campaign-fake",
                    "source_sample_id": "signal-fake",
                    "symbol": "ETHUSDT",
                    "outcome": "FAILURE",
                    "duration": 12.0,
                    "metrics": {"early_mae": -8.0, "campaign_duration": 12.0},
                },
            ]
        },
        "early_mae_discriminator": {
            "campaign_physics_rows": [
                {
                    "campaign_id": "campaign-real",
                    "early_mae": -2.0,
                    "recovery_ratio": 2.0,
                    "initial_drawdown_velocity": -0.5,
                    "campaign_duration": 10.0,
                },
                {
                    "campaign_id": "campaign-fake",
                    "early_mae": -8.0,
                    "recovery_ratio": 0.5,
                    "initial_drawdown_velocity": -1.0,
                    "campaign_duration": 12.0,
                },
            ]
        },
        "campaign_contract": {"contract_version": "campaign_physics_contract_v1", "fields": fields},
        "mirror_output_schema": {
            "fields": [],
            "decision_enum": ["REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"],
            "reason_code_required": True,
        },
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
                {"evidence_id": "LOW_CONFIDENCE"},
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
                {"from": "confidence", "to": "LOW_CONFIDENCE"},
            ],
            "evidence_to_reason": [
                {"from": "RECOVERY_STRONG", "to": "RECOVERY_SUPPORT"},
                {"from": "RECOVERY_WEAK", "to": "RECOVERY_FAILURE"},
                {"from": "LOW_CONFIDENCE", "to": "INSUFFICIENT_EVIDENCE"},
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
