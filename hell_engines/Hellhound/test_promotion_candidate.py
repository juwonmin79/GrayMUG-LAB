from __future__ import annotations

import unittest

try:
    from promotion_candidate import (
        build_shadow_decision,
        compute_outcome_correlation,
        evaluate_promotion_candidate,
        replay_shadow_cases,
    )
except ImportError:
    from .promotion_candidate import (
        build_shadow_decision,
        compute_outcome_correlation,
        evaluate_promotion_candidate,
        replay_shadow_cases,
    )


class PromotionCandidateTest(unittest.TestCase):
    def test_promote_low_risk_high_score(self) -> None:
        result = evaluate_promotion_candidate(
            hellhound_score=0.68,
            accumulation_score=0.62,
            repeat_activity_score=0.4,
            structure_type="ACCUMULATION_BASE",
            distribution_risk=0.28,
        )

        self.assertEqual(result["promotion_status"], "PROMOTE")

    def test_reject_high_distribution_risk(self) -> None:
        result = evaluate_promotion_candidate(
            hellhound_score=0.72,
            accumulation_score=0.2,
            repeat_activity_score=0.1,
            structure_type="DISTRIBUTION",
            distribution_risk=0.88,
        )

        self.assertEqual(result["promotion_status"], "REJECT")

    def test_build_shadow_decision_is_not_trade_command(self) -> None:
        decision = build_shadow_decision(
            symbol="BELUSDT",
            setup_type="BEL",
            structure_type="ACCUMULATION_BASE",
            hellhound_score=0.58,
            accumulation_score=0.56,
            repeat_activity_score=0.28,
            distribution_risk=0.22,
        )

        self.assertEqual(decision["promotion_status"], "PROMOTE")
        self.assertFalse(decision["is_trade_command"])

    def test_bel_act_ace_met_night_replay(self) -> None:
        replay = replay_shadow_cases(_replay_cases())
        by_setup = {row["setup_type"]: row["promotion_status"] for row in replay}

        self.assertEqual(by_setup["BEL"], "PROMOTE")
        self.assertEqual(by_setup["ACT"], "REJECT")
        self.assertEqual(by_setup["ACE"], "REJECT")
        self.assertEqual(by_setup["MET"], "WATCH")
        self.assertEqual(by_setup["NIGHT"], "WATCH")

    def test_outcome_correlation_score_bands(self) -> None:
        correlation = compute_outcome_correlation(_outcome_rows())
        bands = {row["score_band"]: row for row in correlation["score_bands"]}

        self.assertEqual(bands["0.0~0.2"]["win_rate"], 0.0)
        self.assertEqual(bands["0.6~0.8"]["win_rate"], 1.0)
        self.assertEqual(bands["0.8~1.0"]["windows"]["24h"]["win_rate"], 1.0)


def _replay_cases() -> list[dict[str, object]]:
    return [
        {
            "symbol": "BELUSDT",
            "setup_type": "BEL",
            "structure_type": "ACCUMULATION_BASE",
            "hellhound_score": 0.68,
            "accumulation_score": 0.62,
            "repeat_activity_score": 0.42,
            "distribution_risk": 0.22,
        },
        {
            "symbol": "ACTUSDT",
            "setup_type": "ACT",
            "structure_type": "DISTRIBUTION",
            "hellhound_score": 0.12,
            "accumulation_score": 0.0,
            "repeat_activity_score": 0.0,
            "distribution_risk": 0.94,
        },
        {
            "symbol": "ACEUSDT",
            "setup_type": "ACE",
            "structure_type": "DISTRIBUTION",
            "hellhound_score": 0.52,
            "accumulation_score": 0.25,
            "repeat_activity_score": 0.48,
            "distribution_risk": 0.72,
        },
        {
            "symbol": "METUSDT",
            "setup_type": "MET",
            "structure_type": "ACCUMULATION_BASE",
            "hellhound_score": 0.48,
            "accumulation_score": 0.56,
            "repeat_activity_score": 0.12,
            "distribution_risk": 0.31,
        },
        {
            "symbol": "NIGHTUSDT",
            "setup_type": "NIGHT",
            "structure_type": "MID_CYCLE",
            "hellhound_score": 0.57,
            "accumulation_score": 0.42,
            "repeat_activity_score": 0.62,
            "distribution_risk": 0.48,
        },
    ]


def _outcome_rows() -> list[dict[str, object]]:
    return [
        {"hellhound_score": 0.12, "evaluation_window": "1h", "result": "FAIL"},
        {"hellhound_score": 0.32, "evaluation_window": "4h", "result": "FAIL"},
        {"hellhound_score": 0.52, "evaluation_window": "24h", "result": "SUCCESS"},
        {"hellhound_score": 0.66, "evaluation_window": "1h", "result": "SUCCESS"},
        {"hellhound_score": 0.72, "evaluation_window": "4h", "result": "SUCCESS"},
        {"hellhound_score": 0.88, "evaluation_window": "24h", "result": "SUCCESS"},
    ]


if __name__ == "__main__":
    unittest.main()
