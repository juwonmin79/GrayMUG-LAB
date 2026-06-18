# Hellhound-001-B Production Universe Loader

## 1. Purpose

Hellhound-001-B upgrades the validation runner so Production Hound Universe loading is explicit and auditable.

This is not a performance validation step. It only establishes whether a real read-only Production Hound universe artifact can be loaded from `backup_GrayMUG`.

## 2. Safety Rules

- Do not modify `backup_GrayMUG`.
- Do not execute Production Hound.
- Do not import Production Hound modules.
- Do not read or print `.env`, key, token, credential, or secret values.
- Do not add trading, automatic orders, DB, FastAPI, dashboard, Forecast, Graph ML, or Whale ML.

## 3. Loader Priority

The loader checks sources in this order:

1. Explicit watchlist, universe, symbol list, or top30 files under `backup_GrayMUG`.
2. Static symbol list literals in `backup_GrayMUG/hound/scanner.py`.
3. Dynamic universe generator detection in `HoundScanner.get_top_symbols`.
4. Fallback universe if no real symbol list exists.

## 4. Current Production Finding

The current backup does not contain an explicit watchlist, universe, symbol list, or top30 artifact file.

The Production Hound universe is generated dynamically by:

```text
backup_GrayMUG/hound/scanner.py:HoundScanner.get_top_symbols
```

That function builds a symbol universe from exchange tickers at runtime. Because Hellhound-001-B must not execute Production Hound, the runner cannot extract the live symbol list from this function.

## 5. Fallback Rule

When no real read-only symbol artifact exists, the runner uses fallback symbols only to keep the validation pipeline executable:

```text
BTC/USDT
ETH/USDT
BNB/USDT
```

The output must mark this clearly:

```json
{
  "production_universe_source": "fallback",
  "production_universe_is_fallback": true
}
```

Required note:

```text
Production universe not found. Fallback used. This is not a real validation result.
```

## 6. Output Contract

`outputs/hellhound001/universe_compare.json` includes:

- `production_universe_source`
- `production_universe_is_fallback`
- `summary.production_universe_source`
- `summary.production_universe_is_fallback`

## 7. Next Step

Hellhound-001-C should connect a real read-only Production universe artifact, preferably an exported Hound watchlist snapshot, without modifying Production Hound or `backup_GrayMUG`.
