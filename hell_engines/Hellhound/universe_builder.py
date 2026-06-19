from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib import error, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


UNIVERSE_SNAPSHOT_TABLE = "hellhound_universe_snapshots"
LOCAL_FIXTURE_PATH = (
    Path(__file__).resolve().parent / "test_data" / "universe_builder_fixture.json"
)
DEFAULT_EXCHANGE_NAME = "binance"
DEFAULT_TOP_N = 30

LOGGER = logging.getLogger("hellhound.universe_builder")


@dataclass(frozen=True)
class ExchangeConfig:
    exchange_name: str
    api_key_present: bool
    api_secret_present: bool
    testnet: bool


@dataclass(frozen=True)
class UniverseCandidate:
    symbol: str
    base_asset: Optional[str]
    quote_asset: str
    quote_volume: float
    volume_ratio: Optional[float]
    price_change_pct: float
    volatility: float
    last_price: Optional[float]
    rank_score: float


@dataclass(frozen=True)
class UniverseBuilderResult:
    ok: bool
    local_mode: bool
    stored: bool
    skipped_store: bool
    message: str
    exchange: ExchangeConfig
    generated_at: str
    candidates_count: int
    top_symbols: list[str]
    universe: list[Dict[str, Any]]


class UniverseBuilderError(RuntimeError):
    pass


def build_universe_from_market_data(
    market_data: Mapping[str, Any], *, top_n: int = DEFAULT_TOP_N
) -> tuple[list[Dict[str, Any]], int]:
    markets = _extract_markets(market_data)
    tickers = _extract_tickers(market_data)
    allowed_usdt_symbols = _usdt_symbols_from_markets(markets)

    candidates: list[UniverseCandidate] = []
    for ticker in tickers:
        symbol = _symbol_from_ticker(ticker)
        if not symbol:
            continue
        symbol = symbol.upper()
        if allowed_usdt_symbols is not None and symbol not in allowed_usdt_symbols:
            continue
        if allowed_usdt_symbols is None and not symbol.endswith("USDT"):
            continue

        market = markets.get(symbol, {})
        base_asset = _string_or_none(market.get("baseAsset") or market.get("base"))
        quote_asset = str(
            market.get("quoteAsset")
            or market.get("quote")
            or _quote_asset_from_symbol(symbol)
            or ""
        ).upper()
        if quote_asset != "USDT":
            continue

        quote_volume = _first_float(
            ticker,
            "quoteVolume",
            "quote_volume",
            "turnover24h",
            "volumeQuote",
        )
        if quote_volume is None or quote_volume <= 0:
            continue

        price_change_pct = _first_float(
            ticker,
            "priceChangePercent",
            "price_change_pct",
            "priceChangePcnt",
        )
        volume_ratio = _first_float(ticker, "volume_ratio", "volumeRatio")
        last_price = _first_float(ticker, "lastPrice", "last_price", "last")
        high_price = _first_float(ticker, "highPrice", "high_price", "high")
        low_price = _first_float(ticker, "lowPrice", "low_price", "low")
        volatility = _volatility(high_price, low_price, last_price)

        if price_change_pct is None:
            price_change_pct = 0.0

        candidates.append(
            UniverseCandidate(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                quote_volume=quote_volume,
                volume_ratio=volume_ratio,
                price_change_pct=price_change_pct,
                volatility=volatility,
                last_price=last_price,
                rank_score=_rank_score(
                    quote_volume=quote_volume,
                    volume_ratio=volume_ratio,
                    price_change_pct=price_change_pct,
                    volatility=volatility,
                ),
            )
        )

    ranked = sorted(
        candidates,
        key=lambda item: (
            item.quote_volume,
            item.volume_ratio if item.volume_ratio is not None else -1.0,
            item.price_change_pct,
            item.volatility,
            item.symbol,
        ),
        reverse=True,
    )
    return (
        [
            _candidate_payload(index, candidate)
            for index, candidate in enumerate(ranked[:top_n], start=1)
        ],
        len(candidates),
    )


def build_dynamic_top30_universe() -> UniverseBuilderResult:
    config = _exchange_config()
    local_mode = _local_mode_enabled()
    generated_at = _now_utc()

    try:
        market_data = (
            _load_local_fixture()
            if local_mode
            else _load_exchange_market_data(config)
        )
        universe, candidates_count = build_universe_from_market_data(
            market_data, top_n=DEFAULT_TOP_N
        )
    except (OSError, ValueError, json.JSONDecodeError, UniverseBuilderError) as exc:
        LOGGER.error("Hellhound universe build failed: %s", exc)
        return UniverseBuilderResult(
            ok=False,
            local_mode=local_mode,
            stored=False,
            skipped_store=True,
            message=str(exc),
            exchange=config,
            generated_at=generated_at,
            candidates_count=0,
            top_symbols=[],
            universe=[],
        )

    top_symbols = [row["symbol"] for row in universe]
    stored = False
    skipped_store = True
    message = f"built top {len(top_symbols)} Hellhound universe symbols"

    if _store_supabase_enabled():
        supabase_url, supabase_key = _supabase_credentials()
        if not supabase_url or not supabase_key:
            message = f"{message}; missing Supabase environment, store skipped"
        else:
            try:
                _insert_universe_snapshot(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    exchange=config,
                    generated_at=generated_at,
                    candidates_count=candidates_count,
                    universe=universe,
                    top_symbols=top_symbols,
                )
                stored = True
                skipped_store = False
            except UniverseBuilderError as exc:
                LOGGER.error("Hellhound universe snapshot store failed: %s", exc)
                return UniverseBuilderResult(
                    ok=False,
                    local_mode=local_mode,
                    stored=False,
                    skipped_store=False,
                    message=str(exc),
                    exchange=config,
                    generated_at=generated_at,
                    candidates_count=candidates_count,
                    top_symbols=top_symbols,
                    universe=universe,
                )

    return UniverseBuilderResult(
        ok=True,
        local_mode=local_mode,
        stored=stored,
        skipped_store=skipped_store,
        message=message,
        exchange=config,
        generated_at=generated_at,
        candidates_count=candidates_count,
        top_symbols=top_symbols,
        universe=universe,
    )


def _load_exchange_market_data(config: ExchangeConfig) -> Dict[str, Any]:
    base_url = _exchange_base_url(config.exchange_name, config.testnet)
    exchange_info = _exchange_json(f"{base_url}/api/v3/exchangeInfo")
    tickers = _exchange_json(f"{base_url}/api/v3/ticker/24hr")
    return {"exchangeInfo": exchange_info, "tickers": tickers}


def _exchange_base_url(exchange_name: str, testnet: bool) -> str:
    normalized = exchange_name.strip().lower()
    if normalized in {"binance", "binance_spot", "binance-spot"}:
        return "https://testnet.binance.vision" if testnet else "https://api.binance.com"
    if normalized in {"binanceus", "binance_us", "binance-us"}:
        if testnet:
            raise UniverseBuilderError("binanceus testnet market data is not configured")
        return "https://api.binance.us"
    raise UniverseBuilderError(f"unsupported exchange {exchange_name!r}")


def _exchange_json(endpoint: str) -> Any:
    req = request.Request(endpoint, method="GET", headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise UniverseBuilderError(f"exchange HTTP {exc.code}: {safe_body}") from exc
    except error.URLError as exc:
        raise UniverseBuilderError(f"exchange connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise UniverseBuilderError("exchange market data request timed out") from exc
    except json.JSONDecodeError as exc:
        raise UniverseBuilderError("exchange market data response was not JSON") from exc


def _insert_universe_snapshot(
    *,
    supabase_url: str,
    supabase_key: str,
    exchange: ExchangeConfig,
    generated_at: str,
    candidates_count: int,
    universe: list[Mapping[str, Any]],
    top_symbols: list[str],
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{UNIVERSE_SNAPSHOT_TABLE}"
    body = {
        "exchange_name": exchange.exchange_name,
        "exchange_testnet": exchange.testnet,
        "generated_at": generated_at,
        "top_n": len(top_symbols),
        "candidates_count": candidates_count,
        "symbols": top_symbols,
        "universe_payload": universe,
    }
    status, _ = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="POST",
        body=body,
        prefer="return=minimal",
    )
    if status < 200 or status >= 300:
        raise UniverseBuilderError(f"unexpected Supabase status {status}")


def _supabase_json(
    *,
    endpoint: str,
    supabase_key: str,
    method: str,
    body: Optional[Mapping[str, Any]] = None,
    prefer: Optional[str] = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = request.Request(endpoint, data=data, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=15) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise UniverseBuilderError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise UniverseBuilderError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise UniverseBuilderError("Supabase universe snapshot insert timed out") from exc
    except json.JSONDecodeError as exc:
        raise UniverseBuilderError("Supabase response was not JSON") from exc


def _extract_markets(market_data: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_markets = market_data.get("markets")
    if raw_markets is None:
        exchange_info = market_data.get("exchangeInfo")
        if isinstance(exchange_info, Mapping):
            raw_markets = exchange_info.get("symbols")

    markets: Dict[str, Dict[str, Any]] = {}
    if not isinstance(raw_markets, list):
        return markets

    for market in raw_markets:
        if not isinstance(market, Mapping):
            continue
        symbol = _string_or_none(market.get("symbol"))
        if not symbol:
            continue
        status = str(market.get("status") or "TRADING").upper()
        if status != "TRADING":
            continue
        markets[symbol.upper()] = dict(market)
    return markets


def _extract_tickers(market_data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_tickers = market_data.get("tickers")
    if raw_tickers is None:
        raw_tickers = market_data.get("ticker24h")
    if not isinstance(raw_tickers, list):
        raise UniverseBuilderError("market data is missing ticker list")
    return [ticker for ticker in raw_tickers if isinstance(ticker, Mapping)]


def _usdt_symbols_from_markets(
    markets: Mapping[str, Mapping[str, Any]],
) -> Optional[set[str]]:
    if not markets:
        return None
    return {
        symbol
        for symbol, market in markets.items()
        if str(market.get("quoteAsset") or market.get("quote") or "").upper() == "USDT"
    }


def _candidate_payload(rank: int, candidate: UniverseCandidate) -> Dict[str, Any]:
    data = asdict(candidate)
    data["rank"] = rank
    return data


def _rank_score(
    *,
    quote_volume: float,
    volume_ratio: Optional[float],
    price_change_pct: float,
    volatility: float,
) -> float:
    return (
        quote_volume
        + ((volume_ratio or 0.0) * 1_000_000)
        + (price_change_pct * 10_000)
        + (volatility * 100_000)
    )


def _volatility(
    high_price: Optional[float],
    low_price: Optional[float],
    last_price: Optional[float],
) -> float:
    if high_price is None or low_price is None or last_price is None or last_price <= 0:
        return 0.0
    return max(0.0, (high_price - low_price) / last_price)


def _symbol_from_ticker(ticker: Mapping[str, Any]) -> Optional[str]:
    return _string_or_none(ticker.get("symbol") or ticker.get("s"))


def _quote_asset_from_symbol(symbol: str) -> Optional[str]:
    if symbol.endswith("USDT") and len(symbol) > 4:
        return "USDT"
    return None


def _first_float(ticker: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = ticker.get(key)
        parsed = _float_or_none(value)
        if parsed is not None:
            return parsed
    return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _exchange_config() -> ExchangeConfig:
    return ExchangeConfig(
        exchange_name=os.environ.get("EXCHANGE_NAME", DEFAULT_EXCHANGE_NAME),
        api_key_present=bool(os.environ.get("EXCHANGE_API_KEY")),
        api_secret_present=bool(os.environ.get("EXCHANGE_API_SECRET")),
        testnet=_env_bool("EXCHANGE_TESTNET", False),
    )


def _load_local_fixture() -> Dict[str, Any]:
    path = Path(os.environ.get("HELLHOUND_UNIVERSE_FIXTURE_PATH", LOCAL_FIXTURE_PATH))
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("universe fixture must be a JSON object")
    return dict(data)


def _local_mode_enabled() -> bool:
    return _env_bool("HELLHOUND_UNIVERSE_LOCAL", False)


def _store_supabase_enabled() -> bool:
    return _env_bool("HELLHOUND_UNIVERSE_STORE_SUPABASE", False)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


def _redact_secret_text(value: str) -> str:
    redacted = value
    for secret in (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        os.environ.get("SUPABASE_ANON_KEY"),
    ):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_result(result: UniverseBuilderResult) -> None:
    print(
        json.dumps(
            {
                "candidates_count": result.candidates_count,
                "exchange": asdict(result.exchange),
                "generated_at": result.generated_at,
                "local_mode": result.local_mode,
                "message": result.message,
                "skipped_store": result.skipped_store,
                "stored": result.stored,
                "top_symbols": result.top_symbols,
                "universe": result.universe,
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = build_dynamic_top30_universe()
    _print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
