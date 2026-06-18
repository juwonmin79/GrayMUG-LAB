# Hellhound-001

Hellhound-001 compares the Production Hound Universe with the LAB Lead Line Universe.

This directory contains the Hellhound-001 validation runner. It creates the input/output structure needed for universe comparison, but it does not perform trading, automatic order placement, Forecast, Graph ML, Whale ML, DB integration, FastAPI, dashboard work, or Production Hound execution.

## Scope

- Load Lead Line Universe from the existing LAB Lead Line API Socket.
- Load Production Hound Universe read-only when a simple universe file exists.
- Detect the Production Hound dynamic universe generator in `backup_GrayMUG/hound/scanner.py`.
- Use a small fallback Production universe only when no explicit read-only symbol artifact exists.
- Compare overlap, Lead Line only symbols, Production only symbols, and overlap ratio.
- Write small output artifacts under `outputs/hellhound001/`.

## Production Fallback Warning

Production universe not found. Fallback used. This is not a real validation result.

The current fallback is:

```text
BTC/USDT
ETH/USDT
BNB/USDT
```

This fallback exists because the current Production Hound universe is generated dynamically from exchange tickers inside `HoundScanner.get_top_symbols()`. Hellhound-001-B detects that source path read-only, but does not execute Production Hound or call production exchange code.

## Commands

```bash
python -B research/hellhound001/validation_runner.py
python -B research/hellhound001/test_validation_runner.py
```

## Outputs

- `outputs/hellhound001/universe_compare.json`
- `outputs/hellhound001/universe_compare.csv`
- `outputs/hellhound001/summary.md`

## Next Step

Hellhound-001-C should connect a real read-only Production universe artifact, such as an exported watchlist snapshot, without modifying `backup_GrayMUG` or Production Hound logic.
