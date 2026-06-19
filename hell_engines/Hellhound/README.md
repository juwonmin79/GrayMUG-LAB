# Hellhound

Hellhound is the experimental Hound attachment space for GrayMUG-LAB.

Purpose:

- Test LAB integration without modifying Production Hound.
- Validate Lead Line Universe Priority as a safe pre-scan overlay.
- Validate Execution Guidance Attachment after Hound has already detected a target.

Initial attachment candidates:

- Lead Line Universe Priority.
- Watch Priority overlay.
- Execution Guidance metadata attached after alert generation.

Rules:

- Do not copy Production Hound code into this folder.
- Do not modify Hound detection logic.
- Do not replace RSI, volume, BTC relative strength, taker, MACD, or whale alert conditions.
- Do not add automatic orders or position management.

## Hellhound-001-D Minimal Shadow Runner

Status: completed.

Hellhound-001-D Minimal Shadow Runner completed: first shadow-only signal inserted into Supabase.

`shadow_runner.py` is the isolated minimal OracleJP-Supabase shadow runner.

Flow:

```text
OracleJP-style payload
  -> Hellhound shadow signal normalization
  -> hellhound_shadow_signals insert
```

Runtime environment:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
SHADOW_RUNNER_DRY_RUN
```

Dry-run:

```bash
SHADOW_RUNNER_DRY_RUN=1 python3 hell_engines/Hellhound/shadow_runner.py
```

Safety notes:

- Shadow runner is isolated from production.
- It does not import or modify Production Hound, Ward, Core, or production loaders.
- It inserts only into `hellhound_shadow_signals`.
- Dry-run prints the normalized shadow signal and performs no Supabase insert.
- Missing Supabase environment skips insertion without crashing production callers.

## Hellhound-001-E Hypothesis Registry

Status: completed.

`hypotheses_schema.sql` creates the `hypotheses` registry:

```text
id
name
status
config
created_at
```

Hellhound-001-E initially loads only `status = 'active'` hypotheses for shadow signal generation. Hellhound-002 can later update lifecycle status to `active`, `promotion_candidate`, or `retired`.

`shadow_runner.py` loads active hypotheses from Supabase and generates one shadow signal per active hypothesis. It does not call Binance, Oracle, cron, or production engines.

Acceptance:

```text
3 active hypotheses
  -> 3 shadow signals inserted
```

## Hellhound-001-F Outcome Tracker

Status: completed.

`outcomes_schema.sql` creates the `hellhound_outcomes` table:

```text
id
shadow_signal_id
symbol
evaluation_window
outcome_return
result
created_at
```

Supported evaluation windows:

```text
1h
4h
24h
```

Supported outcome results:

```text
PENDING
SUCCESS
FAIL
INCONCLUSIVE
```

`outcome_tracker.py` attaches three initial `PENDING` outcome records to one shadow signal, one for each evaluation window. It does not call Binance, exchanges, Oracle, cron, schedulers, or production engines.

Local test data:

```text
hell_engines/Hellhound/test_data/slow_creep_shadow_signal.json
```

Dry-run:

```bash
OUTCOME_TRACKER_DRY_RUN=1 python3 hell_engines/Hellhound/outcome_tracker.py
```

Acceptance:

```text
Shadow signal pattern = SLOW_CREEP
  -> 1h PENDING outcome
  -> 4h PENDING outcome
  -> 24h PENDING outcome
```

## Hellhound-001-G Outcome Resolver

Status: completed.

`outcome_resolver.py` resolves `hellhound_outcomes` rows where `result = PENDING` into:

```text
SUCCESS
FAIL
INCONCLUSIVE
```

Default resolution thresholds:

```text
WATCH:
  outcome_return > 0  -> SUCCESS
  outcome_return <= 0 -> FAIL

AVOID:
  outcome_return < 0  -> SUCCESS
  outcome_return >= 0 -> FAIL

WAIT_CONFIRMATION:
  unresolved -> INCONCLUSIVE
```

If `outcome_return` is missing, the resolver returns `INCONCLUSIVE`. Thresholds can be overridden with `OUTCOME_RESOLVER_THRESHOLDS` JSON.

Local test data:

```text
hell_engines/Hellhound/test_data/pending_outcomes_to_resolve.json
```

Local dry-run:

```bash
OUTCOME_RESOLVER_LOCAL=1 python3 hell_engines/Hellhound/outcome_resolver.py
```

Supabase mode reads pending rows from `hellhound_outcomes`, reads linked shadow signal metadata from `hellhound_shadow_signals`, and writes resolved `result` values back to `hellhound_outcomes`. It does not call Binance, exchanges, Oracle, cron, schedulers, or production engines.

## Hellhound-001-H Market Snapshot

Status: completed.

`market_snapshot.py` reads pending `hellhound_outcomes`, reads each linked shadow signal for `symbol` and signal timestamp, and computes market return fields from read-only local market data.

Outcome fields updated:

```text
entry_price
current_price
return_pct
snapshot_time
outcome_return
```

`outcome_return` mirrors `return_pct` so `outcome_resolver.py` can resolve `SUCCESS`, `FAIL`, or `INCONCLUSIVE` using actual return values.

Schema support is in `outcomes_schema.sql`.

Local test data:

```text
hell_engines/Hellhound/test_data/pending_outcomes_for_snapshot.json
hell_engines/Hellhound/test_data/local_market_prices.json
```

Local dry-run:

```bash
MARKET_SNAPSHOT_LOCAL=1 python3 hell_engines/Hellhound/market_snapshot.py
```

Acceptance:

```text
One shadow signal
  -> 1h outcome gets entry_price, current_price, return_pct
  -> 4h outcome gets entry_price, current_price, return_pct
  -> 24h outcome gets entry_price, current_price, return_pct
```

The market snapshot layer is read-only for market data. It does not call Binance trading, exchanges, Oracle promotion, cron, schedulers, production engines, or `backup_GrayMUG`.

## Hellhound-002 Evaluation Loop

Status: completed.

`evaluation_loop.py` summarizes resolved outcome performance and updates hypothesis lifecycle status.

Scoreboard metrics:

```text
pattern
signals_count
outcomes_count
resolved_count
success_count
fail_count
inconclusive_count
accuracy
```

Accuracy:

```text
success_count / (success_count + fail_count)
```

`INCONCLUSIVE` outcomes are ignored from the accuracy denominator.

Allowed hypothesis statuses:

```text
active
promotion_candidate
retired
```

Default promotion rules:

```text
promotion_candidate:
  accuracy >= 0.70
  resolved_count >= 50

retired:
  accuracy < 0.40
  resolved_count >= 50

otherwise:
  active
```

Local test command:

```bash
EVALUATION_LOOP_LOCAL=1 python3 hell_engines/Hellhound/evaluation_loop.py
```

Supabase command:

```bash
python3 hell_engines/Hellhound/evaluation_loop.py
```

Supabase mode reads resolved rows from `hellhound_outcomes`, reads linked signal metadata from `hellhound_shadow_signals`, aggregates by hypothesis and pattern, and updates `hypotheses.status`.

Local fixture:

```text
hell_engines/Hellhound/test_data/evaluation_loop_resolved_outcomes.json
```

Local acceptance:

```text
SLOW_CREEP -> promotion_candidate
CHAIN_ROTATION -> active
DISTRIBUTION_RISK -> retired
```

Safety boundaries:

- Hellhound-002 does not call Binance trading.
- Hellhound-002 does not promote Oracle.
- Hellhound-002 does not run a scheduler or cron.
- Hellhound-002 does not import or modify Production Hound, Ward, Core, or `backup_GrayMUG`.
