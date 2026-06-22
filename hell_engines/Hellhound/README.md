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
target_time
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

`outcome_tracker.py` attaches three initial `PENDING` outcome records to one shadow signal, one for each evaluation window. Each row stores `target_time = hellhound_shadow_signals.created_at + evaluation_window`, so downstream evaluation can keep 1h, 4h, and 24h windows separate. It does not call Binance, exchanges, Oracle, cron, schedulers, or production engines.

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

`outcome_resolver.py` resolves `hellhound_outcomes` rows where `result = PENDING` and `now_utc >= target_time` into:

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

If `outcome_return` is missing after the target time has passed, the resolver returns `INCONCLUSIVE`. Thresholds can be overridden with `OUTCOME_RESOLVER_THRESHOLDS` JSON. Pending rows whose target time has not passed are left unresolved.

Local test data:

```text
hell_engines/Hellhound/test_data/pending_outcomes_to_resolve.json
```

Local dry-run:

```bash
OUTCOME_RESOLVER_LOCAL=1 python3 hell_engines/Hellhound/outcome_resolver.py
```

Supabase mode reads pending rows from `hellhound_outcomes`, reads linked shadow signal metadata from `hellhound_shadow_signals`, filters out rows before their target time, and writes resolved `result` values back to `hellhound_outcomes`. It does not call Binance, exchanges, Oracle, cron, schedulers, or production engines.

## Hellhound-001-H Market Snapshot

Status: completed.

`market_snapshot.py` reads pending `hellhound_outcomes`, reads each linked shadow signal for `symbol` and signal timestamp, filters to rows where `now_utc >= target_time`, and computes market return fields.

Server/Supabase mode uses Binance public read-only ticker prices. It does not read `test_data/local_market_prices.json` unless `MARKET_SNAPSHOT_LOCAL=1` is set. `entry_price` comes from the linked shadow signal payload when available; if the signal has no usable entry or universe price yet, the first live ticker price is used as `entry_price` for that outcome snapshot.

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

Local test data, used only with `MARKET_SNAPSHOT_LOCAL=1`:

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
  -> due outcomes get entry_price, current_price, return_pct
  -> not-yet-due outcomes remain untouched and unresolved
```

The market snapshot layer is read-only for market data. It uses `market_snapshot_source=binance_public_ticker` in server mode and `market_snapshot_source=local_fixture` in local fixture mode. It does not call Binance trading APIs, order endpoints, account endpoints, Oracle promotion, cron, schedulers, production engines, or `backup_GrayMUG`.

Rows resolved before this target-time gate was introduced should be treated as contaminated for evaluation-window performance analysis.

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

## Hellhound-003 24h Experiment Runner

Status: completed.

`experiment_24h_runner.py` runs the Hellhound research cycle repeatedly for a fixed window, then stops automatically.

Cycle order:

```text
shadow_runner.py
outcome_tracker.py
market_snapshot.py
outcome_resolver.py
evaluation_loop.py
```

Environment:

```text
HELLHOUND_EXPERIMENT_INTERVAL_MINUTES=15
HELLHOUND_EXPERIMENT_DURATION_HOURS=24
HELLHOUND_EXPERIMENT_DRY_RUN=false
```

Local shortened test:

```bash
HELLHOUND_EXPERIMENT_INTERVAL_MINUTES=0.1 \
HELLHOUND_EXPERIMENT_DURATION_HOURS=0.01 \
python3 hell_engines/Hellhound/experiment_24h_runner.py
```

Supabase mode:

```bash
python3 hell_engines/Hellhound/experiment_24h_runner.py
```

Cycle summary fields:

```text
cycle number
timestamp
signals generated
outcomes created
snapshots updated
outcomes resolved
hypotheses evaluated
```

Final summary fields:

```text
total cycles
total signals
total outcomes
total snapshots
total resolved outcomes
final scoreboard if available
```

Ctrl+C exits through safe interrupt handling and prints the partial final summary before stopping.

Safety boundaries:

- Hellhound-003 does not use cron or an external scheduler.
- Hellhound-003 does not call Binance trading APIs or place orders.
- Hellhound-003 does not promote Oracle automatically.
- Hellhound-003 does not import or modify Production Hound, Ward, Core, or `backup_GrayMUG`.
- All persisted research results remain in Supabase shadow tables.

## Hellhound-004 Universe Builder

Status: completed.

`universe_builder.py` builds a Hellhound-only dynamic Top30 target universe from read-only exchange market data. It does not call trading endpoints and does not place orders. The 24h experiment runner uses `HELLHOUND_UNIVERSE_LIMIT` to choose how many ranked symbols to send to `shadow_runner.py`; the default is `30`.

Exchange environment:

```text
EXCHANGE_NAME=binance
EXCHANGE_API_KEY
EXCHANGE_API_SECRET
EXCHANGE_TESTNET=false
```

`EXCHANGE_API_KEY` and `EXCHANGE_API_SECRET` are read only as config presence flags; the builder uses public market-data endpoints for candidate discovery.

Ranking input:

```text
USDT spot pairs only
quote volume
volatility from 24h high/low/last
absolute price_change_pct
volume_ratio if available
```

Main universe exclusions:

```text
USDC
FDUSD
TUSD
USDP
DAI
USD1
RLUSD
EUR
TRY
BRL
XAUT
PAXG
non-ASCII symbols or base assets
```

Extreme movers:

```text
abs(price_change_pct) >= 30
```

Extreme movers are excluded from the main Top30 by default and are emitted separately for anomaly review.

Local fixture mode:

```bash
HELLHOUND_UNIVERSE_LOCAL=1 python3 hell_engines/Hellhound/universe_builder.py
```

Optional fixture override:

```bash
HELLHOUND_UNIVERSE_LOCAL=1 \
HELLHOUND_UNIVERSE_FIXTURE_PATH=hell_engines/Hellhound/test_data/universe_builder_fixture.json \
python3 hell_engines/Hellhound/universe_builder.py
```

Live read-only market-data mode:

```bash
EXCHANGE_NAME=binance \
EXCHANGE_TESTNET=false \
python3 hell_engines/Hellhound/universe_builder.py
```

24h runner live universe limit:

```bash
HELLHOUND_UNIVERSE_LIMIT=3 python3 hell_engines/Hellhound/experiment_24h_runner.py
```

Each cycle generates `active hypotheses x selected symbols` shadow signals. For example, three active hypotheses and `HELLHOUND_UNIVERSE_LIMIT=3` generate nine shadow signals.

Optional Supabase snapshot storage:

```bash
HELLHOUND_UNIVERSE_STORE_SUPABASE=1 python3 hell_engines/Hellhound/universe_builder.py
```

Schema support is in `universe_snapshots_schema.sql` for table:

```text
hellhound_universe_snapshots
```

Output fields:

```text
top_symbols
universe rank rows
excluded_assets
excluded_candidates with reason = excluded_base_asset or non_ascii_symbol
extreme_movers
candidates_count
exchange config summary
stored / skipped_store
```

Safety boundaries:

- Hellhound-004 does not use trading endpoints.
- Hellhound-004 reads only exchange market data.
- Hellhound-004 uses dynamic symbols from USDT pairs and has no fixed `ETHUSDT` dependency.
- Hellhound-004 keeps `BTCUSDT` and `ETHUSDT` eligible for the main universe.
- Hellhound-004 does not import or modify Production Hound, Ward, Core, or `backup_GrayMUG`.
- Fixture data is isolated behind explicit local flags: `HELLHOUND_UNIVERSE_LOCAL=1` and `MARKET_SNAPSHOT_LOCAL=1`.
- Server-mode logs include `universe_source=binance_public_market`, `shadow_signal_source=live_universe`, and `market_snapshot_source=binance_public_ticker`.

## Hellhound-005 Event Layer and Decision API Draft

Status: initial implementation.

Hellhound-005 shifts the analysis unit from isolated outcomes to symbol event timelines. Outcomes still measure whether a signal worked, but event timelines explain whether many shadow signals are part of one developing market structure.

Reason for the shift:

```text
84 METUSDT shadow signals should not become 84 independent market stories.
They should become one event timeline with many observations.
```

Implemented modules:

```text
event_layer.py
pre_spike_features.py
event_classifier.py
decision_api.py
integration_stub.py
event_layer_schema.sql
test_event_layer.py
```

Event fields:

```text
event_id
symbol
event_start_bucket
max_gap_hours
first_seen_time
last_seen_time
event_age_hours
observation_count
observation_timeframe_hint
event_state
hypotheses
shadow_actions
patterns
```

Deduplication:

```text
symbol + source_time + hypothesis
```

Raw `hellhound_shadow_signals` rows are not deleted. Deduplication is analysis-only, so hypothesis-level signal history remains available.

Current `event_id` limitation:

```text
event_id = symbol + first_seen_time
```

This is acceptable for the first LAB event layer, but a late backfill can change `first_seen_time` and therefore change `event_id`. Future key candidates are `symbol + event_start_bucket`, `symbol + gap-window cluster`, `symbol + first_hound_alert_id`, or `symbol + first_shadow_signal_id`.

Multi-timeframe snapshot interface:

```text
1m
15m
1h
4h
1d
1w
```

Initial pre-spike features:

```text
micro_vol_rise
vol_ma_acceleration
price_compression
rs_slope
candle_body_expansion
spike_count_7d
spike_interval
watchlist_age
```

`watchlist_age` remains TODO until a safe read-only first-seen source is confirmed.

Initial event classes:

```text
BEL   bottom rebound / expansion candidate
ACT   long decline / distribution candidate
ACE   late detection candidate
NIGHT repeated re-accumulation candidate
```

Decision API draft:

```python
evaluate_symbol(symbol, as_of_time=None) -> dict
```

Default:

```text
HELLHOUND_DECISION_ENABLED=false
```

Fail-safe:

```text
entry_bias="neutral"
confidence=0
error present
```

Hound integration is example-only in `integration_stub.py`. Production Hound is not modified.

Schema support is drafted in `event_layer_schema.sql` for:

```text
hellhound_events
hellhound_event_observations
hellhound_mtf_snapshots
```

`event_layer_schema.sql` is draft-only until a writer exists. `updated_at` has no automatic trigger yet.

Safety boundaries:

- Hellhound-005 does not use Binance trading endpoints.
- Hellhound-005 does not place orders or manage positions.
- Hellhound-005 does not update/delete production tables.
- Hellhound-005 does not modify Production Hound, Ward, Core, `.env`, or `backup_GrayMUG`.

## Hellhound-006 Accumulation Intelligence Layer

Status: initial implementation.

Sprint 3 shifts Hellhound from:

```text
already exploded detection
```

to:

```text
pre-explosion preparation detection
```

Implemented module:

```text
accumulation_features.py
test_accumulation_features.py
```

Primary API:

```python
compute_accumulation_features(symbol, historical_candles, event_history=None) -> dict
```

Feature groups:

```text
vol_7d_avg
vol_14d_avg
vol_30d_avg
vol_ratio_7d_vs_30d
vol_ratio_14d_vs_30d
price_return_7d
price_return_14d
price_return_30d
price_from_30d_high
price_from_52w_high
price_from_30d_low
price_from_52w_low
```

Repeated whale activity:

```text
spike_count_7d
spike_count_14d
spike_count_30d
avg_spike_interval_days
min_spike_interval_days
repeat_activity_score
```

Structure context:

```text
weekly_trend
monthly_trend
distance_ma200
distance_52w_high
distance_52w_low
structure_type
setup_type
```

Supported structure types:

```text
ACCUMULATION_BASE
MID_CYCLE
DISTRIBUTION
CAPITULATION
UNKNOWN
```

Setup hints:

```text
BEL
ACT
ACE
MET
UNKNOWN
```

Hellhound Score v0.2:

```text
accumulation_score
repeat_activity_score
structure_score
hellhound_score
```

`decision_api.evaluate_symbol()` accepts optional `historical_candles` and `event_history` and returns the new score fields when provided.

Safety boundaries:

- Hellhound-006 does not use ML.
- Hellhound-006 does not use Binance trading endpoints.
- Hellhound-006 does not place orders or manage positions.
- Hellhound-006 does not update/delete DB rows.
- Hellhound-006 does not modify Production Hound, Ward, Core, `.env`, or `backup_GrayMUG`.

## Hellhound-007 Shadow Promotion Layer

Status: initial implementation.

Sprint 4 shifts Hellhound from:

```text
good signal
```

to:

```text
Production promotion candidate
```

Implemented module:

```text
promotion_candidate.py
test_promotion_candidate.py
```

Primary APIs:

```python
evaluate_promotion_candidate(...) -> dict
build_shadow_decision(...) -> dict
replay_shadow_cases(cases) -> list[dict]
compute_outcome_correlation(outcomes) -> dict
```

Promotion status:

```text
PROMOTE
WATCH
REJECT
```

Initial promotion rule:

```text
PROMOTE:
  hellhound_score >= 0.60
  distribution_risk <= 0.40

PROMOTE fallback:
  structure_type = ACCUMULATION_BASE
  accumulation_score >= 0.55
  repeat_activity_score >= 0.25
  distribution_risk <= 0.40

WATCH:
  middle score/risk profile

REJECT:
  distribution_risk >= 0.65
  or structure_type in DISTRIBUTION/CAPITULATION
```

Shadow decision payload:

```text
symbol
setup_type
structure_type
hellhound_score
promotion_status
reasons
is_trade_command=false
```

Replay acceptance:

```text
BEL   -> PROMOTE
ACT   -> REJECT
ACE   -> REJECT
MET   -> WATCH
NIGHT -> WATCH
```

Outcome correlation groups supplied outcome rows into:

```text
0.0~0.2
0.2~0.4
0.4~0.6
0.6~0.8
0.8~1.0
```

Safety boundaries:

- Hellhound-007 is shadow-only.
- Hellhound-007 does not change Production Hound/Ward/Core.
- Hellhound-007 does not change real trading logic.
- Hellhound-007 does not update/delete DB rows.
- Hellhound-007 does not stage, commit, or push git changes.

## Hellhound-008 Shadow Advisor Mode

Status: initial implementation.

Sprint 5 attaches Hellhound as a shadow advisor without modifying Production Hound.

Flow:

```text
Hound Signal
  -> Hellhound Evaluate
  -> Shadow Decision
  -> Log Only
```

Advisor mode contract:

```text
Hellhound has no Trade Authority.
Hellhound does not change Hound entry conditions.
Hellhound does not change Hound exit conditions.
Hellhound does not change Hound results.
Hellhound does not place orders.
```

Implemented modules:

```text
integration_stub.py
shadow_advisor.py
test_shadow_advisor.py
```

Optional advisor API:

```python
optional_hellhound_decision(
    symbol,
    signal=None,
    shadow_signals=None,
    historical_candles=None,
    event_history=None,
    as_of_time=None,
) -> dict
```

Advisor output:

```text
hellhound_score
accumulation_score
repeat_activity_score
structure_type
setup_type
promotion_status
distribution_risk
entry_bias
reasons
is_trade_command=false
```

In Advisor Mode, `entry_bias` is fixed to `neutral` at the integration surface. Promotion status is recorded for audit, but Hellhound does not suggest executable entry or exit changes.

Shadow evaluation pipeline:

```python
run_shadow_evaluation_pipeline(...) -> dict
```

Audit row:

```text
symbol
signal_time
event_id
hellhound_score
promotion_status
entry_bias
actual_1h_outcome
actual_4h_outcome
actual_24h_outcome
```

Shadow log:

```text
shadow_decision_log.jsonl
```

The log is file-based. DB is not required for Sprint 5.

Replay validation compares:

```text
Hound Signal
Hellhound Decision
Actual Outcome
```

False-positive analysis extracts:

```text
PROMOTE but failed
REJECT but succeeded
Top Failure Reasons
Top Success Reasons
```

Safety boundaries:

- Hellhound-008 is Advisor Mode only.
- Hellhound-008 has no Trade Authority.
- Hellhound-008 does not modify Production Hound/Ward/Core.
- Hellhound-008 does not modify entry or exit logic.
- Hellhound-008 does not use Binance order endpoints.
- Hellhound-008 does not update/delete DB rows.
- Hellhound-008 does not stage, commit, or push git changes.

## Hellhound-009 Real Shadow Feed

Status: initial implementation.

Sprint 6 connects actual Hound/Hellhound signal rows to Shadow Advisor without modifying Production Hound.

Read sources:

```text
hound_scan_log
hellhound_shadow_signals
```

The reader tries `hound_scan_log` first, then `hellhound_shadow_signals`. Reads use Supabase REST GET only.

Flow:

```text
Real signal row
  -> run_shadow_evaluation_pipeline()
  -> PROMOTE/WATCH/REJECT
  -> outputs/hellhound_shadow_decisions.jsonl
```

Primary module:

```text
real_shadow_feed.py
test_real_shadow_feed.py
```

Primary APIs:

```python
load_recent_signals(limit=100)
load_recent_outcomes(limit=500)
build_real_shadow_decision(signal, outcome_rows=None)
process_recent_signals(signals, outcome_rows=None, dry_run=True)
write_shadow_feed_log(decisions)
join_outcomes(signal, outcome_rows)
```

Default log path:

```text
outputs/hellhound_shadow_decisions.jsonl
```

Shadow log fields:

```text
symbol
signal_time
event_id
hellhound_score
promotion_status
structure_type
setup_type
distribution_risk
reasons
actual_1h_outcome
actual_4h_outcome
actual_24h_outcome
is_trade_command=false
```

Daily Open Alert Cluster:

```text
UTC 00:00 +/- 15m alerts
cluster_id
symbols
alert_count
avg_vol_ratio
max_vol_ratio
daily_open_cluster=true
detection_delay_candidate=true
```

Cluster rows are written to the same JSONL shadow log with `record_type=daily_open_alert_cluster`.

CLI:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 100 --dry-run
```

Mock dry-run:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 5 --dry-run --mock
```

Outcome join:

```text
hellhound_outcomes read-only join
1h / 4h / 24h fields are null when no outcome row exists
```

Safety boundaries:

- Hellhound-009 does not modify Production Hound/Ward/Core.
- Hellhound-009 does not modify `backup_GrayMUG`.
- Hellhound-009 does not use Binance order/trading endpoints.
- Hellhound-009 does not update/delete DB rows.
- Hellhound-009 does not apply `event_layer_schema.sql`.
- Hellhound-009 does not stage, commit, or push git changes.

## Hellhound-010 Library/API Boundary

Status: initial implementation.

Sprint 7 defines the safe communication boundary between future Production Hound callers and Hellhound.

Principles:

```text
Hellhound does not trade.
Hellhound does not return trade commands.
Hellhound is Advisor Mode only.
Production Hound remains the execution engine.
```

Implemented module:

```text
library_interface.py
test_library_interface.py
```

Boundary inputs:

```text
signal row
event row
snapshot row
signal batch
```

Boundary outputs:

```text
shadow_decision
advisor_result
cluster
```

Primary APIs:

```python
evaluate_signal_row(signal, shadow_signals=None, historical_candles=None, event_history=None)
evaluate_event_row(event, signal=None, historical_candles=None)
evaluate_snapshot_row(snapshot, signal=None)
detect_cluster_rows(signals)
evaluate_real_feed_row(signal, outcome_rows=None)
```

Output contract:

```text
hellhound_interface_version
input_type
output_type
is_trade_command=false
```

Integration surface rule:

```text
entry_bias=neutral
```

Event Writer status:

```text
deferred
append-only JSONL remains the persistence boundary
event_layer_schema.sql is not applied
```

Safety boundaries:

- Hellhound-010 does not modify Production Hound/Ward/Core.
- Hellhound-010 does not modify `backup_GrayMUG`.
- Hellhound-010 does not use Binance order/trading endpoints.
- Hellhound-010 does not update/delete DB rows.
- Hellhound-010 does not stage, commit, or push git changes.

## Hellhound-011 Event Writer + Persistence

Status: initial implementation.

Sprint 8 adds append-only research persistence for Hellhound Event Layer outputs.

Purpose:

```text
Lead Line input
MFE/MAE input
Mirror Pattern ML input
Shadow Advisor audit history
```

Implemented module:

```text
event_writer.py
test_event_writer.py
```

Default JSONL path:

```text
outputs/hellhound_event_layer.jsonl
```

Supported record types:

```text
shadow_decision
daily_open_alert_cluster
real_feed_outcome
```

Required event fields:

```text
event_id
event_time
record_type
source
hellhound_version
symbol when available
is_trade_command=false
```

Primary API:

```python
EventWriter(path).append_event(record)
EventWriter(path).append_events(records)
append_event(record, path=...)
append_events(records, path=...)
validate_event(record)
record_from_boundary_output(payload)
records_from_boundary_output(payload)
```

Validation rejects:

```text
missing required fields
invalid record_type
is_trade_command=true
```

Safety boundaries:

- Hellhound-011 is append-only JSONL.
- Hellhound-011 does not update/delete DB rows.
- Hellhound-011 does not apply Supabase schema.
- Hellhound-011 does not modify Production Hound/Ward/Core.
- Hellhound-011 does not use Binance order/trading endpoints.
- Hellhound-011 does not stage, commit, or push git changes.

## Hellhound-012 Lead Line Dataset Builder

Status: initial implementation.

Sprint 9 asks:

```text
What did Hellhound see before the positive outcome?
```

Mission:

```text
Detection Delay reduction
```

Implemented module:

```text
lead_line_dataset.py
test_lead_line_dataset.py
```

Input:

```text
outputs/hellhound_event_layer.jsonl
```

Outcome anchor:

```text
record_type=real_feed_outcome
```

Default windows:

```text
24h
48h
72h
```

Output:

```text
outputs/hellhound_lead_line_dataset.jsonl
```

Primary API:

```python
build_lead_line_dataset(...)
collect_pre_outcome_events(...)
create_lead_line_record(...)
load_event_records(path)
write_lead_line_dataset(rows, output_path=..., append=True)
```

Dataset row fields:

```text
lead_line_id
symbol
outcome_time
hours_before_outcome
saw_shadow_decision
saw_daily_open_cluster
promotion_status
structure_type
hellhound_score
entry_bias
signal_hour
daily_open_cluster
alert_count
event_count
is_trade_command=false
```

Safety boundaries:

- Hellhound-012 is research-only.
- Hellhound-012 is append-only JSONL.
- Hellhound-012 does not modify Production Hound/Ward/Core.
- Hellhound-012 does not use Binance endpoints.
- Hellhound-012 does not update/delete DB rows.
- Hellhound-012 does not stage, commit, or push git changes.

## Hellhound-013 Outcome Window Validation

Status: initial implementation.

Sprint 10 asks:

```text
Did the Lead Line matter?
```

Mission:

```text
Detection Delay measurement
```

Implemented module:

```text
outcome_validator.py
test_outcome_validator.py
```

Input:

```text
outputs/hellhound_lead_line_dataset.jsonl
```

Default windows:

```text
24h
48h
72h
```

Validation status:

```text
VALIDATED
DELAYED
INCONCLUSIVE
REJECTED
```

Output:

```text
outputs/hellhound_validation_dataset.jsonl
```

Primary API:

```python
validate_lead_line(...)
validate_outcome_window(...)
create_validation_record(...)
write_validation_dataset(...)
load_lead_line_rows(path)
```

Validation row fields:

```text
validation_id
lead_line_id
symbol
validation_status
validation_window_hours
hours_before_outcome
saw_daily_open_cluster
promotion_status
structure_type
daily_open_cluster
alert_count
event_count
validation_score
is_trade_command=false
```

Safety boundaries:

- Hellhound-013 is research-only.
- Hellhound-013 is append-only JSONL.
- Hellhound-013 does not modify Production Hound/Ward/Core.
- Hellhound-013 does not use Binance endpoints.
- Hellhound-013 does not update/delete DB rows.
- Hellhound-013 does not stage, commit, or push git changes.

## Hellhound-014 MFE / MAE Engine

Status: initial implementation.

Sprint 11 asks:

```text
How much does this pattern usually pay?
```

Mission:

```text
Whale profit-zone learning
```

Implemented module:

```text
mfe_mae_engine.py
test_mfe_mae_engine.py
```

Input:

```text
outputs/hellhound_validation_dataset.jsonl
post-validation price path
```

Output:

```text
outputs/hellhound_mfe_mae_dataset.jsonl
```

Primary API:

```python
calculate_mfe(...)
calculate_mae(...)
calculate_time_to_peak(...)
calculate_time_to_stop(...)
create_mfe_mae_record(...)
write_mfe_mae_dataset(...)
aggregate_mfe_mae_by_structure(...)
load_validation_rows(path)
```

Dataset row fields:

```text
mfe_mae_id
lead_line_id
symbol
structure_type
validation_status
mfe_pct
mae_pct
time_to_peak_hours
time_to_stop_hours
peak_price
stop_price
outcome_price
is_trade_command=false
```

Structure statistics:

```text
average_mfe
median_mfe
average_mae
median_mae
```

Safety boundaries:

- Hellhound-014 is research-only.
- Hellhound-014 is append-only JSONL.
- Hellhound-014 does not modify Production Hound/Ward/Core.
- Hellhound-014 does not use Binance endpoints.
- Hellhound-014 does not update/delete DB rows.
- Hellhound-014 does not stage, commit, or push git changes.

## Hellhound-014-A Production Interface v1

Status: initial implementation.

Sprint 11A asks:

```text
Can Production Hound call Hellhound as a modular advisory library without giving Hellhound trade authority?
```

Implemented module:

```text
production_interface.py
test_production_interface.py
```

Adapter document:

```text
docs/020_HELLHOUND_PRODUCTION_INTERFACE.md
```

Input:

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

Output:

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

Primary API:

```python
validate_production_interface_input(payload)
evaluate_case(case)
evaluate_cases(cases)
build_production_interface_response(results)
enforce_non_trade_output(payload)
evaluate_production_payload(payload)
```

Output contract:

```text
is_trade_command=false
entry_bias=neutral
risk_note=shadow_only
```

Safety boundaries:

- Hellhound-014-A is advisory-only.
- Hellhound-014-A does not modify Production Hound/Ward/Core.
- Hellhound-014-A does not return trade commands.
- Hellhound-014-A does not use Binance endpoints.
- Hellhound-014-A does not update/delete DB rows.
- Hellhound-014-A does not stage, commit, or push git changes.
