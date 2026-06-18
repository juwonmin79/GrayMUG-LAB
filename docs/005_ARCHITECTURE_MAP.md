# GrayMUG Architecture Map

* **작성일**: 2026-06-18
* **범위**: GrayMUG-LAB에서 정리한 GrayMUG Core / Whale Link Flow / Validation 구조
* **목적**: 모듈 간 책임과 데이터 흐름을 고정하여 이후 개발자가 전체 구조를 빠르게 복구할 수 있게 한다.

---

## 1. High-Level Structure

```text
GrayMUG Core
|
+-- Hound
|   `-- Whale detection / observation target
|
+-- Ward
|   `-- Risk monitoring / safety layer
|
+-- Whale Link Flow
|   |-- Cycle Layer
|   |-- Live Flow Layer
|   |-- Link Graph
|   |-- Sector Map
|   |-- Sector Flow
|   |-- Flow Persistence
|   |-- Whale Type
|   `-- Watch Priority
|
+-- ML Core
|   `-- Planned research layer
|
`-- Backtest / Validation
    `-- Research falsification and production gate
```

---

## 2. Whale Link Flow Pipeline

```text
Cycle Layer
    |
    v
Live Flow Layer
    |
    v
Link Graph
    |
    v
Sector Flow
    |
    v
Flow Persistence
    |
    v
Whale Type
    |
    v
Watch Priority
    |
    v
Hound
    |
    v
Trade Signal
```

Trade Signal은 이 문서 기준 Production 계층의 최종 결과이며, GrayMUG-LAB 산출물이 직접 생성하거나 직접 편입해서는 안 된다.

---

## 3. Layer Responsibilities

### Cycle Layer
* 시장의 큰 순환 국면을 식별한다.
* 이벤트 전후, 반감기 전후, 리스크 오프/온 전환 등 시간 축의 구조를 제공한다.

### Live Flow Layer
* 현재 자금 흐름을 실시간 또는 리플레이 방식으로 추적한다.
* 개별 자산 단위의 유입/유출 스코어를 산출한다.

### Link Graph
* 자산 간 흐름의 연결 구조를 표현한다.
* 단일 자산의 고립된 신호가 아니라 섹터/자산 간 이동 경로를 추적한다.

### Sector Flow
* 자산을 섹터 단위로 묶어 자금 순환 강도를 계산한다.
* v0.4 검증에서 사용된 주요 섹터:
  - L1
  - EXCHANGE
  - MEME
  - DEX
  - INFRA
  - AI
  - UNKNOWN

### Flow Persistence
* 일회성 스파이크와 지속적 순환 흐름을 구분한다.
* 기존 고정 Lead Time 모델의 한계를 보완하는 핵심 계층이다.

### Whale Type
* 관찰된 흐름의 고래 유형을 분류한다.
* v0.4 검증에서 관찰된 유형:
  - shark
  - orca
  - humpback
  - blue_whale

### Watch Priority
* Hound가 어떤 자산을 더 집중해서 관찰할지 결정하는 우선순위 점수.
* 직접 매매 신호가 아니다.
* 표준 인터페이스는 `watch_priority(symbol)` 형태를 유지한다.

### Hound
* 고래 감지 및 관찰 계층.
* Whale Link Flow의 Watch Priority를 입력으로 받을 수 있으나, LAB 단계에서 직접 수정해서는 안 된다.

### Ward
* 위험 감시 및 안전 계층.
* Production 편입 이후에도 리서치 모델의 과도한 신호를 제한하는 방어선 역할을 한다.

---

## 4. Research / Validation Pipeline

```text
Research
    |
    v
Backtest
    |
    v
Validation
    |
    v
Production
```

### Research
* 아이디어 제안과 가설 검증.
* 가격/거래량 슬로프, Rank Momentum, Relative Strength, RS vs BTC Decoupling 등을 탐색한다.

### Backtest
* 수수료, 슬리피지, 호가창 두께, 다양한 시장 국면을 반영한다.
* BTC 기준 성과와 과최적화 여부를 확인한다.

### Validation
* Paper Trading / Dry Run 기준 최소 2주 이상 검증한다.
* 실시간 데이터 지연, API 제한, Tracking Error를 확인한다.

### Production
* 검증 통과 후 설정 또는 제한된 인터페이스로만 편입한다.
* Hound/Core/Ward 코드를 LAB에서 직접 수정하지 않는다.

---

## 5. Current Validated Event Set

Whale Link Flow v0.4는 다음 7개 대형 이벤트로 검증되었다.

| Event | Primary Use |
| :--- | :--- |
| LUNA Collapse | 사후 변동성, 안전자산 선호, 알고리즘 편향 검증 |
| FTX Collapse | 거래소 리스크, 리스크 오프 흐름 |
| SVB Collapse | 전통 금융 리스크와 암호화폐 대체 자산 흐름 |
| BTC ETF Approval | 기관 자금 유입, Blue Whale 성향 |
| BTC Halving | 예정 이벤트 전후 순환매 |
| Carry Trade Shock | 글로벌 자산 급락, 디커플링 해제 |
| Yoon Martial Law Shock | 김치 프리미엄, 국내 거래소 투매, 정치적 블랙스완 |

---

## 6. Core Design Principle

Whale Link Flow는 Hound를 대체하지 않는다.

Whale Link Flow는 시장의 자금 순환, 지속성, 고래 유형, 섹터 우선순위를 계산해서 Hound가 더 집중해서 볼 대상을 알려주는 Lead Line이다.
