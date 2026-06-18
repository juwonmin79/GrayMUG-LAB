# WhaleLab-005-E: LAB Signal Calibration Layer

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-E
* **목적**: LAB에서 생성한 지표가 Core / Ward / Hound의 기존 로직을 침범하거나 왜곡하지 않도록 신호 강도, 신뢰도, 적용 범위를 표준화한다.

---

## 1. Definition

LAB 지표는 강할수록 좋은 것이 아니다.

LAB 지표는 정확도와 적용 범위가 함께 정의되어야 한다.

강한 지표라도 엔진의 기본 로직을 대체하면 설계 오류다.

WhaleLab-005-E는 Forecast, Graph ML, Whale ML, Execution Guidance가 아니다.

WhaleLab-005-E는 LAB 지표를 안전하게 엔진에 적용하기 위한 Calibration Layer다.

---

## 2. Engine Responsibility

```text
Core = BTC 축적 판단
Ward = 생존 판단
Hound = 사냥 판단
LAB = 판단 보조 / 타겟 보정 / 신호 보강
```

LAB은 엔진 판단을 대체하지 않는다.

LAB은 엔진의 기본 로직 위에 참고 신호를 제공한다.

---

## 3. Engine Scopes

### Core

Allowed scope:

```text
BTC_ACCUMULATION_REFERENCE
```

Forbidden:

```text
FINAL_STRATEGY_DECISION
```

Max influence:

```text
0.20
```

이유: Core는 BTC 본류 엔진이므로 보수적으로 적용한다.

### Ward

Allowed scope:

```text
RISK_HINT
```

Forbidden:

```text
FINAL_DEFENSE_DECISION
```

Max influence:

```text
0.15
```

이유: Ward는 생존 엔진이므로 가장 보수적으로 적용한다.

### Hound

Allowed scope:

```text
TARGET_PRIORITY_BOOST
```

Forbidden:

```text
DETECTION_LOGIC_REPLACEMENT
```

Max influence:

```text
0.30
```

이유: Hound는 타겟 우선순위 보정을 소비하므로 상대적으로 크게 적용할 수 있다.

---

## 4. Calibration Formula

```text
final_weight = signal_strength * confidence * max_influence
```

단, 결과는 `0.0 ~ 1.0` 범위로 제한한다.

또한 각 엔진의 `max_influence`를 초과할 수 없다.

---

## 5. Implementation

구현 위치:

```text
research/calibration/
```

생성 파일:

* `calibration_schema.py`
* `signal_calibrator.py`
* `engine_scope.py`
* `calibration_policy.py`
* `calibration_pipeline.py`
* `test_calibration_pipeline.py`
* `README.md`

실행:

```bash
source .venv/bin/activate && python -B research/calibration/calibration_pipeline.py
source .venv/bin/activate && python -B research/calibration/test_calibration_pipeline.py
```

---

## 6. Absolute Prohibitions

* Forecast 구현 금지
* Graph ML 구현 금지
* Whale ML 구현 금지
* DB 추가 금지
* FastAPI 추가 금지
* Dashboard 구현 금지
* 실제 Core 수정 금지
* 실제 Ward 수정 금지
* 실제 Hound 수정 금지
* Hound 감지 로직 대체 금지
* Ward 방어 판단 대체 금지
* Core 전략 판단 대체 금지

---

## 7. Final Definition

LAB은 엔진의 핸들을 빼앗지 않는다.

LAB은 Core / Ward / Hound가 더 정확한 타겟과 판단 보조값을 받도록 신호 강도, 신뢰도, 적용 범위를 조정한다.
