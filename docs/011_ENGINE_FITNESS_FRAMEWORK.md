# WhaleLab-005-D: Engine Fitness Framework

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-D
* **목적**: WhaleLab 연구 결과가 실제로 Core / Ward / Hound의 능력을 향상시키는지 측정 가능한 Framework를 구축한다.

---

## 1. Core Definition

GrayMUG-LAB의 연구 성과는 지표 개수로 평가하지 않는다.

GrayMUG-LAB의 연구 성과는 다음 기준으로 평가한다.

* Core 판단력
* Ward 생존력
* Hound 사냥능력
* BTC 증가 기여도

WhaleLab-005-D부터 GrayMUG-LAB은 다음 루프를 형성한다.

```text
연구
  |
  v
적용
  |
  v
측정
  |
  v
개선
```

---

## 2. Fitness Targets

### Core Fitness

목표:

* BTC 축적 능력 평가

초기 필드:

* `score`
* `btc_accumulation_score`
* `btc_relative_alpha`
* `focus_assets`

초기 버전은 규칙 기반이며 실제 수익 계산을 하지 않는다.

### Ward Fitness

목표:

* 생존 능력 평가

초기 필드:

* `score`
* `survival_score`
* `drawdown_avoidance`
* `warning_accuracy`

초기 버전은 규칙 기반이며 Ward의 최종 방어 판단을 대체하지 않는다.

### Hound Fitness

목표:

* 사냥 능력 평가

초기 필드:

* `score`
* `hit_rate`
* `forward_return_score`
* `target_accuracy`

초기 버전은 규칙 기반이며 실거래나 백테스트를 수행하지 않는다.

---

## 3. Fitness Report

FitnessReport 필드:

* `timestamp`
* `core`
* `ward`
* `hound`
* `overall_score`

초기 overall score는 가중 평균으로 계산한다.

```text
Core 40%
Ward 30%
Hound 30%
```

---

## 4. Registry

Fitness Registry는 LAB 결과를 비교하기 위한 기준점이다.

예:

```python
FITNESS_REGISTRY = {
    "whale_link_flow": {
        "core": 0.74,
        "ward": 0.82,
        "hound": 0.67,
    }
}
```

향후 비교 대상:

* Forecast V1
* Forecast V2
* Graph ML V1
* Graph ML V2

---

## 5. Implementation

구현 위치:

```text
research/fitness/
```

생성 파일:

* `fitness_schema.py`
* `core_fitness.py`
* `ward_fitness.py`
* `hound_fitness.py`
* `fitness_registry.py`
* `fitness_score.py`
* `fitness_pipeline.py`
* `test_fitness_pipeline.py`
* `README.md`

실행:

```bash
source .venv/bin/activate && python -B research/fitness/fitness_pipeline.py
source .venv/bin/activate && python -B research/fitness/test_fitness_pipeline.py
```

---

## 6. Absolute Prohibitions

* Lead Time 구현 금지
* Forecast 구현 금지
* Graph ML 구현 금지
* Whale ML 구현 금지
* DB 추가 금지
* FastAPI 추가 금지
* Dashboard 구현 금지
* 실제 Core 수정 금지
* 실제 Ward 수정 금지
* 실제 Hound 수정 금지
* 실거래 로직 추가 금지
* 백테스트 추가 금지

---

## 7. Final Definition

GrayMUG-LAB은 연구 결과를 생산하는 곳이 아니다.

GrayMUG-LAB은 Core의 판단력, Ward의 생존력, Hound의 사냥능력을 강화하는 훈련소다.

모든 연구는 최종적으로 BTC 수량 증가에 기여해야 한다.
