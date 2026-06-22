from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from lead_line_dataset import (
        build_lead_line_dataset,
        collect_pre_outcome_events,
        create_lead_line_record,
        load_event_records,
        write_lead_line_dataset,
    )
except ImportError:
    from .lead_line_dataset import (
        build_lead_line_dataset,
        collect_pre_outcome_events,
        create_lead_line_record,
        load_event_records,
        write_lead_line_dataset,
    )


class LeadLineDatasetTest(unittest.TestCase):
    def test_collect_pre_outcome_events_window_filtering(self) -> None:
        events = _events()
        outcome = events[-1]

        collected = collect_pre_outcome_events(
            events,
            outcome_event=outcome,
            hours_before_outcome=24,
        )

        self.assertEqual([event["event_id"] for event in collected], ["shadow-1", "cluster-1"])

    def test_create_lead_line_record(self) -> None:
        events = _events()
        outcome = events[-1]
        pre_events = collect_pre_outcome_events(events, outcome_event=outcome, hours_before_outcome=24)

        row = create_lead_line_record(
            outcome_event=outcome,
            pre_events=pre_events,
            hours_before_outcome=24,
        )

        self.assertEqual(row["symbol"], "BELUSDT")
        self.assertEqual(row["hours_before_outcome"], 24)
        self.assertTrue(row["saw_shadow_decision"])
        self.assertTrue(row["saw_daily_open_cluster"])
        self.assertEqual(row["promotion_status"], "PROMOTE")
        self.assertEqual(row["structure_type"], "BEL")
        self.assertEqual(row["event_count"], 2)
        self.assertFalse(row["is_trade_command"])

    def test_build_lead_line_dataset_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "empty.jsonl"
            output_path = Path(directory) / "dataset.jsonl"
            event_path.write_text("", encoding="utf-8")
            result = build_lead_line_dataset(
                event_log_path=event_path,
                output_path=output_path,
                windows_hours=(24,),
            )

        self.assertEqual(result["dataset_count"], 0)
        self.assertEqual(result["rows"], [])

    def test_malformed_events_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "events.jsonl"
            event_path.write_text(
                "\n".join(
                    [
                        "{bad-json",
                        json.dumps({"event_id": "bad", "record_type": "shadow_decision"}),
                        json.dumps(_events()[-1]),
                    ]
                ),
                encoding="utf-8",
            )

            records = load_event_records(event_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["record_type"], "real_feed_outcome")

    def test_build_dataset_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "events.jsonl"
            output_path = Path(directory) / "lead_line.jsonl"
            event_path.write_text(
                "\n".join(json.dumps(event) for event in _events()),
                encoding="utf-8",
            )

            result = build_lead_line_dataset(
                event_log_path=event_path,
                output_path=output_path,
                windows_hours=(24, 48),
                append=True,
            )
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["dataset_count"], 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["hours_before_outcome"], 24)
        self.assertEqual(rows[1]["hours_before_outcome"], 48)

    def test_write_lead_line_dataset_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "lead_line.jsonl"
            row = create_lead_line_record(
                outcome_event=_events()[-1],
                pre_events=_events()[:-1],
                hours_before_outcome=24,
            )
            write_lead_line_dataset([row], output_path=output_path, append=True)
            write_lead_line_dataset([row], output_path=output_path, append=True)
            rows = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(rows), 2)


def _events() -> list[dict[str, object]]:
    return [
        {
            "event_id": "old-shadow",
            "event_time": "2026-01-01T00:00:00+00:00",
            "record_type": "shadow_decision",
            "source": "test",
            "hellhound_version": "test",
            "symbol": "BELUSDT",
            "is_trade_command": False,
            "payload": {"promotion_status": "WATCH", "structure_type": "UNKNOWN", "hellhound_score": 0.2},
        },
        {
            "event_id": "shadow-1",
            "event_time": "2026-01-02T12:00:00+00:00",
            "record_type": "shadow_decision",
            "source": "test",
            "hellhound_version": "test",
            "symbol": "BELUSDT",
            "is_trade_command": False,
            "payload": {
                "promotion_status": "PROMOTE",
                "structure_type": "BEL",
                "hellhound_score": 0.72,
                "entry_bias": "neutral",
            },
        },
        {
            "event_id": "cluster-1",
            "event_time": "2026-01-03T00:00:00+00:00",
            "record_type": "daily_open_alert_cluster",
            "source": "test",
            "hellhound_version": "test",
            "symbol": None,
            "is_trade_command": False,
            "payload": {
                "daily_open_cluster": True,
                "alert_count": 4,
                "symbols": ["BELUSDT", "ACTUSDT"],
            },
        },
        {
            "event_id": "outcome-1",
            "event_time": "2026-01-03T12:00:00+00:00",
            "record_type": "real_feed_outcome",
            "source": "test",
            "hellhound_version": "test",
            "symbol": "BELUSDT",
            "is_trade_command": False,
            "payload": {"actual_24h_outcome": "SUCCESS"},
        },
    ]


if __name__ == "__main__":
    unittest.main()
