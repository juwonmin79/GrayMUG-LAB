from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from event_writer import (
        EventValidationError,
        EventWriter,
        append_event,
        append_events,
        record_from_boundary_output,
        records_from_boundary_output,
        validate_event,
    )
    from library_interface import detect_cluster_rows, evaluate_real_feed_row
    from real_shadow_feed import mock_signal_rows
except ImportError:
    from .event_writer import (
        EventValidationError,
        EventWriter,
        append_event,
        append_events,
        record_from_boundary_output,
        records_from_boundary_output,
        validate_event,
    )
    from .library_interface import detect_cluster_rows, evaluate_real_feed_row
    from .real_shadow_feed import mock_signal_rows


class EventWriterTest(unittest.TestCase):
    def test_single_row_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            result = append_event(_valid_event("event-1"), path=path)
            rows = _read_jsonl(path)

        self.assertEqual(result["written_count"], 1)
        self.assertEqual(rows[0]["event_id"], "event-1")
        self.assertFalse(rows[0]["is_trade_command"])

    def test_batch_write_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            writer = EventWriter(path)
            writer.append_event(_valid_event("event-1"))
            writer.append_events([_valid_event("event-2"), _valid_event("event-3")])
            rows = _read_jsonl(path)

        self.assertEqual([row["event_id"] for row in rows], ["event-1", "event-2", "event-3"])

    def test_schema_validation_rejects_missing_required_field(self) -> None:
        malformed = _valid_event("event-1")
        malformed.pop("event_time")

        with self.assertRaises(EventValidationError):
            validate_event(malformed)

    def test_schema_validation_rejects_invalid_record_type(self) -> None:
        malformed = _valid_event("event-1")
        malformed["record_type"] = "order"

        with self.assertRaises(EventValidationError):
            validate_event(malformed)

    def test_schema_validation_rejects_trade_command(self) -> None:
        malformed = _valid_event("event-1")
        malformed["is_trade_command"] = True

        with self.assertRaises(EventValidationError):
            validate_event(malformed)

    def test_cluster_row_write_from_boundary_output(self) -> None:
        cluster_payload = detect_cluster_rows(mock_signal_rows(3))
        records = records_from_boundary_output(cluster_payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            result = append_events(records, path=path)
            rows = _read_jsonl(path)

        self.assertEqual(result["written_count"], 1)
        self.assertEqual(rows[0]["record_type"], "daily_open_alert_cluster")
        self.assertTrue(rows[0]["payload"]["daily_open_cluster"])
        self.assertFalse(rows[0]["is_trade_command"])

    def test_shadow_decision_record_from_real_feed_boundary(self) -> None:
        payload = evaluate_real_feed_row(mock_signal_rows(1)[0])
        record = record_from_boundary_output(payload)

        self.assertEqual(record["record_type"], "real_feed_outcome")
        self.assertEqual(record["symbol"], payload["symbol"])
        self.assertFalse(record["is_trade_command"])


def _valid_event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_time": "2026-01-01T00:00:00+00:00",
        "record_type": "shadow_decision",
        "source": "test",
        "hellhound_version": "test-version",
        "symbol": "BELUSDT",
        "is_trade_command": False,
    }


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
