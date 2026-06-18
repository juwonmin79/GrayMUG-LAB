# Hellhound-001

Hellhound-001 compares the Production Hound Universe with the LAB Lead Line Universe.

This directory contains the Validation Runner Skeleton only. It creates the input/output structure needed for later validation, but it does not perform trading, automatic order placement, Forecast, Graph ML, Whale ML, DB integration, FastAPI, or dashboard work.

## Scope

- Load Lead Line Universe from the existing LAB Lead Line API Socket.
- Load Production Hound Universe read-only when a simple universe file exists.
- Use a small fallback Production universe when no read-only universe artifact exists.
- Compare overlap, Lead Line only symbols, Production only symbols, and overlap ratio.
- Write small output artifacts under `outputs/hellhound001/`.

## Production Fallback Warning

Production universe fallback is only for runner skeleton test.
It is not a validation result.

The current fallback is:

```text
BTC/USDT
ETH/USDT
BNB/USDT
```

This fallback exists so the runner and smoke test can execute before a real read-only Production universe loader is connected.

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

Hellhound-001-B should connect a real read-only Production universe source without modifying `backup_GrayMUG` or Production Hound logic.
