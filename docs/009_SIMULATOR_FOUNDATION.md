# Simulator Foundation

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-B
* **목적**: GrayMUG Simulator의 철학과 초기 관찰 대상을 정의한다.

---

## 1. Simulator Philosophy

GrayMUG Simulator는 매매 시뮬레이터가 아니다.

현재 단계의 목적은 주문, 체결, 수익률 계산이 아니라 Core / Ward / Hound / Lead Line 상태를 동시에 관찰하는 것이다.

Simulator는 다음 질문에 답해야 한다.

* Core는 어떤 모드인가?
* Ward는 위험을 어떻게 보고 있는가?
* Hound는 어떤 universe를 보고 있는가?
* Lead Line은 어느 흐름을 가장 강하게 가리키는가?

---

## 2. Observation Targets

Simulator가 동시에 관찰할 상태:

* Core 상태
* Ward 상태
* Hound 상태
* Lead Line 상태

---

## 3. Expected Command Center View

```text
GRAYMUG COMMAND CENTER
MODE
BTC_ACCUMULATION
CORE
BTC Focus
WARD
NORMAL
HOUND
ETH/BTC
SOL/BTC
TAO/BTC
LEAD LINE
ETH -> SOL
```

---

## 4. Non-Goals

이번 단계에서 하지 않는 것:

* Lead Time 부활
* Forecast 구현
* Graph ML 구현
* Whale ML 구현
* DB 추가
* FastAPI 추가
* Dashboard 구현
* 실제 Core 수정
* 실제 Ward 수정
* 실제 Hound 수정

---

## 5. Path to WhaleLab-005-C

WhaleLab-005-B의 성공 기준은 실제 엔진 없이 다음 흐름을 검증하는 것이다.

```text
Lead Line -> Core
Lead Line -> Ward
Lead Line -> Hound
```

WhaleLab-005-C는 이 harness를 바탕으로 Socket 기반 실연결 검증으로 진입한다.
