# WhaleLab-005 Integration Directive

* **작성일**: 2026-06-18
* **기준 상태**: WhaleLab-005-A 완료
* **목적**: GrayMUG-LAB의 WhaleLab-005 이후 통합 철학, 엔진 역할, 금지 규칙, 후속 로드맵을 고정한다.

---

## 1. Current State

WhaleLab-001 ~ WhaleLab-004 완료.

검증 완료 항목:

* Event Validation
* Whale Detection
* Sector Flow
* Watch Priority
* Whale Link Flow
* 고정 Lead Time 가설 폐기

WhaleLab-005-A 완료.

구현 파일:

```text
research/whale_link_flow/lead_line_socket.py
docs/007_WHALELAB_005A_LEAD_LINE_API_SOCKET.md
```

지원 API:

* `get_current_lead_line()`
* `get_hound_universe()`
* `get_ward_context()`
* `get_core_payload()`

지원 모드:

* `BEAR_ESCAPE`
* `BTC_ACCUMULATION`
* `OBSERVE_ONLY`

---

## 2. Final Philosophy

GrayMUG의 목표는 USDT 수익률 극대화가 아니다.

GrayMUG의 목표는 BTC 수량 증가다.

모든 전략은 최종적으로 BTC 개수로 평가한다.

---

## 3. Engine Roles

### Core

역할:

* BTC 본류 엔진

책임:

* 시장 국면 판단
* 전략 모드 선택
* BTC 축적 방향 유지

지원 모드:

* `BEAR_ESCAPE`
* `BTC_ACCUMULATION`
* `OBSERVE_ONLY`

Core는 BTC 개수 증가를 최우선 목표로 한다.

### Ward

역할:

* 생존 엔진

책임:

* 시장 위험 감시
* 리스크 평가
* 방어 상태 판단

Ward는 Core와 Hound에 정보를 제공할 수 있지만, 최종 방어 판단의 독립성을 유지한다.

### Hound

역할:

* 알트 사냥 엔진

책임:

* Lead Line 추적
* 알트 기회 탐색
* 회전 수익 확보

주의:

* Hound 직접 수정 금지
* Hound 탐지 로직 수정 금지
* Hound는 Lead Line이 제공하는 Universe만 소비한다

---

## 4. Whale Link Flow Definition

Whale Link Flow는 Core, Ward, Hound를 연결하는 Lead Line API Socket이다.

특정 엔진의 보조도구가 아니다.

```text
                 Whale Link Flow
                         |
                         v
                Lead Line API Socket
        +----------------+----------------+
        v                v                v
      Core             Hound            Ward
```

---

## 5. Data Flow

```text
Whale Event
      |
      v
Flow Analysis
      |
      v
Watch Priority
      |
      v
Lead Line API Socket
      |
      v
Core / Hound / Ward
```

---

## 6. Absolute Prohibitions

### 금지 1. 고정 Lead Time 가설 부활 금지

고정 Lead Time은 검증에서 폐기된 가설이다. 이후 WhaleLab 단계에서 다시 전제로 사용하지 않는다.

### 금지 2. Hound 내부 수정 금지

Hound 탐지 로직 내부에 Lead Line 조건을 직접 삽입하지 않는다.

### 금지 3. Ward 내부 판단 로직 침범 금지

Ward는 생존 엔진이며 독립적인 방어 판단을 유지한다.

### 금지 4. Core 전략 판단을 Whale Link Flow 안에 삽입 금지

Whale Link Flow는 Lead Line을 제공한다. 전략 모드 선택과 실행 방향 판단은 Core 책임이다.

---

## 7. WhaleLab-005 Roadmap

### 005-A: Lead Line API Socket

상태:

```text
Complete
```

목표:

* Whale Link Flow를 Core / Hound / Ward 공통 내부 API Socket으로 제공

### 005-B: Engine Integration Harness

상태:

```text
Complete
```

목표:

* Lead Line Socket을 Core / Ward / Hound state로 변환
* 실제 엔진 없이 연결 흐름 검증
* Simulator Payload 기반 생성

### 005-C: Core / Ward / Hound 실연결

상태:

```text
Next
```

목표:

* Socket 기반 연결 검증
* Hound는 universe만 소비
* Ward는 risk context만 참고
* Core는 mode와 축적 방향 결정

### 005-D: Flow Forecast Dataset

목표:

```text
현재 흐름 -> 다음 흐름
```

학습 데이터 구축.

### 005-E: Graph ML

입력:

* `link_edges.csv`
* `watch_priority.csv`
* `sector_flow_scores.csv`

목표:

* Flow Path Forecast

### 005-F: Whale Pattern ML

최종 목표:

```text
고래가 어디로 갔는가
```

가 아니라

```text
고래가 다음에 어디로 갈 것인가
```

를 예측한다.

---

## 8. Final Definition

Core는 BTC를 모은다.

Ward는 살아남게 한다.

Hound는 알트를 사냥한다.

Whale Link Flow는 세 엔진을 연결한다.

모든 결과는 BTC 수량 증가로 환류된다.
