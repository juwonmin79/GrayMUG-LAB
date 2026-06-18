from __future__ import annotations

from dataclasses import dataclass
from typing import List


PATTERN_NAMES = {
    "SLOW_CREEP",
    "SHOCK_PUMP",
    "DISTRIBUTION_RISK",
    "CHAIN_ROTATION",
    "BTC_HIDE",
}


@dataclass
class PatternHint:
    pattern_name: str
    confidence: float
    description: str


@dataclass
class EntryGuidance:
    entry_style: str
    reason: str


@dataclass
class TPSLGuidance:
    tp_case: str
    sl_case: str
    tp_template: str
    sl_template: str


@dataclass
class ExitGuidance:
    exit_triggers: List[str]
    reason: str


@dataclass
class ExecutionGuidancePayload:
    target: str
    pattern: PatternHint
    entry: EntryGuidance
    tp_sl: TPSLGuidance
    exit: ExitGuidance
    source: str = "execution_guidance_api"
