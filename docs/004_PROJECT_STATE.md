# GrayMUG Project State

* **작성일**: 2026-06-22
* **범위**: GrayMUG-LAB 기준 프로젝트 현재 상태 요약
* **목적**: 세션, 모델, 담당자가 바뀌어도 GrayMUG가 어디까지 왔는지 5분 안에 복구할 수 있도록 현재 버전, 완료 항목, 진행 항목, 향후 방향을 고정한다.

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
