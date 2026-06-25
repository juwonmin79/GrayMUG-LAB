from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import mirror_packet_contract
    import mirror_replay_harness as harness
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_replay_harness as harness


class MirrorReplayHarnessTest(unittest.TestCase):
    def test_replay_packets_preserves_packet_content(self) -> None:
        packets = [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")]
        schema = mirror_packet_contract.build_schema()
        rows = harness.replay_packets(packets, schema=schema, reason_registry={"RECOVERY_SUPPORT", "CONFLICTING_EVIDENCE"})

        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["contract_validation"] == "PASS" for row in rows))
        self.assertTrue(all(row["packet_mutated"] is False for row in rows))
        self.assertEqual(rows[0]["decision"], "REAL_WHALE_BACK")
        self.assertEqual(rows[1]["decision"], "INCONCLUSIVE")

    def test_replay_sequence_validation_detects_changes(self) -> None:
        packets = [_packet("REAL_WHALE_BACK")]
        rows = [
            {
                "sequence_index": 0,
                "timestamp_order_valid": True,
                "decision": "INCONCLUSIVE",
                "reason_code": packets[0]["reason_code"],
                "confidence": packets[0]["confidence"],
                "validation_state": packets[0]["validation_state"],
                "packet_mutated": False,
            }
        ]

        result = harness.validate_replay_sequence(packets, rows)

        self.assertEqual(result["sequence_validation"], "FAIL")
        self.assertIn({"index": 0, "error": "decision_changed"}, result["sequence_errors"])

    def test_golden_sample_replay_skips_absent_fake_without_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mirror_packet_golden_samples.json"
            golden = {
                "samples": {
                    "REAL_WHALE_BACK": _packet("REAL_WHALE_BACK"),
                    "INCONCLUSIVE": _packet("INCONCLUSIVE"),
                    "FAKE_WHALE_BACK": {"status": "absent_in_source", "reason": "No actual validated packet for this decision type in current source."},
                }
            }
            path.write_text(json.dumps(golden), encoding="utf-8")

            result = harness.replay_golden_samples(
                path,
                schema=mirror_packet_contract.build_schema(),
                reason_registry={"RECOVERY_SUPPORT", "CONFLICTING_EVIDENCE"},
            )

            self.assertEqual(result["golden_sample_replay"], "PASS")
            self.assertEqual(result["decision_results"]["FAKE_WHALE_BACK"]["status"], "SKIPPED")
            self.assertFalse(result["synthetic_samples_created"])
            self.assertEqual(result["fake_golden_sample"], "SKIPPED (absent in source)")

    def test_determinism_report_passes_for_repeated_replay(self) -> None:
        result = harness.build_determinism_report(
            [_packet("REAL_WHALE_BACK"), _packet("INCONCLUSIVE")],
            schema=mirror_packet_contract.build_schema(),
            reason_registry={"RECOVERY_SUPPORT", "CONFLICTING_EVIDENCE"},
            replay_counts=[10, 100],
        )

        self.assertEqual(result["replay_determinism"], "PASS")
        self.assertEqual([row["replay_count"] for row in result["runs"]], [10, 100])
        self.assertTrue(all(row["mismatch_count"] == 0 for row in result["runs"]))

    def test_run_writes_replay_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            packet_path = base / "mirror_shadow_log.jsonl"
            golden_path = base / "mirror_packet_golden_samples.json"
            packet_rows = [{"mirror_packet": _packet("REAL_WHALE_BACK")}, {"mirror_packet": _packet("INCONCLUSIVE")}]
            packet_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in packet_rows), encoding="utf-8")
            golden_path.write_text(
                json.dumps(
                    {
                        "samples": {
                            "REAL_WHALE_BACK": _packet("REAL_WHALE_BACK"),
                            "INCONCLUSIVE": _packet("INCONCLUSIVE"),
                            "FAKE_WHALE_BACK": {"status": "absent_in_source", "reason": "No actual validated packet for this decision type in current source."},
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = harness.run_mirror_replay_harness(
                output_dir=base,
                golden_sample_path=golden_path,
                packet_path=packet_path,
                replay_counts=[10, 100],
            )

            self.assertEqual(result["replay_harness"], "PASS")
            self.assertEqual(result["contract_validation"], "PASS")
            self.assertEqual(result["replay_compatibility"], "PASS")
            self.assertEqual(result["golden_sample_replay"], "PASS")
            self.assertEqual(result["replay_determinism"], "PASS")
            self.assertTrue((base / "mirror_replay_report.json").exists())
            self.assertTrue((base / "mirror_replay_statistics.json").exists())
            self.assertTrue((base / "mirror_replay_determinism.json").exists())


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
