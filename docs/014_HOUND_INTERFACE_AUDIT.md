# Hound Interface Audit

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-G
* **목적**: 실제 Hound 코드 구조를 분석하여 LAB 계층이 어디에 안전하게 연결될 수 있는지 문서화한다.

---

## 1. Purpose

WhaleLab-005-G는 Hound를 강화하거나 수정하는 작업이 아니다.

이 문서는 Hound를 건드리지 않고 LAB 신호를 어디에 꽂아야 Hound / Ward / Core 로직이 틀어지지 않는지 찾기 위한 Audit / Design 문서다.

이번 작업 원칙:

* 코드 수정 금지
* Hound 수정 금지
* Ward 수정 금지
* Core 수정 금지
* 새 기능 추가 금지

대상 연결 흐름:

```text
LAB
  |
  v
Lead Line Socket
  |
  v
Target Feed
  |
  v
Calibration
  |
  v
Execution Guidance
  |
  v
Hound
```

---

## 2. Current Hound Structure

### Production Hound source status

현재 `GrayMUG-LAB` repository 안에는 production Hound 구현 파일이 포함되어 있지 않다.

검색 결과:

```text
hound/                          NOT FOUND
scanner.py                      NOT FOUND
relative_strength.py            NOT FOUND
engine.py                       NOT FOUND
alarm.py                        NOT FOUND
config.py                       NOT FOUND
```

현재 repository에서 확인 가능한 Hound 관련 파일은 production Hound가 아니라 LAB 쪽 Hound-facing adapter / feed / fitness 파일이다.

```text
research/integration/hound_adapter.py
research/targeting/hound_hunt_feed.py
research/fitness/hound_fitness.py
```

그 외 Hound에 연결되는 LAB 인터페이스:

```text
research/whale_link_flow/lead_line_socket.py
research/integration/state_schema.py
research/targeting/target_schema.py
research/execution/execution_pipeline.py
research/execution/execution_schema.py
```

따라서 이 Audit은 실제 production Hound 내부 구현을 확정하지 않고, 현재 LAB repository 기준으로 확인 가능한 Hound 접점만 정리한다.

---

## 3. Current Input Contract

### 확인 가능 항목

현재 LAB에서 Hound에 제공 가능한 입력은 `Lead Line Socket -> Hound Adapter -> Hound Target Feed -> Execution Guidance` 흐름이다.

#### Lead Line Socket

파일:

```text
research/whale_link_flow/lead_line_socket.py
```

Hound-facing API:

```python
get_hound_universe(
    mode: str,
    top_n: int = 12,
    min_priority: float = 0.0,
) -> list[str]
```

입력 파라미터:

* `mode`: `BEAR_ESCAPE`, `BTC_ACCUMULATION`, `OBSERVE_ONLY`
* `top_n`: Hound에 전달할 상위 universe 개수
* `min_priority`: 최소 watch priority 기준

반환:

* `list[str]`
* 예: `ETH/BTC`, `XRP/BTC`, `TAO/BTC`

#### Hound Adapter

파일:

```text
research/integration/hound_adapter.py
```

Hound-facing state:

```python
HoundState(
    tracked_symbols: list[str],
    priority_rank: dict[str, int],
    target_count: int,
)
```

#### Hound Target Feed

파일:

```text
research/targeting/hound_hunt_feed.py
research/targeting/target_schema.py
```

Feed:

```python
HoundHuntFeed(
    engine="HOUND",
    mode=str,
    top_targets=list[str],
    priority_rank=dict[str, int],
    hunt_pressure=float,
    confidence=float,
    source=str,
)
```

### 확인 불가 항목

Production Hound source가 repository에 없기 때문에 다음은 실제 기준으로 확인할 수 없다.

* Universe가 production Hound 내부에서 어디서 생성되는가
* Watchlist가 production Hound에 어디서 주입되는가
* Symbol list가 production Hound에서 어디서 결정되는가
* Scan interval이 어디서 결정되는가
* Threshold가 어디서 결정되는가

### 현재 Input Contract 결론

현재 LAB 기준 안전한 Hound input contract는 다음으로 제한한다.

```text
Hound consumes:
  - universe / tracked_symbols
  - priority_rank
  - target_count
  - optional execution guidance metadata after alert
```

Hound가 직접 소비하면 안 되는 것:

```text
Hound must not consume:
  - modified RSI threshold
  - modified volume threshold
  - replacement relative strength formula
  - LAB final buy/sell decision
  - Ward risk decision replacement
  - Core strategy decision replacement
```

---

## 4. Baseline Hound Logic

### Production baseline logic status

Production Hound implementation is not present in this repository. Therefore the following baseline conditions cannot be verified from source:

* FNG 조건
* 거래량 조건
* RSI 조건
* BTC 상대강도 조건
* Whale alert 조건
* 기존 ML / score 조건

### LAB-side confirmed boundary

현재 LAB 문서와 코드에서 반복적으로 고정된 원칙은 다음과 같다.

* Hound 내부 탐지 로직 수정 금지
* Hound threshold 직접 변경 금지
* RSI 조건 직접 변경 금지
* RS 계산식 변경 금지
* Volume spike 기준 변경 금지
* Hound ML score 대체 금지

### Baseline Hound Logic 결론

Production Hound baseline logic은 이 repository에서 확인되지 않았다.

따라서 WhaleLab-005-H 이전에 production Hound repository 또는 Hound source path를 확보해야 한다.

확보 전까지 LAB은 Hound baseline logic을 대체하거나 보정하지 않고, universe priority와 post-alert guidance metadata만 제공해야 한다.

---

## 5. Current Output Contract

### Production Hound output status

Production Hound source가 없기 때문에 다음은 실제 기준으로 확인할 수 없다.

* Alert payload 형태
* Whale 감지 발생 위치
* Candidate signal 발생 위치
* Telegram / Alarm 출력 생성 위치

### LAB-side output candidates

현재 LAB에서 Hound 결과에 첨부 가능한 output metadata는 Execution Guidance API가 만든다.

파일:

```text
research/execution/execution_pipeline.py
research/execution/execution_schema.py
```

Payload:

```python
ExecutionGuidancePayload(
    target=str,
    pattern=PatternHint,
    entry=EntryGuidance,
    tp_sl=TPSLGuidance,
    exit=ExitGuidance,
    source="execution_guidance_api",
)
```

제공 가능 항목:

* Pattern Hint
* Entry Style
* TP Case
* SL Case
* Exit Trigger

제공하면 안 되는 항목:

* 실제 주문
* 자동 진입
* 자동 청산
* 포지션 사이징
* 최종 매수 / 매도 판단

---

## 6. LAB Attachment Candidates

### A. Before Universe Build

가능 여부:

* 제한적으로 가능하나 권장하지 않는다.

장점:

* Hound가 scan하기 전부터 LAB priority를 반영할 수 있다.
* 불필요한 symbol을 줄여 scan 비용을 낮출 수 있다.

위험:

* Hound의 기존 universe 구성 원칙을 LAB이 대체할 수 있다.
* production Hound의 watchlist 생성 규칙을 모르는 상태에서는 base coverage를 훼손할 수 있다.
* Core mode 판단이 Hound universe 생성에 과도하게 개입할 위험이 있다.

권장 여부:

* 비권장.
* production Hound universe builder가 확인되기 전에는 사용하지 않는다.

### B. After Universe Build / Before Scanner

가능 여부:

* 가능.

장점:

* Hound의 기존 universe 생성 로직을 보존한다.
* LAB Lead Line이 universe 우선순위만 보정할 수 있다.
* Scanner 내부의 RSI, volume, RS, whale 조건을 변경하지 않는다.
* `get_hound_universe()`와 `HoundState.priority_rank`를 자연스럽게 연결할 수 있다.

위험:

* priority boost가 filtering으로 오해되면 Hound coverage가 줄어들 수 있다.
* production Hound scanner가 ordered universe를 지원하지 않으면 adapter가 필요하다.
* Hound가 watchlist와 priority를 분리하지 못하면 부작용이 생길 수 있다.

권장 여부:

* Primary Attachment로 권장.

권장 방식:

```text
Hound base universe
  |
  v
LAB priority overlay
  |
  v
Hound scanner runs unchanged
```

### C. After Signal / Before Alert

가능 여부:

* 제한적으로 가능.

장점:

* Hound가 생성한 candidate signal에 LAB context를 붙일 수 있다.
* Alert 생성 전 confidence / priority metadata를 추가할 수 있다.

위험:

* candidate signal을 suppress하거나 promote하면 Hound alert logic을 사실상 대체할 수 있다.
* threshold, score, alert gate를 LAB이 침범할 위험이 있다.

권장 여부:

* 조건부 비권장.
* 단순 metadata append만 허용하고, alert 생성 여부를 바꾸면 안 된다.

허용 가능한 형태:

```text
candidate_signal["lab_context"] = {
    "priority_rank": ...,
    "hunt_pressure": ...,
}
```

금지 형태:

```text
if lab_score > x:
    force_alert()
```

### D. After Alert / Execution Guidance

가능 여부:

* 가능.

장점:

* Hound가 이미 물어온 target에 대해 LAB이 설명을 덧붙인다.
* Hound baseline detection / alert generation을 건드리지 않는다.
* Execution Guidance API를 안전하게 연결할 수 있다.
* Telegram / Alarm payload에 참고 정보를 첨부하는 구조로 확장 가능하다.

위험:

* Guidance가 trade command로 오해될 수 있다.
* Alert consumer가 `WAIT_CONFIRMATION`, `AVOID`, TP/SL template을 자동 주문 규칙으로 잘못 사용할 수 있다.

권장 여부:

* Secondary Attachment로 권장.

권장 방식:

```text
Hound alert payload
  |
  v
LAB Execution Guidance metadata append
  |
  v
Alarm / UI / human review
```

---

## 7. Recommended Attachment Point

### Primary Attachment

```text
B. After Universe Build / Before Scanner
```

이유:

* Hound 내부 감지 로직을 보존한다.
* LAB Lead Line으로 감시 universe와 우선순위만 보정할 수 있다.
* Watch priority 주입에 적합하다.
* RSI, volume, RS, FNG, whale alert baseline condition을 건드리지 않는다.

Primary attachment contract:

```text
Input:
  - Hound base universe
  - LAB hound universe / priority_rank

Output:
  - same symbols or expanded symbols
  - priority metadata
  - no threshold changes
  - no forced alerts
```

### Secondary Attachment

```text
D. After Alert / Execution Guidance
```

이유:

* Hound가 이미 탐지한 target에 대해 LAB이 pattern, entry, TP/SL, exit guide를 덧붙일 수 있다.
* Alert 생성 여부를 바꾸지 않는다.
* Human / Core / Ward / Hound가 참고할 context를 구조화할 수 있다.

Secondary attachment contract:

```text
Input:
  - Hound alert target
  - LAB ExecutionGuidancePayload

Output:
  - alert payload + lab_guidance metadata
  - no auto order
  - no position management
```

---

## 8. Forbidden Changes

금지:

* Hound baseline logic 대체
* Hound ML score 대체
* Hound threshold 직접 변경
* RSI 조건 직접 변경
* RS 계산식 변경
* Volume spike 기준 변경
* FNG 조건 변경
* Whale alert gate 변경
* Ward risk decision 대체
* Core strategy decision 대체
* 자동 주문 연결
* 포지션 관리 연결

비권장:

* LAB score로 Hound alert를 강제 생성
* LAB score로 Hound alert를 강제 suppress
* LAB universe로 Hound base universe를 완전히 대체

권장 가능:

* Hound universe 우선순위 강화
* Watch priority 주입
* Execution Guidance를 alert payload에 참고 정보로 첨부
* LAB metadata를 alarm / UI에 표시하되 실행 로직과 분리

---

## 9. Next Step: WhaleLab-005-H First Live Attachment Plan

WhaleLab-005-H에서 수행해야 할 일:

1. Production Hound repository 또는 source path 확보.
2. 실제 Hound universe builder 위치 확인.
3. 실제 scanner entrypoint 확인.
4. 실제 alert payload schema 확인.
5. 실제 alarm / Telegram output 위치 확인.
6. Primary attachment인 `After Universe Build / Before Scanner`에 adapter plan 작성.
7. Secondary attachment인 `After Alert / Execution Guidance`에 metadata append plan 작성.
8. 코드 수정 전 dry-run contract test 작성.

005-H의 첫 설계 목표:

```text
Hound base universe
  |
  v
LAB priority overlay
  |
  v
Hound scanner unchanged
```

005-H에서 여전히 금지되는 것:

* Hound threshold 변경
* Hound scanner condition 변경
* Hound alert gate 변경
* 자동 주문 연결
* Ward / Core 판단 침범

---

## Final Definition

WhaleLab-005-G는 Hound를 강화하는 작업이 아니다.

Hound를 건드리지 않고 LAB 신호를 어디에 꽂아야 Hound / Ward / Core 로직이 틀어지지 않는지 찾는 작업이다.
