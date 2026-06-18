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

---

## 3. In Progress

### Watch Priority -> Hound Integration
* Whale Link Flow v0.4의 `watch_priority(symbol)` 인터페이스를 Hound 관찰 가중치에 연결하는 단계.
* 현재 원칙:
  - Whale Link Flow는 Lead Line이다.
  - Hound는 최종 감지/관찰 계층이다.
  - LAB에서 Hound를 직접 수정하지 않는다.

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

### Regime Similarity Engine
* 현재 시장 국면을 과거 이벤트와 비교.
* LUNA, FTX, SVB, BTC ETF, BTC Halving, Carry Trade Shock, Yoon Martial Law Shock 등 역사적 국면과의 유사도를 계산.

---

## 5. Current Working Assumption

GrayMUG의 현재 핵심 가설은 다음과 같다.

> 고래의 작업 시작 시점은 고정된 시간차로 역산할 수 없다. 대신 Rank Momentum, RS vs BTC Decoupling, Sector Flow, Flow Persistence, Whale Type, Watch Priority가 함께 개선되는 누적 흐름으로 탐지해야 한다.

따라서 GrayMUG v0.4 이후의 개발 방향은 단일 알람 모델이 아니라, Hound가 어디를 더 집중해서 볼지 결정하는 관찰 우선순위 시스템이다.
