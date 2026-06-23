from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import mfe_mae_production as mfe_mae_production_module
    from mfe_mae_production import build_mfe_mae_records_from_outcomes, update_mfe_mae_from_supabase
except ImportError:
    from . import mfe_mae_production as mfe_mae_production_module
    from .mfe_mae_production import build_mfe_mae_records_from_outcomes, update_mfe_mae_from_supabase


class ProductionMfeMaeTest(unittest.TestCase):
    def test_builds_record_from_calculated_outcome_windows(self) -> None:
        records = build_mfe_mae_records_from_outcomes([_signal()], {_signal()["id"]: _outcomes()})

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["signal_id"], _signal()["id"])
        self.assertEqual(record["shadow_signal_id"], _signal()["id"])
        self.assertEqual(record["symbol"], "BELUSDT")
        self.assertEqual(record["mfe_pct"], 20.0)
        self.assertEqual(record["mae_pct"], -5.0)
        self.assertEqual(record["time_to_peak_hours"], 24.0)
        self.assertEqual(record["time_to_stop_hours"], 4.0)
        self.assertEqual(record["calculated_window_count"], 3)
        self.assertFalse(record["is_trade_command"])

    def test_skips_pending_and_unpriced_outcomes(self) -> None:
        outcomes = [
            {**_outcomes()[0], "result": "PENDING"},
            {**_outcomes()[1], "current_price": None},
        ]
        records = build_mfe_mae_records_from_outcomes([_signal()], {_signal()["id"]: outcomes})

        self.assertEqual(records, [])

    def test_update_skips_existing_equal_completeness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mfe.jsonl"
            existing = build_mfe_mae_records_from_outcomes([_signal()], {_signal()["id"]: _outcomes()})[0]
            path.write_text(json.dumps(existing) + "\n", encoding="utf-8")

            with patch.object(mfe_mae_production_module, "_supabase_credentials", return_value=("url", "key")), patch.object(
                mfe_mae_production_module, "_load_recent_shadow_signals", return_value=[_signal()]
            ), patch.object(
                mfe_mae_production_module, "_load_outcomes_for_signals", return_value={_signal()["id"]: _outcomes()}
            ):
                result = update_mfe_mae_from_supabase(output_path=path, signal_limit=1)

        self.assertTrue(result.skipped)
        self.assertEqual(result.records, [])


def _signal() -> dict[str, object]:
    return {
        "id": "11111111-1111-4111-8111-111111111111",
        "symbol": "BELUSDT",
        "pattern": "BEL",
        "shadow_action": "WATCH",
    }


def _outcomes() -> list[dict[str, object]]:
    return [
        {
            "shadow_signal_id": _signal()["id"],
            "symbol": "BELUSDT",
            "evaluation_window": "1h",
            "entry_price": 100.0,
            "current_price": 98.0,
            "result": "FAIL",
        },
        {
            "shadow_signal_id": _signal()["id"],
            "symbol": "BELUSDT",
            "evaluation_window": "4h",
            "entry_price": 100.0,
            "current_price": 95.0,
            "result": "FAIL",
        },
        {
            "shadow_signal_id": _signal()["id"],
            "symbol": "BELUSDT",
            "evaluation_window": "24h",
            "entry_price": 100.0,
            "current_price": 120.0,
            "result": "SUCCESS",
        },
    ]


if __name__ == "__main__":
    unittest.main()
