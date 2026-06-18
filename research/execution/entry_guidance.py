from __future__ import annotations

from research.execution.execution_schema import EntryGuidance, PatternHint


def build_entry_guidance(pattern: PatternHint) -> EntryGuidance:
    if pattern.pattern_name == "DISTRIBUTION_RISK":
        return EntryGuidance(
            entry_style="AVOID",
            reason="Distribution risk pattern does not support fresh entry guidance.",
        )
    if pattern.pattern_name in {"CHAIN_ROTATION", "SLOW_CREEP"}:
        return EntryGuidance(
            entry_style="WAIT_CONFIRMATION",
            reason="Pattern is constructive but still requires Hound confirmation.",
        )
    return EntryGuidance(
        entry_style="WAIT_CONFIRMATION",
        reason="LAB guidance does not issue direct entry commands.",
    )
