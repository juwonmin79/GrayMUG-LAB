# GrayMUG-LAB Roadmap

## Wave Engine v0

Status:

```text
Implemented
```

Purpose:

```text
Build the Wave Dataset before any Mirror Pattern ML, Lead Line ML, or Wave Encoder work.
```

Scope:

- Observation only.
- Dataset accumulation only.
- No Entry/Exit logic changes.
- No Signal Scoring changes.
- No Hound Position structure changes.
- No Wave Feature usage in live judgment.

## Snapshot Layer

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/wave_snapshot.py
```

Function:

```text
_build_snapshot(symbol, timeframe, timestamp)
```

Snapshot vector:

- `price_vs_ma20`
- `price_vs_ma99`
- `volume_ratio_ma5`
- `volume_ratio_ma20`
- `rsi_15m`
- `macd_hist_15m`
- `btc_15m_trend`
- `btc_1h_trend`
- `btc_4h_trend`
- `btc_1d_trend`
- `btc_4h_weather`
- `signal_hour`
- `is_daily_open`
- `is_weekly_open`
- `is_monthly_open`

## Diff Layer

Status:

```text
Implemented
```

Formula:

```text
Diff_A = Snapshot(T-1) - Snapshot(T-2)
Diff_B = Snapshot(T0) - Snapshot(T-1)
```

## Delta Layer

Status:

```text
Implemented
```

Formula:

```text
Delta = Diff_B - Diff_A
```

## Wave Log

Status:

```text
Implemented
```

Append-only file output:

```text
outputs/hellhound_wave_log.jsonl
```

Schema draft:

```text
hell_engines/Hellhound/hound_wave_log_schema.sql
```

Fields:

- `signal_id`
- `snapshot_t2`
- `snapshot_t1`
- `snapshot_t0`
- `diff_a`
- `diff_b`
- `delta`
- `created_at`
- `outcome_mfe_6h`
- `outcome_mae_6h`
- `outcome_mfe_24h`
- `outcome_mae_24h`
- `outcome_mfe_72h`
- `outcome_mae_72h`

## Success Condition

Collect at least 30 Wave rows, then analyze:

- Delta vs MFE correlation.
- Delta vs MAE correlation.
- Similar Delta pattern clusters.

If correlation exists, Sprint 13 can start Wave Encoder research.

If correlation does not exist, redesign the Snapshot definition.

## Outcome Updater

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/wave_outcome_updater.py
```

Windows:

- `6h`
- `24h`
- `72h`

Output fields:

- `outcome_mfe_6h`
- `outcome_mae_6h`
- `outcome_time_to_peak_6h`
- `outcome_mfe_24h`
- `outcome_mae_24h`
- `outcome_time_to_peak_24h`
- `outcome_mfe_72h`
- `outcome_mae_72h`
- `outcome_time_to_peak_72h`

Rule:

```text
No DB update is performed by LAB. The updater returns a new completed wave row for append-only storage or later approved table handling.
```

## Outcome Engine Automation

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/outcome_scheduler.py
```

Production registration:

```text
deploy/systemd/graymug-lab-outcome-scheduler.service
deploy/systemd/graymug-lab-outcome-scheduler.timer
```

Schedule:

```text
Every 15 minutes after boot.
```

Rule:

```text
Fail open. Scheduler failures must not stop Hellhound shadow signal generation or production trading logic.
```

## Production MFE/MAE Lineage

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/mfe_mae_production.py
```

Input:

```text
Supabase hellhound_shadow_signals
Supabase hellhound_outcomes
```

Output:

```text
outputs/hellhound_mfe_mae_dataset.jsonl
```

Lineage key:

```text
signal_id = hellhound_shadow_signals.id
shadow_signal_id = hellhound_shadow_signals.id
```

Rule:

```text
No production trading logic is changed. No Supabase schema migration is required. The production MFE/MAE lineage writer is append-only and is invoked after the Outcome Scheduler resolves due outcomes.
```

## MFE/MAE Dataset Report

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/mfe_mae_dataset_report.py
```

Input:

```text
outputs/hellhound_mfe_mae_dataset.jsonl
```

Output:

```text
outputs/hellhound_mfe_mae_report.json
```

Metrics:

```text
MFE/MAE average, median, p25, p50, p75, p90
Time-To-Peak average, median, p75, p90
Time-To-Stop average, median, p75, p90 for actual stop-hit rows
Structure, promotion_status, and signal_hour group summaries
```

## MFE/MAE Feature Dataset

Status:

```text
Implemented
```

Module:

```text
hell_engines/Hellhound/mfe_mae_feature_enrichment.py
```

Input:

```text
outputs/hellhound_mfe_mae_dataset.jsonl
Supabase hellhound_shadow_signals
```

Output:

```text
outputs/hellhound_mfe_mae_feature_dataset.jsonl
outputs/hellhound_mfe_mae_feature_report.json
```

Fields:

```text
mfe_bucket
mae_bucket
structure_type
hellhound_score
decision_source
signal_hour
signal_day_of_week
btc_weather
volume_ratio_ma5
volume_ratio_ma20
rsi_15m
macd_hist_15m
```

Rule:

```text
No ML training. Feature importance candidates are simple HIGH/EXTREME MFE vs LOSS bucket summary statistics only.
```

Capture path:

```text
shadow_runner.py persists incoming signal features into hellhound_shadow_signals.payload.
real_shadow_feed.py preserves the same feature keys in shadow decision JSONL rows.
mfe_mae_feature_enrichment.py reads the persisted payload by signal_id.
```

## Sprint 12M BTC Missed Accumulation Replay

Status:

```text
Evidence complete
```

Purpose:

```text
Replay a missed BTC accumulation/ignition/peak window with the current Hellhound pipeline.
No new feature, threshold, gate, production logic, ML, Mirror Pattern, Medusa, or Campaign work.
```

Replay target:

```text
symbol: BTCUSDT
accumulation_start: 2026-06-20T14:00:00+00:00
ignition_time: 2026-06-21T13:45:00+00:00
local_peak_time: 2026-06-22T13:45:00+00:00
row_count: 192
selection_method: max_24h_forward_return_latest_1000_15m
```

Outputs:

```text
outputs/btc_replay_dataset.jsonl
outputs/btc_replay_report.json
outputs/leadline_candidate_report.json
outputs/detectability_verdict.json
```

Result:

```text
Detectability Verdict: DETECTABLE_AFTER_THRESHOLD_TUNING
Max pre-ignition score: 0.5212
Pre-ignition promote count: 0
Pre-ignition feature coverage: 100%
```

Missed reason summary:

```text
E_NOT_DETECTABLE_CURRENT_PIPELINE: 170
B_THRESHOLD_INSUFFICIENT: 22
```

Lead Line candidate order:

```text
hellhound_score
rsi_15m
volume_ratio_ma20
macd_hist_15m
volume_ratio_ma5
btc_weather
signal_hour
```

Next direction:

```text
Use this replay evidence as input for Mirror Pattern Feature design.
Do not add new features without replay evidence.
Evidence -> Feature -> ML remains the order.
```

## Sprint 12N Mirror Pattern Feature Discovery

Status:

```text
Evidence complete
```

Purpose:

```text
Define Mirror Pattern Feature candidates from Sprint 12M replay evidence.
No threshold tuning, score formula change, PROMOTE gate change, ML, or Mirror Pattern implementation.
```

Input:

```text
outputs/btc_replay_dataset.jsonl
outputs/btc_replay_report.json
outputs/leadline_candidate_report.json
outputs/detectability_verdict.json
```

Focus features:

```text
hellhound_score
rsi_15m
volume_ratio_ma20
```

Outputs:

```text
outputs/mirror_pattern_feature_candidates.json
outputs/mirror_pattern_sequence_report.json
outputs/pre_ignition_temporal_report.json
outputs/feature_transition_matrix.json
```

Temporal evidence:

```text
Dominant sequence: hellhound_score -> rsi_15m -> volume_ratio_ma20
hellhound_score first rise index: 1
rsi_15m first rise index: 1
volume_ratio_ma20 first rise index: 3
volume lag after score/RSI: 2 candles
```

Candidate order:

```text
1. rsi_15m temporal line
2. hellhound_score temporal line
3. volume_ratio_ma20 temporal line
```

Success vs missed comparison:

```text
High-MFE rows: 82
Loss rows: 0
Conclusion: this BTC replay supports temporal candidate extraction, but does not provide a loss-side contrast set.
```

Sprint 12O input:

```text
Use only these evidence-backed candidates for Mirror Pattern Feature Layer design.
Do not begin ML training.
```
