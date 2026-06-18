from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


SUPPORTED_MODES = {"BEAR_ESCAPE", "BTC_ACCUMULATION", "OBSERVE_ONLY"}

MODE_CONFIG = {
    "BEAR_ESCAPE": {
        "quote_asset": "USDT",
        "purpose": "USDT survival / risk avoidance",
        "core_direction": "defensive",
    },
    "BTC_ACCUMULATION": {
        "quote_asset": "BTC",
        "purpose": "increase BTC-denominated holdings",
        "core_direction": "accumulation",
    },
    "OBSERVE_ONLY": {
        "quote_asset": "NONE",
        "purpose": "observe / learn / no execution",
        "core_direction": "observe_only",
    },
}

DEFAULT_WATCH_PRIORITY_PATH = (
    Path(__file__).resolve().parents[2] / "outputs" / "whale_link_flow" / "watch_priority.csv"
)


class LeadLineSocket:
    """
    In-memory API socket for exposing Whale Link Flow output to Core, Hound, and Ward.

    This class does not modify Hound, Ward, Core, databases, or trading state. It only
    translates Watch Priority rows into the shared Lead Line contract.
    """

    def __init__(self, watch_priority_df: pd.DataFrame):
        self.watch_priority_df = self._validate_watch_priority_df(watch_priority_df)

    @classmethod
    def from_csv(cls, path: Path = DEFAULT_WATCH_PRIORITY_PATH) -> "LeadLineSocket":
        return cls(pd.read_csv(path))

    def get_current_lead_line(
        self,
        mode: str,
        top_n: int = 12,
        min_priority: float = 0.0,
    ) -> Dict:
        mode = self._validate_mode(mode)
        candidate_rows = self._latest_priority_rows(
            top_n=len(self.watch_priority_df),
            min_priority=min_priority,
        )
        quote_asset = MODE_CONFIG[mode]["quote_asset"]
        timestamp = self._latest_timestamp()

        items = []
        symbols = []
        for row in candidate_rows.to_dict("records"):
            symbol = str(row["symbol"])
            if quote_asset != "NONE" and symbol == quote_asset:
                continue
            pair = self._to_pair(symbol, quote_asset)
            symbols.append(pair)
            items.append(
                {
                    "symbol": symbol,
                    "pair": pair,
                    "priority_score": self._normalize_priority(row["priority_score"]),
                    "sector": str(row.get("sector", "UNKNOWN")),
                    "whale_type": str(row.get("whale_type", "UNKNOWN")),
                    "rank": len(items) + 1,
                }
            )
            if len(items) >= top_n:
                break

        return {
            "source": "whale_link_flow",
            "socket": "lead_line",
            "timestamp": timestamp,
            "mode": mode,
            "quote_asset": quote_asset,
            "hound_direct_modify": False,
            "symbols": symbols,
            "items": items,
        }

    def get_hound_universe(
        self,
        mode: str,
        top_n: int = 12,
        min_priority: float = 0.0,
    ) -> List[str]:
        return self.get_current_lead_line(
            mode=mode,
            top_n=top_n,
            min_priority=min_priority,
        )["symbols"]

    def get_ward_context(self, mode: str) -> Dict:
        mode = self._validate_mode(mode)
        latest = self._latest_priority_rows(top_n=12, min_priority=0.0)
        top_sectors = latest["sector"].value_counts().head(3).index.tolist()
        top_whale_types = latest["whale_type"].value_counts().head(3).index.tolist()

        return {
            "source": "whale_link_flow",
            "socket": "lead_line",
            "timestamp": self._latest_timestamp(),
            "mode": mode,
            "quote_asset": MODE_CONFIG[mode]["quote_asset"],
            "ward_independent_decision": True,
            "hound_direct_modify": False,
            "risk_context": {
                "max_priority_score": self._normalize_priority(latest["priority_score"].max()),
                "top_sectors": top_sectors,
                "top_whale_types": top_whale_types,
                "mode_purpose": MODE_CONFIG[mode]["purpose"],
            },
        }

    def get_core_payload(self, mode: str) -> Dict:
        mode = self._validate_mode(mode)
        return {
            "source": "whale_link_flow",
            "socket": "lead_line",
            "timestamp": self._latest_timestamp(),
            "mode": mode,
            "quote_asset": MODE_CONFIG[mode]["quote_asset"],
            "core_direction": MODE_CONFIG[mode]["core_direction"],
            "hound_direct_modify": False,
            "ward_independent_decision": True,
            "execution_authority": "core",
            "lead_line_role": "observation_priority",
        }

    @staticmethod
    def _validate_watch_priority_df(df: pd.DataFrame) -> pd.DataFrame:
        required = {"timestamp", "symbol", "priority_score", "sector", "whale_type"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"watch_priority_df missing required columns: {sorted(missing)}")

        clean = df.copy()
        clean = clean.dropna(subset=["timestamp", "symbol", "priority_score"])
        clean["timestamp"] = clean["timestamp"].astype("int64")
        clean["priority_score"] = pd.to_numeric(clean["priority_score"], errors="coerce")
        clean = clean.dropna(subset=["priority_score"])
        if clean.empty:
            raise ValueError("watch_priority_df has no usable rows")
        return clean

    @staticmethod
    def _validate_mode(mode: str) -> str:
        normalized = str(mode).upper()
        if normalized not in SUPPORTED_MODES:
            raise ValueError(f"unsupported mode: {mode}. supported modes: {sorted(SUPPORTED_MODES)}")
        return normalized

    def _latest_priority_rows(self, top_n: int, min_priority: float) -> pd.DataFrame:
        if top_n <= 0:
            return self.watch_priority_df.iloc[0:0]

        latest_timestamp = self.watch_priority_df["timestamp"].max()
        latest = self.watch_priority_df[self.watch_priority_df["timestamp"] == latest_timestamp].copy()
        latest["_normalized_priority"] = latest["priority_score"].map(self._normalize_priority)

        threshold = self._normalize_threshold(min_priority)
        latest = latest[latest["_normalized_priority"] >= threshold]
        latest = latest.sort_values("priority_score", ascending=False).head(top_n)
        return latest.drop(columns=["_normalized_priority"])

    def _latest_timestamp(self) -> int:
        return int(self.watch_priority_df["timestamp"].max())

    @staticmethod
    def _normalize_priority(priority_score: float) -> float:
        score = float(priority_score)
        if score > 1.0:
            score = score / 100.0
        return round(max(0.0, min(score, 1.0)), 4)

    @classmethod
    def _normalize_threshold(cls, min_priority: float) -> float:
        return cls._normalize_priority(min_priority)

    @staticmethod
    def _to_pair(symbol: str, quote_asset: str) -> str:
        if quote_asset == "NONE":
            return symbol
        if quote_asset == "BTC" and symbol == "BTC":
            return "BTC"
        return f"{symbol}/{quote_asset}"


_DEFAULT_SOCKET: Optional[LeadLineSocket] = None


def _get_default_socket() -> LeadLineSocket:
    global _DEFAULT_SOCKET
    if _DEFAULT_SOCKET is None:
        _DEFAULT_SOCKET = LeadLineSocket.from_csv()
    return _DEFAULT_SOCKET


def get_current_lead_line(
    mode: str,
    top_n: int = 12,
    min_priority: float = 0.0,
) -> Dict:
    return _get_default_socket().get_current_lead_line(mode, top_n, min_priority)


def get_hound_universe(
    mode: str,
    top_n: int = 12,
    min_priority: float = 0.0,
) -> List[str]:
    return _get_default_socket().get_hound_universe(mode, top_n, min_priority)


def get_ward_context(mode: str) -> Dict:
    return _get_default_socket().get_ward_context(mode)


def get_core_payload(mode: str) -> Dict:
    return _get_default_socket().get_core_payload(mode)
