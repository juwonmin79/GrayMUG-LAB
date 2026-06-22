# Hellhound Production Interface v1

## Purpose

Hellhound Production Interface v1 defines a safe library/API boundary for future Production Hound adapter work.

The interface does not modify Production Hound. It accepts a batch of Hound-style cases and returns advisory metadata only.

```text
Production Hound
  -> signal/case batch
  -> Hellhound Production Interface
  -> advisory output
  -> Production Hound keeps final authority
```

## Safety Contract

- Hellhound does not trade.
- Hellhound does not return trade commands.
- Production Hound keeps existing execution responsibility.
- Every output must contain `is_trade_command=false`.
- `entry_bias` is forced to `neutral`.
- Production Hound/Ward/Core are not modified by this interface.
- Binance endpoints are not used.
- DB update/delete is not used.

## Module

```text
hell_engines/Hellhound/production_interface.py
```

## Input Schema

```json
{
  "interface_version": "hellhound_production_interface_v1",
  "mode": "shadow",
  "cases": [
    {
      "case_id": "case-1",
      "symbol": "BELUSDT",
      "signal": {},
      "snapshot": {}
    }
  ]
}
```

Optional per-case fields:

- `shadow_signals`
- `historical_candles`
- `event_history`

These fields allow LAB context to improve advisory output without changing Production Hound behavior.

## Output Schema

```json
{
  "interface_version": "hellhound_production_interface_v1",
  "mode": "shadow",
  "is_trade_command": false,
  "results": [
    {
      "case_id": "case-1",
      "symbol": "BELUSDT",
      "structure_type": "BEL",
      "promotion_status": "PROMOTE",
      "hellhound_score": 0.72,
      "entry_bias": "neutral",
      "advisory": "WATCH_STRONG",
      "risk_note": "shadow_only",
      "is_trade_command": false
    }
  ]
}
```

## Functions

- `validate_production_interface_input(payload)`
- `evaluate_case(case)`
- `evaluate_cases(cases)`
- `build_production_interface_response(results)`
- `enforce_non_trade_output(payload)`
- `evaluate_production_payload(payload)`

## Adapter Design

Production Hound should not import Hellhound internals directly. A future adapter can:

1. Build a case batch from Hound signal rows.
2. Call `evaluate_production_payload(payload)`.
3. Read advisory fields such as `promotion_status`, `hellhound_score`, and `risk_note`.
4. Keep all execution decisions inside Production Hound.

The adapter must treat Hellhound output as advisory metadata. It must not map `PROMOTE` to an automatic order.

## Versioning

Hellhound is a versioned library surface:

- `hellhound_production_interface_v1`
- future `hellhound_production_interface_v2`
- future `hellhound_production_interface_v3`

LAB can keep evolving new versions while Production chooses a stable pinned interface.

Multiple interface versions can coexist. Production should only enable a version after replay, validation, and safety review.

## Current Status

Sprint 11A provides a local Python library boundary only.

No Production Hound files are modified.

No DB schema is applied.

No Binance endpoint is called.
