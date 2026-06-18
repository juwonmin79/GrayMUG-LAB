# WhaleLab-005-C: Target Intelligence Pipeline

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-C
* **목적**: Whale Link Flow 연구 결과를 사람이 보는 지표에서 Core / Ward / Hound가 바로 소비할 수 있는 Target Feed API Pipeline으로 전환한다.

---

## 1. Definition

WhaleLab-005-C는 Dashboard가 아니다.

WhaleLab-005-C는 Simulator가 아니다.

WhaleLab-005-C는 Target Feed API Pipeline이다.

흐름:

```text
Whale Link Flow
    |
    v
Lead Line Socket
    |
    v
Engine Integration Harness
    |
    v
Target Intelligence Pipeline
    |
    v
Core / Ward / Hound Target Feed
```

---

## 2. Target Acquisition Principle

GrayMUG-LAB은 재미있는 지표를 만드는 연구소가 아니다.

GrayMUG-LAB은 Core / Ward / Hound가 더 정확한 지점을 타겟하게 만드는 API Pipeline 연구소다.

모든 지표는 반드시 다음 질문을 통과해야 한다.

```text
이 지표가 어느 엔진의 어떤 판단을 더 정확하게 만드는가?
```

통과하지 못하면 추가하지 않는다.

---

## 3. Engine Feed Definition

### Core Feed

Core Feed는 BTC 축적 판단을 보조한다.

필드:

* `engine`
* `mode`
* `quote_asset`
* `btc_accumulation_bias`
* `focus_assets`
* `confidence`
* `source`

Core Feed는 최종 매수/매도 판단을 하지 않는다.

### Ward Feed

Ward Feed는 생존 판단을 보조한다.

필드:

* `engine`
* `mode`
* `risk_hint`
* `escape_pressure`
* `risk_alignment`
* `warning_flags`
* `source`

Ward Feed는 위험 힌트만 제공한다. Ward의 최종 방어 판단을 대체하지 않는다.

### Hound Feed

Hound Feed는 알트 사냥 타겟 지정을 보조한다.

필드:

* `engine`
* `mode`
* `top_targets`
* `priority_rank`
* `hunt_pressure`
* `confidence`
* `source`

Hound Feed는 universe / target 후보를 제공한다. Hound 감지 로직을 수정하지 않는다.

---

## 4. Payload

Target Pipeline Payload 필드:

* `timestamp`
* `mode`
* `source`
* `core`
* `ward`
* `hound`

각 feed는 반드시 하나의 엔진에만 귀속된다.

---

## 5. Implementation

구현 위치:

```text
research/targeting/
```

생성 파일:

* `target_schema.py`
* `target_feed_builder.py`
* `core_target_feed.py`
* `ward_risk_feed.py`
* `hound_hunt_feed.py`
* `target_pipeline.py`
* `test_target_pipeline.py`
* `README.md`

선택적 보조 출력:

```text
outputs/targeting/latest_target_feed.json
```

---

## 6. Absolute Prohibitions

* Lead Time 구현 금지
* Forecast 구현 금지
* Graph ML 구현 금지
* Whale ML 구현 금지
* DB 추가 금지
* FastAPI 추가 금지
* Dashboard 추가 금지
* 실제 Core 수정 금지
* 실제 Ward 수정 금지
* 실제 Hound 수정 금지
* 재미있는 지표라는 이유만으로 추가 금지
* 한 지표가 여러 엔진 판단을 동시에 대체하면 안 됨

---

## 7. Final Definition

LAB은 세 엔진의 최종 판단을 대체하지 않는다.

LAB은 판단하지 않고 Target Feed만 제공한다.

모든 Feed는 BTC 수량 증가라는 최종 목적에 기여해야 한다.
