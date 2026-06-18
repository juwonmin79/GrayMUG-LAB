from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from research.hellhound001.validation_schema import UniverseSnapshot
from research.whale_link_flow.lead_line_socket import get_hound_universe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP_GRAYMUG_ROOT = PROJECT_ROOT / "backup_GrayMUG"

PRODUCTION_FALLBACK_UNIVERSE = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
FALLBACK_NOTE = (
    "Production universe fallback is only for runner skeleton test. "
    "It is not a validation result."
)

READ_ONLY_CANDIDATES = [
    BACKUP_GRAYMUG_ROOT / "hound_watchlist.json",
    BACKUP_GRAYMUG_ROOT / "hound_watchlist.csv",
    BACKUP_GRAYMUG_ROOT / "hound" / "hound_watchlist.json",
    BACKUP_GRAYMUG_ROOT / "hound" / "hound_watchlist.csv",
]


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
            )

    return UniverseSnapshot(
        source="PRODUCTION_HOUND",
        mode=mode,
        symbols=PRODUCTION_FALLBACK_UNIVERSE[:top_n],
        timestamp=_utc_now(),
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
