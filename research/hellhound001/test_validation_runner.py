from __future__ import annotations

import os
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.hellhound001.universe_compare import compare_universes
from research.hellhound001.universe_loader import (
    load_lead_line_universe,
    load_production_hound_universe,
)
from research.hellhound001.validation_runner import (
    CSV_OUTPUT_PATH,
    JSON_OUTPUT_PATH,
    SUMMARY_OUTPUT_PATH,
    run_validation,
)
from research.hellhound001.validation_schema import Hellhound001Report, UniverseComparison


def test_validation_runner() -> None:
    lead_line = load_lead_line_universe(mode="BTC_ACCUMULATION", top_n=3)
    assert lead_line.source == "LEAD_LINE"
    assert lead_line.symbols

    production = load_production_hound_universe(mode="BTC_ACCUMULATION", top_n=3)
    assert production.source == "PRODUCTION_HOUND"
    assert production.symbols

    comparison = compare_universes(production.symbols, lead_line.symbols)
    assert isinstance(comparison, UniverseComparison)
    assert 0.0 <= comparison.overlap_ratio <= 1.0

    report = run_validation(mode="BTC_ACCUMULATION", top_n=12)
    assert isinstance(report, Hellhound001Report)
    assert report.mode == "BTC_ACCUMULATION"
    assert report.summary["production_count"] > 0
    assert report.summary["lead_line_count"] > 0

    assert JSON_OUTPUT_PATH.exists()
    assert CSV_OUTPUT_PATH.exists()
    assert SUMMARY_OUTPUT_PATH.exists()


if __name__ == "__main__":
    test_validation_runner()
    print("Hellhound-001 validation runner smoke test passed")
