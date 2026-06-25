from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_input_readiness as readiness
except ImportError:
    from . import mirror_input_readiness as readiness


class MirrorInputReadinessTest(unittest.TestCase):
    def test_build_packets_from_campaign_physics_rows(self) -> None:
        packets = readiness.build_campaign_physics_packets(_inputs())

        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0]["schema_version"], "campaign_physics_contract_v1")
        self.assertEqual(packets[0]["campaign_id"], "campaign-1")
        self.assertEqual(packets[0]["timeframe"], "15m")
        self.assertEqual(packets[0]["recovery_ratio"], 3.0)
        self.assertEqual(packets[0]["confidence"], 1.0)

    def test_validate_packet_verdicts(self) -> None:
        inputs = _inputs()
        packets = readiness.build_campaign_physics_packets(inputs)
        valid = readiness.validate_packets(packets, inputs["contract"], inputs["validation_rules"])
        self.assertEqual(valid["results"][0]["verdict"], "ACCEPT")

        warning_packet = dict(packets[0], unexpected=True)
        warning = readiness.validate_packets([warning_packet], inputs["contract"], inputs["validation_rules"])
        self.assertEqual(warning["results"][0]["verdict"], "WARNING")

        hold_packet = dict(packets[0], initial_drawdown_velocity=None)
        hold = readiness.validate_packets([hold_packet], inputs["contract"], inputs["validation_rules"])
        self.assertEqual(hold["results"][0]["verdict"], "HOLD")

        reject_packet = dict(packets[0])
        reject_packet.pop("early_mae")
        rejected = readiness.validate_packets([reject_packet], inputs["contract"], inputs["validation_rules"])
        self.assertEqual(rejected["results"][0]["verdict"], "REJECT")

    def test_audit_simulation_for_non_accept_packets(self) -> None:
        inputs = _inputs()
        packet = dict(readiness.build_campaign_physics_packets(inputs)[0], unexpected=True)
        validation = readiness.validate_packets([packet], inputs["contract"], inputs["validation_rules"])
        audit = readiness.simulate_audit_log(validation, inputs["audit_policy"], inputs["contract"])

        self.assertEqual(audit["event_count"], 1)
        self.assertTrue(audit["audit_log_generation_possible"])
        self.assertEqual(audit["events"][0]["validation_error_code"], "unknown_field")

    def test_run_writes_readiness_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            paths = {
                "contract": base / "campaign_physics_contract.json",
                "mirror_input_schema": base / "mirror_input_schema.json",
                "validation_rules": base / "contract_validation_rules.json",
                "audit_policy": base / "interface_audit_policy.json",
                "campaign_dataset": base / "campaign_replay_dataset.json",
                "campaign_physics_summary": base / "campaign_physics_summary.json",
                "early_mae_discriminator": base / "early_mae_discriminator.json",
            }
            for key, path in paths.items():
                path.write_text(json.dumps(_inputs()[key]), encoding="utf-8")

            result = readiness.run_mirror_input_readiness(
                output_dir=base,
                contract_path=paths["contract"],
                mirror_input_schema_path=paths["mirror_input_schema"],
                validation_rules_path=paths["validation_rules"],
                audit_policy_path=paths["audit_policy"],
                campaign_dataset_path=paths["campaign_dataset"],
                physics_summary_path=paths["campaign_physics_summary"],
                early_mae_path=paths["early_mae_discriminator"],
            )

            self.assertEqual(result["readiness_verdict"], "READY")
            self.assertEqual(result["packet_count"], 2)
            self.assertTrue((base / "mirror_input_readiness_report.json").exists())
            self.assertTrue((base / "mirror_contract_validation_result.json").exists())
            self.assertTrue((base / "mirror_input_audit_simulation.json").exists())
            self.assertTrue((base / "mirror_packet_readiness_summary.json").exists())


def _inputs() -> dict:
    fields = [
        _field("schema_version", "string", True, False, enum=["campaign_physics_contract_v1"]),
        _field("campaign_id", "string", True, False),
        _field("signal_id", "string", True, True),
        _field("symbol", "string", True, False),
        _field("timeframe", "string", True, False, enum=["15m", "1h"]),
        _field("outcome", "string", True, False, enum=["SUCCESS", "FAILURE", "INCONCLUSIVE"]),
        _field("early_mae", "number", True, False, minimum=-100.0, maximum=0.0),
        _field("recovery_ratio", "number", True, False, minimum=0.0),
        _field("initial_drawdown_velocity", "number", True, True, maximum=0.0),
        _field("campaign_duration", "number", True, True, minimum=0.0),
        _field("confidence", "number", True, False, minimum=0.0, maximum=1.0),
        _field("created_at", "string", True, False),
    ]
    return {
        "contract": {
            "campaign_physics_contract_schema_version": "campaign_physics_contract_v1",
            "contract_version": "campaign_physics_contract_v1",
            "fields": fields,
        },
        "mirror_input_schema": {"accepted_input": "Campaign Physics Packet"},
        "validation_rules": {
            "rules": [
                {"validation_error_code": "required_field_missing", "actions": ["SKIP"]},
                {"validation_error_code": "type_mismatch", "actions": ["SKIP", "ALERT"]},
                {"validation_error_code": "invalid_value", "actions": ["SKIP", "WARNING"]},
                {"validation_error_code": "schema_version_mismatch", "actions": ["HOLD"]},
                {"validation_error_code": "unknown_field", "actions": ["WARNING"]},
                {"validation_error_code": "partial_packet", "actions": ["HOLD"]},
            ]
        },
        "audit_policy": {
            "audit_log_required_for": ["REJECT", "HOLD", "WARNING"],
            "audit_log_fields": [
                {"field": "contract_version", "required": True},
                {"field": "campaign_id", "required": True},
                {"field": "signal_id", "required": True},
                {"field": "symbol", "required": True},
                {"field": "validation_error_code", "required": True},
                {"field": "validation_reason", "required": True},
                {"field": "action", "required": True},
                {"field": "timestamp", "required": True},
            ],
        },
        "campaign_dataset": {
            "campaigns": [
                {
                    "campaign_id": "campaign-1",
                    "source_sample_id": "signal-1",
                    "symbol": "BTCUSDT",
                    "outcome": "SUCCESS",
                    "duration": 10.0,
                    "metrics": {"early_mae": -2.0, "campaign_duration": 10.0},
                },
                {
                    "campaign_id": "campaign-2",
                    "source_sample_id": "signal-2",
                    "symbol": "ETHUSDT",
                    "outcome": "FAILURE",
                    "duration": 12.0,
                    "metrics": {"early_mae": -6.0, "campaign_duration": 12.0},
                },
            ]
        },
        "campaign_physics_summary": {"evidence_level": "VERIFIED"},
        "early_mae_discriminator": {
            "campaign_physics_rows": [
                {
                    "campaign_id": "campaign-1",
                    "early_mae": -2.0,
                    "recovery_ratio": 3.0,
                    "initial_drawdown_velocity": -0.5,
                    "campaign_duration": 10.0,
                },
                {
                    "campaign_id": "campaign-2",
                    "early_mae": -6.0,
                    "recovery_ratio": 0.5,
                    "initial_drawdown_velocity": -1.0,
                    "campaign_duration": 12.0,
                },
            ]
        },
    }


def _field(name, data_type, required, nullable, enum=None, minimum=None, maximum=None):
    return {
        "field": name,
        "type": data_type,
        "required": required,
        "nullable": nullable,
        "valid_enum": enum,
        "valid_range": {"minimum": minimum, "maximum": maximum}
        if minimum is not None or maximum is not None
        else None,
    }


if __name__ == "__main__":
    unittest.main()
