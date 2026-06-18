from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class UniverseSnapshot:
    source: str
    mode: str
    symbols: List[str]
    timestamp: Optional[str] = None
    source_path: Optional[str] = None
    is_fallback: bool = False
    note: str = ""


@dataclass(frozen=True)
class UniverseComparison:
    production_symbols: List[str]
    lead_line_symbols: List[str]
    overlap_symbols: List[str]
    lead_line_only: List[str]
    production_only: List[str]
    overlap_ratio: float


@dataclass(frozen=True)
class Hellhound001Report:
    mode: str
    comparison: UniverseComparison
    production_universe_source: str
    production_universe_is_fallback: bool
    summary: Dict[str, Any] = field(default_factory=dict)
