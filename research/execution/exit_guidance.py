from __future__ import annotations

from research.execution.execution_schema import ExitGuidance, PatternHint


def build_exit_guidance(pattern: PatternHint) -> ExitGuidance:
    triggers = ["WARD_RISK_UP"]

    if pattern.pattern_name == "BTC_HIDE":
        triggers.append("BTC_HIDE")
    if pattern.pattern_name == "DISTRIBUTION_RISK":
        triggers.append("DISTRIBUTION_SPIKE")
    if pattern.pattern_name in {"CHAIN_ROTATION", "SLOW_CREEP"}:
        triggers.append("LEAD_LINE_BREAK")

    return ExitGuidance(
        exit_triggers=triggers,
        reason="Exit triggers are guidance only and do not close positions.",
    )
