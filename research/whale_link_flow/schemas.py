from dataclasses import dataclass
from typing import List, Dict, Optional
import datetime

@dataclass
class AssetFeatures:
    timestamp: int
    datetime: datetime.datetime
    close: float
    volume: float
    rs_vs_btc: float
    rs_zscore: float
    volume_rank: float
    rank_momentum: float
    volume_slope: float
    price_slope: float
    volatility_expansion: float

@dataclass
class FlowEdge:
    source: str
    target: str
    weight: float       # probability of capital flow (0.0 to 1.0)
    lag_candles: int    # time delay in candles
    confidence: float   # confidence level (0.0 to 1.0)
    timestamp: int
    narrative: str

@dataclass
class FlowGraphState:
    timestamp: int
    datetime: datetime.datetime
    nodes: Dict[str, float]      # asset symbol -> Whale Link Score (0 to 100)
    edges: List[FlowEdge]        # active edges with flow probability > threshold

@dataclass
class WhaleLinkAlert:
    timestamp: int
    datetime: datetime.datetime
    path: List[str]              # e.g., ["BTC", "ETH", "SOL", "FET"]
    confidence: float            # e.g., 0.72 (72%)
    lead_score: float            # e.g., 84.0
    narrative: str               # e.g., "AI Rotation"
