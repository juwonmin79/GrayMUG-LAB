from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict


if __package__ is None or __package__ == "":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.hellhound001.universe_compare import compare_universes
from research.hellhound001.universe_loader import (
    FALLBACK_NOTE,
    PRODUCTION_FALLBACK_UNIVERSE,
    load_lead_line_universe,
    load_production_hound_universe,
)
from research.hellhound001.validation_schema import Hellhound001Report


OUTPUT_DIR = Path("outputs/hellhound001")
JSON_OUTPUT_PATH = OUTPUT_DIR / "universe_compare.json"
CSV_OUTPUT_PATH = OUTPUT_DIR / "universe_compare.csv"
SUMMARY_OUTPUT_PATH = OUTPUT_DIR / "summary.md"


def build_validation_report(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 12,
) -> Hellhound001Report:
    production = load_production_hound_universe(mode=mode, top_n=top_n)
    lead_line = load_lead_line_universe(mode=mode, top_n=top_n)
    comparison = compare_universes(
        production_symbols=production.symbols,
        lead_line_symbols=lead_line.symbols,
    )

    used_fallback = production.is_fallback
    production_universe_source = production.source_path or "unknown"
    summary: Dict = {
        "runner": "hellhound001_validation_runner",
        "mode": mode,
        "top_n": top_n,
        "production_source": production.source,
        "lead_line_source": lead_line.source,
        "production_universe_source": production_universe_source,
        "production_universe_is_fallback": used_fallback,
        "production_count": len(production.symbols),
        "lead_line_count": len(lead_line.symbols),
        "overlap_count": len(comparison.overlap_symbols),
        "overlap_ratio": comparison.overlap_ratio,
        "note": production.note or ("Production universe loaded read-only." if not used_fallback else FALLBACK_NOTE),
    }
    return Hellhound001Report(
        mode=mode,
        comparison=comparison,
        production_universe_source=production_universe_source,
        production_universe_is_fallback=used_fallback,
        summary=summary,
    )


def write_outputs(report: Hellhound001Report) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    JSON_OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_csv(report)
    _write_summary(report)


def _write_csv(report: Hellhound001Report) -> None:
    comparison = report.comparison
    rows = []
    max_len = max(
        len(comparison.production_symbols),
        len(comparison.lead_line_symbols),
        len(comparison.overlap_symbols),
        len(comparison.lead_line_only),
        len(comparison.production_only),
        1,
    )
    for idx in range(max_len):
        rows.append(
            {
                "row": idx + 1,
                "production_symbol": _get_or_empty(comparison.production_symbols, idx),
                "lead_line_symbol": _get_or_empty(comparison.lead_line_symbols, idx),
                "overlap_symbol": _get_or_empty(comparison.overlap_symbols, idx),
                "lead_line_only": _get_or_empty(comparison.lead_line_only, idx),
                "production_only": _get_or_empty(comparison.production_only, idx),
                "overlap_ratio": comparison.overlap_ratio,
            }
        )

    with CSV_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(report: Hellhound001Report) -> None:
    comparison = report.comparison
    lines = [
        "# Hellhound-001 Universe Compare Summary",
        "",
        f"- Mode: `{report.mode}`",
        f"- Production universe source: `{report.production_universe_source}`",
        f"- Production universe fallback: `{report.production_universe_is_fallback}`",
        f"- Production symbols: `{len(comparison.production_symbols)}`",
        f"- Lead Line symbols: `{len(comparison.lead_line_symbols)}`",
        f"- Overlap count: `{len(comparison.overlap_symbols)}`",
        f"- Overlap ratio: `{comparison.overlap_ratio:.4f}`",
        f"- Note: {report.summary['note']}",
        "",
        "## Production Hound Universe",
        "",
        *[f"- `{symbol}`" for symbol in comparison.production_symbols],
        "",
        "## Lead Line Universe",
        "",
        *[f"- `{symbol}`" for symbol in comparison.lead_line_symbols],
        "",
        "## Lead Line Only",
        "",
        *[f"- `{symbol}`" for symbol in comparison.lead_line_only],
    ]
    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _get_or_empty(values: list[str], idx: int) -> str:
    return values[idx] if idx < len(values) else ""


def run_validation(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 12,
) -> Hellhound001Report:
    report = build_validation_report(mode=mode, top_n=top_n)
    write_outputs(report)
    return report


def main() -> None:
    report = run_validation(mode="BTC_ACCUMULATION", top_n=12)
    comparison = report.comparison

    print("HELLHOUND-001 VALIDATION RUNNER")
    print("MODE")
    print(report.mode)
    print("PRODUCTION HOUND UNIVERSE")
    for symbol in comparison.production_symbols:
        print(symbol)
    print("LEAD LINE UNIVERSE")
    for symbol in comparison.lead_line_symbols:
        print(symbol)
    print("OVERLAP")
    print(len(comparison.overlap_symbols))
    print("LEAD LINE ONLY")
    for symbol in comparison.lead_line_only:
        print(symbol)
    print("NOTE")
    print(report.summary["note"])


if __name__ == "__main__":
    main()
