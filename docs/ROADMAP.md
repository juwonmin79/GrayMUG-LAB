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

## Sprint 12O Mirror Contrast Dataset

Status:

```text
Contrast evidence complete; Mirror Pattern implementation remains blocked.
```

Purpose:

```text
Build a success/failure contrast dataset before implementing Mirror Pattern Feature Layer.
No threshold, score formula, gate, ML, Mirror implementation, Medusa, Campaign, or rule changes.
```

Outputs:

```text
outputs/mirror_contrast_dataset.json
outputs/mirror_contrast_report.json
outputs/mirror_feature_validation.json
outputs/replay_contrast_matrix.json
outputs/mirror_feature_stability.json
```

Replay cases:

```text
Success cases:
- WLDUSDT: ignition_return_24h 19.1085
- SOLUSDT: ignition_return_24h 6.693595

Failure cases:
- WLDUSDT: ignition_return_24h -10.442024
- ARBUSDT: ignition_return_24h -8.899297
```

Contrast matrix summary:

```text
Success average score_slope_4: 0.002037
Failure average score_slope_4: -0.0098
Success average RSI persistence: 4.0
Failure average RSI persistence: 6.5
Success average volume delay after score: 0.0
Failure average volume delay after score: -0.5
```

Mirror candidate validation:

```text
hellhound_score temporal line: not validated
rsi_15m temporal line: not validated
volume_ratio_ma20 temporal line: not validated
```

Evidence conclusion:

```text
The 12N temporal line candidates repeat in Success cases, but also repeat in Failure cases.
The current three candidates are not sufficient discriminators.
Sprint 12P should remain evidence/design work unless a stronger contrast discriminator is found.
```

## Sprint 12P Mirror Discriminator Candidate Validation

Status:

```text
Validation complete; Mirror Pattern implementation remains blocked.
```

Purpose:

```text
Validate whether score_slope, rsi_persistence, and volume_delay are repeatable Mirror Discriminators or incidental findings.
No Mirror Layer, threshold, Hellhound Score, PROMOTE gate, ML, or candidate promotion work.
```

Outputs:

```text
outputs/mirror_candidate_validation.json
outputs/mirror_candidate_statistics.json
outputs/mirror_discriminator_ranking.json
outputs/mirror_candidate_stability.json
outputs/replay_expansion_report.json
```

Replay expansion sourcing:

```text
Existing replay outputs reused:
- outputs/btc_replay_dataset.jsonl
- outputs/mirror_contrast_dataset.json

Binance Historical OHLCV pull was not executed because existing replay outputs met the minimum sample count.
```

Replay coverage:

```text
Success: 10
Failure: 10
Asset buckets: BTC 4, Major Alt 3, Mid Cap 13
Failure archetypes: Fake Breakout, Failed Accumulation, Dead Cat Bounce, Liquidity Sweep, Bull Trap
```

Verified:

```text
None
```

Not Verified:

```text
rsi_persistence: stability_score 0.381501, separation 0.216695
score_slope: stability_score 0.314945, separation 0.374723
volume_delay: stability_score 0.236515, separation 0.182574
```

New Candidate:

```text
None
```

Next Sprint:

```text
Sprint 12Q must not implement Mirror Pattern Layer from these candidates.
Keep all three candidates as Candidate Only.
Collect additional contrast evidence and rerun validation before any promotion.
```

## Sprint 12P-A Stability Formula & Threshold Audit

Status:

```text
Audit complete
```

Purpose:

```text
Audit the Sprint 12P Stability Score formula and threshold basis.
This sprint does not pass candidates, implement Mirror Layer, train ML, or change any production logic.
```

Outputs:

```text
outputs/stability_formula_audit.json
outputs/stability_threshold_audit.json
outputs/stability_threshold_evidence.json
outputs/evidence_threshold_design.json
```

Stability formula:

```text
Mirror Candidate Stability Score =
0.4 * Repeatability + 0.4 * Discrimination + 0.2 * Noise
```

Threshold basis:

```text
Temporary Engineering Threshold
Current value is not statistically validated.
Evidence-based Threshold will be derived from Replay Dataset in future sprint.
```

Audit finding:

```text
The requested stability_threshold=0.4 is not present as a standalone pass/fail threshold in code.
The value 0.4 is a formula weight for Repeatability and Discrimination.
The actual Verified rule is stability_score >= 0.6, repeatability >= 0.6, and discrimination >= 0.25.
No dataset-derived ROC, percentile, distribution, Bayesian, or holdout selection process exists yet.
```

Evidence-based threshold design:

```text
Future sprint should derive thresholds from replay data using one or more of:
- ROC-based selection
- Distribution separation
- Percentile-based conservative gate
- Bayesian decision boundary
```

Next Sprint:

```text
Do not change thresholds before threshold derivation rules are fixed.
Do not promote Mirror candidates.
Do not implement Mirror Pattern Layer.
```

## Sprint 12Q Evidence-based Threshold Discovery

Status:

```text
Evidence threshold discovery complete
Mirror Feature Layer remains blocked
```

Purpose:

```text
Remove human-selected candidate thresholds and let Replay Dataset distributions generate threshold candidates.
No new candidates, Mirror Pattern Layer, ML, score change, gate change, or replay data mutation.
```

Inputs:

```text
outputs/replay_expansion_report.json
outputs/mirror_candidate_validation.json
outputs/mirror_candidate_statistics.json
outputs/mirror_discriminator_ranking.json
outputs/mirror_contrast_dataset.json
```

Outputs:

```text
outputs/evidence_threshold_candidates.json
outputs/candidate_distribution_report.json
outputs/candidate_threshold_scan.json
outputs/candidate_best_threshold.json
outputs/candidate_threshold_confidence.json
```

Threshold discovery method:

```text
For each candidate, calculate Success/Failure distributions, mean, median, std, P10/P25/P50/P75/P90.
Run exhaustive ROC-style threshold scan across candidate values.
Calculate precision, recall, F1, and balanced accuracy for each threshold.
Select the best threshold by balanced accuracy, then F1, then precision.
```

Evidence thresholds:

```text
hellhound_score_slope: threshold 0.017537, direction success_lower, precision 0.555556, recall 1.0, F1 0.714286, balanced_accuracy 0.6
rsi_persistence: threshold 6.5, direction success_higher, precision 1.0, recall 0.2, F1 0.333333, balanced_accuracy 0.6
volume_delay: threshold 0.5, direction success_higher, precision 0.666667, recall 0.4, F1 0.5, balanced_accuracy 0.6
```

Final verdict:

```text
hellhound_score_slope: NOT_ENOUGH_EVIDENCE
rsi_persistence: NOT_ENOUGH_EVIDENCE
volume_delay: NOT_ENOUGH_EVIDENCE
```

Temporary threshold comparison:

```text
hellhound_score_slope: threshold_difference 0.017175, precision_change -0.044444, recall_change 0.4, f1_change 0.114286, balanced_accuracy_change 0.0
rsi_persistence: threshold_difference 2.0, precision_change 0.5, recall_change -0.3, f1_change -0.166667, balanced_accuracy_change 0.1
volume_delay: threshold_difference 1.0, precision_change 0.166667, recall_change -0.1, f1_change 0.0, balanced_accuracy_change 0.1
```

Next Sprint:

```text
Do not proceed to 12R Mirror Feature Layer yet.
The Replay Dataset generated numbers, but the evidence level is not sufficient for Mirror layer design.
Expand replay evidence or predeclare a larger derivation dataset before revisiting 12R.
```

## Sprint 12R Campaign Replay Dataset Construction

Status:

```text
Campaign Dataset construction complete
```

Purpose:

```text
Move from single-point Feature Replay to Campaign-level Replay evidence.
Campaign is a structural event covering Pre-Accumulation -> Accumulation -> Ignition -> Expansion -> Distribution or Failure.
No Mirror Pattern Layer, ML training, threshold change, Hellhound Score change, gate change, Replay mutation, or new candidate feature.
```

Outputs:

```text
outputs/campaign_replay_dataset.json
outputs/campaign_summary_report.json
outputs/campaign_statistics.json
outputs/campaign_feature_timeline.json
outputs/campaign_duration_distribution.json
outputs/campaign_candidate_matrix.json
```

Campaign sample requirement:

```text
Success Campaign >= 10
Failure Campaign >= 10
INCONCLUSIVE is recorded for statistics only and excluded from the minimum.
If unmet, Sprint status = PARTIAL.
```

Result:

```text
Sprint status: COMPLETE
Success Campaign: 10
Failure Campaign: 10
INCONCLUSIVE: 0
Binance Historical Pull: not executed
Source priority used: outputs/ existing Replay Dataset expansion
```

Campaign metrics:

```text
Success mean peak_mfe: 11.088732
Failure mean peak_mfe: 6.015404
Success mean early_mae: -2.719359
Failure mean early_mae: -10.91604
Success mean ignition_delay_hours: 10.35
Failure mean ignition_delay_hours: 11.025
Success mean campaign_duration_hours: 20.8
Failure mean campaign_duration_hours: 21.45
```

Phase evidence:

```text
Feature timeline stores hellhound_score, rsi_15m, and volume_ratio_ma20 only.
Candidate matrix records phase appearance, persistence, and collapse phase per Campaign.
No threshold is generated from Campaign data in this Sprint.
```

Next Sprint:

```text
Use Campaign Dataset as shared evidence foundation for future Mirror Pattern, Wave Engine, Rhythm, Campaign Intelligence, and Medusa Board research.
Do not add judgment logic until Campaign-level evidence is reviewed.
```
