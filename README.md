# GrayMUG-LAB

GrayMUG-LAB is the research, validation, and experimental engine lab for GrayMUG.

Current state:

```text
WhaleLab Foundation Complete.
Hellhound Production Shadow Pipeline verified.
Pre-ML observation collection active.
```

## 1. Project Vision

GrayMUG is not designed to maximize USDT returns as the final goal.

The final goal is:

```text
BTC Accumulation Engine
```

Every research module, engine feed, validation result, and future production candidate is judged by whether it can help increase BTC quantity over time.

Core philosophy:

- BTC accumulation comes first.
- USDT return is a tactical measurement, not the final objective.
- Halving cycle is the macro season.
- Whale Link Flow is the live capital current.
- Hound detects alt opportunities.
- Ward keeps the system alive.
- Core keeps the system pointed toward BTC accumulation.
- LAB does not replace production judgment; LAB produces validated candidates.

## 2. Architecture

GrayMUG is now organized as three layers:

```text
GrayMUG-LAB
    |
    v
Hell Engines
    |
    v
Production Engines
```

### GrayMUG-LAB

GrayMUG-LAB is the research and validation layer.

It builds:

- Lead Line Socket
- Target Intelligence Feed
- Engine Fitness Framework
- Signal Calibration Layer
- Execution Guidance API
- Hellhound validation and shadow-node plans

LAB output is not a trade command. It becomes a candidate only after validation.

### Hell Engines

Hell Engines are experimental evolution spaces.

They do not replace production. They create tested merge candidates.

```text
hell_engines/
├─ Hellcore
├─ Hellward
└─ Hellhound
```

### Production Engines

Production engines are the protected operating engines.

They are treated as source-of-truth runtime systems and must not be directly modified by LAB experiments.

Production reference:

```text
backup_GrayMUG/
```

`backup_GrayMUG` is read-only reference material.

## 3. Engine Definition

### Core

Core is the BTC accumulation engine.

Responsibilities:

- BTC accumulation direction
- Market mode context
- Main strategy authority
- Final BTC-focused operating posture

Core is not replaced by LAB.

### Ward

Ward is the survival engine.

Responsibilities:

- Risk monitoring
- Defensive context
- Emergency and survival judgment
- System protection

Ward keeps independent defensive authority.

### Hound

Hound is the alt hunting engine.

Responsibilities:

- Alt target detection
- Rotation opportunity discovery
- Production alert generation
- Hound baseline logic

Hound detection logic must not be directly modified by LAB.

## 4. Hell Engine Definition

### Hellcore

Hellcore is the Core evolution experiment space.

It is used to test BTC accumulation context, Core payloads, and future Core improvement candidates without changing Production Core.

### Hellward

Hellward is the Ward evolution experiment space.

It is used to test LAB risk hints, calibration hints, and defensive context without replacing Ward judgment.

### Hellhound

Hellhound is the Hound evolution experiment space.

It is used to test Lead Line universe priority, Target Feed, Calibration, Execution Guidance, and OracleJP-Supabase shadow-node behavior without changing Production Hound.

Important rule:

```text
Hell Engines do not replace Production.
Hell Engines create validated merge candidates.
```

## 5. WhaleLab Status

WhaleLab-005 foundation is complete through 005-G.

Completed:

- `005-A`: Lead Line API Socket
  - Exposes Whale Link Flow as an internal API socket for Core, Ward, and Hound.
- `005-B`: Engine Integration Harness
  - Builds Core / Ward / Hound state payloads without touching production engines.
- `005-C`: Target Intelligence Pipeline
  - Converts LAB context into engine-owned feeds: Core Target Feed, Ward Risk Feed, Hound Hunt Feed.
- `005-D`: Engine Fitness Framework
  - Measures whether LAB outputs improve Core judgment, Ward survival, and Hound hunting ability.
- `005-E`: LAB Signal Calibration Layer
  - Limits LAB signal strength by engine scope and prevents engine judgment replacement.
- `005-F`: Execution Guidance API
  - Produces pattern, entry style, TP/SL case, and exit trigger guidance without issuing trade commands.
- `005-G`: Hound Interface Audit
  - Maps safe Hound attachment points and confirms Hound should not be directly modified.

WhaleLab conclusion:

```text
Fixed Lead Time hypothesis: rejected
Link Flow approach: retained
Lead Line role: retained
Direct production modification: forbidden
```

## 6. Hellhound Status

Hellhound Pre-ML observation collection is the current active track.

Completed:

- `001-A`: Validation Runner Skeleton
  - Created the minimum runner structure for comparing Production Hound Universe vs Lead Line Universe.
- `001-B`: Production Universe Loader
  - Confirmed Production Hound universe is not a static file.
  - Found dynamic generation at `backup_GrayMUG/hound/scanner.py:HoundScanner.get_top_symbols`.
- `001-C`: OracleJP-Supabase Shadow Node Plan
  - Defined Hellhound as a read-only OracleJP-Supabase shadow node.
  - Defined `hellhound_shadow_signals` and `hellhound_shadow_outcomes` schemas.
  - Confirmed Hellhound creates `shadow_signal` records only.

Current Hellhound architecture:

```text
OracleJP
  |
  v
Supabase market data read-only
  |
  v
Hellhound Shadow Node
  |
  v
LAB Context
  |
  v
hellhound_shadow_signals
  |
  v
hellhound_shadow_outcomes
```

Hellhound does not place orders and does not manage positions.

Current Hellhound analysis direction:

```text
Hound = execution institution
Hellhound = detachable analysis brain
GPT/LAB = continuous Hellhound upgrade surface
ProductHound = future consumer of validated Hellhound decisions
```

Hellhound now treats repeated shadow signals as observations inside event timelines. Outcome tables remain intact, but event analysis is the primary structure for pre-spike detection.

Hellhound is currently Advisor Mode only:

```text
Trade Authority: none
Production Hound result mutation: none
Entry/Exit mutation: none
Order authority: none
Shadow logging: file-based
Communication: library/API boundary
Persistence: append-only JSONL
Dataset: Lead Line pre-outcome rows
Validation: Outcome window rows
MFE/MAE: structure performance rows
Feedback: Production Shadow research dataset
```

Production Shadow Pipeline status:

```text
Production Hound
  -> Hellhound
  -> production_hellhound_shadow.jsonl
  -> outputs/hellhound_feedback_dataset.jsonl
```

This pipeline is built and verified. LAB now focuses on missed cases, success cases, delay measurement, and structure outcome ranking before any ML work starts.

## 7. Current Roadmap

Current stage:

```text
Pre-ML Phase
Observation Collection Before ML
```

The current implementation target is a detachable, fail-safe advisor API that:

- Groups repeated symbol signals into stable event timelines.
- Dedupes `symbol + source_time + hypothesis` at the analysis layer.
- Prepares multi-timeframe snapshots for `1m`, `15m`, `1h`, `4h`, `1d`, and `1w`.
- Computes initial pre-spike features.
- Classifies events as `BEL`, `ACT`, `ACE`, `NIGHT`, or `UNCLASSIFIED`.
- Computes accumulation context and Hellhound Score v0.2.
- Produces shadow promotion status: `PROMOTE`, `WATCH`, or `REJECT`.
- Builds file-based shadow audit rows for later accuracy measurement.
- Reads recent `hound_scan_log` or `hellhound_shadow_signals` rows through read-only GET.
- Writes shadow decisions to `outputs/hellhound_shadow_decisions.jsonl`.
- Exposes signal/event/snapshot facade functions with `is_trade_command=false`.
- Persists validated Event Layer records to `outputs/hellhound_event_layer.jsonl`.
- Builds lead-line candidate rows at `outputs/hellhound_lead_line_dataset.jsonl`.
- Validates lead-line rows at `outputs/hellhound_validation_dataset.jsonl`.
- Measures MFE/MAE at `outputs/hellhound_mfe_mae_dataset.jsonl`.
- Registers missed cases at `outputs/hellhound_missed_cases.jsonl`.
- Registers success cases at `outputs/hellhound_success_cases.jsonl`.
- Ranks structure outcomes at `outputs/hellhound_structure_stats.jsonl`.
- Reports detection delay at `outputs/hellhound_detection_delay_report.jsonl`.
- Converts Production Shadow output into `outputs/hellhound_feedback_dataset.jsonl`.
- Exposes `evaluate_symbol(symbol, as_of_time=None) -> dict`.
- Does not place orders.
- Does not mutate production tables.

Implemented Hellhound-005 files:

- `hell_engines/Hellhound/event_layer.py`
- `hell_engines/Hellhound/pre_spike_features.py`
- `hell_engines/Hellhound/event_classifier.py`
- `hell_engines/Hellhound/decision_api.py`
- `hell_engines/Hellhound/integration_stub.py`
- `hell_engines/Hellhound/wave_snapshot.py`
- `hell_engines/Hellhound/wave_outcome_updater.py`
- `hell_engines/Hellhound/event_layer_schema.sql`
- `hell_engines/Hellhound/test_event_layer.py`
- `hell_engines/Hellhound/accumulation_features.py`
- `hell_engines/Hellhound/promotion_candidate.py`
- `hell_engines/Hellhound/shadow_advisor.py`
- `hell_engines/Hellhound/test_accumulation_features.py`
- `hell_engines/Hellhound/test_promotion_candidate.py`
- `hell_engines/Hellhound/test_shadow_advisor.py`
- `hell_engines/Hellhound/real_shadow_feed.py`
- `hell_engines/Hellhound/test_real_shadow_feed.py`
- `hell_engines/Hellhound/library_interface.py`
- `hell_engines/Hellhound/test_library_interface.py`
- `hell_engines/Hellhound/event_writer.py`
- `hell_engines/Hellhound/test_event_writer.py`
- `hell_engines/Hellhound/lead_line_dataset.py`
- `hell_engines/Hellhound/test_lead_line_dataset.py`
- `hell_engines/Hellhound/outcome_validator.py`
- `hell_engines/Hellhound/test_outcome_validator.py`
- `hell_engines/Hellhound/mfe_mae_engine.py`
- `hell_engines/Hellhound/test_mfe_mae_engine.py`
- `hell_engines/Hellhound/production_interface.py`
- `hell_engines/Hellhound/test_production_interface.py`
- `hell_engines/Hellhound/missed_case_registry.py`
- `hell_engines/Hellhound/success_case_registry.py`
- `hell_engines/Hellhound/structure_outcome_ranking.py`
- `hell_engines/Hellhound/detection_delay_report.py`
- `hell_engines/Hellhound/production_feedback_dataset.py`
- `hell_engines/Hellhound/decision_api.py`
- `hell_engines/Hellhound/integration_stub.py`

Schema draft:

- `hellhound_events`
- `hellhound_event_observations`
- `hellhound_mtf_snapshots`

The API is default OFF:

```text
HELLHOUND_DECISION_ENABLED=false
```

Fail-safe behavior:

```text
entry_bias="neutral"
confidence=0
error present
```

Shadow Advisor flow:

```text
Hound Signal
  -> Hellhound Evaluate
  -> Shadow Decision
  -> Log Only
```

Shadow audit fields:

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

Real shadow feed command:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 100 --dry-run
```

Mock dry-run:

```bash
python3 hell_engines/Hellhound/real_shadow_feed.py --limit 5 --dry-run --mock
```

Library boundary:

```python
evaluate_signal_row(signal)
evaluate_event_row(event)
evaluate_snapshot_row(snapshot)
detect_cluster_rows(signals)
evaluate_real_feed_row(signal)
```

Boundary output never contains a trade command.

Event writer:

```python
append_event(record)
append_events(records)
validate_event(record)
record_from_boundary_output(payload)
records_from_boundary_output(payload)
```

Supported event records:

```text
shadow_decision
daily_open_alert_cluster
real_feed_outcome
```

Lead Line dataset builder:

```python
build_lead_line_dataset(...)
collect_pre_outcome_events(...)
create_lead_line_record(...)
```

Default output:

```text
outputs/hellhound_lead_line_dataset.jsonl
```

Outcome validator:

```python
validate_lead_line(...)
validate_outcome_window(...)
create_validation_record(...)
write_validation_dataset(...)
```

Validation output:

```text
outputs/hellhound_validation_dataset.jsonl
```

## 8. Safety Rules

### backup_GrayMUG

`backup_GrayMUG` is a production reference artifact.

Rules:

- Do not modify.
- Do not delete.
- Do not move.
- Do not rename.
- Do not stage.
- Do not commit.
- Do not push.
- Do not print secrets, keys, tokens, credentials, or `.env` contents.

### Production Core / Ward / Hound

Production engines are protected.

Rules:

- Do not directly modify Production Core.
- Do not directly modify Production Ward.
- Do not directly modify Production Hound.
- Do not replace Hound detection logic.
- Do not replace Ward defense judgment.
- Do not replace Core strategy judgment.

### Experiments

All experiments run through Hell Engines first.

Rules:

- No live trading from LAB.
- No automatic orders.
- No position management.
- No Binance order endpoint calls.
- No production Supabase table update/delete.
- Shadow tables only for Hellhound shadow runs.

## 9. Project Memory

Start with these documents:

| Document | Purpose |
| :--- | :--- |
| `docs/004_PROJECT_STATE.md` | Current project state |
| `docs/000_GOVERNANCE.md` | Mission, ownership, boundaries, non-negotiable rules |
| `docs/005_ARCHITECTURE_MAP.md` | Architecture map |
| `docs/006_DEVELOPMENT_RULES.md` | Development and safety rules |
| `docs/014_HOUND_INTERFACE_AUDIT.md` | Hound attachment audit |
| `docs/015_PRODUCTION_ENGINE_MAP.md` | Production Core / Ward / Hound map |
| `docs/016_HELLHOUND_001_VALIDATION_PLAN.md` | Hellhound-001 validation plan |
| `docs/017_HELLHOUND_001B_PRODUCTION_UNIVERSE_LOADER.md` | Production universe loader finding |
| `docs/018_HELLHOUND_001C_ORACLEJP_SUPABASE_SHADOW_NODE_PLAN.md` | OracleJP-Supabase shadow node plan |
| `docs/019_HELLHOUND_EVENT_LAYER.md` | Hellhound Event Layer and research pipeline |
| `docs/020_HELLHOUND_PRODUCTION_INTERFACE.md` | Hellhound Production Interface v1 adapter boundary |
| `docs/021_ECOSYSTEM_ARCHITECTURE.md` | LAB / Production ecosystem and role separation |
| `docs/022_MISSED_BTC_CASE_REVIEW.md` | Fixed missed BTC rise case review |
| `docs/023_HELLHOUND_OPTIONAL_DECISION_IMPORT.md` | Sprint 12A optional decision import root cause and activation |
| `docs/ROADMAP.md` | Wave Engine v0 Snapshot/Diff/Delta roadmap |

For WhaleLab foundation details:

| Document | Purpose |
| :--- | :--- |
| `docs/007_WHALELAB_005A_LEAD_LINE_API_SOCKET.md` | Lead Line API Socket |
| `docs/010_WHALELAB_005C_TARGET_INTELLIGENCE_PIPELINE.md` | Target Intelligence Pipeline |
| `docs/011_ENGINE_FITNESS_FRAMEWORK.md` | Engine Fitness Framework |
| `docs/012_LAB_SIGNAL_CALIBRATION_LAYER.md` | Signal Calibration Layer |
| `docs/013_EXECUTION_GUIDANCE_API.md` | Execution Guidance API |

## 10. Final Operating Definition

```text
Core accumulates BTC.
Ward keeps the system alive.
Hound hunts alts.
WhaleLab builds validated LAB context.
Hell Engines test evolution candidates.
Production Engines remain protected.
Hellhound can advise Production Hound only through versioned, non-trading interfaces.
ML starts only after missed, success, delay, feedback, and structure datasets have enough real observations.
Every result must flow back to BTC quantity growth.
```

## Sprint 12M BTC Missed Accumulation Replay

Status: evidence complete.

Replay target:

```text
symbol: BTCUSDT
accumulation_start: 2026-06-20T14:00:00+00:00
ignition_time: 2026-06-21T13:45:00+00:00
local_peak_time: 2026-06-22T13:45:00+00:00
row_count: 192
```

Outputs:

```text
outputs/btc_replay_dataset.jsonl
outputs/btc_replay_report.json
outputs/leadline_candidate_report.json
outputs/detectability_verdict.json
```

Detectability verdict:

```text
DETECTABLE_AFTER_THRESHOLD_TUNING
```

Reason:

```text
Pre-ignition features were present and Hellhound score reached 0.5212,
but no pre-ignition row reached the current PROMOTE gate.
```

Missed reason summary:

```text
E_NOT_DETECTABLE_CURRENT_PIPELINE: 170
B_THRESHOLD_INSUFFICIENT: 22
```

Lead Line candidate ranking:

```text
1. hellhound_score
2. rsi_15m
3. volume_ratio_ma20
4. macd_hist_15m
5. volume_ratio_ma5
6. btc_weather
7. signal_hour
```

Boundary:

```text
No Production code changed.
No threshold or gate changed.
No ML, Mirror Pattern, Medusa, or Campaign implementation.
```

## Sprint 12N Mirror Pattern Feature Discovery

Status: evidence complete.

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

Generated outputs:

```text
outputs/mirror_pattern_feature_candidates.json
outputs/mirror_pattern_sequence_report.json
outputs/pre_ignition_temporal_report.json
outputs/feature_transition_matrix.json
```

Dominant sequence:

```text
hellhound_score -> rsi_15m -> volume_ratio_ma20
```

Feature candidates:

```text
1. rsi_15m temporal line
2. hellhound_score temporal line
3. volume_ratio_ma20 temporal line
```

Evidence notes:

```text
hellhound_score and rsi_15m first rose simultaneously.
volume_ratio_ma20 first rose 2 candles later.
The replay window contained 82 high-MFE rows and 0 loss rows, so high-vs-loss delta is not yet available from this single BTC replay.
```

Boundary:

```text
No threshold change.
No score formula change.
No PROMOTE gate change.
No ML training.
No Mirror Pattern implementation.
```

## Sprint 12O Mirror Contrast Dataset

Status: contrast evidence complete; Mirror candidates not validated yet.

Generated outputs:

```text
outputs/mirror_contrast_dataset.json
outputs/mirror_contrast_report.json
outputs/mirror_feature_validation.json
outputs/replay_contrast_matrix.json
outputs/mirror_feature_stability.json
```

Replay cases:

```text
Success:
1. WLDUSDT ignition_return_24h=19.1085
2. SOLUSDT ignition_return_24h=6.693595

Failure:
1. WLDUSDT ignition_return_24h=-10.442024
2. ARBUSDT ignition_return_24h=-8.899297
```

Contrast summary:

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
The 12N candidates repeat in success cases, but they also repeat in failure cases.
Therefore they are not sufficient by themselves to answer whether a Line is real accumulation or a fake signal.
Sprint 12P should not implement Mirror Pattern yet without a stronger contrast discriminator.
```

## Sprint 12P Mirror Discriminator Candidate Validation

Status: validation complete; Mirror promotion blocked.

Generated outputs:

```text
outputs/mirror_candidate_validation.json
outputs/mirror_candidate_statistics.json
outputs/mirror_discriminator_ranking.json
outputs/mirror_candidate_stability.json
outputs/replay_expansion_report.json
```

Replay expansion:

```text
Success samples: 10
Failure samples: 10
Source priority used: existing replay outputs first
Binance Historical OHLCV pull: not executed
Coverage: BTC, Major Alt, Mid Cap
Failure archetypes: Fake Breakout, Failed Accumulation, Dead Cat Bounce, Liquidity Sweep, Bull Trap
```

Verified:

```text
None
```

Not Verified:

```text
rsi_persistence: stability_score=0.381501
score_slope: stability_score=0.314945
volume_delay: stability_score=0.236515
```

New Candidate:

```text
None
```

Next Sprint:

```text
Do not start Mirror Pattern Layer implementation in Sprint 12Q.
Keep score_slope, rsi_persistence, and volume_delay as Candidate Only.
Add more contrast evidence before revalidation.
```

## Sprint 12P-A Stability Formula & Threshold Audit

Status: audit complete.

Generated outputs:

```text
outputs/stability_formula_audit.json
outputs/stability_threshold_audit.json
outputs/stability_threshold_evidence.json
outputs/evidence_threshold_design.json
```

Formula audit:

```text
Mirror Candidate Stability Score =
0.4 * Repeatability + 0.4 * Discrimination + 0.2 * Noise
```

Threshold audit:

```text
Temporary Engineering Threshold
Current value is not statistically validated.
Evidence-based Threshold will be derived from Replay Dataset in future sprint.
```

Code finding:

```text
No standalone stability_threshold=0.4 pass/fail threshold exists in the 12P code.
The value 0.4 is used as a formula weight.
The actual Verified rule is stability_score >= 0.6, repeatability >= 0.6, and discrimination >= 0.25.
Those cutoffs are also Temporary Engineering Thresholds.
```

Next Sprint:

```text
Design an evidence-based threshold using ROC, distribution separation, percentile, or Bayesian boundary methods.
Do not change thresholds until the derivation dataset and selection rule are fixed.
```

## Sprint 12Q Evidence-based Threshold Discovery

Status: evidence threshold discovery complete; Mirror Feature Layer remains blocked.

Generated outputs:

```text
outputs/evidence_threshold_candidates.json
outputs/candidate_distribution_report.json
outputs/candidate_threshold_scan.json
outputs/candidate_best_threshold.json
outputs/candidate_threshold_confidence.json
```

Method:

```text
Replay Dataset distributions were calculated for Success and Failure.
Candidate thresholds were generated by ROC-style exhaustive scan.
Best threshold selection uses balanced accuracy first, then F1, then precision.
No Mirror Pattern Layer, ML, gate, score, or replay data change was performed.
```

Evidence thresholds:

```text
hellhound_score_slope: threshold=0.017537, direction=success_lower, precision=0.555556, recall=1.0, F1=0.714286, balanced_accuracy=0.6, verdict=NOT_ENOUGH_EVIDENCE
rsi_persistence: threshold=6.5, direction=success_higher, precision=1.0, recall=0.2, F1=0.333333, balanced_accuracy=0.6, verdict=NOT_ENOUGH_EVIDENCE
volume_delay: threshold=0.5, direction=success_higher, precision=0.666667, recall=0.4, F1=0.5, balanced_accuracy=0.6, verdict=NOT_ENOUGH_EVIDENCE
```

Temporary vs Evidence Threshold:

```text
hellhound_score_slope: threshold_difference=0.017175, precision_change=-0.044444, recall_change=0.4, f1_change=0.114286, balanced_accuracy_change=0.0
rsi_persistence: threshold_difference=2.0, precision_change=0.5, recall_change=-0.3, f1_change=-0.166667, balanced_accuracy_change=0.1
volume_delay: threshold_difference=1.0, precision_change=0.166667, recall_change=-0.1, f1_change=0.0, balanced_accuracy_change=0.1
```

Next Sprint:

```text
12R Mirror Feature Layer should not begin yet.
Collect more replay evidence or predeclare a larger threshold derivation dataset before any Mirror layer work.
```

## Sprint 12R Campaign Replay Dataset Construction

Status: Campaign Dataset construction complete.

Generated outputs:

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
INCONCLUSIVE is recorded for statistics only and does not count toward the minimum.
Sprint status is PARTIAL if the minimum is not met.
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

Campaign metrics summary:

```text
Success mean peak_mfe: 11.088732
Failure mean peak_mfe: 6.015404
Success mean early_mae: -2.719359
Failure mean early_mae: -10.91604
Success mean campaign_duration_hours: 20.8
Failure mean campaign_duration_hours: 21.45
```

Boundary:

```text
No Mirror Pattern Layer implementation.
No ML training.
No threshold change.
No Hellhound Score calculation change.
No gate change.
No Replay data mutation.
No new Candidate Feature.
```
