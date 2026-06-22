# Hellhound Optional Decision Import Investigation

## Sprint

Sprint 12A - Optional Decision Import activation investigation.

## Problem

Production Shadow JSONL showed repeated fallback reasons:

```text
source_error=Hellhound optional decision import is disabled.
```

`library_interface.py` was therefore using signal fallback output instead of the real Hellhound decision path.

## Root Cause

Cause: feature flag disable.

There were two gates:

1. `integration_stub.optional_hellhound_decision()`
   - Checked `HELLHOUND_DECISION_ENABLED`.
   - Defaulted to `false`.
   - Returned fail-safe neutral before importing decision modules.

2. `decision_api.evaluate_symbol()`
   - Checked `HELLHOUND_DECISION_ENABLED` again.
   - Defaulted to `false`.
   - Returned fail-safe neutral even when the outer import path was bypassed.

This was not caused by missing decision files or ImportError.

## Import Targets

Actual optional import targets:

- `decision_api.evaluate_symbol`
- `promotion_candidate.build_shadow_decision`

Related callers:

- `library_interface.evaluate_signal_row`
- `library_interface.evaluate_event_row`
- `library_interface.evaluate_snapshot_row`
- `shadow_advisor.run_shadow_evaluation_pipeline`
- `real_shadow_feed.build_real_shadow_decision`
- `production_interface.evaluate_case`

## Fix

The core optional API remains fail-safe by default.

LAB/library shadow paths now pass `decision_enabled=True` explicitly so the real decision path is active without relying on ambient environment variables.

Explicit fallback is still available by passing:

```text
decision_enabled=false
```

## Verification

Sample actual decision output:

```json
{
  "advisory": "WATCH_STRONG",
  "decision_source": "decision_api",
  "fallback_used": false,
  "hellhound_score": 0.5786,
  "is_trade_command": false,
  "promotion_status": "PROMOTE",
  "source_error_present": false,
  "structure_type": "ACCUMULATION_BASE",
  "symbol": "BELUSDT"
}
```

## Boundary

- Production was not modified.
- GrayMUG was not modified.
- Binance was not accessed.
- No order path was created.
- Output remains `is_trade_command=false`.
