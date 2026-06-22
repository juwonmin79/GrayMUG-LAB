# GrayMUG-LAB Research Roadmap

본 로드맵은 실거래 코드 수정 없이 오직 연구 목적으로 시장에서 고래의 흔적(Footprint)을 사전에 발굴하고 프로토타이핑하는 단계적 계획입니다.

---

## Phase 1: UNI Case Study
* **핵심 질문**: "고래가 발견된 시점" vs "고래가 실제로 작업을 개시한 시점"의 차이를 정의하고 포착할 수 있는가?
* **연구 대상**: Uniswap (UNI) 토큰 거래량 급증(Volume Spike) 이전의 선행 징후 탐색.
* **주요 탐색 지표 후보**:
  1. **Price Slope**: 가격 변화 기울기의 미세한 상승 추세 전환.
  2. **Volume Slope**: 거래량 누적 변화 추이의 기울기 가속화.
  3. **Rank Momentum**: 주요 시장참여자들의 거래 대금/거래 횟수 순위 모멘텀.
  4. **Relative Strength**: 전체 시장 대비 UNI의 상대적 강세 지표.

---

## Phase 2: Historical Event Dataset
* **목표**: 고래들이 급격한 포지션 조정이나 작업을 수행하는 역사적인 블랙스완/이벤트 시점의 원본 데이터를 구축하고 분석.
* **주요 역사적 이벤트**:
  * **LUNA Collapse**: 테라-루나 사태 및 알고리즘 스테이블코인 붕괴 전후.
  * **FTX Collapse**: FTX 거래소 파산 선언에 따른 시장 패닉 전후.
  * **SVB Collapse**: 실리콘밸리은행 파산에 따른 금융 불안 및 스테이블코인 디페깅 전후.
  * **BTC ETF Approval**: 비트코인 현물 ETF 승인 전후의 자금 유입 및 고래 포지션 변동.
  * **BTC Halving**: 반감기 전후의 채굴자 및 장기 보유자 거동 분석.
  * **Yoon Martial Law Shock**: 대한민국 비상계엄 선포에 따른 김치 프리미엄 변동 및 국내 거래소 투매 현상 분석.
  * **Carry Trade Shock**: 엔 캐리 트레이드 청산 우려로 인한 글로벌 자산 급락 및 암호화폐 시장 반응.

---

## Phase 3: Regime Similarity Engine
* **목표**: 현재의 시장 상황(변동성, 거래량, 가격 흐름, 오더북 상태 등)이 과거 역사적 시점 중 어느 시기와 가장 유사한지 실시간으로 비교 분석하는 엔진 구축.
* **핵심 알고리즘**:
  * 다차원 시계열 피처 추출 및 거리 측정 (Dynamic Time Warping, Cosine Similarity 등).
  * 국면 분류(Regime Classification) 모델 구축.

---

## Phase 4: Whale Lifecycle Model
* **목표**: 고래의 전체 자금 집행 주기를 모형화하여 각 단계별 진입과 이탈 시점을 탐지.
* **4단계 생애주기**:
  1. **Accumulation (매집)**: 조용한 자금 유입, 오더북 압박 최소화, 거래량의 미세 변화.
  2. **Expansion (확장/발산)**: 본격적인 가격 상승 유도, 리테일 참여 유도, Vol Spike 시작.
  3. **Distribution (분산/차익실현)**: 고점에서의 물량 분산, 대량 거래량 동반, 호가 지지선 구축.
  4. **Exit (이탈/정리)**: 포지션 청산 완료 또는 쇼트 헤징 완료 후 급락 유도.

---

## Phase 5: Hellhound Event Layer
* **목표**: Hound를 직접 수정하지 않고, Hellhound를 탈착식 분석 두뇌로 발전시킨다.
* **핵심 전환**: signal/outcome 중심 분석에서 event timeline 중심 분석으로 이동한다.
* **이유**: 동일 심볼에서 반복 발생하는 shadow signal은 독립 사건이 아니라 하나의 누적 시장 구조일 수 있다. METUSDT처럼 84개 signal이 발생한 경우 84개 판단이 아니라 1개 또는 소수 event timeline으로 분석해야 한다.
* **구현 상태**:
  1. `event_layer.py`: `symbol + source_time + hypothesis` 기준 분석-layer deduplication 및 event builder.
  2. `pre_spike_features.py`: `1m/15m/1h/4h/1d/1w` snapshot interface와 기초 pre-spike feature 계산.
  3. `event_classifier.py`: `BEL`, `ACT`, `ACE`, `NIGHT` rule-based classifier.
  4. `decision_api.py`: Hound가 나중에 optional import할 수 있는 fail-safe API 초안.
  5. `integration_stub.py`: Production Hound 수정 없이 붙이는 예시.
* **기본값**: `HELLHOUND_DECISION_ENABLED=false`.
* **안전 원칙**: Production Hound/Ward/Core, `backup_GrayMUG`, `.env`, Binance trading endpoint, DB delete/update 금지.

---

## Phase 6: Hellhound Accumulation Intelligence Layer
* **목표**: Hellhound가 "이미 터진 코인"보다 "터지기 전에 오래 모으고 있던 코인"을 먼저 찾도록 한다.
* **핵심 전환**: 폭발 이후 감지에서 폭발 이전 준비 상태 감지로 이동한다.
* **구현 상태**:
  1. `accumulation_features.py`: 7d/14d/30d volume, return, high/low distance, structure context 계산.
  2. Repeated Whale Activity: 7d/14d/30d spike count, 평균/최소 spike interval, repeat activity score 계산.
  3. Structure Context: weekly/monthly trend, MA200 distance, 52w high/low distance, `ACCUMULATION_BASE`, `MID_CYCLE`, `DISTRIBUTION`, `CAPITULATION`, `UNKNOWN` 분류.
  4. Hellhound Score v0.2: `accumulation_score`, `repeat_activity_score`, `structure_score`, `hellhound_score` 통합.
* **사례 재분류**:
  - `BEL`: 바닥권 반복 활동이 있는 accumulation base.
  - `ACT`: distribution/capitulation 계열의 일회성 폭발 위험.
  - `ACE`: 고점권 반복 활동이 있는 late detection 위험.
  - `MET`: accumulation base이나 BEL 반복 기준이 아직 약한 후보.
* **금지 유지**: ML 사용 금지, Production 수정 금지, DB delete/update 금지, Binance trading endpoint 금지.

---

## Phase 7: Hellhound Shadow Promotion Layer
* **목표**: 좋은 신호가 아니라 Production으로 승격할 후보를 선별한다.
* **핵심 전환**: Hellhound score 산출에서 shadow promotion gate로 이동한다.
* **구현 상태**:
  1. `promotion_candidate.py`: `PROMOTE`, `WATCH`, `REJECT` rule-based promotion gate.
  2. `build_shadow_decision()`: 실거래 없는 shadow decision payload 생성.
  3. BEL/ACT/ACE/MET/NIGHT replay: BEL은 `PROMOTE`, ACT는 `REJECT` 가능 여부 검증.
  4. Outcome correlation: supplied outcome rows를 score band별 승률로 집계.
* **Score bands**:
  - `0.0~0.2`
  - `0.2~0.4`
  - `0.4~0.6`
  - `0.6~0.8`
  - `0.8~1.0`
* **금지 유지**: Production Hound/Ward/Core 수정 금지, 실제 거래 로직 수정 금지, DB delete/update 금지, git stage/commit/push 금지.

---

## Phase 8: Hellhound Shadow Advisor Mode
* **목표**: Production Hound를 수정하지 않고 Hellhound를 옆자리 advisor로 붙인다.
* **핵심 전환**: Production 승격 후보 판정에서 실시간 증명 가능한 shadow audit/history 확보로 이동한다.
* **흐름**:
  1. Hound Signal
  2. Hellhound Evaluate
  3. Shadow Decision
  4. Log Only
* **구현 상태**:
  1. `integration_stub.py`: `optional_hellhound_decision()`이 signal, shadow_signals, historical_candles, event_history를 받아 advisor payload 반환.
  2. `shadow_advisor.py`: pipeline, audit, replay validation, false-positive analysis, JSONL log writer.
  3. `shadow_decision_log.jsonl`: writer 구현 전 파일 기반 shadow history interface.
* **명시 원칙**:
  - Hellhound는 Advisor Mode.
  - Trade Authority 없음.
  - Hound 결과를 변경하지 않음.
  - 실거래 영향 없음.

---

## Phase 9: Hellhound Real Shadow Feed
* **목표**: Hellhound가 실제 Hound/Hellhound 신호를 읽고, 거래 없이 shadow decision log를 쌓기 시작한다.
* **핵심 전환**: synthetic replay 중심에서 real signal feed 중심으로 이동한다.
* **구현 상태**:
  1. `real_shadow_feed.py`: `hound_scan_log` 또는 `hellhound_shadow_signals` 최근 신호 read-only 조회.
  2. Real signal -> `run_shadow_evaluation_pipeline()` -> JSONL shadow decision.
  3. `hellhound_outcomes` read-only join 준비. 결과가 없으면 `actual_1h_outcome`, `actual_4h_outcome`, `actual_24h_outcome`은 `null`.
  4. DB 없이 mock rows로 dry-run/test 가능.
* **기본 로그 경로**:
  - `outputs/hellhound_shadow_decisions.jsonl`
* **CLI**:
  - `python3 hell_engines/Hellhound/real_shadow_feed.py --limit 100 --dry-run`
  - `python3 hell_engines/Hellhound/real_shadow_feed.py --limit 5 --dry-run --mock`
* **금지 유지**: Production 수정 금지, DB delete/update 금지, event schema 즉시 적용 금지, Binance trading endpoint 금지.

### Phase 9-A: Daily Open Alert Cluster
* **목표**: UTC daily open 전후 `00:00 +/- 15m`에 몰린 Hound alerts를 cluster로 묶고 detection delay candidate로 기록한다.
* **출력**:
  - `cluster_id`
  - `symbols`
  - `alert_count`
  - `avg_vol_ratio`
  - `max_vol_ratio`
  - `daily_open_cluster=true`
  - `detection_delay_candidate=true`
* **저장**: `outputs/hellhound_shadow_decisions.jsonl`에 `record_type=daily_open_alert_cluster` row로 기록.

---

## Phase 10: Hellhound Library/API Boundary
* **목표**: Production Hound를 수정하지 않고 Hellhound를 옆에서 호출 가능한 순수 library/API boundary로 정리한다.
* **핵심 원칙**:
  - Hellhound는 거래하지 않는다.
  - Hellhound는 판단, 연구, Shadow Advisor 역할만 한다.
  - Production Hound는 기존처럼 거래 담당이다.
  - Hellhound output은 trade command가 아니며 항상 `is_trade_command=false`.
* **구현 상태**:
  1. `library_interface.py`: signal/event/snapshot row 입력을 shadow decision/advisor result/cluster result로 변환하는 facade.
  2. `test_library_interface.py`: interface 호출, cluster output, dry-run boundary, trade command 미발생 검증.
  3. Event Writer는 보류. append-only JSONL 원칙 유지.
* **API 후보**:
  - `evaluate_signal_row(signal, ...)`
  - `evaluate_event_row(event, ...)`
  - `evaluate_snapshot_row(snapshot, ...)`
  - `detect_cluster_rows(signals)`
  - `evaluate_real_feed_row(signal, outcome_rows=None)`
* **금지 유지**: Production Hound/Ward/Core 수정 금지, `backup_GrayMUG` 수정 금지, Binance order/trading endpoint 금지, DB delete/update 금지.

---

## Phase 11: Hellhound Event Writer + Persistence
* **목표**: Hellhound 연구 결과를 미래 Lead Line, MFE/MAE, Mirror Pattern ML 입력이 될 append-only Event Layer로 저장한다.
* **핵심 원칙**:
  - JSONL append-only.
  - DB delete/update 없음.
  - trade command 저장 금지.
  - Event Layer는 연구용 데이터 자산.
* **지원 record_type**:
  - `shadow_decision`
  - `daily_open_alert_cluster`
  - `real_feed_outcome`
* **공통 필드**:
  - `event_id`
  - `event_time`
  - `record_type`
  - `source`
  - `hellhound_version`
  - `symbol`
  - `is_trade_command`
* **구현 상태**:
  1. `event_writer.py`: `EventWriter`, `append_event`, `append_events`, `validate_event`.
  2. Boundary output 변환: `record_from_boundary_output`, `records_from_boundary_output`.
  3. malformed row reject, record_type 검증, `is_trade_command=false` 검증.
* **기본 저장 경로**:
  - `outputs/hellhound_event_layer.jsonl`

---

## Phase 12: Hellhound Lead Line Dataset Builder
* **목표**: "상승 결과가 발생하기 전에 Hellhound가 무엇을 보았는가?"를 학습 가능한 dataset으로 변환한다.
* **Mission**: Detection Delay 감소.
* **입력**:
  - `outputs/hellhound_event_layer.jsonl`
  - `record_type=real_feed_outcome`을 outcome anchor로 사용.
* **처리**:
  1. outcome event 발생 시점 확인.
  2. 이전 N시간 event 수집.
  3. Shadow decision / Daily open cluster 여부와 score context를 feature로 변환.
* **기본 window**:
  - `24h`
  - `48h`
  - `72h`
* **출력**:
  - `outputs/hellhound_lead_line_dataset.jsonl`
* **구현 상태**:
  - `lead_line_dataset.py`
  - `test_lead_line_dataset.py`
* **원칙**:
  - append-only.
  - 연구 전용.
  - Production 수정 없음.
  - DB 적용 없음.

---

## Phase 13: Hellhound Outcome Window Validation
* **목표**: Lead Line이 실제 outcome에 대해 얼마나 선행성이 있었는지 검증한다.
* **핵심 질문**:
  - Sprint 9: "우리는 무엇을 보았는가?"
  - Sprint 10: "그것이 실제로 의미 있었는가?"
* **Mission**: Detection Delay 측정 시작.
* **지원 validation window**:
  - `24h`
  - `48h`
  - `72h`
* **Validation status**:
  - `VALIDATED`
  - `DELAYED`
  - `INCONCLUSIVE`
  - `REJECTED`
* **출력**:
  - `outputs/hellhound_validation_dataset.jsonl`
* **구현 상태**:
  - `outcome_validator.py`
  - `test_outcome_validator.py`
* **원칙**:
  - 연구 전용.
  - append-only JSONL.
  - Production 수정 없음.
  - DB 적용 없음.

---

## Phase 14: Hellhound MFE / MAE Engine
* **목표**: 검증된 Lead Line 패턴이 보통 얼마나 먹고, 얼마나 흔들리는지 측정한다.
* **핵심 질문**:
  - Sprint 10: "이 패턴은 맞았는가?"
  - Sprint 11: "이 패턴은 보통 얼마나 먹는가?"
* **Mission**: 세력 수익구간 학습.
* **입력**:
  - `outputs/hellhound_validation_dataset.jsonl`
  - validation row별 post-validation price path.
* **산출 지표**:
  - `mfe_pct`
  - `mae_pct`
  - `time_to_peak_hours`
  - `time_to_stop_hours`
  - `peak_price`
  - `stop_price`
  - `outcome_price`
* **구조별 집계**:
  - `average_mfe`
  - `median_mfe`
  - `average_mae`
  - `median_mae`
* **출력**:
  - `outputs/hellhound_mfe_mae_dataset.jsonl`
* **구현 상태**:
  - `mfe_mae_engine.py`
  - `test_mfe_mae_engine.py`
* **원칙**:
  - 연구 전용.
  - append-only JSONL.
  - Production 수정 없음.
  - DB 적용 없음.

---

## Phase 14-A: Hellhound Production Interface v1
* **목표**: Production Hound를 수정하지 않고, Hellhound advisory output을 case batch library/API boundary로 제공한다.
* **흐름**:
  1. Production Hound가 signal/case batch 생성.
  2. Adapter가 Hellhound `production_interface.py` 호출.
  3. Hellhound가 advisory output 반환.
  4. Production Hound가 최종 판단 유지.
* **구현 상태**:
  - `production_interface.py`
  - `test_production_interface.py`
  - `docs/020_HELLHOUND_PRODUCTION_INTERFACE.md`
* **Interface version**:
  - `hellhound_production_interface_v1`
* **Mode**:
  - `shadow`
* **핵심 원칙**:
  - 모든 output은 `is_trade_command=false`.
  - `entry_bias=neutral` 강제.
  - Hellhound는 trade command를 반환하지 않음.
  - v1/v2/v3 library 병렬 유지 가능.
  - LAB은 계속 진화하고 Production은 검증된 stable version만 선택.

---

## Phase 15: Pre-ML Observation Collection
* **목표**: ML 모델 개발 전 Hellhound가 실제 시장에서 무엇을 놓쳤고, 무엇을 맞췄고, 얼마나 늦었는지 축적한다.
* **현재 원칙**:
  - 모델을 만들지 않는다.
  - 먼저 실패/성공/지연/구조별 outcome을 기록한다.
  - Production Hound/Ward/Core는 수정하지 않는다.
  - 모든 출력은 `is_trade_command=false`.
* **ML 보류 대상**:
  - LSTM
  - Transformer
  - Deep Learning
  - Embedding DB
  - Vector Search
  - Fine-tuning
  - GPU 학습
  - Feature Explosion
* **구현 상태**:
  1. `missed_case_registry.py`: 상승 이후 발견된 감지 실패 사례를 `outputs/hellhound_missed_cases.jsonl`에 append-only 기록.
  2. `success_case_registry.py`: Hellhound가 사전에 포착한 성공 사례를 `outputs/hellhound_success_cases.jsonl`에 append-only 기록.
  3. `structure_outcome_ranking.py`: `BEL`, `ACT`, `ACE`, `MET`, `NIGHT` 구조별 발생 횟수, `VALIDATED` 비율, 평균 MFE, 평균 MAE, 평균 Time To Peak 집계.
  4. `detection_delay_report.py`: Signal Time, Outcome Time, Delay Hours 및 평균/중앙값/최소/최대 지연 집계.
  5. `production_feedback_dataset.py`: `production_hellhound_shadow.jsonl`을 연구용 `outputs/hellhound_feedback_dataset.jsonl`로 변환.
* **고정 케이스**:
  - 최근 BTC 상승은 `docs/022_MISSED_BTC_CASE_REVIEW.md`에 missed case로 고정한다.
* **완료 기준**:
  - 성공 사례, 실패 사례, 지연 사례를 모두 축적할 수 있는 상태.
  - 그 다음 단계에서만 ML 설계를 시작한다.

### Phase 15-A: Optional Decision Import Activation
* **목표**: `source_error=Hellhound optional decision import is disabled.` 반복 원인을 규명하고 fallback이 아닌 실제 decision path를 활성화한다.
* **원인**:
  - `integration_stub.optional_hellhound_decision()`과 `decision_api.evaluate_symbol()`의 이중 feature flag gate.
  - 기본 `HELLHOUND_DECISION_ENABLED=false` 때문에 import 이전 또는 decision API 내부에서 fail-safe neutral 반환.
* **수정**:
  - LAB/library shadow path는 `decision_enabled=True`를 명시 전달.
  - 명시적으로 `decision_enabled=False`를 넘긴 경우에만 fallback evaluator 사용.
  - 실제 decision 결과에는 `decision_source=decision_api`를 포함.
* **상세 문서**:
  - `docs/023_HELLHOUND_OPTIONAL_DECISION_IMPORT.md`
