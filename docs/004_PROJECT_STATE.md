# GrayMUG Project State

* **작성일**: 2026-06-18
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
| ML Core | Planned | Whale Type ML, Sector ML, Capital Rotation Forecast 예정 |

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

---

## 3. In Progress

### WhaleLab-005-F: 다음 연구 단계 준비
* Calibration Layer 이후 연구 산출물이 엔진 로직을 침범하지 않는 구조를 유지하는 단계.
* 현재 원칙:
  - Forecast / Graph ML / Whale ML은 아직 구현하지 않는다.
  - Execution Guidance는 calibrated signal만 소비할 수 있다.
  - 각 출력은 Core / Ward / Hound 중 하나에 명확히 귀속되어야 한다.

### ML Core
* 아직 Production 편입 대상이 아님.
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

### WhaleLab-005-F+
* 005-F: 고래가 다음에 어디로 갈 것인지 예측하는 Whale Pattern ML.

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
