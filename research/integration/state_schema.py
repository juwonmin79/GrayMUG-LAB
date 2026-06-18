from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LeadLineState:
    timestamp: int
    mode: str
    quote_asset: str
    symbols: List[str]
    source: str


@dataclass
class CoreState:
    mode: str
    quote_asset: str
    btc_accumulation: bool
    focus_assets: List[str]


@dataclass
class WardState:
    regime: str
    risk_level: str
    warning_flags: List[str]


@dataclass
class HoundState:
    tracked_symbols: List[str]
    priority_rank: Dict[str, int]
    target_count: int


@dataclass
class SimulatorState:
    core: CoreState
    ward: WardState
    hound: HoundState
    lead_line: LeadLineState
