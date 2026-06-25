from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_packet_contract
    import mirror_persistence_readback_audit as audit
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_persistence_readback_audit as audit


class MirrorPersistenceReadbackAuditTest(unittest.TestCase):
    def test_utf8_without_bom_loader_passes_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packets.jsonl"
            path.write_text(json.dumps(_packet(), sort_keys=True) + "\n", encoding="utf-8")

            result = audit.load_jsonl_utf8_no_bom(path)

            self.assertEqual(result["encoding_validation_result"], "PASS")
            self.assertFalse(result["has_bom"])
            self.assertEqual(len(result["packets"]), 1)

    def test_utf8_loader_rejects_bom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packets.jsonl"
            path.write_bytes(b"\xef\xbb\xbf" + (json.dumps(_packet()) + "\n").encode("utf-8"))

            result = audit.load_jsonl_utf8_no_bom(path)

            self.assertEqual(result["encoding_validation_result"], "FAIL")
            self.assertTrue(result["has_bom"])

    def test_equality_report_detects_value_mutation(self) -> None:
        original = _packet()
        readback = _packet()
        readback["confidence"] = 0.1

        result = audit.build_equality_report(
            [original],
            [readback],
            schema=mirror_packet_contract.build_schema(),
            reason_registry={"RECOVERY_SUPPORT"},
        )

        self.assertEqual(result["equality_validation"], "FAIL")
        self.assertEqual(result["mismatch_count"], 1)
        self.assertIn("confidence", result["rows"][0]["field_mismatches"])

    def test_hash_report_matches_canonical_json(self) -> None:
        packet = _packet()
        report = audit.build_hash_report(
            [packet],
            [dict(packet)],
            {"encoding_validation_result": "PASS"},
        )

        self.assertEqual(report["hash_match"], "PASS")
        self.assertEqual(report["hash_match_count"], 1)
        self.assertEqual(report["hash_mismatch_count"], 0)

    def test_replay_after_readback_passes_and_mutates_nothing(self) -> None:
        report = audit.build_replay_after_readback_report(
            [_packet()],
            schema=mirror_packet_contract.build_schema(),
            reason_registry={"RECOVERY_SUPPORT"},
        )

        self.assertEqual(report["replay_after_readback_result"], "PASS")
        self.assertEqual(report["contract_validation"], "PASS")
        self.assertEqual(report["determinism"], "PASS")
        self.assertEqual(report["packet_mutation_count"], 0)

    def test_run_writes_readback_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original_path = base / "source.jsonl"
            readback_path = base / "persisted.jsonl"
            packet = _packet()
            original_path.write_text(json.dumps({"mirror_packet": packet}, sort_keys=True) + "\n", encoding="utf-8")
            readback_path.write_text(json.dumps(packet, sort_keys=True) + "\n", encoding="utf-8")

            result = audit.run_mirror_persistence_readback_audit(
                output_dir=base,
                original_path=original_path,
                readback_path=readback_path,
            )

            self.assertEqual(result["readback_audit"], "PASS")
            self.assertEqual(result["equality_validation"], "PASS")
            self.assertEqual(result["hash_match"], "PASS")
            self.assertEqual(result["replay_after_readback"], "PASS")
            self.assertEqual(result["mutation_count"], 0)
            self.assertTrue((base / "mirror_readback_audit_report.json").exists())
            self.assertTrue((base / "mirror_readback_hash_report.json").exists())
            self.assertTrue((base / "mirror_readback_replay_report.json").exists())


def _packet() -> dict:
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": "mirror-campaign-readback",
        "campaign_id": "campaign-readback",
        "signal_id": "signal-readback",
        "symbol": "BTCUSDT",
        "mirror_decision": "REAL_WHALE_BACK",
        "confidence": 0.9,
        "reason_code": ["RECOVERY_SUPPORT"],
        "supporting_features": {
            "early_mae": -2.0,
            "recovery_ratio": 1.2,
            "campaign_duration": 24.0,
            "confidence": 1.0,
            "evidence": ["RECOVERY_STRONG"],
            "conflict_resolution": {
                "conflict_detected": False,
                "decision_targets": ["REAL_WHALE_BACK"],
                "policy": "DECIDE",
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
