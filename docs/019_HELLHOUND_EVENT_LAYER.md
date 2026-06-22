# Hellhound Event Layer

Date: 2026-06-22

Scope: Hellhound LAB only. Production Hound, Ward, Core, `backup_GrayMUG`, `.env`, and trading endpoints are not touched.

## 1. Direction

Hellhound moves from outcome-first analysis toward event-first analysis.

The old outcome loop is still valid for measuring whether a shadow signal worked, but it is too narrow for pre-spike detection. A symbol can emit many hypothesis signals before one actual market move. METUSDT-style runs with dozens of signals should be analyzed as one event timeline first, then measured by outcomes later.

New operating model:

```text
shadow signal
  -> dedupe by symbol/source_time/hypothesis
  -> event timeline
  -> multi-timeframe snapshot
  -> pre-spike features
  -> event classification
  -> optional decision API
```

## 2. Added Modules

`hell_engines/Hellhound/event_layer.py`

- Builds event timelines from `hellhound_shadow_signals`.
- Keeps raw signals intact.
- Dedupes only at the analysis layer by `symbol + source_time + hypothesis`.
- Emits `event_id`, `event_start_bucket`, `max_gap_hours`, `first_seen_time`, `last_seen_time`, `event_age_hours`, `observation_count`, and `observation_timeframe_hint`.

`hell_engines/Hellhound/pre_spike_features.py`

- Defines the multi-timeframe snapshot interface for `1m`, `15m`, `1h`, `4h`, `1d`, `1w`.
- Computes initial pre-spike features:
  - `micro_vol_rise`
  - `vol_ma_acceleration`
  - `price_compression`
  - `rs_slope`
  - `candle_body_expansion`
  - `spike_count_7d`
  - `spike_interval`
  - `watchlist_age`

`watchlist_age` is a placeholder until Hellhound has a safe read-only watchlist first-seen source.

`hell_engines/Hellhound/event_classifier.py`

- Adds initial rule-based event classes:
  - `BEL`: bottom rebound / expansion candidate.
  - `ACT`: long decline / distribution candidate.
  - `ACE`: late detection candidate.
  - `NIGHT`: repeated re-accumulation candidate.

`hell_engines/Hellhound/decision_api.py`

- Provides `evaluate_symbol(symbol, as_of_time=None) -> dict`.
- Default is OFF via `HELLHOUND_DECISION_ENABLED=false`.
- Any error returns `entry_bias="neutral"` and `confidence=0`.

`hell_engines/Hellhound/integration_stub.py`

- Example-only optional import surface for future Hound work.
- Production Hound is not modified.

`hell_engines/Hellhound/accumulation_features.py`

- Adds Sprint 3 Accumulation Intelligence.
- Computes whether a symbol has been building before a spike.
- Adds long-horizon volume, return, high/low distance, repeated activity, structure context, and Hellhound Score v0.2.

`hell_engines/Hellhound/promotion_candidate.py`

- Adds Sprint 4 Shadow Promotion.
- Converts Hellhound score context into `PROMOTE`, `WATCH`, or `REJECT`.
- Builds a shadow decision payload only. It is not a trade command.
- Computes supplied outcome-row correlation by score band.

`hell_engines/Hellhound/real_shadow_feed.py`

- Adds Sprint 6 Real Shadow Feed.
- Reads recent `hound_scan_log` or `hellhound_shadow_signals` rows through Supabase REST GET only.
- Connects each signal to `run_shadow_evaluation_pipeline()`.
- Writes JSONL shadow decisions to `outputs/hellhound_shadow_decisions.jsonl` when not dry-run.
- Prepares read-only outcome joins.
- Detects UTC 00:00 +/- 15m Daily Open Alert Clusters and writes cluster rows to the shadow JSONL log.

`hell_engines/Hellhound/library_interface.py`

- Adds Sprint 7 library/API boundary.
- Accepts `signal`, `event`, or `snapshot` rows.
- Returns `shadow_decision`, `advisor_result`, or `cluster` output.
- Forces `is_trade_command=false` on all boundary outputs.

`hell_engines/Hellhound/event_writer.py`

- Adds Sprint 8 append-only Event Writer.
- Validates event records before write.
- Writes JSONL only.
- Converts library boundary outputs into event records.

`hell_engines/Hellhound/lead_line_dataset.py`

- Adds Sprint 9 Lead Line Dataset Builder.
- Uses `real_feed_outcome` as the initial outcome anchor.
- Collects prior events inside configurable lookback windows.
- Writes append-only lead-line candidate rows.

`hell_engines/Hellhound/outcome_validator.py`

- Adds Sprint 10 Outcome Window Validation.
- Validates Lead Line rows across configurable windows.
- Writes append-only validation dataset rows.

## 3. Schema

Schema draft:

```text
hell_engines/Hellhound/event_layer_schema.sql
```

New LAB/shadow tables:

- `hellhound_events`
- `hellhound_event_observations`
- `hellhound_mtf_snapshots`

No migration is applied by this change. Existing `hellhound_shadow_signals` and `hellhound_outcomes` are not deleted or changed.

`event_layer_schema.sql` remains draft-only until an insert-only event writer exists. Its `updated_at` column does not have an automatic refresh trigger yet; that is acceptable while the writer is not implemented.

## 3.1 Current Limitations

Current `event_id` is stable only for the same `symbol + first_seen_time`. If late backfill changes the earliest observed signal, the same market structure can receive a different `event_id`. This is acceptable for the LAB first version, but it is not the final event identity model.

Future event key candidates:

- `symbol + event_start_bucket`
- `symbol + gap-window cluster`
- `symbol + first_hound_alert_id`
- `symbol + first_shadow_signal_id`

Current event metadata already includes:

- `event_start_bucket`
- `max_gap_hours`
- `event_schema_version`
- `observation_timeframe_hint`

## 4. Decision API Contract

Return keys:

```text
hellhound_lib_version
decision_schema_version
event_id
event_state
accumulation_score
pre_spike_score
structure_type
distribution_risk
entry_bias
recommended_tp
recommended_sl
confidence
reasons
repeat_activity_score
structure_score
hellhound_score
```

Fail-safe response:

```text
entry_bias = neutral
confidence = 0
error = present
```

## 5. Hound Integration Point

Future Production Hound integration should be an optional import only:

```python
if HELLHOUND_DECISION_ENABLED:
    from hell_engines.Hellhound.decision_api import evaluate_symbol
```

The caller must treat Hellhound as advisory metadata only. It must not place orders, mutate positions, or override Hound detection thresholds.

## 6. Resync Notes

When resuming work:

1. Read this document.
2. Read `hell_engines/Hellhound/README.md`.
3. Run local tests from `hell_engines/Hellhound`:

```bash
PYTHONPYCACHEPREFIX=/Users/JakeMin/Documents/Project/GrayMUG-LAB/.pycache_test \
python3 -m unittest test_event_layer.py test_outcome_time_windows.py
```

4. Compile new modules:

```bash
PYTHONPYCACHEPREFIX=/Users/JakeMin/Documents/Project/GrayMUG-LAB/.pycache_test \
python3 -m py_compile event_layer.py pre_spike_features.py event_classifier.py decision_api.py integration_stub.py accumulation_features.py test_event_layer.py test_accumulation_features.py
```

## 7. Sprint 3 Accumulation Intelligence

Sprint 3 changes the question:

```text
explosion-after detection
  -> pre-explosion preparation detection
```

`compute_accumulation_features(symbol, historical_candles, event_history=None)` returns:

- 7d/14d/30d volume averages and volume ratios.
- 7d/14d/30d price returns.
- Distance from 30d and 52w high/low.
- Repeated spike counts for 7d/14d/30d.
- Average and minimum spike interval.
- Weekly and monthly trend.
- MA200 and 52w distance context.
- `structure_type`: `ACCUMULATION_BASE`, `MID_CYCLE`, `DISTRIBUTION`, `CAPITULATION`, or `UNKNOWN`.
- `setup_type`: `BEL`, `ACT`, `ACE`, `MET`, or `UNKNOWN`.
- `accumulation_score`, `repeat_activity_score`, `structure_score`, and `hellhound_score`.

This layer remains rule-based. ML is intentionally not used.

## 8. Sprint 4 Shadow Promotion

Sprint 4 changes the question:

```text
good signal
  -> Production promotion candidate
```

Primary functions:

- `evaluate_promotion_candidate(...)`
- `build_shadow_decision(...)`
- `replay_shadow_cases(cases)`
- `compute_outcome_correlation(outcomes)`

Promotion outputs:

- `PROMOTE`
- `WATCH`
- `REJECT`

Initial promotion rule:

- `PROMOTE`: `hellhound_score >= 0.60` and `distribution_risk <= 0.40`, or `ACCUMULATION_BASE` with sufficient accumulation and repeat activity.
- `WATCH`: middle score/risk profile.
- `REJECT`: high distribution risk or distribution/capitulation structure.

Outcome correlation is a pure analysis function over supplied rows. It does not read, update, or delete DB rows.

## 9. Sprint 6 Real Shadow Feed

Sprint 6 changes the input:

```text
synthetic replay
  -> real Hound/Hellhound signal feed
```

Primary functions:

- `load_recent_signals(...)`
- `load_recent_outcomes(...)`
- `build_real_shadow_decision(...)`
- `process_recent_signals(...)`
- `write_shadow_feed_log(...)`
- `join_outcomes(...)`

Default JSONL output:

```text
outputs/hellhound_shadow_decisions.jsonl
```

Daily open cluster row:

- `record_type=daily_open_alert_cluster`
- `cluster_id`
- `symbols`
- `alert_count`
- `avg_vol_ratio`
- `max_vol_ratio`
- `daily_open_cluster=true`
- `detection_delay_candidate=true`

Dry-run:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 100 --dry-run
```

Mock dry-run:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 5 --dry-run --mock
```

The feed reader uses read-only GET requests. It does not apply `event_layer_schema.sql`, and it does not update or delete DB rows.

## 10. Sprint 7 Library/API Boundary

Sprint 7 stabilizes how Production Hound can later call Hellhound without direct coupling.

Boundary functions:

- `evaluate_signal_row(signal, ...)`
- `evaluate_event_row(event, ...)`
- `evaluate_snapshot_row(snapshot, ...)`
- `detect_cluster_rows(signals)`
- `evaluate_real_feed_row(signal, outcome_rows=None)`

Input types:

- signal row
- event row
- snapshot row
- signal batch for cluster detection

Output types:

- shadow decision
- advisor result
- cluster

Contract:

```text
is_trade_command=false
entry_bias=neutral at integration surface
no order fields
no position fields
no DB mutation
append-only JSONL until writer is explicitly approved
```

## 11. Sprint 8 Event Writer + Persistence

Sprint 8 adds append-only research persistence:

```text
boundary output
  -> validated event record
  -> outputs/hellhound_event_layer.jsonl
```

Supported `record_type`:

- `shadow_decision`
- `daily_open_alert_cluster`
- `real_feed_outcome`

Required fields:

- `event_id`
- `event_time`
- `record_type`
- `source`
- `hellhound_version`
- `is_trade_command`

`symbol` is included whenever the source payload provides it.

Primary functions:

- `validate_event(record)`
- `append_event(record, path=...)`
- `append_events(records, path=...)`
- `record_from_boundary_output(payload)`
- `records_from_boundary_output(payload)`

Writer class:

- `EventWriter(path)`

Validation rejects:

- Missing required fields.
- Unknown `record_type`.
- `is_trade_command=true`.

Default JSONL path:

```text
outputs/hellhound_event_layer.jsonl
```

## 12. Sprint 9 Lead Line Dataset Builder

Sprint 9 converts Event Layer history into detection-delay research rows:

```text
real_feed_outcome
  -> collect prior events over 24h/48h/72h
  -> lead line candidate row
  -> outputs/hellhound_lead_line_dataset.jsonl
```

Primary functions:

- `build_lead_line_dataset(...)`
- `collect_pre_outcome_events(...)`
- `create_lead_line_record(...)`
- `load_event_records(path)`
- `write_lead_line_dataset(rows, output_path=..., append=True)`

Initial outcome definition:

```text
record_type=real_feed_outcome
```

Dataset fields:

- `lead_line_id`
- `symbol`
- `outcome_time`
- `hours_before_outcome`
- `saw_shadow_decision`
- `saw_daily_open_cluster`
- `promotion_status`
- `structure_type`
- `hellhound_score`
- `entry_bias`
- `signal_hour`
- `daily_open_cluster`
- `alert_count`
- `event_count`

Default output:

```text
outputs/hellhound_lead_line_dataset.jsonl
```

## 13. Sprint 10 Outcome Window Validation

Sprint 10 validates whether a Lead Line row actually mattered:

```text
lead line row
  -> validation windows 24h/48h/72h
  -> validation status
  -> outputs/hellhound_validation_dataset.jsonl
```

Primary functions:

- `validate_lead_line(...)`
- `validate_outcome_window(...)`
- `create_validation_record(...)`
- `write_validation_dataset(...)`
- `load_lead_line_rows(path)`

Validation status:

- `VALIDATED`
- `DELAYED`
- `INCONCLUSIVE`
- `REJECTED`

Validation fields:

- `validation_id`
- `lead_line_id`
- `symbol`
- `validation_status`
- `validation_window_hours`
- `hours_before_outcome`
- `saw_daily_open_cluster`
- `promotion_status`
- `structure_type`
- `daily_open_cluster`
- `alert_count`
- `event_count`
- `validation_score`
- `is_trade_command=false`

Default output:

```text
outputs/hellhound_validation_dataset.jsonl
```

## 14. Sprint 11 MFE / MAE Engine

Sprint 11 measures the realized excursion profile after validation:

```text
validation row
  -> post-validation price path
  -> MFE / MAE record
  -> outputs/hellhound_mfe_mae_dataset.jsonl
```

Primary functions:

- `calculate_mfe(...)`
- `calculate_mae(...)`
- `calculate_time_to_peak(...)`
- `calculate_time_to_stop(...)`
- `create_mfe_mae_record(...)`
- `write_mfe_mae_dataset(...)`
- `aggregate_mfe_mae_by_structure(...)`
- `load_validation_rows(path)`

MFE / MAE fields:

- `mfe_mae_id`
- `lead_line_id`
- `symbol`
- `structure_type`
- `validation_status`
- `mfe_pct`
- `mae_pct`
- `time_to_peak_hours`
- `time_to_stop_hours`
- `peak_price`
- `stop_price`
- `outcome_price`
- `is_trade_command=false`

Structure aggregation:

- `average_mfe`
- `median_mfe`
- `average_mae`
- `median_mae`

Default output:

```text
outputs/hellhound_mfe_mae_dataset.jsonl
```

## 15. Sprint 11A Production Interface v1

Sprint 11A adds a versioned case batch boundary for future Production Hound adapters:

```text
Production Hound
  -> case batch
  -> Hellhound production interface
  -> advisory output
  -> Production Hound final judgment
```

Module:

```text
hell_engines/Hellhound/production_interface.py
```

Interface version:

```text
hellhound_production_interface_v1
```

Mode:

```text
shadow
```

Primary functions:

- `validate_production_interface_input(payload)`
- `evaluate_case(case)`
- `evaluate_cases(cases)`
- `build_production_interface_response(results)`
- `enforce_non_trade_output(payload)`
- `evaluate_production_payload(payload)`

Output contract:

- `is_trade_command=false`
- `entry_bias=neutral`
- `risk_note=shadow_only`
- `advisory` is metadata only.
- `PROMOTE` must not be mapped to an automatic order.

Adapter design:

- Production Hound remains unchanged.
- A future adapter can convert Hound signal rows into interface cases.
- Hellhound v1/v2/v3 libraries can coexist.
- Production should pin only a validated stable interface version.

Detailed adapter document:

```text
docs/020_HELLHOUND_PRODUCTION_INTERFACE.md
```

## 16. Change History

2026-06-22:

- Added event timeline builder.
- Added analysis-layer signal deduplication.
- Added multi-timeframe snapshot interface.
- Added initial pre-spike feature functions.
- Added rule-based event classifier.
- Added fail-safe Hellhound Decision API draft.
- Added Hound integration stub with default OFF behavior.
- Added schema draft for event/snapshot LAB tables.
- Added tests for METUSDT-style event grouping, stable event IDs, deduplication, and fail-safe API behavior.
- Added same-source-time METUSDT hypothesis preservation test.
- Documented first-seen-based `event_id` limitation and draft schema `updated_at` trigger limitation.
- Added Sprint 3 Accumulation Intelligence Layer.
- Added Hellhound Score v0.2.
- Added synthetic tests for BEL/ACT/repeated spike structure context.
- Added Sprint 4 Shadow Promotion Layer.
- Added BEL/ACT/ACE/MET/NIGHT replay tests.
- Added score-band outcome correlation function.
- Added Sprint 6 Real Shadow Feed.
- Added JSONL shadow decision output interface.
- Added read-only outcome join preparation.
- Added Sprint 6A Daily Open Alert Cluster detection.
- Added Sprint 7 library/API boundary.
- Added signal/event/snapshot facade tests.
- Reconfirmed Event Writer remains deferred.
- Added Sprint 8 Event Writer.
- Added append-only JSONL event persistence.
- Added schema validation and malformed row rejection tests.
- Added Sprint 9 Lead Line Dataset Builder.
- Added pre-outcome window collection tests.
- Added malformed event skip and append-only dataset tests.
- Added Sprint 10 Outcome Window Validation.
- Added validation status tests for VALIDATED/DELAYED/INCONCLUSIVE/REJECTED.
- Added append-only validation dataset writer.
- Added Sprint 11 MFE / MAE Engine.
- Added realized excursion, time-to-peak, time-to-stop, and structure aggregation tests.
- Added Sprint 11A Hellhound Production Interface v1.
- Added case batch advisory boundary and recursive non-trade output enforcement tests.
