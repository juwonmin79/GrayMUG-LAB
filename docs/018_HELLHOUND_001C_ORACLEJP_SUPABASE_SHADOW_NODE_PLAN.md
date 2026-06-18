# Hellhound-001-C OracleJP-Supabase Shadow Node Plan

## 1. Purpose

Hellhound-001-C defines the deployment plan for running Hellhound on the OracleJP experiment node in shadow mode.

This is not a runner implementation. This document fixes the node position, Supabase table contract, data flow, safety rules, and next implementation step so Hellhound-001-D can build the minimal Shadow Runner directly.

Core conclusion:

- Hellhound does not replace Production Hound.
- Hellhound observes OracleJP-Supabase market data flow read-only as a shadow node.
- Hellhound combines LAB Lead Line, Target Feed, Calibration, and Execution Guidance into `shadow_signal` records.
- Hellhound never performs live trading, automatic orders, or position management.

## 2. Current Context

Completed:

- Hellhound-001-A Validation Runner Skeleton
- Hellhound-001-B Production Universe Loader

Current finding:

```text
Production Hound universe is not a static file.
Production Hound universe is generated dynamically by:
backup_GrayMUG/hound/scanner.py:HoundScanner.get_top_symbols
```

Because the Production Hound universe is dynamic, Hellhound should not stay as a file-based comparator. The next safe architecture is an OracleJP-Supabase shadow node that observes the same market data flow without modifying Production Hound.

## 3. Safety Rules

Mandatory rules:

- Do not modify Production Hound.
- Do not modify `backup_GrayMUG`.
- Do not execute Production Hound from LAB.
- Do not place automatic orders.
- Do not perform live trading.
- Do not manage positions.
- Do not call Binance order endpoints.
- Do not update or delete Supabase production tables.
- Do not print keys, tokens, credentials, or secret values.
- Do not commit `.env`.
- Only insert into dedicated shadow tables.
- Shadow records must always mark `is_order_executed = false`.
- Shadow records must always mark `is_shadow = true`.

## 4. Runtime Position

Production path:

```text
OracleJP
  ↓
Supabase market data
  ↓
Production Hound
  ↓
Production alert
```

Hellhound shadow path:

```text
OracleJP
  ↓
Supabase market data read-only
  ↓
Hellhound Shadow Node
  ↓
LAB Context
  ↓
hellhound_shadow_signals
  ↓
hellhound_shadow_outcomes
```

Hellhound runs beside Production Hound. It does not run inside Production Hound and does not feed commands back into Production Hound.

## 5. OracleJP Data Flow

Planned read-only flow:

1. OracleJP collects or relays market data.
2. Market data is stored in Supabase read tables.
3. Production Hound consumes its normal data flow independently.
4. Hellhound Shadow Node reads the same market context or derived market snapshots.
5. Hellhound loads LAB context:
   - Lead Line Socket
   - Target Feed
   - Fitness context
   - Calibration result
   - Execution Guidance
6. Hellhound writes shadow-only outputs to Supabase shadow tables.

OracleJP remains the experiment node. Supabase is the shared observation layer. Hellhound writes only shadow records.

## 6. Supabase Read Tables

Expected read tables are placeholders until confirmed on OracleJP / Supabase:

- `market_ohlcv`
- `market_symbols`
- `hound_alerts`
- `oraclejp_events`

Actual table names must be confirmed tomorrow on OracleJP / Supabase.

Read-only usage:

- `market_ohlcv`: OHLCV snapshots for symbol and BTC-relative return calculation.
- `market_symbols`: active symbol list and exchange pair metadata.
- `hound_alerts`: Production Hound alert stream for overlap and first detection comparison.
- `oraclejp_events`: optional node event stream for runtime audit and market data availability.

Forbidden read behavior:

- Do not read secret tables.
- Do not dump full production tables into logs.
- Do not expose API keys, tokens, or credential columns if such columns exist.

## 7. Supabase Write Tables

Hellhound writes only into shadow tables.

```sql
create table if not exists hellhound_shadow_signals (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  run_id text not null,
  mode text not null,
  node_name text not null default 'Hellhound-001',
  symbol text not null,
  base_asset text,
  quote_asset text,
  source_time timestamptz,
  lead_line_rank integer,
  lead_line_score numeric,
  lead_line_payload jsonb,
  target_feed jsonb,
  fitness_payload jsonb,
  calibration_payload jsonb,
  execution_guidance jsonb,
  hound_baseline_signal jsonb,
  pattern text,
  entry_guidance text,
  tp_case text,
  sl_case text,
  exit_triggers jsonb,
  shadow_action text not null,
  confidence numeric,
  final_weight numeric,
  is_order_executed boolean not null default false,
  is_shadow boolean not null default true,
  note text
);

create table if not exists hellhound_shadow_outcomes (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  signal_id uuid references hellhound_shadow_signals(id),
  symbol text not null,
  evaluated_at timestamptz,
  forward_1h_return numeric,
  forward_4h_return numeric,
  forward_24h_return numeric,
  btc_relative_1h numeric,
  btc_relative_4h numeric,
  btc_relative_24h numeric,
  tp_hit boolean,
  sl_hit boolean,
  exit_trigger_hit text,
  max_favorable_excursion numeric,
  max_adverse_excursion numeric,
  note text
);
```

Recommended indexes for Hellhound-001-D or later:

```sql
create index if not exists idx_hellhound_shadow_signals_run_id
  on hellhound_shadow_signals(run_id);

create index if not exists idx_hellhound_shadow_signals_symbol_created
  on hellhound_shadow_signals(symbol, created_at);

create index if not exists idx_hellhound_shadow_outcomes_signal_id
  on hellhound_shadow_outcomes(signal_id);
```

Indexes are optional for the first minimal shadow runner.

## 8. Shadow Signal Schema

`hellhound_shadow_signals` records one shadow decision candidate.

Core fields:

- `run_id`: Shadow run identifier.
- `mode`: LAB mode, initially `BTC_ACCUMULATION`.
- `node_name`: default `Hellhound-001`.
- `symbol`: pair or symbol being evaluated.
- `base_asset`: base token, such as `ETH`.
- `quote_asset`: quote asset, such as `BTC` or `USDT`.
- `source_time`: market snapshot or source event time.

LAB context fields:

- `lead_line_rank`
- `lead_line_score`
- `lead_line_payload`
- `target_feed`
- `fitness_payload`
- `calibration_payload`
- `execution_guidance`

Production comparison field:

- `hound_baseline_signal`: optional Production Hound alert context if a baseline alert exists for the same symbol/time window.

Guidance fields:

- `pattern`
- `entry_guidance`
- `tp_case`
- `sl_case`
- `exit_triggers`
- `shadow_action`
- `confidence`
- `final_weight`

Safety fields:

- `is_order_executed`: must always be `false`.
- `is_shadow`: must always be `true`.
- `note`: must state if data is partial, placeholder, delayed, or fallback.

Allowed `shadow_action` values for Hellhound-001-D:

- `OBSERVE`
- `WATCH`
- `AVOID`
- `WAIT_CONFIRMATION`

Forbidden `shadow_action` values:

- `BUY`
- `SELL`
- `ORDER`
- `CLOSE_POSITION`
- `OPEN_POSITION`

## 9. Outcome Tracking Schema

`hellhound_shadow_outcomes` records post-signal evaluation.

Outcome evaluator responsibilities:

- Join shadow signal to later OHLCV data.
- Calculate forward returns:
  - `forward_1h_return`
  - `forward_4h_return`
  - `forward_24h_return`
- Calculate BTC-relative returns:
  - `btc_relative_1h`
  - `btc_relative_4h`
  - `btc_relative_24h`
- Mark template outcomes:
  - `tp_hit`
  - `sl_hit`
  - `exit_trigger_hit`
- Record excursion:
  - `max_favorable_excursion`
  - `max_adverse_excursion`

Outcome tracking is evaluation only. It is not position management.

## 10. Hellhound Runtime Loop

Pseudo flow for Hellhound-001-D:

1. Load current market snapshot from Supabase read-only tables.
2. Load Lead Line universe from LAB.
3. Build Target Feed.
4. Build Fitness context.
5. Apply Calibration.
6. Build Execution Guidance.
7. Create `shadow_signal`.
8. Insert only into `hellhound_shadow_signals`.
9. Do not place orders.
10. Outcome evaluator later fills `hellhound_shadow_outcomes`.

Runtime constraints:

- No Binance order endpoint.
- No Production Hound import or execution.
- No production table update/delete.
- Insert-only behavior for shadow tables.
- If market data is missing, emit no signal or emit `OBSERVE` with a clear note.

## 11. Comparison Metrics

Hellhound-001 metrics:

- Production Hound alert overlap.
- Lead Line only targets.
- First detection time.
- Forward `+1h`, `+4h`, `+24h` return.
- BTC-relative `+1h`, `+4h`, `+24h` return.
- TP hit.
- SL hit.
- Exit trigger hit.
- Hound baseline vs Hellhound shadow signal.

Comparison examples:

- Production alert exists, Hellhound signal exists: overlap.
- Hellhound signal exists first: shadow first detection.
- Production alert exists first: baseline first detection.
- Hellhound signal exists without Production alert: Lead Line only target.
- Production alert exists without Hellhound signal: Hound baseline only target.

## 12. Failure / Kill Conditions

Hellhound Shadow Node must stop or skip writes when any of these are detected:

- Supabase connection error.
- Missing market table.
- Missing symbol data.
- Required LAB payload cannot be built.
- Any order endpoint is detected.
- Any production table write attempt is detected.
- Any update/delete attempt is detected against Supabase production tables.
- Any secret/key/token print attempt is detected.
- Unexpected mutation of `backup_GrayMUG`.
- `HELLHOUND_MODE` is not `shadow`.
- `is_order_executed` would be anything other than `false`.
- `is_shadow` would be anything other than `true`.

Failure behavior:

- Log only safe metadata.
- Do not print secrets.
- Do not retry with broader permissions.
- Do not fall back to live order code.
- Do not write partial rows unless they are clearly marked as `OBSERVE` shadow rows.

## 13. Environment Variables

Names only. Values must never be committed.

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ANON_KEY
HELLHOUND_MODE=shadow
HELLHOUND_NODE_NAME=Hellhound-001
HELLHOUND_RUN_ID
HELLHOUND_READ_SCHEMA
HELLHOUND_WRITE_SCHEMA
```

Rules:

- Use either `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_ANON_KEY` according to OracleJP policy.
- Never commit `.env`.
- Never print values.
- Never put credentials in docs, logs, CSV, JSON, or markdown outputs.

## 14. Next Step: Hellhound-001-D Minimal Shadow Runner

Hellhound-001-D should implement the minimal Shadow Runner:

- Read OracleJP-Supabase market snapshot from confirmed read tables.
- Load LAB Lead Line universe.
- Build Target Feed, Fitness, Calibration, and Execution Guidance from existing LAB APIs.
- Create one or more `shadow_signal` rows.
- Insert only into `hellhound_shadow_signals`.
- Do not evaluate outcomes yet unless data is already available and insert-only behavior is guaranteed.
- Do not place orders.
- Do not modify Production Hound.

Hellhound-001-D success condition:

```text
One safe shadow run writes shadow-only rows to hellhound_shadow_signals.
No production table is mutated.
No order endpoint is called.
No secret value is printed.
```

## Final Definition

Hellhound-001-C does not release Hellhound into the market.

Hellhound-001-C is the mounting plan for safely placing Hellhound on the OracleJP-Supabase experiment node tomorrow.

Actual market shadow running starts in Hellhound-001-D.
