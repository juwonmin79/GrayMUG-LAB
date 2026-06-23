from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from mfe_mae_engine import (
        aggregate_mfe_mae_by_structure,
        calculate_mae,
        calculate_mfe,
        calculate_time_to_peak,
        calculate_time_to_stop,
        create_mfe_mae_record,
        load_validation_rows,
        write_mfe_mae_dataset,
    )
except ImportError:
    from .mfe_mae_engine import (
        aggregate_mfe_mae_by_structure,
        calculate_mae,
        calculate_mfe,
        calculate_time_to_peak,
        calculate_time_to_stop,
        create_mfe_mae_record,
        load_validation_rows,
        write_mfe_mae_dataset,
    )


class MfeMaeEngineTest(unittest.TestCase):
    def test_mfe_calculation(self) -> None:
        self.assertEqual(calculate_mfe(100.0, _price_path()), 20.0)

    def test_mae_calculation(self) -> None:
        self.assertEqual(calculate_mae(100.0, _price_path()), -6.0)

    def test_time_to_peak(self) -> None:
        self.assertEqual(calculate_time_to_peak(_price_path()), 4.0)

    def test_time_to_stop(self) -> None:
        self.assertEqual(calculate_time_to_stop(100.0, _price_path(), stop_loss_pct=-5.0), 2.0)

    def test_create_mfe_mae_record(self) -> None:
        record = create_mfe_mae_record(_validation_row("BEL"), _price_path())

        self.assertEqual(record["signal_id"], "signal-lead-1")
        self.assertEqual(record["shadow_signal_id"], "signal-lead-1")
        self.assertEqual(record["symbol"], "BELUSDT")
        self.assertEqual(record["structure_type"], "BEL")
        self.assertEqual(record["validation_status"], "VALIDATED")
        self.assertEqual(record["mfe_pct"], 20.0)
        self.assertEqual(record["mae_pct"], -6.0)
        self.assertEqual(record["stop_price"], 94.0)
        self.assertFalse(record["is_trade_command"])

    def test_stop_price_is_null_when_stop_not_hit(self) -> None:
        record = create_mfe_mae_record(_validation_row("BEL"), _no_stop_path())

        self.assertIsNone(record["time_to_stop_hours"])
        self.assertIsNone(record["stop_price"])

    def test_structure_aggregation(self) -> None:
        rows = [
            create_mfe_mae_record(_validation_row("BEL"), _price_path()),
            create_mfe_mae_record(_validation_row("BEL", lead_line_id="lead-2"), _price_path_2()),
            create_mfe_mae_record(_validation_row("ACT", lead_line_id="lead-3"), _act_path()),
        ]

        stats = aggregate_mfe_mae_by_structure(rows)

        self.assertEqual(stats["structures"]["BEL"]["count"], 2)
        self.assertEqual(stats["structures"]["BEL"]["average_mfe"], 15.0)
        self.assertEqual(stats["structures"]["BEL"]["median_mae"], -5.5)
        self.assertEqual(stats["structures"]["ACT"]["average_mfe"], 3.0)

    def test_malformed_validation_rows_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "validation.jsonl"
            path.write_text(
                "\n".join(
                    [
                        "{bad-json",
                        json.dumps({"lead_line_id": "bad", "symbol": "BELUSDT", "is_trade_command": True}),
                        json.dumps(_validation_row("BEL")),
                    ]
                ),
                encoding="utf-8",
            )

            rows = load_validation_rows(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lead_line_id"], "lead-1")

    def test_write_mfe_mae_dataset_append_only(self) -> None:
        row = create_mfe_mae_record(_validation_row("BEL"), _price_path())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mfe_mae.jsonl"
            write_mfe_mae_dataset([row], output_path=path, append=True)
            write_mfe_mae_dataset([row], output_path=path, append=True)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)


def _validation_row(structure_type: str, lead_line_id: str = "lead-1") -> dict[str, object]:
    return {
        "validation_id": f"validation-{lead_line_id}",
        "signal_id": f"signal-{lead_line_id}",
        "shadow_signal_id": f"signal-{lead_line_id}",
        "lead_line_id": lead_line_id,
        "symbol": "BELUSDT" if structure_type != "ACT" else "ACTUSDT",
        "structure_type": structure_type,
        "validation_status": "VALIDATED",
        "is_trade_command": False,
    }


def _price_path() -> list[dict[str, float]]:
    return [
        {"hours_since_entry": 0, "price": 100.0},
        {"hours_since_entry": 1, "price": 98.0},
        {"hours_since_entry": 2, "price": 94.0},
        {"hours_since_entry": 3, "price": 110.0},
        {"hours_since_entry": 4, "price": 120.0},
        {"hours_since_entry": 5, "price": 115.0},
    ]


def _price_path_2() -> list[dict[str, float]]:
    return [
        {"hours_since_entry": 0, "price": 100.0},
        {"hours_since_entry": 1, "price": 95.0},
        {"hours_since_entry": 2, "price": 110.0},
    ]


def _act_path() -> list[dict[str, float]]:
    return [
        {"hours_since_entry": 0, "price": 100.0},
        {"hours_since_entry": 1, "price": 97.0},
        {"hours_since_entry": 2, "price": 103.0},
    ]


def _no_stop_path() -> list[dict[str, float]]:
    return [
        {"hours_since_entry": 0, "price": 100.0},
        {"hours_since_entry": 6, "price": 96.5},
        {"hours_since_entry": 12, "price": 104.0},
        {"hours_since_entry": 24, "price": 118.4},
    ]


if __name__ == "__main__":
    unittest.main()
