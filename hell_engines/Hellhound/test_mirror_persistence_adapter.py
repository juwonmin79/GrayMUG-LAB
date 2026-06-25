from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_persistence_adapter as persistence
except ImportError:
    from . import mirror_persistence_adapter as persistence


class MirrorPersistenceAdapterTest(unittest.TestCase):
    def test_adapter_saves_valid_packet_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packets.jsonl"
            adapter = persistence.MirrorPersistenceAdapter(persistence.JsonlPacketStorage(path))

            result = adapter.save_packets([_packet("REAL_WHALE_BACK")])
            rows = persistence.JsonlPacketStorage(path).load_packets()

            self.assertEqual(result["rows"][0]["status"], "SAVED")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["mirror_decision"], "REAL_WHALE_BACK")
            self.assertFalse(result["rows"][0]["packet_mutated"])

    def test_duplicate_packet_is_detected_and_not_saved_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packets.jsonl"
            adapter = persistence.MirrorPersistenceAdapter(persistence.JsonlPacketStorage(path))
            packet = _packet("REAL_WHALE_BACK")

            first = adapter.save_packets([packet])
            second = adapter.save_packets([packet])
            rows = persistence.JsonlPacketStorage(path).load_packets()

            self.assertEqual(first["rows"][0]["status"], "SAVED")
            self.assertEqual(second["rows"][0]["status"], "DUPLICATE")
            self.assertEqual(len(rows), 1)

    def test_invalid_packet_is_rejected_and_not_saved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packets.jsonl"
            adapter = persistence.MirrorPersistenceAdapter(persistence.JsonlPacketStorage(path))
            packet = _packet("REAL_WHALE_BACK")
            packet.pop("campaign_id")

            result = adapter.save_packets([packet])

            self.assertEqual(result["rows"][0]["status"], "REJECTED")
            self.assertFalse(path.exists())

    def test_replay_compatibility_passes_persisted_packets(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]

        report = persistence.build_replay_compatibility_report(packets)

        self.assertEqual(report["replay_compatibility"], "PASS")
        self.assertEqual(report["contract_validation"], "PASS")
        self.assertEqual(report["json_validation"], "PASS")
        self.assertTrue(report["content_unchanged"])

    def test_run_writes_persistence_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source.jsonl"
            source.write_text(
                "".join(json.dumps({"mirror_packet": packet}, sort_keys=True) + "\n" for packet in [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]),
                encoding="utf-8",
            )

            result = persistence.run_mirror_persistence_adapter(output_dir=base, source_path=source)

            self.assertEqual(result["persistence_adapter"], "PASS")
            self.assertEqual(result["success_count"], 2)
            self.assertEqual(result["reject_count"], 0)
            self.assertEqual(result["duplicate_count"], 0)
            self.assertEqual(result["contract_validation"], "PASS")
            self.assertEqual(result["replay_compatibility"], "PASS")
            self.assertTrue((base / "mirror_persistence_report.json").exists())
            self.assertTrue((base / "mirror_persistence_statistics.json").exists())
            self.assertTrue((base / "mirror_persistence_packets.jsonl").exists())


def _packet(decision: str) -> dict:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-{decision}",
        "campaign_id": f"campaign-{decision}",
        "signal_id": f"signal-{decision}",
        "symbol": "BTCUSDT",
        "mirror_decision": decision,
        "confidence": 0.9 if decision == "REAL_WHALE_BACK" else 0.35,
        "reason_code": reasons,
        "supporting_features": {
            "early_mae": -2.0,
            "recovery_ratio": 1.2,
            "campaign_duration": 24.0,
            "confidence": 1.0,
            "evidence": ["RECOVERY_STRONG"],
            "conflict_resolution": {
                "conflict_detected": decision == "INCONCLUSIVE",
                "decision_targets": [decision] if decision == "REAL_WHALE_BACK" else ["FAKE_WHALE_BACK", "INCONCLUSIVE"],
                "policy": "DECIDE" if decision == "REAL_WHALE_BACK" else "INCONCLUSIVE",
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


if __name__ == "__main__":
    unittest.main()
