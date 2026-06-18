from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CoreTargetFeed:
    mode: str
    quote_asset: str
    btc_accumulation_bias: float
    focus_assets: List[str]
    confidence: float
    source: str
    engine: str = "CORE"


@dataclass
class WardRiskFeed:
    mode: str
    risk_hint: str
    escape_pressure: float
    risk_alignment: str
    warning_flags: List[str]
    source: str
    engine: str = "WARD"


@dataclass
class HoundHuntFeed:
    mode: str
    top_targets: List[str]
    priority_rank: Dict[str, int]
    hunt_pressure: float
    confidence: float
    source: str
    engine: str = "HOUND"


@dataclass
class TargetPipelinePayload:
    timestamp: int
    mode: str
    source: str
    core: CoreTargetFeed = field(metadata={"engine": "CORE"})
    ward: WardRiskFeed = field(metadata={"engine": "WARD"})
    hound: HoundHuntFeed = field(metadata={"engine": "HOUND"})
