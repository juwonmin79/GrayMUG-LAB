from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

try:
    from integration_stub import optional_hellhound_decision
    from shadow_advisor import (
        analyze_false_positives,
        audit_decision,
        replay_validation,
        run_shadow_evaluation_pipeline,
        write_shadow_decision_log,
    )
    from test_accumulation_features import _bel_base_candles, _distribution_candles, _signals
except ImportError:
    from .integration_stub import optional_hellhound_decision
    from .shadow_advisor import (
        analyze_false_positives,
        audit_decision,
        replay_validation,
        run_shadow_evaluation_pipeline,
        write_shadow_decision_log,
    )
    from .test_accumulation_features import _bel_base_candles, _distribution_candles, _signals


class ShadowAdvisorTest(unittest.TestCase):
    def test_optional_hellhound_decision_returns_shadow_advice(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"

        decision = optional_hellhound_decision(
            "BELUSDT",
            signal=_signals("BELUSDT", 1)[0],
            shadow_signals=_signals("BELUSDT", 40),
            historical_candles=_bel_base_candles(),
        )

        self.assertEqual(decision["symbol"], "BELUSDT")
        self.assertEqual(decision["promotion_status"], "PROMOTE")
        self.assertFalse(decision["is_trade_command"])
        self.assertIn("hellhound_score", decision)

    def test_optional_hellhound_decision_fail_safe_neutral(self) -> None:
        os.environ.pop("HELLHOUND_DECISION_ENABLED", None)

        decision = optional_hellhound_decision("BELUSDT")

        self.assertEqual(decision["entry_bias"], "neutral")
        self.assertEqual(decision["promotion_status"], "WATCH")
        self.assertFalse(decision["is_trade_command"])
        self.assertIn("error", decision)

    def test_audit_decision_shape(self) -> None:
        audit = audit_decision(
            symbol="BELUSDT",
            signal_time="2026-06-20T00:00:00+00:00",
            event_id="event-1",
            hellhound_score=0.68,
            promotion_status="PROMOTE",
            entry_bias="neutral",
            actual_1h_outcome="SUCCESS",
        )

        self.assertEqual(audit["symbol"], "BELUSDT")
        self.assertEqual(audit["actual_1h_outcome"], "SUCCESS")
        self.assertFalse(audit["is_trade_command"])

    def test_shadow_pipeline_writes_jsonl_log_only(self) -> None:
        os.environ["HELLHOUND_DECISION_ENABLED"] = "true"
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "shadow_decision_log.jsonl"
            result = run_shadow_evaluation_pipeline(
                symbol="BELUSDT",
                signal=_signals("BELUSDT", 1)[0],
                shadow_signals=_signals("BELUSDT", 40),
                historical_candles=_bel_base_candles(),
                log_path=log_path,
            )
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(result["pipeline"], "Hound Signal -> Hellhound Evaluate -> Shadow Decision -> Log Only")
        self.assertFalse(result["is_trade_command"])
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["symbol"], "BELUSDT")

    def test_replay_validation_and_false_positive_analysis(self) -> None:
        rows = replay_validation(_replay_cases())
        analysis = analyze_false_positives(rows)
        comparison = {row["symbol"]: row["comparison"] for row in rows}

        self.assertEqual(comparison["BELUSDT"], "PROMOTE_SUCCESS")
        self.assertEqual(comparison["ACTUSDT"], "REJECT_FAIL_AVOIDED")
        self.assertEqual(comparison["ACEUSDT"], "PROMOTE_FAIL")
        self.assertEqual(comparison["METUSDT"], "REJECT_SUCCESS_FALSE_NEGATIVE")
        self.assertEqual(analysis["false_positive_count"], 1)
        self.assertEqual(analysis["false_negative_count"], 1)
        self.assertGreaterEqual(len(analysis["top_failure_reasons"]), 1)
        self.assertGreaterEqual(len(analysis["top_success_reasons"]), 1)

    def test_write_shadow_decision_log_explicit(self) -> None:
        audit = audit_decision(
            symbol="ACTUSDT",
            signal_time="2026-06-20T00:00:00+00:00",
            event_id="event-2",
            hellhound_score=0.1,
            promotion_status="REJECT",
            entry_bias="neutral",
        )
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "lab_shadow_decisions.jsonl"
            result = write_shadow_decision_log(audit, log_path=log_path)
            logged = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertTrue(result["written"])
        self.assertEqual(logged["symbol"], "ACTUSDT")
        self.assertFalse(logged["is_trade_command"])


def _replay_cases() -> list[dict[str, object]]:
    return [
        {
            "symbol": "BELUSDT",
            "hound_signal": _signals("BELUSDT", 1)[0],
            "hellhound_decision": {
                "symbol": "BELUSDT",
                "setup_type": "BEL",
                "promotion_status": "PROMOTE",
                "reasons": ["ACCUMULATION_BASE has sufficient accumulation and repeat activity with low risk."],
            },
            "actual_outcome": {"actual_24h_outcome": "SUCCESS"},
        },
        {
            "symbol": "ACTUSDT",
            "hound_signal": _signals("ACTUSDT", 1)[0],
            "hellhound_decision": {
                "symbol": "ACTUSDT",
                "setup_type": "ACT",
                "promotion_status": "REJECT",
                "reasons": ["distribution_risk is too high for shadow promotion."],
            },
            "actual_outcome": {"actual_24h_outcome": "FAIL"},
        },
        {
            "symbol": "ACEUSDT",
            "hound_signal": _signals("ACEUSDT", 1)[0],
            "hellhound_decision": {
                "symbol": "ACEUSDT",
                "setup_type": "ACE",
                "promotion_status": "PROMOTE",
                "reasons": ["hellhound_score >= 0.60 and distribution_risk <= 0.40."],
            },
            "actual_outcome": {"actual_24h_outcome": "FAIL"},
        },
        {
            "symbol": "METUSDT",
            "hound_signal": _signals("METUSDT", 1)[0],
            "hellhound_decision": {
                "symbol": "METUSDT",
                "setup_type": "MET",
                "promotion_status": "REJECT",
                "reasons": ["score is too weak for shadow promotion."],
            },
            "actual_outcome": {"actual_24h_outcome": "SUCCESS"},
        },
        {
            "symbol": "NIGHTUSDT",
            "hound_signal": _signals("NIGHTUSDT", 1)[0],
            "hellhound_decision": {
                "symbol": "NIGHTUSDT",
                "setup_type": "NIGHT",
                "promotion_status": "WATCH",
                "reasons": ["middle score/risk profile remains watchable."],
            },
            "actual_outcome": {"actual_24h_outcome": "SUCCESS"},
        },
    ]


if __name__ == "__main__":
    unittest.main()
