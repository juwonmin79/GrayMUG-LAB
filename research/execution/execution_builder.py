from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from research.execution.entry_guidance import build_entry_guidance
from research.execution.exit_guidance import build_exit_guidance
from research.execution.execution_schema import ExecutionGuidancePayload, PatternHint
from research.execution.tp_sl_guidance import build_tp_sl_guidance


def build_execution_guidance_payload(
    target: str,
    pattern: PatternHint,
) -> Dict:
    payload = ExecutionGuidancePayload(
        target=target,
        pattern=pattern,
        entry=build_entry_guidance(pattern),
        tp_sl=build_tp_sl_guidance(pattern),
        exit=build_exit_guidance(pattern),
    )
    return asdict(payload)
