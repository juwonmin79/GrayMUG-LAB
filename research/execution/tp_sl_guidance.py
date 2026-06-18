from __future__ import annotations

from research.execution.execution_schema import PatternHint, TPSLGuidance


def build_tp_sl_guidance(pattern: PatternHint) -> TPSLGuidance:
    if pattern.pattern_name == "CHAIN_ROTATION":
        return TPSLGuidance(
            tp_case="CASE A",
            sl_case="CASE A",
            tp_template="TP 5%",
            sl_template="SL 3%",
        )
    if pattern.pattern_name == "SHOCK_PUMP":
        return TPSLGuidance(
            tp_case="CASE B",
            sl_case="CASE B",
            tp_template="TP 10%",
            sl_template="SL 5%",
        )
    return TPSLGuidance(
        tp_case="CASE C",
        sl_case="CASE C",
        tp_template="TP Dynamic",
        sl_template="SL Dynamic",
    )
