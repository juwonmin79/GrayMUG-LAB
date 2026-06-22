from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from missed_case_registry import create_missed_case_record, write_missed_cases
    from success_case_registry import create_success_case_record, write_success_cases
except ImportError:
    from .missed_case_registry import create_missed_case_record, write_missed_cases
    from .success_case_registry import create_success_case_record, write_success_cases


class CaseRegistriesTest(unittest.TestCase):
    def test_missed_case_captures_required_review_fields(self) -> None:
        record = create_missed_case_record(
            symbol="btcusdt",
            outcome_time="2026-06-23T00:00:00+00:00",
            case_name="recent_btc_rise",
            hound_scan={"result": "no_alert"},
            shadow_result={"hellhound_score": 0.21, "promotion_status": "WATCH", "structure_type": "NIGHT"},
        )

        self.assertEqual(record["symbol"], "BTCUSDT")
        self.assertEqual(record["case_type"], "MISSED")
        self.assertEqual(record["hellhound_score"], 0.21)
        self.assertEqual(record["promotion_status"], "WATCH")
        self.assertEqual(record["structure_classification"], "NIGHT")
        self.assertFalse(record["is_trade_command"])

    def test_success_case_captures_pre_outcome_signal(self) -> None:
        record = create_success_case_record(
            symbol="belusdt",
            signal_time="2026-06-22T00:00:00+00:00",
            outcome_time="2026-06-23T00:00:00+00:00",
            case_name="bel_pre_move",
            hellhound_score=0.86,
            promotion_status="PROMOTE",
            structure_classification="BEL",
            mfe_pct=18.0,
            mae_pct=-3.0,
        )

        self.assertEqual(record["case_type"], "SUCCESS")
        self.assertEqual(record["symbol"], "BELUSDT")
        self.assertEqual(record["structure_classification"], "BEL")
        self.assertFalse(record["is_trade_command"])

    def test_registries_write_append_only_jsonl(self) -> None:
        missed = create_missed_case_record(
            symbol="BTCUSDT",
            outcome_time="2026-06-23T00:00:00+00:00",
            case_name="recent_btc_rise",
        )
        success = create_success_case_record(
            symbol="BELUSDT",
            signal_time="2026-06-22T00:00:00+00:00",
            outcome_time="2026-06-23T00:00:00+00:00",
            case_name="bel_pre_move",
        )
        with tempfile.TemporaryDirectory() as directory:
            missed_path = Path(directory) / "missed.jsonl"
            success_path = Path(directory) / "success.jsonl"
            write_missed_cases([missed], output_path=missed_path, append=True)
            write_missed_cases([missed], output_path=missed_path, append=True)
            write_success_cases([success], output_path=success_path, append=True)

            missed_rows = [json.loads(line) for line in missed_path.read_text(encoding="utf-8").splitlines()]
            success_rows = [json.loads(line) for line in success_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(missed_rows), 2)
        self.assertEqual(len(success_rows), 1)
        self.assertFalse(missed_rows[0]["is_trade_command"])
        self.assertFalse(success_rows[0]["is_trade_command"])


if __name__ == "__main__":
    unittest.main()
