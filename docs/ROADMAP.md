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
