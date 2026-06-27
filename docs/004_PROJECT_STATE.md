# GrayMUG Project State

* **작성일**: 2026-06-22
* **Phase 전환일**: 2026-06-27
* **범위**: GrayMUG-LAB 기준 프로젝트 현재 상태 요약
* **목적**: 세션, 모델, 담당자가 바뀌어도 GrayMUG가 어디까지 왔는지 5분 안에 복구할 수 있도록 현재 버전, 완료 항목, 진행 항목, 향후 방향을 고정한다.

---

## GrayMUG Phase 2 : GARAGE — Phase Transition Declaration

> LAB built the foundation. GARAGE builds the machine.

### 현재 Phase

```text
Phase 2 — GARAGE
전환일: 2026-06-27
```

### Phase 1 (LAB) 종료 요약

```text
완료: Mirror Foundation / Replay / Persistence / Dataset / Outcome
     Label Pipeline / Feature Matrix / Dataset Split
     ML Training Contract (mirror_ml_training_v1)
     ML Baseline (mirror_ml_baseline_trainer_v1)
Full Test: 903 PASS
```

LAB의 목적은 달성되었다.

### Phase 2 (GARAGE) 운영 원칙

```text
Architect Rule:
  Dynamic Adaptation에 직접 기여하는가?
  기여하지 않으면 만들지 않는다.
```

### Garage Mission (Closed Loop)

```text
Live Market → Shadow → Mirror Feature → Mirror ML → Prediction
     ↑                                                     ↓
Retraining ← Dynamic Adaptation ← Dataset Growth ← Outcome
```

### 고정 vs 진화

```text
고정 (변경 금지)            진화 (계속 갱신)
──────────────────────     ──────────────────────
Mirror Contract            ML Model
Dataset Schema             Feature Weight
Replay Determinism         Threshold / Confidence
JSON Contract              Pattern Ranking
Feature Interface          Retraining Policy
```

### Sprint 우선순위 (GARAGE)

```text
1. Shadow Integration
2. Live Market Data
3. Dynamic Adaptation
4. Continuous Learning
5. Production Promotion
```

---

---

## 1. Current Version

| Area | Version / Status | Notes |
| :--- | :--- | :--- |
| GrayMUG Core | v0.4 기준 | Hound, Ward, Whale Link Flow, Backtest / Validation 축으로 구성 |
| GrayMUG-LAB | Research / Backtest Sandbox | Production 코드 직접 수정 금지 |
| Whale Link Flow | v0.4 validated | Sector Map, Sector Flow, Flow Persistence, Watch Priority 검증 완료 |
| Lead Line API Socket | WhaleLab-005-A complete | Core / Hound / Ward 공통 내부 API 계약 구현 |
| Engine Integration Harness | WhaleLab-005-B complete | Lead Line -> Core / Ward / Hound state 변환 검증 |
| Target Intelligence Pipeline | WhaleLab-005-C complete | Core / Ward / Hound Target Feed API 파이프라인 구현 |
| Engine Fitness Framework | WhaleLab-005-D complete | Core / Ward / Hound 능력 향상 측정 Framework 구현 |
| LAB Signal Calibration Layer | WhaleLab-005-E complete | LAB 신호 강도, 신뢰도, 적용 범위 표준화 |
| Execution Guidance API | WhaleLab-005-F complete | Hound target 발견 후 건별 guidance 생성 |
| Hellhound Event Layer | Initial implementation | Event timeline, pre-spike features, classifier, fail-safe decision API |
| Hellhound Accumulation Intelligence | Initial implementation | Accumulation features, repeated activity, structure context, Hellhound Score v0.2 |
| Hellhound Shadow Promotion | Initial implementation | PROMOTE/WATCH/REJECT gate, shadow decision, replay, outcome band correlation |
| Hellhound Shadow Advisor | Initial implementation | Optional advisor surface, audit rows, replay validation, false-positive analysis, JSONL log interface |
| Hellhound Real Shadow Feed | Initial implementation | Read-only signal feed, advisor pipeline, JSONL shadow decision log, outcome join prep |
| Hellhound Daily Open Cluster | Initial implementation | UTC 00:00 +/- 15m Hound alert cluster detection in shadow log |
| Hellhound Library Boundary | Initial implementation | signal/event/snapshot facade, non-trade output contract, cluster boundary |
| Hellhound Event Writer | Initial implementation | append-only JSONL event persistence, schema validation, boundary output conversion |
| Hellhound Lead Line Dataset | Initial implementation | pre-outcome event collection, lead-line candidate dataset, detection delay research |
| Hellhound Outcome Validation | Initial implementation | validation windows, VALIDATED/DELAYED/INCONCLUSIVE/REJECTED, validation dataset |
| Hellhound Production Interface v1 | Initial implementation | case batch advisory boundary, non-trade output enforcement, future adapter contract |
| Hellhound MFE/MAE Engine | Initial implementation | MFE, MAE, peak/stop timing, structure aggregation |
| Production Shadow Pipeline | Verified | Production Hound -> Hellhound -> production_hellhound_shadow.jsonl verified |
| Pre-ML Observation Collection | Initial implementation | missed/success cases, delay report, structure stats, feedback dataset |
| Optional Decision Import | Activated for LAB/library shadow paths | `decision_enabled=True`, `decision_source=decision_api`, fallback still explicit |
| Wave Engine v0 Dataset Layer | Initial implementation | Snapshot, Diff, Delta, append-only wave log, outcome updater |
| ML Core | Deferred | ML design postponed until observation data is sufficient |

---

## 2. Completed

### Hound
* 고래 감지 계층.
* Whale Link Flow의 Watch Priority를 받을 수 있는 최종 관찰 대상 계층으로 정의됨.
* LAB 산출물은 Hound에 직접 병합하지 않고 Research -> Backtest -> Validation -> Production 절차를 통과해야 함.

### Ward
* 위험 감시 계층.
* Production 안전장치에 해당하며 LAB 리서치와 직접 결합하지 않음.

### Whale Link Flow v0.4
* 4.5년 역사 데이터 기준 7대 이벤트 검증 완료.
* 구현/검증된 구성:
  - Cycle Layer
  - Live Flow Layer
  - Link Graph
  - Sector Map / Sector Flow
  - Flow Persistence
  - Whale Type
  - Watch Priority
* 역할은 직접 매매가 아니라 Hound의 관찰 가중치를 조절하는 Lead Line.

### Backtest / Validation
* Whale Inception 고정 Lead Time 가설 검증 완료.
* 기존 "평균 22.61시간 Lead Time" 가설은 역방향 탐색 윈도우 편향으로 판정되어 폐기.
* 대안 방향은 단일 시점 탐지가 아니라 다차원 시그널의 누적 개선:
  - 지속적인 Rank Momentum
  - RS vs BTC Decoupling
  - 유동적 Inception 탐색
  - Flow Persistence

### WhaleLab-005-A
* Lead Line API Socket 구현 완료.
* 구현 파일:
  - `research/whale_link_flow/lead_line_socket.py`
  - `docs/007_WHALELAB_005A_LEAD_LINE_API_SOCKET.md`
* 지원 API:
  - `get_current_lead_line()`
  - `get_hound_universe()`
  - `get_ward_context()`
  - `get_core_payload()`
* 지원 모드:
  - `BEAR_ESCAPE`
  - `BTC_ACCUMULATION`
  - `OBSERVE_ONLY`

### WhaleLab-005-B
* Engine Integration Harness 구현 완료.
* 구현 파일:
  - `research/integration/state_schema.py`
  - `research/integration/core_adapter.py`
  - `research/integration/ward_adapter.py`
  - `research/integration/hound_adapter.py`
  - `research/integration/integration_harness.py`
  - `research/integration/simulator_payload.py`
  - `research/integration/test_harness.py`
  - `research/integration/README.md`
  - `docs/009_SIMULATOR_FOUNDATION.md`
* 검증:
  - Lead Line 수신 성공
  - CoreState 생성 성공
  - WardState 생성 성공
  - HoundState 생성 성공
  - Simulator Payload 생성 성공

### WhaleLab-005-C
* Target Intelligence Pipeline 구현 완료.
* 구현 파일:
  - `research/targeting/target_schema.py`
  - `research/targeting/target_feed_builder.py`
  - `research/targeting/core_target_feed.py`
  - `research/targeting/ward_risk_feed.py`
  - `research/targeting/hound_hunt_feed.py`
  - `research/targeting/target_pipeline.py`
  - `research/targeting/test_target_pipeline.py`
  - `research/targeting/README.md`
  - `docs/010_WHALELAB_005C_TARGET_INTELLIGENCE_PIPELINE.md`
* 보조 출력:
  - `outputs/targeting/latest_target_feed.json`
* 검증:
  - CoreTargetFeed 생성 성공
  - WardRiskFeed 생성 성공
  - HoundHuntFeed 생성 성공
  - TargetPipelinePayload 생성 성공
  - 각 Feed의 engine 귀속 확인

### WhaleLab-005-D
* Engine Fitness Framework 구현 완료.
* 구현 파일:
  - `research/fitness/fitness_schema.py`
  - `research/fitness/core_fitness.py`
  - `research/fitness/ward_fitness.py`
  - `research/fitness/hound_fitness.py`
  - `research/fitness/fitness_registry.py`
  - `research/fitness/fitness_score.py`
  - `research/fitness/fitness_pipeline.py`
  - `research/fitness/test_fitness_pipeline.py`
  - `research/fitness/README.md`
  - `docs/011_ENGINE_FITNESS_FRAMEWORK.md`
* 검증:
  - CoreFitness 생성 성공
  - WardFitness 생성 성공
  - HoundFitness 생성 성공
  - FitnessReport 생성 성공
  - overall_score 계산 성공

### WhaleLab-005-E
* LAB Signal Calibration Layer 구현 완료.
* 구현 파일:
  - `research/calibration/calibration_schema.py`
  - `research/calibration/signal_calibrator.py`
  - `research/calibration/engine_scope.py`
  - `research/calibration/calibration_policy.py`
  - `research/calibration/calibration_pipeline.py`
  - `research/calibration/test_calibration_pipeline.py`
  - `research/calibration/README.md`
  - `docs/012_LAB_SIGNAL_CALIBRATION_LAYER.md`
* 정책:
  - Core max influence: `0.20`
  - Ward max influence: `0.15`
  - Hound max influence: `0.30`
* 검증:
  - Core final_weight <= 0.20
  - Ward final_weight <= 0.15
  - Hound final_weight <= 0.30
  - 각 signal의 단일 engine 귀속 확인
  - forbidden scope 미사용 확인

### WhaleLab-005-F
* Execution Guidance API 구현 완료.
* 구현 파일:
  - `research/execution/execution_schema.py`
  - `research/execution/pattern_classifier.py`
  - `research/execution/entry_guidance.py`
  - `research/execution/tp_sl_guidance.py`
  - `research/execution/exit_guidance.py`
  - `research/execution/execution_builder.py`
  - `research/execution/execution_pipeline.py`
  - `research/execution/test_execution_pipeline.py`
  - `research/execution/README.md`
  - `docs/013_EXECUTION_GUIDANCE_API.md`
* 검증:
  - Pattern 생성 성공
  - Entry 생성 성공
  - TP/SL 생성 성공
  - Exit 생성 성공
  - Payload 생성 성공

### Hellhound-005 Event Layer
* Hound 직접 수정 없이 Hellhound를 탈착식 분석 두뇌로 만드는 1차 구현.
* 구현 파일:
  - `hell_engines/Hellhound/event_layer.py`
  - `hell_engines/Hellhound/pre_spike_features.py`
  - `hell_engines/Hellhound/event_classifier.py`
  - `hell_engines/Hellhound/decision_api.py`
  - `hell_engines/Hellhound/integration_stub.py`
  - `hell_engines/Hellhound/event_layer_schema.sql`
  - `hell_engines/Hellhound/test_event_layer.py`
  - `docs/019_HELLHOUND_EVENT_LAYER.md`
* 핵심:
  - 동일 symbol의 연속 shadow signal을 event timeline으로 묶음.
  - `symbol + source_time + hypothesis` 기준 중복 signal은 분석 단위에서 제거.
  - 기존 `hellhound_shadow_signals`와 `hellhound_outcomes`는 삭제하지 않음.
  - `1m/15m/1h/4h/1d/1w` multi-timeframe snapshot interface 준비.
  - `BEL`, `ACT`, `ACE`, `NIGHT` rule-based classifier 추가.
  - `evaluate_symbol(symbol, as_of_time=None)` fail-safe API 추가.
* 기본값:
  - `HELLHOUND_DECISION_ENABLED=false`
  - 오류 또는 비활성 상태에서는 `entry_bias="neutral"`, `confidence=0`
* 검증:
  - METUSDT 84개 signal -> 1개 event.
  - event_id 안정성.
  - duplicate signal deduplication.
  - `evaluate_symbol()` fail-safe off 동작.

### Hellhound-006 Accumulation Intelligence Layer
* 목적:
  - "고래가 나타났다"가 아니라 "고래가 준비 중이다"를 찾는 layer.
  - 폭발 이후 감지에서 폭발 이전 준비 상태 감지로 전환.
* 구현 파일:
  - `hell_engines/Hellhound/accumulation_features.py`
  - `hell_engines/Hellhound/test_accumulation_features.py`
* 추가 API:
  - `compute_accumulation_features(symbol, historical_candles, event_history=None)`
  - `evaluate_symbol(..., historical_candles=None, event_history=None)` optional context
* 출력:
  - `vol_7d_avg`, `vol_14d_avg`, `vol_30d_avg`
  - `vol_ratio_7d_vs_30d`, `vol_ratio_14d_vs_30d`
  - `price_return_7d`, `price_return_14d`, `price_return_30d`
  - `price_from_30d_high`, `price_from_52w_high`
  - `price_from_30d_low`, `price_from_52w_low`
  - `spike_count_7d`, `spike_count_14d`, `spike_count_30d`
  - `avg_spike_interval_days`, `min_spike_interval_days`
  - `weekly_trend`, `monthly_trend`, `distance_ma200`, `distance_52w_high`, `distance_52w_low`
  - `structure_type`, `setup_type`
  - `accumulation_score`, `repeat_activity_score`, `structure_score`, `hellhound_score`
* 검증:
  - 장기 바닥 + 거래량 증가 -> 높은 accumulation score.
  - 고점 부근 + 거래량 감소 -> 높은 distribution risk.
  - 반복 spike -> 높은 repeat activity score.
  - ACT 유사 데이터 -> `DISTRIBUTION` 또는 `CAPITULATION`.
  - BEL 유사 데이터 -> `ACCUMULATION_BASE`.

### Hellhound-007 Shadow Promotion Layer
* 목적:
  - "좋은 신호"가 아니라 Production 승격 후보를 찾는 gate.
  - Production Hound 이식 전 shadow-only 승격 판단을 분리.
* 구현 파일:
  - `hell_engines/Hellhound/promotion_candidate.py`
  - `hell_engines/Hellhound/test_promotion_candidate.py`
* 추가 API:
  - `evaluate_promotion_candidate(...)`
  - `build_shadow_decision(...)`
  - `replay_shadow_cases(cases)`
  - `compute_outcome_correlation(outcomes)`
* Promotion status:
  - `PROMOTE`
  - `WATCH`
  - `REJECT`
* 검증:
  - BEL replay -> `PROMOTE`
  - ACT replay -> `REJECT`
  - ACE replay -> `REJECT`
  - MET replay -> `WATCH`
  - NIGHT replay -> `WATCH`
  - score band별 outcome win rate 계산

### Hellhound-008 Shadow Advisor Mode
* 목적:
  - Production Hound를 수정하지 않고 Hellhound 판단을 옆에서 기록한다.
  - "Hellhound가 맞았는가?"를 실시간으로 증명하기 위한 shadow history 확보.
* 구현 파일:
  - `hell_engines/Hellhound/integration_stub.py`
  - `hell_engines/Hellhound/shadow_advisor.py`
  - `hell_engines/Hellhound/test_shadow_advisor.py`
* 추가 API:
  - `optional_hellhound_decision(symbol, signal=None, shadow_signals=None, historical_candles=None, event_history=None, as_of_time=None)`
  - `run_shadow_evaluation_pipeline(...)`
  - `audit_decision(...)`
  - `write_shadow_decision_log(...)`
  - `replay_validation(cases)`
  - `analyze_false_positives(rows)`
* 출력:
  - `hellhound_score`
  - `accumulation_score`
  - `repeat_activity_score`
  - `structure_type`
  - `setup_type`
  - `promotion_status`
  - `distribution_risk`
  - `entry_bias`
  - `reasons`
  - `is_trade_command=false`
* Shadow audit fields:
  - `symbol`, `signal_time`, `event_id`
  - `hellhound_score`, `promotion_status`, `entry_bias`
  - `actual_1h_outcome`, `actual_4h_outcome`, `actual_24h_outcome`
* Log interface:
  - JSONL file path, default name `shadow_decision_log.jsonl`
  - DB is not required and not used.
* 명시:
  - Hellhound는 Advisor Mode.
  - Trade Authority 없음.
  - Hound 결과, entry, exit, order path에 영향 없음.

### Hellhound-009 Real Shadow Feed
* 목적:
  - 실제 Hound/Hellhound DB 신호를 Shadow Advisor에 연결한다.
  - 거래 없이 shadow decision history를 파일로 축적한다.
* 구현 파일:
  - `hell_engines/Hellhound/real_shadow_feed.py`
  - `hell_engines/Hellhound/test_real_shadow_feed.py`
* 추가 API:
  - `load_recent_signals(limit=100, table_candidates=(hound_scan_log, hellhound_shadow_signals))`
  - `load_recent_outcomes(limit=500)`
  - `build_real_shadow_decision(signal, outcome_rows=None)`
  - `process_recent_signals(signals, outcome_rows=None, output_path=..., dry_run=True)`
  - `write_shadow_feed_log(decisions, output_path=...)`
  - `join_outcomes(signal, outcome_rows)`
* Log interface:
  - 기본 경로: `outputs/hellhound_shadow_decisions.jsonl`
  - 필드: `symbol`, `signal_time`, `event_id`, `hellhound_score`, `promotion_status`, `structure_type`, `setup_type`, `distribution_risk`, `reasons`
* Outcome join:
  - `hellhound_outcomes` read-only GET 준비.
  - `actual_1h_outcome`, `actual_4h_outcome`, `actual_24h_outcome`은 있으면 채우고 없으면 `null`.
* CLI:
  - `python3 hell_engines/Hellhound/real_shadow_feed.py --limit 100 --dry-run`
  - `python3 hell_engines/Hellhound/real_shadow_feed.py --limit 5 --dry-run --mock`
* 명시:
  - DB delete/update 없음.
  - event schema 적용 없음.
  - Production Hound/Ward/Core 영향 없음.

### Hellhound-009-A Daily Open Alert Cluster
* 목적:
  - UTC daily open 전후에 몰리는 Hound alerts를 하나의 delay candidate cluster로 기록한다.
* 구현:
  - UTC `00:00 +/- 15m` 내 signal을 date bucket으로 묶음.
  - `cluster_id`, `symbols`, `alert_count`, `avg_vol_ratio`, `max_vol_ratio` 계산.
  - `daily_open_cluster=true`, `detection_delay_candidate=true`.
  - `record_type=daily_open_alert_cluster`로 shadow JSONL log에 함께 기록.

### Hellhound-010 Library/API Boundary
* 목적:
  - Production Hound 옆에서 Hellhound를 안전하게 호출할 수 있는 순수 함수/API 경계를 정리한다.
  - 직접 결합이 아니라 library boundary로 `signal/event/snapshot` row를 받아 shadow output만 반환한다.
* 구현 파일:
  - `hell_engines/Hellhound/library_interface.py`
  - `hell_engines/Hellhound/test_library_interface.py`
* Interface:
  - `evaluate_signal_row(signal, shadow_signals=None, historical_candles=None, event_history=None)`
  - `evaluate_event_row(event, signal=None, historical_candles=None)`
  - `evaluate_snapshot_row(snapshot, signal=None)`
  - `detect_cluster_rows(signals)`
  - `evaluate_real_feed_row(signal, outcome_rows=None)`
* Output contract:
  - `shadow_decision`
  - `advisor_result`
  - `cluster`
  - `is_trade_command=false`
  - `entry_bias=neutral` at integration surface
* Event Writer:
  - Sprint 7에서는 보류.
  - append-only JSONL 원칙 유지.
  - DB persistence보다 boundary 안정화 우선.

### Hellhound-011 Event Writer + Persistence
* 목적:
  - Hellhound research output을 학습 가능한 Event Layer로 append-only 저장.
  - 미래 Lead Line, MFE/MAE, Mirror Pattern ML 입력 데이터 준비.
* 구현 파일:
  - `hell_engines/Hellhound/event_writer.py`
  - `hell_engines/Hellhound/test_event_writer.py`
* 추가 API:
  - `EventWriter(path).append_event(record)`
  - `EventWriter(path).append_events(records)`
  - `append_event(record, path=...)`
  - `append_events(records, path=...)`
  - `validate_event(record)`
  - `record_from_boundary_output(payload)`
  - `records_from_boundary_output(payload)`
* 지원 record_type:
  - `shadow_decision`
  - `daily_open_alert_cluster`
  - `real_feed_outcome`
* 필수 공통 필드:
  - `event_id`, `event_time`, `record_type`, `source`, `hellhound_version`, `is_trade_command`
  - `symbol`은 가능 시 포함.
* 저장:
  - 기본 경로 `outputs/hellhound_event_layer.jsonl`
  - JSONL append-only.
* 검증:
  - 필수 필드 누락 reject.
  - invalid record_type reject.
  - `is_trade_command=true` reject.
  - 단일 row, batch row, cluster row append 검증.

### Hellhound-012 Lead Line Dataset Builder
* 목적:
  - "상승 결과가 발생하기 전에 Hellhound가 무엇을 보았는가?"를 dataset으로 변환.
  - Detection Delay 감소 연구 입력 생성.
* 구현 파일:
  - `hell_engines/Hellhound/lead_line_dataset.py`
  - `hell_engines/Hellhound/test_lead_line_dataset.py`
* 추가 API:
  - `build_lead_line_dataset(...)`
  - `collect_pre_outcome_events(...)`
  - `create_lead_line_record(...)`
  - `load_event_records(path)`
  - `write_lead_line_dataset(rows, output_path=..., append=True)`
* Outcome anchor:
  - 초기 버전은 `record_type=real_feed_outcome`.
* 기본 window:
  - `24h`, `48h`, `72h`
* Dataset output:
  - `outputs/hellhound_lead_line_dataset.jsonl`
* 주요 fields:
  - `lead_line_id`, `symbol`, `outcome_time`
  - `hours_before_outcome`
  - `saw_shadow_decision`, `saw_daily_open_cluster`
  - `promotion_status`, `structure_type`, `hellhound_score`, `entry_bias`
  - `signal_hour`, `daily_open_cluster`, `alert_count`, `event_count`
* 검증:
  - outcome join.
  - window filtering.
  - empty dataset.
  - malformed event skip.
  - dataset row append.

### Hellhound-013 Outcome Window Validation
* 목적:
  - Lead Line row가 실제 outcome에 대해 의미 있었는지 검증한다.
  - Detection Delay 측정을 시작한다.
* 구현 파일:
  - `hell_engines/Hellhound/outcome_validator.py`
  - `hell_engines/Hellhound/test_outcome_validator.py`
* 추가 API:
  - `validate_lead_line(...)`
  - `validate_outcome_window(...)`
  - `create_validation_record(...)`
  - `write_validation_dataset(...)`
  - `load_lead_line_rows(path)`
* 지원 status:
  - `VALIDATED`
  - `DELAYED`
  - `INCONCLUSIVE`
  - `REJECTED`
* 기본 window:
  - `24h`, `48h`, `72h`
* Output:
  - `outputs/hellhound_validation_dataset.jsonl`
* 주요 fields:
  - `validation_id`, `lead_line_id`, `symbol`
  - `validation_status`, `validation_window_hours`, `hours_before_outcome`
  - `saw_daily_open_cluster`, `promotion_status`, `structure_type`
  - `daily_open_cluster`, `alert_count`, `event_count`
  - `validation_score`, `is_trade_command=false`
* 검증:
  - `VALIDATED`, `DELAYED`, `INCONCLUSIVE`, `REJECTED`
  - validation window 생성.
  - malformed row skip.
  - append-only validation dataset.

### Hellhound-014 MFE / MAE Engine
* 목적:
  - 검증된 Lead Line 패턴의 수익구간과 손실 흔들림을 측정한다.
  - "맞았는가" 이후 "보통 얼마나 먹는가"를 구조별로 집계한다.
* 구현 파일:
  - `hell_engines/Hellhound/mfe_mae_engine.py`
  - `hell_engines/Hellhound/test_mfe_mae_engine.py`
* 추가 API:
  - `calculate_mfe(...)`
  - `calculate_mae(...)`
  - `calculate_time_to_peak(...)`
  - `calculate_time_to_stop(...)`
  - `create_mfe_mae_record(...)`
  - `write_mfe_mae_dataset(...)`
  - `aggregate_mfe_mae_by_structure(...)`
  - `load_validation_rows(path)`
* 입력:
  - `outputs/hellhound_validation_dataset.jsonl`
  - validation row별 post-validation price path.
* Dataset output:
  - `outputs/hellhound_mfe_mae_dataset.jsonl`
* 주요 fields:
  - `mfe_mae_id`, `lead_line_id`, `symbol`
  - `structure_type`, `validation_status`
  - `mfe_pct`, `mae_pct`
  - `time_to_peak_hours`, `time_to_stop_hours`
  - `peak_price`, `stop_price`, `outcome_price`
  - `is_trade_command=false`
* 검증:
  - MFE / MAE 계산.
  - peak / stop 시간 계산.
  - 구조별 집계.
  - malformed validation row skip.
  - append-only MFE/MAE dataset.

### Hellhound-014-A Production Interface v1
* 목적:
  - Production Hound를 수정하지 않고 Hellhound를 모듈형 advisory library로 호출할 수 있는 case batch boundary를 제공한다.
  - Claude 쪽 Production에는 나중에 adapter 형태로 붙일 수 있게 한다.
* 구현 파일:
  - `hell_engines/Hellhound/production_interface.py`
  - `hell_engines/Hellhound/test_production_interface.py`
  - `docs/020_HELLHOUND_PRODUCTION_INTERFACE.md`
* 추가 API:
  - `validate_production_interface_input(payload)`
  - `evaluate_case(case)`
  - `evaluate_cases(cases)`
  - `build_production_interface_response(results)`
  - `enforce_non_trade_output(payload)`
  - `evaluate_production_payload(payload)`
* Input:
  - `interface_version=hellhound_production_interface_v1`
  - `mode=shadow`
  - `cases=[{case_id, symbol, signal, snapshot}]`
* Output:
  - `results=[{case_id, symbol, structure_type, promotion_status, hellhound_score, entry_bias, advisory, risk_note}]`
  - `is_trade_command=false`
* 검증:
  - 다수 case batch 처리.
  - `case_id` 보존.
  - recursive non-trade output 강제.
  - malformed case fail-safe.
  - empty cases 처리.
  - 기존 `library_interface` 호환.

### Hellhound Pre-ML Observation Collection
* 목적:
  - ML 이전에 Hellhound의 실전 관찰 결과를 축적한다.
  - "무엇을 놓쳤는가"를 체계적으로 기록한다.
* 구현 파일:
  - `hell_engines/Hellhound/missed_case_registry.py`
  - `hell_engines/Hellhound/success_case_registry.py`
  - `hell_engines/Hellhound/structure_outcome_ranking.py`
  - `hell_engines/Hellhound/detection_delay_report.py`
  - `hell_engines/Hellhound/production_feedback_dataset.py`
  - `hell_engines/Hellhound/test_case_registries.py`
  - `hell_engines/Hellhound/test_pre_ml_datasets.py`
* 출력:
  - `outputs/hellhound_missed_cases.jsonl`
  - `outputs/hellhound_success_cases.jsonl`
  - `outputs/hellhound_structure_stats.jsonl`
  - `outputs/hellhound_detection_delay_report.jsonl`
  - `outputs/hellhound_feedback_dataset.jsonl`
* 구조별 대상:
  - `BEL`
  - `ACT`
  - `ACE`
  - `MET`
  - `NIGHT`
* 검증:
  - missed/success case record 생성.
  - append-only JSONL writer.
  - structure별 발생 횟수, VALIDATED 비율, 평균 MFE/MAE/Time To Peak.
  - detection delay 평균/중앙값/최소/최대.
  - Production Shadow row의 feedback dataset 변환.
  - 모든 output `is_trade_command=false`.

### Sprint 12A Optional Decision Import
* 목적:
  - `source_error=Hellhound optional decision import is disabled.` 반복 원인 조사.
  - fallback evaluator가 아니라 실제 decision path 활성화.
* 원인:
  - `integration_stub.py`와 `decision_api.py` 모두 `HELLHOUND_DECISION_ENABLED=false` 기본값으로 fail-safe neutral을 반환했다.
  - import 대상 파일은 존재했고 ImportError가 아니었다.
* 수정:
  - `optional_hellhound_decision(..., decision_enabled=...)`
  - `evaluate_symbol(..., decision_enabled=...)`
  - LAB/library/real shadow/production interface 호출부는 기본 `decision_enabled=True`.
  - 명시적 fallback은 `decision_enabled=False`로 유지.
* 상세:
  - `docs/023_HELLHOUND_OPTIONAL_DECISION_IMPORT.md`

### Sprint 12B Wave Engine v0
* 목적:
  - Wave Engine용 Dataset Layer를 구축한다.
  - Mirror Pattern ML, Lead Line ML, MFE/MAE Engine의 미래 학습 기반을 만든다.
* 구현 파일:
  - `hell_engines/Hellhound/wave_snapshot.py`
  - `hell_engines/Hellhound/wave_outcome_updater.py`
  - `hell_engines/Hellhound/hound_wave_log_schema.sql`
  - `hell_engines/Hellhound/test_wave_snapshot.py`
  - `hell_engines/Hellhound/test_wave_outcome_updater.py`
  - `docs/ROADMAP.md`

### Sprint 12M BTC Missed Accumulation Replay

Status:

```text
Evidence complete
```

Scope:

```text
Replay only. No Production code, threshold, gate, ML, Mirror Pattern, Medusa, or Campaign changes.
```

Replay target:

```text
symbol: BTCUSDT
accumulation_start: 2026-06-20T14:00:00+00:00
ignition_time: 2026-06-21T13:45:00+00:00
local_peak_time: 2026-06-22T13:45:00+00:00
row_count: 192
```

Generated outputs:

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

Evidence:

```text
Pre-ignition feature coverage: 100%
Max pre-ignition score: 0.5212
Pre-ignition PROMOTE count: 0
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

Next state:

```text
Sprint 12M output is input evidence for Mirror Pattern Feature design.
No new Feature or ML work should begin without replay-backed evidence.
```

### Sprint 12N Mirror Pattern Feature Discovery

Status:

```text
Evidence complete
```

Scope:

```text
Read-only evidence analysis from Sprint 12M replay outputs.
No threshold, Hellhound score formula, PROMOTE gate, ML, Mirror Pattern implementation, Medusa, or Campaign changes.
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

Generated outputs:

```text
outputs/mirror_pattern_feature_candidates.json
outputs/mirror_pattern_sequence_report.json
outputs/pre_ignition_temporal_report.json
outputs/feature_transition_matrix.json
```

Feature candidate ranking:

```text
1. rsi_15m temporal line
2. hellhound_score temporal line
3. volume_ratio_ma20 temporal line
```

Sequence evidence:

```text
Dominant sequence: hellhound_score -> rsi_15m -> volume_ratio_ma20
hellhound_score and rsi_15m first rise together.
volume_ratio_ma20 first rise occurs 2 candles later.
```

Success vs missed note:

```text
High-MFE rows: 82
Loss rows: 0
This replay has no loss-side contrast set; additional missed/loss replay cases are needed before ML or threshold optimization.
```

Next state:

```text
Sprint 12O may design a Mirror Pattern Feature Layer using only these evidence-backed temporal line candidates.
ML remains blocked.
```

### Sprint 12O Mirror Contrast Dataset

Status:

```text
Contrast evidence complete
Mirror Pattern implementation remains blocked
```

Scope:

```text
Replay and compare only.
No threshold change, Hellhound score change, PROMOTE gate change, ML, Mirror Pattern implementation, Medusa, Campaign, or rule changes.
```

Generated outputs:

```text
outputs/mirror_contrast_dataset.json
outputs/mirror_contrast_report.json
outputs/mirror_feature_validation.json
outputs/replay_contrast_matrix.json
outputs/mirror_feature_stability.json
```

Replay case set:

```text
Success:
- WLDUSDT ignition_return_24h=19.1085
- SOLUSDT ignition_return_24h=6.693595

Failure:
- WLDUSDT ignition_return_24h=-10.442024
- ARBUSDT ignition_return_24h=-8.899297
```

Contrast result:

```text
Success average score_slope_4: 0.002037
Failure average score_slope_4: -0.0098
Success average RSI persistence: 4.0
Failure average RSI persistence: 6.5
Success average volume delay after score: 0.0
Failure average volume delay after score: -0.5
```

Candidate validation:

```text
hellhound_score temporal line: not validated
rsi_15m temporal line: not validated
volume_ratio_ma20 temporal line: not validated
```

Evidence conclusion:

```text
The 12N candidates repeat in success cases, but also repeat in failure cases.
They are not sufficient by themselves to distinguish real accumulation from fake signals.
Mirror Pattern implementation should not start until a stronger contrast discriminator is identified.
```

### Sprint 12P Mirror Discriminator Candidate Validation

Status:

```text
Validation complete
Mirror Pattern implementation remains blocked
```

Scope:

```text
Replay expansion, statistics, stability scoring, and evidence accumulation only.
No Mirror Layer implementation, threshold change, Hellhound Score change, PROMOTE gate change, ML training, or candidate promotion.
```

Generated outputs:

```text
outputs/mirror_candidate_validation.json
outputs/mirror_candidate_statistics.json
outputs/mirror_discriminator_ranking.json
outputs/mirror_candidate_stability.json
outputs/replay_expansion_report.json
```

Replay source and coverage:

```text
Source priority: existing replay outputs first.
Used outputs/btc_replay_dataset.jsonl and outputs/mirror_contrast_dataset.json.
Binance Historical OHLCV pull: not executed.
Success replay samples: 10
Failure replay samples: 10
Asset coverage: BTC, Major Alt, Mid Cap
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
Do not promote candidates.
Do not begin Mirror Pattern Layer implementation in Sprint 12Q.
Keep all three candidates as Candidate Only and collect more contrast evidence before revalidation.
```

### Sprint 12P-A Stability Formula & Threshold Audit

Status:

```text
Audit complete
```

Scope:

```text
Formula and threshold audit only.
No threshold change, Mirror promotion, Mirror Layer implementation, ML training, Hellhound Score change, PROMOTE Gate change, Replay Dataset change, or real trading logic change.
```

Generated outputs:

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
Sprint 12P did not contain a standalone stability_threshold=0.4 pass/fail gate.
The 0.4 values are formula weights for Repeatability and Discrimination.
The actual Verified rule is stability_score >= 0.6, repeatability >= 0.6, and discrimination >= 0.25.
Those values are not statistically validated and were not derived from ROC, distribution, percentile, Bayesian, or holdout analysis.
```

Evidence-based Threshold design:

```text
Future threshold derivation should use fixed Replay Dataset evidence and predeclared selection rules.
Candidate approaches: ROC, distribution separation, percentile gate, Bayesian decision boundary.
```

Next Sprint:

```text
Derive an evidence-based threshold before any Mirror candidate promotion.
Do not implement Mirror Pattern Layer from the current 12P candidates.
```

### Sprint 12Q Evidence-based Threshold Discovery

Status:

```text
Evidence threshold discovery complete
Mirror Feature Layer remains blocked
```

Scope:

```text
Replay Dataset threshold discovery only.
No Mirror Pattern Layer implementation, ML training, threshold hardcoding, Hellhound formula change, gate change, Replay Dataset mutation, or real trading logic change.
```

Generated outputs:

```text
outputs/evidence_threshold_candidates.json
outputs/candidate_distribution_report.json
outputs/candidate_threshold_scan.json
outputs/candidate_best_threshold.json
outputs/candidate_threshold_confidence.json
```

Candidate scope:

```text
hellhound_score_slope
rsi_persistence
volume_delay
```

Discovery method:

```text
Success/Failure distributions were calculated from Replay Dataset samples.
Mean, median, std, and P10/P25/P50/P75/P90 were recorded.
Threshold candidates were generated by exhaustive ROC-style scan.
Precision, recall, F1, and balanced accuracy were calculated for each threshold.
Best threshold selection uses balanced accuracy first, then F1, then precision.
```

Evidence thresholds:

```text
hellhound_score_slope: threshold=0.017537, direction=success_lower, precision=0.555556, recall=1.0, F1=0.714286, balanced_accuracy=0.6
rsi_persistence: threshold=6.5, direction=success_higher, precision=1.0, recall=0.2, F1=0.333333, balanced_accuracy=0.6
volume_delay: threshold=0.5, direction=success_higher, precision=0.666667, recall=0.4, F1=0.5, balanced_accuracy=0.6
```

Final verdict:

```text
hellhound_score_slope: NOT_ENOUGH_EVIDENCE
rsi_persistence: NOT_ENOUGH_EVIDENCE
volume_delay: NOT_ENOUGH_EVIDENCE
```

Temporary threshold comparison:

```text
hellhound_score_slope: threshold_difference=0.017175, precision_change=-0.044444, recall_change=0.4, f1_change=0.114286, balanced_accuracy_change=0.0
rsi_persistence: threshold_difference=2.0, precision_change=0.5, recall_change=-0.3, f1_change=-0.166667, balanced_accuracy_change=0.1
volume_delay: threshold_difference=1.0, precision_change=0.166667, recall_change=-0.1, f1_change=0.0, balanced_accuracy_change=0.1
```

Next Sprint:

```text
Do not begin 12R Mirror Feature Layer yet.
The first data-generated thresholds exist, but current evidence is not sufficient for Mirror design.
Expand replay evidence or predeclare a larger threshold derivation dataset before 12R.
```

### Sprint 12R Campaign Replay Dataset Construction

Status:

```text
Campaign Dataset construction complete
```

Scope:

```text
Campaign-level Replay Dataset construction only.
No Mirror Pattern Layer implementation, ML training, threshold change, Hellhound Score calculation change, gate change, Replay Dataset mutation, or new Candidate Feature.
```

Generated outputs:

```text
outputs/campaign_replay_dataset.json
outputs/campaign_summary_report.json
outputs/campaign_statistics.json
outputs/campaign_feature_timeline.json
outputs/campaign_duration_distribution.json
outputs/campaign_candidate_matrix.json
```

Campaign definition:

```text
Campaign is a structural event, not a single signal.
Minimum flow: Pre-Accumulation -> Accumulation -> Ignition -> Expansion -> Distribution or Failure.
Each Campaign stores start_time, end_time, duration, replay timestamps, outcome, feature timeline, and campaign metrics.
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
Campaign count: 20
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
Success mean campaign_duration_hours: 20.8
Failure mean campaign_duration_hours: 21.45
```

Feature timeline:

```text
Stored features: hellhound_score, rsi_15m, volume_ratio_ma20.
Stored candidate metrics: score_slope, rsi_persistence, volume_delay, early_mae, peak_mfe, campaign_duration, ignition_delay.
No new feature was added.
```

Next Sprint:

```text
Use Campaign Dataset as evidence foundation.
Do not add Mirror judgment logic until Campaign-level evidence is reviewed.
```

### Sprint 12S Early MAE Discriminator Evidence

Status:

```text
Campaign Physics evidence complete
```

Scope:

```text
Campaign Physics validation only.
No Mirror Pattern implementation, ML training, threshold change, gate change, score calculation change, Replay mutation, or Production code change.
```

Generated outputs:

```text
hell_engines/Hellhound/early_mae_discriminator.py
hell_engines/Hellhound/test_early_mae_discriminator.py
outputs/early_mae_discriminator.json
outputs/early_mae_statistics.json
outputs/early_mae_candidate_report.json
outputs/early_mae_confidence.json
outputs/campaign_physics_summary.json
```

Sample requirement:

```text
Success Campaign: 10
Failure Campaign: 10
INCONCLUSIVE: excluded
Binance Historical Pull: forbidden and not executed
```

Verified:

```text
early_mae: repeatability=1.0, separation_score=3.000014, candidate_score=1.0
recovery_ratio: repeatability=0.9, separation_score=1.610528, candidate_score=0.852632
```

Not Verified:

```text
initial_drawdown_velocity: NOT_ENOUGH_EVIDENCE
campaign_duration: NOT_ENOUGH_EVIDENCE
```

Candidate Ranking:

```text
1. early_mae
2. recovery_ratio
3. initial_drawdown_velocity
4. campaign_duration
```

Evidence Level:

```text
VERIFIED
```

Next Sprint recommendation:

```text
Review verified Campaign Physics evidence before considering Mirror or Campaign Intelligence design.
Do not implement judgment logic from this evidence alone.
```

### Sprint 12T Campaign Physics Layer Design

Status:

```text
Campaign Physics Layer design complete
```

Scope:

```text
Design only.
No Mirror Pattern implementation, ML training, threshold change, gate change, score calculation change, Replay mutation, or Production code change.
```

Generated outputs:

```text
hell_engines/Hellhound/campaign_physics_design.py
hell_engines/Hellhound/test_campaign_physics_design.py
outputs/campaign_physics_layer.json
outputs/campaign_physics_dependencies.json
outputs/campaign_feature_flow.json
outputs/campaign_physics_design_report.json
```

Layer Diagram:

```text
Snapshot -> Lead Line -> Campaign Physics -> Mirror Pattern -> ML -> Medusa Board
```

Dependency Diagram:

```text
Snapshot -> Lead Line
Lead Line -> Campaign Physics
Campaign Physics -> Mirror Pattern
Mirror Pattern -> ML
ML -> Medusa Board
```

Campaign Physics before Mirror:

```text
Campaign Physics records measurable Campaign behavior from replayable data.
Mirror Pattern remains a future interpretation layer and depends on Campaign Physics, not the reverse.
```

Verified:

```text
early_mae
recovery_ratio
```

Not Verified:

```text
initial_drawdown_velocity
campaign_duration
```

Validation:

```text
No circular dependency: true
Replay possible: true
Real-time calculation possible: true
Independent without Mirror: true
Design status: VERIFIED
```

Next Sprint recommendation:

```text
Define the Campaign Physics to Mirror Pattern interface contract.
Do not add Mirror Pattern, ML, threshold, gate, score, replay, or production behavior.
```

### Sprint 12U Campaign Physics to Mirror Pattern Interface Contract

Status:

```text
Interface Contract design complete
```

Scope:

```text
Design and validation only.
No Mirror Pattern implementation, ML training, threshold change, gate change, score calculation change, Replay mutation, Campaign Physics calculation change, or Production code change.
```

Generated outputs:

```text
hell_engines/Hellhound/campaign_physics_contract.py
hell_engines/Hellhound/test_campaign_physics_contract.py
outputs/campaign_physics_contract.json
outputs/mirror_input_schema.json
outputs/contract_validation_rules.json
outputs/interface_contract_report.json
outputs/interface_audit_policy.json
```

Contract Schema summary:

```text
contract_version: campaign_physics_contract_v1
packet: Campaign Physics Packet
required fields: schema_version, campaign_id, signal_id, symbol, timeframe, outcome, early_mae, recovery_ratio, initial_drawdown_velocity, campaign_duration, confidence, created_at
field metadata: type, required, nullable, description, valid enum/range/pattern
```

Dependency Rule:

```text
Snapshot -> Lead Line -> Campaign Physics -> Interface Contract -> Mirror Pattern -> ML -> Medusa Board
Mirror Pattern accepts only Campaign Physics Packet.
Mirror Pattern does not directly reference Snapshot or Lead Line.
```

Validation Rule:

```text
required_field_missing: REJECT -> SKIP
type_mismatch: REJECT -> SKIP + ALERT
invalid_value: REJECT -> SKIP + WARNING
schema_version_mismatch: HOLD -> HOLD
unknown_field: WARNING -> WARNING
partial_packet: HOLD -> HOLD
valid_packet: ACCEPT
```

Error Handling Policy:

```text
Mirror does not repair rejected packets.
Mirror does not infer missing Campaign Physics values.
Only packets passing contract validation can become Mirror input.
All REJECT, HOLD, and WARNING events must emit audit logs.
```

Audit Log Rule:

```text
contract_version
campaign_id
signal_id
symbol
validation_error_code
validation_reason
action
timestamp
```

Version Policy:

```text
current_version: campaign_physics_contract_v1
unknown field: WARNING
deprecated field: WARNING during supported deprecation window, REJECT after removal
version mismatch: HOLD until compatible contract version or migration policy is available
```

Verified:

```text
Campaign Physics Contract Schema
Mirror Input Schema
Validation Rule
Error Handling Policy
Audit Log Rule
Version Policy
Dependency Rule
```

Not Verified:

```text
None
```

Next Sprint recommendation:

```text
Review whether Mirror Pattern design can consume only Campaign Physics Packets.
Do not add Mirror Pattern, ML, threshold, gate, score, replay, Campaign Physics calculation, or production behavior.
```

### Sprint 12V Mirror Input Readiness Review

Status:

```text
Mirror input readiness review complete
```

Scope:

```text
Contract validation and readiness review only.
No Mirror Pattern implementation, ML training, threshold change, gate change, score calculation change, Replay mutation, or Production code change.
```

Generated outputs:

```text
hell_engines/Hellhound/mirror_input_readiness.py
hell_engines/Hellhound/test_mirror_input_readiness.py
outputs/mirror_input_readiness_report.json
outputs/mirror_contract_validation_result.json
outputs/mirror_input_audit_simulation.json
outputs/mirror_packet_readiness_summary.json
```

Contract Validation:

```text
contract_version: campaign_physics_contract_v1
packet_count: 20
ACCEPT: 20 / 1.0
WARNING: 0 / 0.0
HOLD: 0 / 0.0
REJECT: 0 / 0.0
```

Failure Reason:

```text
required_field_missing: 0
type_mismatch: 0
invalid_value: 0
schema_version_mismatch: 0
partial_packet: 0
unknown_field: 0
major_failure_reasons: none
```

Audit Simulation:

```text
audit_event_count: 0
audit_log_generation_possible: true
```

Mirror Input Readiness:

```text
mirror_input_usable_count: 20
mirror_input_readiness_rate: 1.0
mirror_input_readiness_verdict: READY
```

Next Sprint recommendation:

```text
Review Mirror Pattern design using Campaign Physics Packet as the only input.
Do not add Mirror Pattern, ML, threshold, gate, score, replay, or production behavior yet.
```

### Sprint 12W Mirror Pattern Decision Contract

Status:

```text
Mirror Decision Contract design complete
```

Scope:

```text
Design and contract validation only.
No Mirror Pattern implementation, ML training, threshold change, gate change, score calculation change, Replay mutation, Campaign Physics calculation change, or Production code change.
```

Generated outputs:

```text
hell_engines/Hellhound/mirror_decision_contract.py
hell_engines/Hellhound/test_mirror_decision_contract.py
outputs/mirror_decision_scope.json
outputs/mirror_output_schema.json
outputs/mirror_explainability_rules.json
outputs/mirror_validation_rules.json
outputs/mirror_decision_contract_report.json
outputs/mirror_dependency_graph.json
```

Mirror Decision Enum:

```text
REAL_WHALE_BACK
FAKE_WHALE_BACK
INCONCLUSIVE
```

Decision Scope:

```text
Mirror judges Campaign authenticity, not price direction.
Input is Campaign Physics Packet only.
Allowed features: early_mae, recovery_ratio, campaign_duration, initial_drawdown_velocity, confidence
Forbidden direct inputs: Raw Candle, Snapshot, Lead Line, Raw Score
```

Mirror Output Schema:

```text
schema_version
mirror_pattern_id
campaign_id
signal_id
symbol
mirror_decision
confidence
explainability
supporting_features
validation_state
created_at
```

Explainability Rule:

```text
Reason Code required.
Free-form LLM narrative forbidden.
Reason codes must map every Mirror decision to reproducible feature evidence.
```

Validation / Error Handling:

```text
missing_decision: REJECT -> SKIP
missing_confidence: REJECT -> SKIP
invalid_enum: REJECT -> ALERT
missing_reason_code: REJECT -> SKIP
invalid_schema: REJECT -> ALERT
missing_field: REJECT -> SKIP
partial_packet: HOLD -> HOLD
unknown_field: WARNING -> WARNING
invalid_reason_code: REJECT -> SKIP
Mirror does not repair or infer rejected packets.
```

Audit Policy:

```text
contract_version
mirror_pattern_id
campaign_id
signal_id
decision
reason_code
validation_result
action
timestamp
```

Dependency Rule:

```text
Campaign Physics -> Mirror Decision -> Mirror Packet -> ML -> Medusa
Mirror does not depend on ML.
ML learns from Mirror results.
```

Verified:

```text
Mirror Decision Scope
Mirror Output Schema
Explainability Rule
Validation Rule
Error Handling Policy
Audit Policy
Dependency Rule
```

Not Verified:

```text
None
```

Next Sprint recommendation:

```text
Sprint 12X should review Mirror Pattern design against the Mirror Decision Contract.
Do not add Mirror Pattern implementation, ML, threshold, gate, score, replay, Campaign Physics calculation, or production behavior yet.
```

### Sprint 12X Mirror Engine Architecture Blueprint

Status:

```text
Mirror Engine Blueprint complete
```

Scope:

```text
Architecture blueprint only.
No Mirror Pattern implementation, ML training, threshold generation/change, gate change, score change, Replay mutation, Campaign Physics change, or Production change.
```

Generated outputs:

```text
hell_engines/Hellhound/mirror_engine_blueprint.py
hell_engines/Hellhound/test_mirror_engine_blueprint.py
outputs/mirror_engine_pipeline.json
outputs/mirror_component_definition.json
outputs/mirror_state_machine.json
outputs/mirror_evidence_lifecycle.json
outputs/mirror_confidence_lifecycle.json
outputs/mirror_failure_flow.json
outputs/mirror_extension_points.json
outputs/mirror_engine_blueprint_report.json
```

Semantic Layer Definition:

```text
Mirror is not a price prediction engine.
Mirror is the Semantic Interpretation Layer that converts Campaign Physics Evidence into Meaning.
```

Engine Pipeline:

```text
Campaign Physics Packet
-> Packet Validation
-> Evidence Builder
-> Evidence Normalizer
-> Pattern Matcher
-> Decision Builder
-> Explainability Builder
-> Mirror Pattern Packet
```

Component Definition:

```text
Packet Validator
Evidence Builder
Evidence Normalizer
Pattern Matcher
Decision Builder
Confidence Manager
Explainability Builder
Packet Serializer
```

State Machine:

```text
IDLE
WAIT_PACKET
VALIDATING
BUILDING_EVIDENCE
NORMALIZING
MATCHING
BUILDING_DECISION
BUILDING_EXPLAINABILITY
PACKET_READY
REJECTED
HOLD
```

Evidence / Confidence Lifecycle:

```text
Evidence: Packet -> Evidence -> Normalized Evidence -> Matched Pattern -> Decision -> Reason Code -> Mirror Packet
Explainability: Reason Code -> Audit Log -> ML -> Medusa
Confidence: created by Confidence Manager, modified only by Confidence Manager and Decision Builder, frozen by Packet Serializer.
No confidence formula defined.
```

Failure Flow:

```text
Packet Error: REJECT -> SKIP
Validation Fail: REJECT -> SKIP + ALERT
Evidence Missing: HOLD -> HOLD
Unsupported Version: HOLD -> HOLD + ALERT
Unknown Feature: WARNING -> WARNING
Reason Code Failure: REJECT -> SKIP
```

Extension Point:

```text
Feature Registry
Reason Registry
Evidence Registry
```

Dependency Rule:

```text
Mirror input: Campaign Physics Packet only
Forbidden direct access: Snapshot, Lead Line, Raw Candle, ML, Medusa, Production
```

Verified:

```text
Engine Pipeline
Component Definition
State Machine
Evidence Lifecycle
Confidence Lifecycle
Explainability Lifecycle
Failure Flow
Extension Point
Semantic Layer Definition
Dependency Rule
```

Not Verified:

```text
None
```

Next Sprint recommendation:

```text
Sprint 12Y should define registry contracts before implementation.
Do not add Mirror Pattern implementation, ML, threshold, gate, score, replay, Campaign Physics calculation, or production behavior yet.
```

### Sprint 12Y Mirror Reasoning Registry Contract

Status:

```text
Mirror Reasoning Registry Contract complete
```

Scope:

```text
Registry contract only.
No Mirror Pattern implementation, ML training, threshold generation/change, gate change, score change, Replay mutation, Campaign Physics change, or Production change.
```

Generated outputs:

```text
hell_engines/Hellhound/mirror_reasoning_registry.py
hell_engines/Hellhound/test_mirror_reasoning_registry.py
outputs/mirror_feature_registry.json
outputs/mirror_evidence_registry.json
outputs/mirror_reason_registry.json
outputs/mirror_registry_dependency.json
outputs/mirror_registry_validation.json
outputs/mirror_registry_lifecycle.json
outputs/mirror_reasoning_principle.json
outputs/mirror_reasoning_registry_report.json
```

Mirror Reasoning Principle:

```text
Mirror does not make decisions directly from Features.
Mirror transforms Features into Evidence, Evidence into Reasons, and Reasons into Decisions.
Meaning always precedes Decision.
```

Feature Registry:

```text
early_mae
recovery_ratio
campaign_duration
initial_drawdown_velocity
confidence
```

Evidence Registry:

```text
EARLY_MAE_HEALTHY
EARLY_MAE_EXCESSIVE
RECOVERY_STRONG
RECOVERY_WEAK
CAMPAIGN_SHORT
CAMPAIGN_LONG
LOW_CONFIDENCE
INSUFFICIENT_EVIDENCE
```

Reason Registry:

```text
EARLY_MAE_SUPPORT
RECOVERY_SUPPORT
EARLY_MAE_RISK
RECOVERY_FAILURE
INSUFFICIENT_EVIDENCE
CONFLICTING_EVIDENCE
```

Registry Dependency:

```text
Feature -> Evidence -> Reason -> Mirror Decision
Reverse reference: forbidden
Reason direct Feature reference: forbidden
Feature -> Decision shortcut: forbidden
```

Validation / Lifecycle:

```text
statuses: ACTIVE, DEPRECATED, RESERVED, REMOVED
validation rules: duplicate_feature, duplicate_reason, missing_evidence, invalid_reference, deprecated_usage, unknown_registry_item
validation_passed: true
```

Registry Audit:

```text
registry_type
registry_id
version
status
changed_at
change_reason
```

Extension Policy:

```text
Future Mirror features must be added by registry entries without changing engine pipeline stages.
New features must enter through Campaign Physics Packet and registry metadata.
```

Verified:

```text
Feature Registry
Evidence Registry
Reason Registry
Registry Dependency
Registry Lifecycle
Registry Validation
Registry Audit
Extension Policy
Semantic Consistency Rule
Reasoning Principle
```

Not Verified:

```text
None
```

Next Sprint recommendation:

```text
Sprint 12Z should validate registry-driven Mirror design before any implementation.
Do not add Mirror Pattern implementation, ML, threshold, gate, score, replay, Campaign Physics calculation, or production behavior yet.
```

### Sprint 12Z Hellhound Mirror v1 Readiness Audit

Status:

```text
Mirror v1 readiness audit complete
```

Scope:

```text
Readiness audit only.
No Mirror Pattern implementation, ML training, threshold/gate/score/replay/Campaign Physics/Production change.
```

Generated outputs:

```text
hell_engines/Hellhound/mirror_v1_readiness_audit.py
hell_engines/Hellhound/test_mirror_v1_readiness_audit.py
outputs/mirror_v1_readiness_report.json
outputs/mirror_contract_compatibility.json
outputs/mirror_registry_chain_audit.json
outputs/mirror_reason_coverage_report.json
outputs/mirror_validation_flow_audit.json
outputs/mirror_implementation_readiness.json
```

Verified:

```text
Contract Compatibility: PASS
Reason Coverage: PASS
Dependency Rule: PASS
Semantic Rule: PASS
Pipeline Compatibility: PASS
```

Not Verified:

```text
Registry Chain: FAIL
Validation Flow: FAIL
Implementation Readiness: FAIL
```

Readiness Verdict:

```text
PARTIAL
```

Blocking Issues:

```text
registry_chain_pass:
  initial_drawdown_velocity is registered as a Feature but has no Evidence mapping.

validation_flow_pass:
  Mirror Validation Rules do not explicitly define an ACCEPT verdict path.
```

Compatibility Result:

```text
Campaign Physics Packet -> Mirror Input Schema: PASS
Mirror Decision Contract -> Mirror Output Schema: PASS
```

Registry Chain Result:

```text
Feature -> Evidence -> Reason -> Mirror Decision: PARTIAL
Reason direct Feature reference: forbidden and preserved
Feature -> Decision shortcut: forbidden and preserved
```

Reason Coverage Result:

```text
REAL_WHALE_BACK: covered
FAKE_WHALE_BACK: covered
INCONCLUSIVE: covered
```

Validation Flow Result:

```text
REJECT: covered
HOLD: covered
WARNING: covered
ACCEPT: missing explicit rule
```

Next Sprint recommendation:

```text
Do not start Sprint 12AA implementation yet.
Resolve Blocking Issues first: add registry Evidence mapping for initial_drawdown_velocity or mark it RESERVED, and define explicit ACCEPT validation flow.
```

### Sprint 12Z-A Mirror Readiness Blocking Fix

Status:

```text
Mirror v1 readiness blocking fix complete
```

Scope:

```text
Blocking fix only.
No Mirror Pattern implementation, ML training, threshold/gate/score/replay/Campaign Physics/Production change.
```

Modified files:

```text
hell_engines/Hellhound/mirror_reasoning_registry.py
hell_engines/Hellhound/mirror_decision_contract.py
hell_engines/Hellhound/mirror_v1_readiness_audit.py
hell_engines/Hellhound/test_mirror_reasoning_registry.py
hell_engines/Hellhound/test_mirror_decision_contract.py
```

Registry Change:

```text
initial_drawdown_velocity: RESERVED
Reason Chain: excluded until replay evidence supports official Evidence mapping
```

Validation Rule Change:

```text
valid_packet -> ACCEPT -> PASS
```

Readiness Audit Result:

```text
Contract Compatibility: PASS
Registry Chain: PASS
Reason Coverage: PASS
Validation Flow: PASS
Implementation Readiness: PASS
Blocking Issues: 0
Readiness Verdict: READY
```

Next Sprint recommendation:

```text
Sprint 12AA can proceed as Mirror Pattern Engine v1 Offline implementation.
Keep ML, threshold/gate/score/replay/Campaign Physics/Production changes out of scope unless separately approved.
```

### Sprint 12AA Mirror Pattern Engine v1 Offline

Status:

```text
Mirror Pattern Engine v1 offline implementation complete
```

Scope:

```text
Offline Replay only.
No ML training, threshold/gate/score/replay logic/Campaign Physics/Production change, or realtime Hellhound Shadow connection.
```

Generated files:

```text
hell_engines/Hellhound/mirror_pattern_engine.py
hell_engines/Hellhound/test_mirror_pattern_engine.py
outputs/mirror_pattern_packets.jsonl
outputs/mirror_engine_report.json
outputs/mirror_decision_distribution.json
outputs/mirror_reason_statistics.json
outputs/mirror_confidence_distribution.json
```

Mirror Engine Pipeline:

```text
Campaign Physics Packet
-> Packet Validation
-> Evidence Builder
-> Evidence Normalizer
-> Pattern Matcher
-> Decision Builder
-> Confidence Manager
-> Explainability Builder
-> Packet Serializer
-> Mirror Pattern Packet
```

Offline Replay Result:

```text
Mirror Pattern Packets: 20
Contract Validation: PASS
Registry Validation: PASS
Mirror Packet Validation: PASS
```

Decision Distribution:

```text
REAL_WHALE_BACK: 10
FAKE_WHALE_BACK: 10
INCONCLUSIVE: 0
```

Reason Code Distribution:

```text
RECOVERY_SUPPORT: 10
RECOVERY_FAILURE: 10
CONFLICTING_EVIDENCE: 10
```

Confidence Distribution:

```text
min: 0.9
max: 0.95
mean: 0.925
```

Temporary Engineering Confidence:

```text
Confidence is temporary engineering confidence.
It is not statistically validated.
It is generated by Confidence Manager and frozen by Packet Serializer.
```

Next Sprint recommendation:

```text
Sprint 12AB can proceed as Mirror Shadow Integration design/review.
Do not connect live execution or production behavior without separate approval.
```

### Sprint 12AB Mirror Decision Calibration

Status:

```text
Mirror Decision Calibration audit complete
```

Scope:

```text
Audit only.
No Mirror Engine logic change, Decision Rule change, Registry change, Threshold/Gate/Score/Replay/Campaign Physics/Production change, Shadow Integration, or ML training.
```

Generated files:

```text
hell_engines/Hellhound/mirror_decision_calibration.py
hell_engines/Hellhound/test_mirror_decision_calibration.py
outputs/mirror_decision_calibration.json
outputs/mirror_decision_stability.json
outputs/mirror_conflict_analysis.json
outputs/mirror_evidence_sufficiency.json
outputs/mirror_confidence_calibration.json
outputs/mirror_inconclusive_analysis.json
outputs/mirror_decision_calibration_report.json
```

Decision Distribution:

```text
REAL_WHALE_BACK: 10
FAKE_WHALE_BACK: 10
INCONCLUSIVE: 0
```

Conflict Analysis:

```text
conflict_count: 10
inconclusive_candidate_count: 10
example conflict: RECOVERY_FAILURE + CONFLICTING_EVIDENCE
```

Evidence Sufficiency:

```text
packet_count: 20
sufficient_count: 10
issue_counts:
  reason_conflict: 10
```

Confidence Calibration:

```text
CONSISTENT: 10
OVERCONFIDENT_CONFLICT: 10
confidence_modified: false
```

INCONCLUSIVE Analysis:

```text
INCONCLUSIVE count: 0
rule_gap: true
conflict_handling_gap: true
evidence_gap: false
registry_gap: false
```

Decision Stability:

```text
deterministic: true
mismatch_count: 0
```

Calibration Verdict:

```text
CALIBRATION_NEEDED
```

Next Sprint recommendation:

```text
Sprint 12AC should be Mirror Decision Refinement, not Shadow Integration.
Define how conflict candidates become INCONCLUSIVE before live/shadow attachment.
```

### Sprint 12AC Mirror Decision Refinement

Status:

```text
Mirror Decision Refinement complete
```

Scope:

```text
Conflict Resolver added between Pattern Matcher and Decision Builder.
No Registry, Feature, Evidence, Campaign Physics, Replay, Threshold/Gate/Score, Production, Shadow, or ML change.
```

Modified files:

```text
hell_engines/Hellhound/mirror_pattern_engine.py
hell_engines/Hellhound/test_mirror_pattern_engine.py
```

Generated files:

```text
hell_engines/Hellhound/mirror_decision_refinement.py
hell_engines/Hellhound/test_mirror_decision_refinement.py
outputs/mirror_conflict_resolution_report.json
outputs/mirror_inconclusive_statistics.json
outputs/mirror_decision_refinement_report.json
outputs/mirror_pattern_packets.jsonl
outputs/mirror_decision_distribution.json
outputs/mirror_reason_statistics.json
outputs/mirror_confidence_distribution.json
```

Decision Distribution:

```text
Before: REAL_WHALE_BACK 10, FAKE_WHALE_BACK 10, INCONCLUSIVE 0
After: REAL_WHALE_BACK 10, FAKE_WHALE_BACK 0, INCONCLUSIVE 10
```

Conflict Resolution:

```text
conflict_candidates: 10
conflict_to_inconclusive: 10
```

Confidence:

```text
overconfident_conflict_before: 10
overconfident_conflict_after: 0
conflict confidence: 0.35 Temporary Engineering Confidence
```

Validation:

```text
Contract Validation: PASS
Registry Validation: PASS
Replay Validation: PASS
Mirror Packet Validation: PASS
JSON Validation: PASS
```

Next Sprint recommendation:

```text
Sprint 12AD can proceed as Mirror Shadow Integration in Offline Shadow Mode.
Live execution and production behavior remain out of scope unless separately approved.
```
* Layer:
  - Snapshot Layer: T-2, T-1, T0 state vector.
  - Diff Layer: Diff_A, Diff_B.
  - Delta Layer: Diff_B - Diff_A.
  - Outcome Layer: 6h/24h/72h MFE, MAE, Time To Peak field fill.
* 출력:
  - `outputs/hellhound_wave_log.jsonl`
* 금지 준수:
  - Entry/Exit 로직 수정 없음.
  - Signal Scoring 수정 없음.
  - Hound Position 구조 수정 없음.
  - Wave Feature를 판단 로직에 반영하지 않음.
  - DB update 없음.
  - `is_trade_command=false`.

### Sprint 12AD Mirror Shadow Integration Offline Shadow Mode
* 상태:
  - 완료.
  - Mirror Pattern Engine v1을 Hellhound Shadow 관측 경계에 연결했다.
  - 실시간 거래가 아니라 Offline Shadow Mode 관측 및 기록만 수행한다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_shadow_adapter.py`
  - `hell_engines/Hellhound/test_mirror_shadow_adapter.py`
  - `outputs/mirror_shadow_log.jsonl`
  - `outputs/mirror_shadow_statistics.json`
  - `outputs/mirror_shadow_processing_time.json`
  - `outputs/mirror_shadow_integration_report.json`
* Shadow Pipeline:
  - Hellhound Shadow
  - Campaign Physics Packet
  - Mirror Engine
  - Mirror Pattern Packet
  - Shadow Log
  - Replay Storage
  - Optional Telegram Info Only
* 입력 경계:
  - 허용: Campaign Physics Packet.
  - 금지: Snapshot, Lead Line, Raw Candle, Raw Score, ML, Medusa 직접 입력.
* Shadow 결과:
  - packet_count: 20
  - REAL_WHALE_BACK: 10
  - FAKE_WHALE_BACK: 0
  - INCONCLUSIVE: 10
  - average_confidence: 0.625
  - average_processing_time_ms: 0.010537
  - shadow_log_created: true
* 검증:
  - Contract Validation: PASS
  - Mirror Packet Validation: PASS
  - JSON Validation: PASS
  - Replay Storage Compatible: true
  - Telegram Default: OFF
  - `is_trade_command=false`
* 금지 준수:
  - Production 거래 없음.
  - 주문 생성 없음.
  - Position 생성/종료 없음.
  - ML 학습 없음.
  - Threshold/Gate/Score/Replay Logic/Campaign Physics/Medusa 변경 없음.
* 다음 Sprint:
  - 12AE Mirror Live Evidence Accumulation.
  - Mirror는 별도 승격 전까지 시장 행동에 영향을 주지 않는 Shadow Observer로 유지한다.

### Sprint 12AE Mirror Live Evidence Accumulation
* 상태:
  - 완료.
  - Mirror Shadow Log JSONL 누적분을 Live Evidence로 분석했다.
  - DB 생성 및 Supabase 연결 없이 JSONL 기반 산출물만 생성했다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_live_evidence_accumulator.py`
  - `hell_engines/Hellhound/test_mirror_live_evidence_accumulator.py`
  - `outputs/mirror_live_evidence_report.json`
  - `outputs/mirror_live_decision_distribution.json`
  - `outputs/mirror_live_reason_distribution.json`
  - `outputs/mirror_live_schema_stability.json`
  - `outputs/mirror_live_replay_compatibility.json`
  - `outputs/mirror_live_processing_stats.json`
* 입력:
  - `outputs/mirror_shadow_log.jsonl`
* Evidence Summary:
  - packet_count: 20
  - REAL_WHALE_BACK: 10
  - FAKE_WHALE_BACK: 0
  - INCONCLUSIVE: 10
  - INCONCLUSIVE_rate: 0.5
  - INCONCLUSIVE_drift_level: WATCH
  - average_confidence: 0.625
* Reason Code Distribution:
  - RECOVERY_SUPPORT: 10
  - RECOVERY_FAILURE: 10
  - CONFLICTING_EVIDENCE: 10
* Processing Stats:
  - average_ms: 0.010537
  - p90_ms: 0.011321
  - max_ms: 0.021917
* 검증:
  - Schema Stability: PASS
  - Replay Compatibility: PASS
  - JSON Validation: PASS
  - DB Created: false
  - Supabase Connected: false
  - Rule Change Performed: false
  - `is_trade_command=false`
* 금지 준수:
  - DB 생성 없음.
  - Supabase 연결 없음.
  - Production 거래/주문/Position 생성 또는 종료 없음.
  - ML 학습 없음.
  - Threshold/Gate/Score/Replay Logic/Campaign Physics/Medusa 변경 없음.
* 다음 Sprint:
  - 12AF Mirror Packet Schema Freeze Review.
  - DB 작업은 Schema Freeze 이후로 유지한다.

### Sprint 12AF Mirror Packet Schema Freeze Review
* 상태:
  - 완료.
  - Mirror Packet v1 Contract를 실제 검증된 `mirror_pattern_packet_v1` 기준으로 Freeze했다.
  - DB 생성 및 Supabase 연결 없이 Contract 검증 산출물만 생성했다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_packet_contract.py`
  - `hell_engines/Hellhound/test_mirror_packet_contract.py`
  - `outputs/mirror_packet_schema_v1.json`
  - `outputs/mirror_packet_contract_report.json`
  - `outputs/mirror_packet_validation_report.json`
  - `outputs/mirror_packet_golden_samples.json`
* Frozen Contract:
  - contract_version: `mirror_pattern_packet_v1`
  - freeze_status: FROZEN
  - source: `outputs/mirror_shadow_log.jsonl` 내부 `mirror_packet`
  - packet_count: 20
* Required Fields:
  - `schema_version`
  - `mirror_pattern_id`
  - `campaign_id`
  - `signal_id`
  - `symbol`
  - `mirror_decision`
  - `confidence`
  - `reason_code`
  - `supporting_features`
  - `validation_state`
  - `created_at`
  - `is_trade_command`
* Nested Object:
  - `supporting_features`
  - `supporting_features.conflict_resolution`
* Enum:
  - mirror_decision: REAL_WHALE_BACK, FAKE_WHALE_BACK, INCONCLUSIVE
  - validation_state: ACCEPT, WARNING, HOLD, REJECT
  - conflict_resolution.policy: DECIDE, INCONCLUSIVE
* Freeze Policy:
  - Required Field 제거 금지.
  - Required -> Optional 변경 금지.
  - Optional -> Required 변경 금지.
  - Enum 의미 변경 금지.
  - 기존 Field 의미 변경 금지.
  - 향후 확장은 Optional v1 Field 추가 또는 `mirror_pattern_packet_v2`로만 허용.
* Golden Sample:
  - REAL_WHALE_BACK: 실제 검증 패킷 존재.
  - INCONCLUSIVE: 실제 검증 패킷 존재.
  - FAKE_WHALE_BACK: 현재 소스에 없어 `absent_in_source`로 기록. 합성 금지.
* 검증:
  - Contract Validation: PASS
  - Schema Stability: PASS
  - Replay Compatibility: PASS
  - JSON Validation: PASS
  - Existing Packet Compatibility: PASS
  - Golden Sample Validation: PASS
* 금지 준수:
  - Production/Trading/Position/Order 변경 없음.
  - Replay Logic/Campaign Physics/Lead Line 변경 없음.
  - Mirror Registry Logic/Mirror Decision Logic/Threshold/Gate/Score 변경 없음.
  - ML 학습 없음.
  - DB 생성 없음.
  - Supabase 연결 없음.
  - Medusa 변경 없음.
* 다음 단계:
  - DB, Supabase, Dashboard, ML, Replay 확장, Production은 모두 `mirror_pattern_packet_v1` Frozen Contract 기준으로만 진행한다.

### Sprint 12AG Mirror Replay Harness
* 상태:
  - 완료.
  - Frozen Contract `mirror_pattern_packet_v1` 기준 Replay Harness를 구축했다.
  - Packet을 수정하지 않고 순차 Replay, Contract Validation, Summary, Error Collection을 수행한다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_replay_harness.py`
  - `hell_engines/Hellhound/test_mirror_replay_harness.py`
  - `outputs/mirror_replay_report.json`
  - `outputs/mirror_replay_statistics.json`
  - `outputs/mirror_replay_determinism.json`
* Replay Source:
  - Frozen Contract: `mirror_pattern_packet_v1`
  - Packet source: `outputs/mirror_shadow_log.jsonl` 내부 `mirror_packet`
  - Golden Sample source: `outputs/mirror_packet_golden_samples.json`
* Replay Summary:
  - Replay Harness: PASS
  - packet_count: 20
  - replay_count: 20
  - success_count: 20
  - failure_count: 0
  - contract_validation_count: 20
  - average_processing_time_ms: 0.018946
  - max_processing_time_ms: 0.107541
* Sequence Validation:
  - Packet order preserved: true
  - Timestamp order preserved: true
  - Decision preserved: true
  - Reason Code preserved: true
  - Confidence preserved: true
  - Validation State preserved: true
  - Packet mutation: false
* Golden Sample Replay:
  - REAL_WHALE_BACK: PASS
  - INCONCLUSIVE: PASS
  - FAKE_WHALE_BACK: SKIPPED (absent in source)
  - Synthetic samples created: false
* Long Replay Determinism:
  - 10 replay runs: PASS
  - 100 replay runs: PASS
  - total repeated packets: 2200
  - mismatch_count: 0
* 검증:
  - Replay Harness: PASS
  - Contract Validation: PASS
  - Replay Compatibility: PASS
  - Golden Sample Replay: PASS
  - Replay Determinism: PASS
* 금지 준수:
  - Mirror Packet Contract 변경 없음.
  - Replay Decision Logic 변경 없음.
  - Production/Trading/Position/Order 변경 없음.
  - Campaign Physics/Lead Line 변경 없음.
  - Mirror Registry Logic/Mirror Decision Logic/Threshold/Gate/Score 변경 없음.
  - ML 학습 없음.
  - DB 생성 없음.
  - Supabase 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AH Mirror Packet Persistence Adapter
* 상태:
  - 완료.
  - `mirror_pattern_packet_v1` Frozen Contract를 변경하지 않고 Persistence Adapter를 구축했다.
  - 현재 저장 구현은 append-only JSONL 파일만 사용한다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_persistence_adapter.py`
  - `hell_engines/Hellhound/test_mirror_persistence_adapter.py`
  - `outputs/mirror_persistence_packets.jsonl`
  - `outputs/mirror_persistence_report.json`
  - `outputs/mirror_persistence_statistics.json`
* Persistence 구조:
  - Packet 저장 요청 수신.
  - Contract Validation.
  - Required Field / JSON Validation.
  - Duplicate Packet Detection.
  - Append-only JSONL 저장.
  - 저장 결과 반환.
  - Persistence 후 Replay Compatibility 확인.
* Storage Policy:
  - 허용: JSONL, JSON Report.
  - 금지: Database, SQLite, PostgreSQL, Supabase.
  - 기존 Packet 수정/삭제 금지.
* Persistence Summary:
  - Persistence Adapter: PASS
  - save_count: 20
  - success_count: 20
  - reject_count: 0
  - duplicate_count: 0
  - average_save_time_ms: 0.761008
  - max_save_time_ms: 1.853708
  - packet_mutation_count: 0
* 검증:
  - Contract Validation: PASS
  - JSON Validation: PASS
  - Replay Compatibility: PASS
  - Duplicate Detection: PASS
  - Invalid Packet Detection: PASS
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - Replay Logic/Mirror Decision Logic/Registry 변경 없음.
  - Campaign Physics/Lead Line 변경 없음.
  - Threshold/Gate/Score 변경 없음.
  - ML 학습 없음.
  - Production/Trading/Position/Order 변경 없음.
  - DB/SQLite/PostgreSQL/Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.
* 향후 확장 원칙:
  - JSONL, Supabase, PostgreSQL 등 모든 저장소는 같은 Persistence Adapter boundary를 구현하는 방식으로만 확장한다.

### Sprint 12AW Mirror ML Baseline Trainer
* 상태:
  - 완료. LAB Phase 마지막 Sprint.
  - Train → Save → Load → Predict → Report 파이프라인 재현 가능성 검증 완료.
  - JSON First. pickle/joblib 금지 준수.
* JSON Model Artifact:
  - model_type = LogisticRegression
  - coef_: list / intercept_: list / classes_: [0,1] / n_features_in_: 5
  - random_seed = 42 / pickle_used = false / joblib_used = false
  - 저장 경로: outputs/mirror_ml_baseline_model.json
* Save/Load Validation: PASS — JSON 직렬화 후 완전 동일 Prediction 재현 / mismatch_count = 0
* Evaluation (REFERENCE_ONLY):
  - Validation(N=3): accuracy=1.0, f1=1.0 / confusion_matrix=[[2,0],[0,1]]
  - Test(N=3): accuracy=1.0, f1=1.0 / confusion_matrix=[[3]] (전부 NEGATIVE — 편향 예고대로)
  - N=20 기반 / 성능 수치는 운영 기준으로 사용하지 않음
* Pipeline: pipeline_result=PASS / mutation_count=0 / reference_only=true
* 테스트: Targeted 61 PASS / Full 903 PASS (기존 842 + 신규 61, 0 regression)
* 다음 단계: Shadow Adapter → 실시간 시장 데이터 축적 → Mirror ML 반복 학습

### Sprint 12AV Mirror ML Baseline Contract
* 상태:
  - 완료.
  - Mirror ML Baseline Training / Prediction / Evaluation Contract를 확립했다.
  - ML 모델 학습 없음. 모델 파일 생성 없음. Contract 계층 정의만 수행.
* Training Contract:
  - training_contract_version = mirror_ml_training_v1
  - model_type = LogisticRegression (등록만 — 학습 없음)
  - random_seed = 42
  - pipeline_stages = [Train, Save, Load, Predict, Report]
  - model_artifact = outputs/mirror_ml_baseline_model.json (12AW에서 생성 예정)
* Prediction Contract 필드: sample_id, packet_hash, prediction, probability, model_version, prediction_time
* Evaluation Contract 필드: accuracy, precision, recall, f1_score, confusion_matrix, dataset_size, reference_only
* reference_only = True / N=20 기준 / 성능 수치는 운영 기준으로 사용하지 않음
* Validation: contract_validation_result PASS / contract_layer_result PASS
* 테스트: Targeted 62 PASS / Full 842 PASS (기존 780 + 신규 62, 0 regression)

### Sprint 12AU Mirror Dataset Split Layer
* 상태:
  - 완료.
  - mirror_ml_feature_matrix_v1을 Train/Validation/Test로 분리했다.
  - ML 학습 없음. Deterministic Split (random_seed=42).
* Split Contract:
  - split_contract_version = mirror_dataset_split_v1
  - random_seed = 42
  - Count Rule: validation=floor(N×0.15), test=floor(N×0.15), train=N-val-test (나머지 → Train)
* Split 결과 (N=20): Train=14 / Validation=3 / Test=3
* Label Distribution (REFERENCE_ONLY):
  - Train: {0:5, 1:9}
  - Validation: {0:2, 1:1}
  - Test: {0:3} — 편향 발생 (지시서 예고대로)
  - N=20 기준 / 통계 불안정 / 성능 평가 참고용으로만 사용
* Validation: split PASS / leakage PASS / coverage 100% / mutation_count=0
* 테스트: Targeted 53 PASS / Full 780 PASS (기존 727 + 신규 53, 0 regression)

### Sprint 12AT Mirror ML Feature Layer
* 상태:
  - 완료.
  - ML_INPUT_APPROVED: true Dataset을 ML Feature Matrix로 변환했다.
  - ML 학습 없음. Feature Engineering 없음. 기존 Dataset Feature만 사용.
* Feature Contract:
  - feature_contract_version = mirror_ml_feature_matrix_v1
  - Feature Columns (고정 순서): early_mae, recovery_ratio, campaign_duration, confidence, decision_encoded
  - Decision Encoding: REAL_WHALE_BACK=1, INCONCLUSIVE=0, FAKE_WHALE_BACK=-1
  - Label Encoding: POSITIVE_MARKET_OUTCOME=1, NEGATIVE_MARKET_OUTCOME=0, INSUFFICIENT_CLASS_DATA=-1
* Feature Matrix: 20 rows × 5 features + 1 label / feature_validation_result: PASS / mutation_count: 0
* Mock FAKE Encoding: FAKE_WHALE_BACK decision_encoded=-1, INSUFFICIENT_CLASS_DATA label_encoded=-1 → PASS (런타임 경로 검증 완료)
* Feature Statistics (REFERENCE_ONLY):
  - Dataset Size=20 / Statistics are reference only.
  - early_mae: mean=-6.818 / recovery_ratio: mean=2.480 / campaign_duration: mean=21.125 / confidence: mean=1.000
* 테스트: Targeted 57 PASS / Full 727 PASS (기존 670 + 신규 57, 0 regression)

### Sprint 12AS Mirror Label Audit
* 상태:
  - 완료.
  - mirror_labeled_dataset.jsonl의 Label 품질을 검증하고 ML 입력 최종 감사를 완료했다.
  - Label/Policy/Dataset 수정 없음. Audit 전용.
* Audit 결과:
  - label_audit_result: PASS
  - decision_label_consistency_result: PASS
  - policy_version_audit_result: PASS (mirror_label_policy_v1)
  - label_candidate_audit_result: PASS
  - dataset_integrity_result: PASS (UTF-8 without BOM, packet_hash 보존, 순서 유지)
  - packet_hash_consistency_result: PASS (unique_hash_count=20, 복수 Decision/Label 없음)
  - original_dataset_protection_result: PASS (label_placeholder null 20/20)
  - deferred_label_audit_result: PASS (INSUFFICIENT_MARKET_DATA=0, UNRESOLVED=0)
  - Mutation Count: 0
* ML_INPUT_APPROVED: true
  - 승인 근거: Label Audit PASS / Dataset Integrity PASS / Original Dataset Protection PASS / packet_hash Consistency PASS
  - mirror_labeled_dataset.jsonl 공식 ML 입력 Dataset으로 승인
* 테스트: Targeted 47 PASS / Full 670 PASS (기존 623 + 신규 47, 0 regression)

### Sprint 12AR Mirror Label Builder
* 상태:
  - 완료.
  - mirror_label_policy_v1을 참조하여 Dataset Sample에 Label을 할당했다.
  - 새 Policy 없음. Threshold/Rule/Score/ML 없음. Apply Policy Only.
  - 원본 mirror_dataset.jsonl 변경 없음.
* Label 적용 기준:
  - mirror_label_policy_v1 decision_policy만 참조. 판단 없음.
  - REAL_WHALE_BACK → POSITIVE_MARKET_OUTCOME
  - INCONCLUSIVE    → NEGATIVE_MARKET_OUTCOME
  - FAKE_WHALE_BACK → INSUFFICIENT_CLASS_DATA (런타임 분기 + Mock 테스트 구현)
  - INSUFFICIENT_MARKET_DATA / UNRESOLVED: 미적용 (발급 조건 미정)
* Label Assignment 결과:
  - POSITIVE_MARKET_OUTCOME: 10 / NEGATIVE_MARKET_OUTCOME: 10
  - INSUFFICIENT_CLASS_DATA: 0 (현재 FAKE_WHALE_BACK 데이터 없음)
  - null_label_count: 0
* Dataset 원본 무변형:
  - mirror_dataset.jsonl label_placeholder=null: 20/20 PASS
  - original_dataset_unchanged: true / Mutation Count: 0
* Mock FAKE_WHALE_BACK: assign → INSUFFICIENT_CLASS_DATA PASS / run full path PASS
* Validation: PASS / policy_reference_valid: true
* 테스트: Targeted 52 PASS / Full 623 PASS (기존 571 + 신규 52, 0 regression)

### Sprint 12AQ Mirror Label Policy Builder
* 상태:
  - 완료.
  - Outcome Distribution 결과를 기반으로 Label Policy Contract를 구축했다.
  - Label 생성 없음. label_placeholder JSON null 유지. Dataset Sample 변경 없음.
* Label Policy Contract:
  - policy_version = mirror_label_policy_v1
  - Required Fields: policy_version, source_distribution_files, decision_policy, class_data_status,
    required_fields, label_candidates, unresolved_policy_cases, observations, created_at
  - Label Candidates: POSITIVE_MARKET_OUTCOME, NEGATIVE_MARKET_OUTCOME, INSUFFICIENT_CLASS_DATA,
    INSUFFICIENT_MARKET_DATA (발급 조건 미정), UNRESOLVED
* Decision별 Policy Draft:
  - REAL_WHALE_BACK: class_data_status=AVAILABLE, candidate=POSITIVE_MARKET_OUTCOME, pos_ratio=1.0
  - INCONCLUSIVE:    class_data_status=AVAILABLE, candidate=NEGATIVE_MARKET_OUTCOME, pos_ratio=0.0
  - FAKE_WHALE_BACK: class_data_status=INSUFFICIENT_CLASS_DATA, candidate=INSUFFICIENT_CLASS_DATA
* unresolved_policy_cases (5):
  - INSUFFICIENT_MARKET_DATA 발급 조건 정의 예정
  - completed=false Sample 처리 여부
  - Replay 부족 처리 여부
  - Live Outcome 부족 처리 여부
  - Market Observation 부족 처리 여부
* Observations:
  - 현재 결과는 Sample 10개 기반. Distribution만을 반영한 관찰 결과.
  - 향후 Dataset 증가 시 Policy 변경 가능성 있음.
  - observed_positive_ratio=0.0을 영구 Rule로 해석하지 않음.
* Policy Validation: PASS / label_placeholder 전 샘플 null 유지 / Mutation Count = 0
* 테스트: Targeted 55 PASS / Full 571 PASS (기존 516 + 신규 55, 0 regression)

### Sprint 12AP Mirror Outcome Distribution Analyzer
* 상태:
  - 완료.
  - Market Outcome 결과를 Decision별로 집계하여 Label Policy 설계에 필요한 분포 데이터를 생성했다.
  - Label 생성 없음. Threshold 없음. Rule 없음. Score 없음. 분포 측정 및 기록 계층만 구현.
* window_duration 기준:
  - window_duration = campaign_duration (Outcome Window Evaluator의 값을 그대로 사용)
  - window_end - window_start 재계산 없음. 임의의 시간 기준 없음.
  - time_to_peak / time_to_trough가 null이어도 window_duration 집계 정상 수행.
* Decision별 Distribution 결과:
  - REAL_WHALE_BACK  10 samples: MFE mean=8.53%, Return PCT mean=+8.53%, Positive Return=10/10
  - INCONCLUSIVE     10 samples: MFE mean=0.00%, Return PCT mean=-5.06%, Negative Return=10/10
  - FAKE_WHALE_BACK   0 samples: 데이터 없음, 전 통계 항목 null
  - Overall          20 samples: MFE mean=4.26%, Return PCT mean=+1.73%, Pos=10 Neg=10
* Extreme Cases:
  - max_mfe:         22.824677  (REAL_WHALE_BACK)
  - max_mae:         16.811404  (INCONCLUSIVE)
  - max_return:     +22.824677  (REAL_WHALE_BACK)
  - min_return:     -11.849300  (INCONCLUSIVE)
  - max_window:      24.0 h     (INCONCLUSIVE)
  - min_window:      14.75 h    (INCONCLUSIVE)
* completed / incomplete:
  - completed_count=20, incomplete_count=0, incomplete_ratio=0.0
  - 경고 없음
* Distribution Validation: PASS (Mean in range, non-negative MFE/MAE, count consistency)
* Mutation Count: 0
* Label Placeholder: 전 샘플 null 유지
* 테스트: Targeted 67 PASS / Full 516 PASS (기존 449 + 신규 67, 0 regression)

### Sprint 12AO Mirror Outcome Window Evaluator
* 상태:
  - 완료.
  - Replay 기반 Market Outcome Window를 Dataset Sample에서 정량적으로 계산하는 계층을 구축했다.
  - 임의의 시간 기준, TP/SL, Profit Target, Strategy Logic 없음.
  - time_to_peak / time_to_trough: null (캔들 수준 데이터 미도입).
* 생성 파일:
  - `hell_engines/Hellhound/mirror_outcome_window_evaluator.py`
  - `hell_engines/Hellhound/test_mirror_outcome_window_evaluator.py`
  - `outputs/mirror_market_outcome_report.json`
  - `outputs/mirror_market_outcome_statistics.json`
  - `outputs/mirror_outcome_window_examples.json`
* Market Outcome Contract:
  - mfe = max(0, (recovery_ratio - 1) × |early_mae|)
  - mae = abs(early_mae)
  - return_pct = (recovery_ratio - 1) × |early_mae|
  - window_duration = campaign_duration (hours)
  - time_to_peak, time_to_trough = null (캔들 수준 타임스탬프 없음)
  - status: COMPLETED | INSUFFICIENT_REPLAY_DATA | NO_PACKET_MATCH
* Outcome Window 종료 조건:
  - window_start = Dataset Sample created_at
  - window_end = campaign_duration summary 기반 (Replay 요약 데이터)
    - campaign_duration은 Packet supporting_features의 요약 통계값이다.
    - 캔들 수준 종료 타임스탬프가 아니다.
    - 실제 마지막 캔들 timestamp는 Live Candle Data 도입 시 확정된다.
  - 임의의 시간 기준 없음
* 계산 결과 (20 samples):
  - Window Validation Result: PASS
  - Completed Count: 20 / 20
  - MFE Mean: 4.262695 %
  - MAE Mean: 6.817699 %
  - Return PCT Mean: 1.734369 %
  - Window Duration Mean: 21.125 h
* 테스트:
  - Targeted Test: 47 PASS
  - Full Test: 449 PASS (기존 402 + 신규 47)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - `mirror_dataset_v1` Contract 변경 없음.
  - Replay Logic / Mirror Decision Logic / Registry 변경 없음.
  - Campaign Physics / Lead Line / Threshold / Gate / Score 변경 없음.
  - 임의의 시간 기준 (1h/4h/24h/N봉) 사용 없음.
  - TP / SL / Profit Target / Rule 기반 종료 조건 없음.
  - Label 생성 없음.
  - ML 알고리즘 구현 없음.
  - Feature Engineering 추가 없음.
  - Live Outcome 연결 없음.
  - Production / Trading / Position / Order 변경 없음.
  - DB / SQLite / PostgreSQL / Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AN Mirror Outcome Joiner
* 상태:
  - 완료.
  - Mirror Dataset Sample과 Replay Outcome을 Packet Hash 기반으로 Join하는 계층을 구축했다.
  - live_outcome은 JSON null 고정 (Live Sprint 전까지 변경 없음).
  - label_placeholder 채우기 없음.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_outcome_joiner.py`
  - `hell_engines/Hellhound/test_mirror_outcome_joiner.py`
  - `outputs/mirror_outcome_join_report.json`
  - `outputs/mirror_outcome_mapping.json`
  - `outputs/mirror_outcome_statistics.json`
* Outcome Contract:
  - `outcome_placeholder.replay_outcome.status`: VALID | MUTATED | INVALID | NO_MATCH
  - `outcome_placeholder.live_outcome`: null (JSON null 고정)
  - `label_placeholder`: null (변경 없음)
* Join 결과:
  - Join Validation Result: PASS
  - Join Result: PASS
  - Sample Count: 20
  - Matched Count: 20
  - Unmatched Count: 0
  - Mutation Count: 0
  - Live Outcome Null Count: 20
  - Label Placeholder Null Count: 20
  - Elapsed MS: 1.336875ms
* 테스트:
  - Targeted Test: 42 PASS
  - Full Test: 402 PASS (기존 360 + 신규 42)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - `mirror_dataset_v1` Contract 변경 없음.
  - Replay Logic / Mirror Decision Logic / Registry 변경 없음.
  - Campaign Physics / Lead Line / Threshold / Gate / Score 변경 없음.
  - Label 생성 없음.
  - ML 알고리즘 구현 없음.
  - Outcome 분석 없음.
  - Feature Engineering 추가 없음.
  - Production / Trading / Position / Order 변경 없음.
  - DB / SQLite / PostgreSQL / Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AM Mirror Dataset Integrity Checker
* 상태:
  - 완료.
  - mirror_dataset.jsonl 전체에 대한 무결성 검증 레이어를 구축했다.
  - 14개 검증 항목 모두 PASS.
  - Dataset 수정 없음. Auto-recovery 없음. 손상 발견 시 Fail-safe 결과만 반환.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_dataset_integrity_checker.py`
  - `hell_engines/Hellhound/test_mirror_dataset_integrity_checker.py`
  - `outputs/mirror_dataset_integrity_report.json`
  - `outputs/mirror_dataset_hash_audit.json`
  - `outputs/mirror_dataset_duplicate_report.json`
* 검증 항목 (14개):
  1. dataset_contract_version 일관성
  2. packet_hash 형식 (64 hex) 검증
  3. packet_hash 중복 여부
  4. sample_id 중복 여부
  5. Canonical JSON Round-trip Hash 일치
  6. Append-only 순서 유지
  7. created_at 시간 역전 여부
  8. outcome_placeholder = JSON null 확인
  9. label_placeholder = JSON null 확인
  10. contract_version = mirror_pattern_packet_v1 확인
  11. dataset_contract_version = mirror_dataset_v1 확인
  12. JSONL 파싱 오류 여부
  13. UTF-8 without BOM 여부
  14. 손상 Sample 발견 시 Fail-safe 결과 반환
* 검증 결과:
  - Integrity Result: PASS
  - Sample Count: 20
  - Parse Error Count: 0
  - Encoding Result: PASS (UTF-8 without BOM)
  - Contract Consistency: PASS (issue_count=0)
  - Hash Format: PASS (invalid_hash_count=0)
  - Duplicate Result: PASS (packet_hash=0, sample_id=0)
  - Canonical Roundtrip: PASS (failure_count=0)
  - Append Order: PASS (time_reversal_count=0)
  - Placeholder Integrity: PASS (issue_count=0)
* 테스트:
  - Targeted Test: 45 PASS
  - Full Test: 360 PASS (기존 315 + 신규 45)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - `mirror_dataset_v1` Contract 변경 없음.
  - Dataset 수정 없음.
  - Sample Auto-recovery 없음.
  - Mirror Decision Logic / Replay Logic / Registry 변경 없음.
  - Campaign Physics / Lead Line / Threshold / Gate / Score 변경 없음.
  - ML 알고리즘 구현 없음.
  - Outcome / Label Placeholder 채우기 없음.
  - Production / Trading / Position / Order 변경 없음.
  - DB / SQLite / PostgreSQL / Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AL Mirror Dataset Layer
* 상태:
  - 완료.
  - Mirror Foundation 결과를 ML이 직접 사용할 수 있는 Dataset Sample 형태로 정규화했다.
  - Dataset Contract (mirror_dataset_v1) 정의 완료.
  - 20개 Sample 생성, 검증 PASS.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_dataset_contract.py`
  - `hell_engines/Hellhound/mirror_dataset_builder.py`
  - `hell_engines/Hellhound/test_mirror_dataset_builder.py`
  - `outputs/mirror_dataset_sample.json`
  - `outputs/mirror_dataset_statistics.json`
  - `outputs/mirror_dataset_schema.json`
  - `outputs/mirror_dataset_validation.json`
  - `outputs/mirror_dataset.jsonl`
* Dataset Contract:
  - Dataset Contract Version: mirror_dataset_v1
  - Packet Contract Version: mirror_pattern_packet_v1 (FROZEN, 변경 없음)
* Dataset Sample 구조:
  - sample_id, contract_version, dataset_contract_version, packet_hash
  - feature: early_mae, recovery_ratio, campaign_duration, confidence
  - evidence (list), reason (list), decision
  - replay_metadata, persistence_metadata, readback_status
  - outcome_placeholder: null (JSON null 고정 — 0, "", "unknown", false 사용 금지)
  - label_placeholder: null (JSON null 고정 — 0, "", "unknown", false 사용 금지)
  - created_at, is_trade_command: false
* 검증 결과:
  - Validation Result: PASS
  - Mutation Count: 0
  - Packet Count: 20
  - Sample Count: 20
  - Hash Verified Count: 20
  - Outcome Placeholder Null Count: 20
  - Label Placeholder Null Count: 20
  - Elapsed MS: 1.5395ms
* 테스트:
  - Targeted Test: 41 PASS
  - Full Test: 315 PASS (기존 274 + 신규 41)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - Mirror Decision Logic / Replay Logic / Registry 변경 없음.
  - Campaign Physics / Lead Line / Threshold / Gate / Score 변경 없음.
  - ML 알고리즘 구현 없음.
  - Feature Engineering 추가 없음.
  - Production / Trading / Position / Order 변경 없음.
  - DB / SQLite / PostgreSQL / Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AK Mirror Foundation End-to-End Validation
* 상태:
  - 완료.
  - Mirror Foundation 전체 레이어를 하나의 파이프라인으로 연결해 E2E 검증을 수행했다.
  - 20개 실제 Packet으로 전체 흐름을 검증했다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_foundation_e2e_validator.py`
  - `hell_engines/Hellhound/test_mirror_foundation_e2e_validator.py`
  - `outputs/mirror_foundation_e2e_report.json`
  - `outputs/mirror_foundation_e2e_failure_report.json`
  - `outputs/mirror_foundation_e2e_timing.json`
* E2E Pipeline:
  - Mirror Packet → Replay → Persistence → Readback Audit → Storage Failure Policy
* E2E 검증 결과:
  - E2E Result: PASS
  - Pipeline Result: PASS
  - Failure Injection Result: PASS
  - Contract Version: mirror_pattern_packet_v1
  - Packet Count: 20
  - Total Mutation Count: 0
  - Total Elapsed MS: 22.535ms
* Layer Boundary 무변형 검증:
  - Replay Stage: mutation_count=0, content_unchanged=true
  - Persistence Stage: mutation_count=0, save_count=20
  - Readback Stage: hash_mismatch_count=0, mutation_count=0, replay_after_readback=PASS
* Failure Injection 검증:
  - Write Failure: FAIL_SAFE=true, none_saved=true, downstream=0
  - Read Failure: FAIL_SAFE=true, downstream=0
  - Corrupt Data Read: FAIL_SAFE=true, correct_classification=true (CORRUPT_DATA)
  - 모든 케이스: no_bad_packets_downstream=true
* 테스트:
  - Targeted Test: 26 PASS
  - Full Test: 274 PASS (기존 248 + 신규 26)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - Mirror Decision Logic / Replay Logic / Registry 변경 없음.
  - Campaign Physics / Lead Line / Threshold / Gate / Score 변경 없음.
  - ML 학습 없음.
  - Production / Trading / Position / Order 변경 없음.
  - DB / SQLite / PostgreSQL / Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AJ Mirror Storage Failure Policy
* 상태:
  - 완료.
  - Storage 계층의 Read/Write 실패를 Fail-Safe 정책으로 처리하는 `StorageFailurePolicy`를 구현했다.
  - Mock 기반 시뮬레이션으로 6가지 실패 케이스를 검증했다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_storage_failure_policy.py`
  - `hell_engines/Hellhound/test_mirror_storage_failure_policy.py`
  - `outputs/mirror_failure_policy_report.json`
  - `outputs/mirror_failure_classification.json`
  - `outputs/mirror_replay_safety_report.json`
  - `outputs/mirror_failure_simulation.json`
  - `outputs/mirror_failure_report.json`
* Failure Classification:
  - `WRITE_FAILURE`: append_packet 실패
  - `READ_FAILURE`: load_packets IOError/OSError
  - `CORRUPT_DATA`: json.JSONDecodeError (Read 계열 전체)
  - `ENCODING_ERROR`: UnicodeDecodeError (Read 계열 전체)
  - `HASH_READ_FAILURE`: existing_hashes 실패
  - `UNKNOWN_FAILURE`: 기타 미분류 예외
* Policy Rules:
  - on_failure: FAIL_SAFE
  - auto_recovery_allowed: false
  - retry_allowed: false
  - repair_allowed: false
  - record_required: true
  - terminate_on_failure: true
* Simulation Method:
  - `unittest.mock.MagicMock` 기반 시뮬레이션만 사용.
  - 실제 파일 권한 변경, 디렉터리 권한 변경, OS 설정 변경 없음.
* 시뮬레이션 결과:
  - Simulation Verdict: PASS
  - simulation_count: 6
  - all_fail_safe: true
  - all_no_auto_recovery: true
  - all_correct_failure_codes: true
* Replay Safety:
  - Write Failure 이후 빈 패킷 목록으로 Replay: PASS
  - Read Failure 이후 빈 패킷 목록으로 Replay: PASS
  - Replay Safety Verdict: PASS
* 테스트:
  - Targeted Test: 29 PASS
  - Full Test: 248 PASS (기존 219 + 신규 29)
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - Replay Logic/Mirror Decision Logic/Registry 변경 없음.
  - Campaign Physics/Lead Line 변경 없음.
  - Threshold/Gate/Score 변경 없음.
  - ML 학습 없음.
  - Production/Trading/Position/Order 변경 없음.
  - DB/SQLite/PostgreSQL/Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.

### Sprint 12AI Mirror Persistence Readback Audit
* 상태:
  - 완료.
  - Persistence Adapter가 저장한 JSONL Packet을 다시 읽어 원본 `mirror_pattern_packet_v1`과 동일성을 검증했다.
  - 저장 파일과 Readback 과정은 UTF-8 without BOM 기준으로 감사했다.
* 생성 파일:
  - `hell_engines/Hellhound/mirror_persistence_readback_audit.py`
  - `hell_engines/Hellhound/test_mirror_persistence_readback_audit.py`
  - `outputs/mirror_readback_audit_report.json`
  - `outputs/mirror_readback_hash_report.json`
  - `outputs/mirror_readback_replay_report.json`
* 입력:
  - Original source: `outputs/mirror_shadow_log.jsonl` 내부 `mirror_packet`
  - Readback source: `outputs/mirror_persistence_packets.jsonl`
* Hash Audit:
  - Encoding: UTF-8 without BOM
  - Hash method: sha256(canonical_json_utf8_without_bom)
  - Canonical JSON: `json.dumps(sort_keys=True,separators=(',',':'))`
* Readback Summary:
  - Readback Audit: PASS
  - original_packet_count: 20
  - readback_packet_count: 20
  - hash_match_count: 20
  - hash_mismatch_count: 0
  - mutation_count: 0
  - average_read_time_ms: 0.00335
  - max_read_time_ms: 0.00875
* 검증:
  - UTF-8 Encoding Validation: PASS
  - Contract Validation: PASS
  - Equality Validation: PASS
  - Hash Match: PASS
  - Replay After Readback: PASS
  - Replay Determinism: PASS
  - Packet Mutation Count: 0
* 금지 준수:
  - `mirror_pattern_packet_v1` Contract 변경 없음.
  - Persistence Adapter Interface 변경 없음.
  - JsonlPacketStorage 저장 정책 변경 없음.
  - Replay Logic/Mirror Decision Logic/Registry 변경 없음.
  - Campaign Physics/Lead Line 변경 없음.
  - Threshold/Gate/Score 변경 없음.
  - ML 학습 없음.
  - Production/Trading/Position/Order 변경 없음.
  - DB/SQLite/PostgreSQL/Supabase 생성 또는 연결 없음.
  - Medusa 변경 없음.
* 향후 저장소 요구사항:
  - DB, Supabase, PostgreSQL, Dashboard storage 등 모든 저장 구현은 이 Readback Audit을 통과해야 신뢰 가능한 저장 계층으로 인정한다.

---

## 3. In Progress

### Pre-ML Dataset Accumulation
* 현재 최우선 작업은 missed case, success case, detection delay, structure stats, production feedback dataset을 실제 관찰 데이터로 채우는 것이다.
* ML 모델 설계는 관찰 데이터가 충분해질 때까지 보류한다.
* Production table update/delete는 여전히 금지한다.

### WhaleLab-006 준비
* WhaleLab-005의 API pipeline과 Hellhound Event Layer를 기반으로 다음 연구 단계를 정의하는 단계.
* 현재 원칙:
  - Forecast / Graph ML / Whale ML은 아직 구현하지 않는다.
  - Execution Guidance는 거래 전략이나 자동 주문이 아니다.
  - 각 출력은 Core / Ward / Hound 중 하나에 명확히 귀속되어야 한다.

### ML Core
* 보류.
* 아직 Production 편입 대상이 아님.
* 시작 조건:
  - missed case 축적.
  - success case 축적.
  - delay case 축적.
  - structure outcome ranking 축적.
  - Production feedback dataset 축적.
* 연구 후보:
  - Whale Type ML
  - Sector Flow ML
  - Regime Similarity Engine
  - Capital Rotation Forecast

### Watch Priority Model Refinement
* Priority > 80 후보군을 실시간 감시 강화 대상으로 활용.
* 현재 v0.4 검증 기준 최우선 감시 후보:
  - DEX: UNI
  - AI: FET, TAO
  - L1: SOL

---

## 4. Future

### Sector ML
* 섹터별 자금 유입/유출 강도와 지속성을 학습.
* 단기 펌핑과 장기 순환매를 분리하는 보조 모델로 사용.

### Whale Type ML
* shark, orca, humpback, blue_whale 등 고래 유형 분류를 규칙 기반에서 학습 기반으로 확장.
* 목표는 이벤트 국면별 지배적 고래 유형의 신뢰도 개선.

### Capital Rotation Forecast
* 현재 자금 흐름에서 다음 순환 후보 섹터/자산을 예측.
* 직접 매수/매도 신호가 아니라 Hound의 관찰 우선순위 보정값으로 사용.

### WhaleLab-006+
* Forecast / Graph ML / Whale Pattern ML은 이후 단계에서 별도 정의한다.

### Regime Similarity Engine
* 현재 시장 국면을 과거 이벤트와 비교.
* LUNA, FTX, SVB, BTC ETF, BTC Halving, Carry Trade Shock, Yoon Martial Law Shock 등 역사적 국면과의 유사도를 계산.

---

## 5. Current Working Assumption

GrayMUG의 현재 핵심 가설은 다음과 같다.

> 고래의 작업 시작 시점은 고정된 시간차로 역산할 수 없다. 대신 Rank Momentum, RS vs BTC Decoupling, Sector Flow, Flow Persistence, Whale Type, Watch Priority가 함께 개선되는 누적 흐름으로 탐지해야 한다.

따라서 GrayMUG v0.4 이후의 개발 방향은 단일 알람 모델이 아니라, Hound가 어디를 더 집중해서 볼지 결정하는 관찰 우선순위 시스템이다.

WhaleLab-005 기준 최종 정의는 다음과 같다.

> Core는 BTC를 모은다. Ward는 살아남게 한다. Hound는 알트를 사냥한다. Whale Link Flow는 세 엔진을 연결한다. 모든 결과는 BTC 수량 증가로 환류된다.

Pre-ML Phase 기준 최종 정의는 다음과 같다.

> 지금은 모델을 만드는 단계가 아니다. Hellhound가 무엇을 놓쳤는지, 무엇을 맞췄는지, 얼마나 늦었는지를 append-only 데이터로 축적하는 단계다. Mission is Boss.
