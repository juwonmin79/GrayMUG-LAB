from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Optional

try:
    from outcome_validator import (
        create_validation_record,
        load_lead_line_rows,
        validate_lead_line,
        validate_outcome_window,
        write_validation_dataset,
    )
except ImportError:
    from .outcome_validator import (
        create_validation_record,
        load_lead_line_rows,
        validate_lead_line,
        validate_outcome_window,
        write_validation_dataset,
    )


class OutcomeValidatorTest(unittest.TestCase):
    def test_validated_status(self) -> None:
        row = _lead_line_row(hours_before=24, outcome_result="SUCCESS")

        validation = validate_outcome_window(row, validation_window_hours=24)

        self.assertEqual(validation["validation_status"], "VALIDATED")
        self.assertGreater(validation["validation_score"], 0.7)
        self.assertFalse(validation["is_trade_command"])

    def test_delayed_status(self) -> None:
        row = _lead_line_row(hours_before=72, outcome_result="SUCCESS")

        validation = validate_outcome_window(row, validation_window_hours=24)

        self.assertEqual(validation["validation_status"], "DELAYED")
        self.assertLess(validation["validation_score"], 0.6)

    def test_inconclusive_status(self) -> None:
        row = _lead_line_row(hours_before=24, outcome_result=None)
        row.pop("outcome_time")

        validation = validate_outcome_window(row, validation_window_hours=24)

        self.assertEqual(validation["validation_status"], "INCONCLUSIVE")

    def test_rejected_status(self) -> None:
        row = _lead_line_row(hours_before=24, outcome_result="FAIL")
        row.pop("outcome_time")

        validation = validate_outcome_window(row, validation_window_hours=24)

        self.assertEqual(validation["validation_status"], "REJECTED")
        self.assertEqual(validation["validation_score"], 0.0)

    def test_create_validation_record_shape(self) -> None:
        record = create_validation_record(
            lead_line_row=_lead_line_row(hours_before=24, outcome_result="SUCCESS"),
            validation_window_hours=24,
            validation_status="VALIDATED",
        )

        self.assertEqual(record["symbol"], "BELUSDT")
        self.assertEqual(record["promotion_status"], "PROMOTE")
        self.assertEqual(record["structure_type"], "BEL")
        self.assertTrue(record["saw_daily_open_cluster"])

    def test_validate_lead_line_window_filtering(self) -> None:
        rows = [_lead_line_row(hours_before=24, outcome_result="SUCCESS")]

        result = validate_lead_line(
            rows,
            validation_windows=(24, 48, 72),
            output_path=None,
        )

        self.assertEqual(result["validation_count"], 3)
        self.assertEqual(
            [row["validation_window_hours"] for row in result["records"]],
            [24, 48, 72],
        )

    def test_malformed_rows_are_skipped_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lead_line.jsonl"
            path.write_text(
                "\n".join(
                    [
                        "{bad-json",
                        json.dumps({"lead_line_id": "bad", "symbol": "BELUSDT", "is_trade_command": True}),
                        json.dumps(_lead_line_row(hours_before=24, outcome_result="SUCCESS")),
                    ]
                ),
                encoding="utf-8",
            )

            rows = load_lead_line_rows(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lead_line_id"], "lead-line-24")

    def test_write_validation_dataset_append_only(self) -> None:
        row = validate_outcome_window(
            _lead_line_row(hours_before=24, outcome_result="SUCCESS"),
            validation_window_hours=24,
        )
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "validation.jsonl"
            write_validation_dataset([row], output_path=output_path, append=True)
            write_validation_dataset([row], output_path=output_path, append=True)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)


def _lead_line_row(hours_before: int, outcome_result: Optional[str]) -> dict[str, object]:
    row = {
        "lead_line_id": f"lead-line-{hours_before}",
        "symbol": "BELUSDT",
        "outcome_time": "2026-01-03T12:00:00+00:00",
        "hours_before_outcome": hours_before,
        "saw_daily_open_cluster": True,
        "promotion_status": "PROMOTE",
        "structure_type": "BEL",
        "daily_open_cluster": True,
        "alert_count": 4,
        "event_count": 2,
        "is_trade_command": False,
    }
    if outcome_result:
        row["outcome_result"] = outcome_result
    return row


if __name__ == "__main__":
    unittest.main()
