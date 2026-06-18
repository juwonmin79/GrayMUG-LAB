# WhaleLab-005-A: Lead Line API Socket

* **작성일**: 2026-06-18
* **범위**: Whale Link Flow v0.4 이후 내부 API Socket 계약
* **목적**: Whale Link Flow를 Hound에 직접 삽입하지 않고, Core / Hound / Ward가 공통으로 소비할 수 있는 Lead Line API Socket으로 제공한다.

---

## 1. Core Principle

* Hound 직접 수정 금지
* Hound 감지 로직 수정 금지
* Ward는 방어 판단만 수행
* Core는 실행 모드와 자산 축적 방향을 결정
* Whale Link Flow는 Lead Line만 제공

Whale Link Flow는 Hound를 고치는 것이 아니라 Core / Hound / Ward가 공통으로 꽂아 쓰는 내부 Lead Line API Socket이다.

---

## 2. Architecture

```text
Whale Link Flow
        |
        v
Lead Line API Socket
        |
        v
+------------+------------+------------+
|    Core    |   Hound    |    Ward    |
+------------+------------+------------+
```

Lead Line API Socket은 Production 실행 권한을 갖지 않는다. Watch Priority를 표준 payload로 바꿔서 각 계층이 독립적으로 소비할 수 있게 한다.

---

## 3. API Socket Roles

### Core

Core는 현재 시장 국면과 전략 목적을 판단한다.

Supported mode:

* `BEAR_ESCAPE`
* `BTC_ACCUMULATION`
* `OBSERVE_ONLY`

Core는 Lead Line API에 `mode`를 전달하고, 최종 실행 모드와 자산 축적 방향을 결정한다.

### Hound

Hound는 Lead Line API에서 `universe`를 받아 감시 대상을 갱신한다.

Hound 내부 탐지 로직은 수정하지 않는다. Lead Line 조건을 Hound 감지 조건 내부에 삽입하지 않는다.

### Ward

Ward는 Lead Line API의 risk context를 참고할 수 있다.

최종 방어 판단은 Ward가 독립적으로 수행한다. Lead Line은 Ward 판단을 대체하지 않는다.

---

## 4. Supported Modes

### BEAR_ESCAPE

목적:

* USDT 생존
* 리스크 회피

Quote asset:

```text
USDT
```

예시 universe:

```text
ETH/USDT
BTC/USDT
BNB/USDT
```

### BTC_ACCUMULATION

목적:

* BTC 수량 증가

Quote asset:

```text
BTC
```

예시 universe:

```text
ETH/BTC
SOL/BTC
BNB/BTC
```

### OBSERVE_ONLY

목적:

* 관찰
* 학습
* 비실행

Quote asset:

```text
NONE
```

---

## 5. Internal API Contract

구현 위치:

```text
research/whale_link_flow/lead_line_socket.py
```

### get_current_lead_line

```python
get_current_lead_line(
    mode: str,
    top_n: int = 12,
    min_priority: float = 0.0,
) -> dict
```

현재 Watch Priority 기준 Lead Line payload를 반환한다.

### get_hound_universe

```python
get_hound_universe(
    mode: str,
    top_n: int = 12,
    min_priority: float = 0.0,
) -> list[str]
```

Hound가 소비할 감시 universe만 반환한다.

### get_ward_context

```python
get_ward_context(
    mode: str,
) -> dict
```

Ward가 참고할 수 있는 risk context를 반환한다. Ward의 최종 방어 판단은 독립적이다.

### get_core_payload

```python
get_core_payload(
    mode: str,
) -> dict
```

Core가 현재 실행 방향과 quote asset을 확인할 수 있는 payload를 반환한다.

---

## 6. Payload Example

```json
{
  "source": "whale_link_flow",
  "socket": "lead_line",
  "mode": "BTC_ACCUMULATION",
  "quote_asset": "BTC",
  "hound_direct_modify": false,
  "symbols": [
    "ETH/BTC",
    "SOL/BTC",
    "BNB/BTC"
  ],
  "items": [
    {
      "symbol": "ETH",
      "pair": "ETH/BTC",
      "priority_score": 0.91,
      "sector": "L1",
      "whale_type": "rotation",
      "rank": 1
    }
  ]
}
```

현재 구현은 v0.4 `watch_priority.csv`의 0~100 점수를 API payload에서 0~1 범위로 정규화한다.

---

## 7. Development Rules

* DB는 현재 단계에서 사용하지 않는다.
* DataFrame / in-memory 기반으로 시작한다.
* 파일 export는 보조 수단이며, 본 구조는 내부 API 우선이다.
* Hound는 API Socket의 결과만 소비한다.
* Hound 내부 로직에는 Lead Line 조건을 삽입하지 않는다.
* Ward는 방어 레이어로 독립성을 유지한다.
* Core는 USDT 생존 모드와 BTC 축적 모드를 전환한다.

---

## 8. One-Line Summary

Whale Link Flow는 Hound를 고치는 것이 아니라, Core / Hound / Ward가 공통으로 꽂아 쓰는 Lead Line API Socket이다.
