from __future__ import annotations

from typing import List

from research.hellhound001.validation_schema import UniverseComparison


def _unique_preserve_order(symbols: List[str]) -> List[str]:
    seen = set()
    unique = []
    for symbol in symbols:
        normalized = str(symbol).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def compare_universes(
    production_symbols: List[str],
    lead_line_symbols: List[str],
) -> UniverseComparison:
    production_unique = _unique_preserve_order(production_symbols)
    lead_line_unique = _unique_preserve_order(lead_line_symbols)

    production_set = set(production_unique)
    lead_line_set = set(lead_line_unique)

    overlap = [symbol for symbol in production_unique if symbol in lead_line_set]
    lead_line_only = [symbol for symbol in lead_line_unique if symbol not in production_set]
    production_only = [symbol for symbol in production_unique if symbol not in lead_line_set]

    union_size = len(production_set | lead_line_set)
    overlap_ratio = round(len(overlap) / union_size, 4) if union_size else 0.0

    return UniverseComparison(
        production_symbols=production_unique,
        lead_line_symbols=lead_line_unique,
        overlap_symbols=overlap,
        lead_line_only=lead_line_only,
        production_only=production_only,
        overlap_ratio=overlap_ratio,
    )
