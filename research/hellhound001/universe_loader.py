from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from research.hellhound001.validation_schema import UniverseSnapshot
from research.whale_link_flow.lead_line_socket import get_hound_universe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP_GRAYMUG_ROOT = PROJECT_ROOT / "backup_GrayMUG"

PRODUCTION_FALLBACK_UNIVERSE = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
FALLBACK_NOTE = (
    "Production universe not found. Fallback used. This is not a real validation result."
)

READ_ONLY_CANDIDATES = [
    BACKUP_GRAYMUG_ROOT / "hound_watchlist.json",
    BACKUP_GRAYMUG_ROOT / "hound_watchlist.csv",
    BACKUP_GRAYMUG_ROOT / "hound" / "hound_watchlist.json",
    BACKUP_GRAYMUG_ROOT / "hound" / "hound_watchlist.csv",
]

SCANNER_SOURCE_PATH = BACKUP_GRAYMUG_ROOT / "hound" / "scanner.py"
RUN_HOUND_SOURCE_PATH = BACKUP_GRAYMUG_ROOT / "hound" / "run_hound.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_symbols(symbols: Iterable[str]) -> List[str]:
    clean = []
    seen = set()
    for symbol in symbols:
        normalized = str(symbol).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        clean.append(normalized)
    return clean


def load_lead_line_universe(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 12,
) -> UniverseSnapshot:
    symbols = get_hound_universe(mode=mode, top_n=top_n)
    return UniverseSnapshot(
        source="LEAD_LINE",
        mode=mode,
        symbols=_clean_symbols(symbols),
        timestamp=_utc_now(),
        source_path="research/whale_link_flow/lead_line_socket.py",
        is_fallback=False,
    )


def load_production_hound_universe(
    mode: str = "BTC_ACCUMULATION",
    top_n: int = 12,
) -> UniverseSnapshot:
    for path in READ_ONLY_CANDIDATES:
        symbols = _try_read_symbol_file(path)
        if symbols:
            return UniverseSnapshot(
                source="PRODUCTION_HOUND",
                mode=mode,
                symbols=_clean_symbols(symbols)[:top_n],
                timestamp=_utc_now(),
                source_path=_relative_path(path),
                is_fallback=False,
                note="Production universe loaded from explicit read-only universe file.",
            )

    scanner_symbols = _try_extract_static_symbols_from_scanner(SCANNER_SOURCE_PATH)
    if scanner_symbols:
        return UniverseSnapshot(
            source="PRODUCTION_HOUND",
            mode=mode,
            symbols=_clean_symbols(scanner_symbols)[:top_n],
            timestamp=_utc_now(),
            source_path=_relative_path(SCANNER_SOURCE_PATH),
            is_fallback=False,
            note="Production universe loaded from static scanner symbol list.",
        )

    _detect_dynamic_production_universe_source()

    return UniverseSnapshot(
        source="PRODUCTION_HOUND",
        mode=mode,
        symbols=PRODUCTION_FALLBACK_UNIVERSE[:top_n],
        timestamp=_utc_now(),
        source_path="fallback",
        is_fallback=True,
        note=FALLBACK_NOTE,
    )


def _try_read_symbol_file(path: Path) -> List[str]:
    if not path.exists() or not path.is_file():
        return []
    if path.suffix.lower() == ".json":
        return _read_json_symbols(path)
    if path.suffix.lower() == ".csv":
        return _read_csv_symbols(path)
    return []


def _read_json_symbols(path: Path) -> List[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(data, list):
        return [str(item) for item in data]
    if isinstance(data, dict):
        symbols = data.get("symbols")
        if isinstance(symbols, list):
            return [str(item) for item in symbols]
    return []


def _read_csv_symbols(path: Path) -> List[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return []
            symbol_field = "symbol" if "symbol" in reader.fieldnames else reader.fieldnames[0]
            return [str(row.get(symbol_field, "")) for row in reader]
    except OSError:
        return []


def _try_extract_static_symbols_from_scanner(path: Path) -> List[str]:
    """
    Read-only static extraction.

    Production Hound currently builds its universe dynamically from exchange tickers.
    This helper only accepts explicit source literals such as SYMBOLS = [...]
    or WATCHLIST = [...]. It does not execute or import production code.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    patterns = [
        r"(?:SYMBOLS|WATCHLIST|UNIVERSE|TOP30)\s*=\s*\[(?P<body>[^\]]+)\]",
        r"(?:symbols|watchlist|universe|top30)\s*=\s*\[(?P<body>[^\]]+)\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        symbols = re.findall(r"['\"]([A-Z0-9]+/[A-Z0-9]+)['\"]", match.group("body"))
        if symbols:
            return symbols
    return []


def _detect_dynamic_production_universe_source() -> str:
    if _source_contains(SCANNER_SOURCE_PATH, "def get_top_symbols") and _source_contains(
        SCANNER_SOURCE_PATH,
        "fetch_tickers",
    ):
        return f"{_relative_path(SCANNER_SOURCE_PATH)}:HoundScanner.get_top_symbols"
    if _source_contains(RUN_HOUND_SOURCE_PATH, "HoundScanner"):
        return f"{_relative_path(RUN_HOUND_SOURCE_PATH)}:HoundScanner"
    return ""


def _source_contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
