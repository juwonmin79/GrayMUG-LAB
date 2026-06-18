# WhaleLab-005-F: Execution Guidance API

* **작성일**: 2026-06-18
* **기준 단계**: WhaleLab-005-F
* **목적**: Hound가 타겟을 탐지했을 때 LAB이 건별 Execution Guidance를 생성한다.

---

## 1. Definition

Execution Guidance는 실거래 로직이 아니다.

Execution Guidance는 Core / Ward / Hound가 참고할 수 있는 실행 가이드다.

최종 진입/청산 판단은 엔진 또는 사용자에게 있다.

LAB은 `BUY` 또는 `SELL` 명령을 내리지 않는다.

---

## 2. Guidance Components

LAB이 제공하는 항목:

* Pattern Hint
* Entry Style
* TP Case
* SL Case
* Exit Trigger

Execution Guidance는 기존 Hound의 탐지 결과를 구조화된 형태로 설명하는 Layer이다.

---

## 3. Pattern Hints

초기 패턴:

* `SLOW_CREEP`
* `SHOCK_PUMP`
* `DISTRIBUTION_RISK`
* `CHAIN_ROTATION`
* `BTC_HIDE`

초기 버전은 규칙 기반이다.

실제 ML은 구현하지 않는다.

---

## 4. Entry Guidance

초기 entry style:

* `ALLOW`
* `WAIT_CONFIRMATION`
* `AVOID`

진입 비율 계산, 자동 주문, 실거래 실행은 하지 않는다.

---

## 5. TP / SL Templates

초기 case:

* Case A: TP 5%, SL 3%
* Case B: TP 10%, SL 5%
* Case C: TP Dynamic, SL Dynamic

현재 단계에서는 템플릿만 제공한다.

---

## 6. Exit Triggers

초기 trigger:

* `WARD_RISK_UP`
* `BTC_HIDE`
* `DISTRIBUTION_SPIKE`
* `LEAD_LINE_BREAK`

Exit Trigger는 청산 명령이 아니다.

---

## 7. Implementation

구현 위치:

```text
research/execution/
```

생성 파일:

* `execution_schema.py`
* `pattern_classifier.py`
* `entry_guidance.py`
* `tp_sl_guidance.py`
* `exit_guidance.py`
* `execution_builder.py`
* `execution_pipeline.py`
* `test_execution_pipeline.py`
* `README.md`

실행:

```bash
source .venv/bin/activate && python -B research/execution/execution_pipeline.py
source .venv/bin/activate && python -B research/execution/test_execution_pipeline.py
```

---

## 8. Absolute Prohibitions

* Forecast 구현 금지
* Graph ML 구현 금지
* Whale ML 구현 금지
* DB 추가 금지
* FastAPI 추가 금지
* Dashboard 추가 금지
* 실제 Core 수정 금지
* 실제 Ward 수정 금지
* 실제 Hound 수정 금지
* 실거래 실행 금지
* 자동 주문 금지
* 포지션 관리 금지

---

## 9. Final Definition

WhaleLab은 무엇을 살지 예측하는 연구소가 아니다.

WhaleLab은 언제 조심해야 하는지, 언제 욕심내지 말아야 하는지, 언제 빠르게 도망가야 하는지를 Core / Ward / Hound에 알려주는 연구소다.

Execution Guidance는 거래 전략을 생성하는 시스템이 아니다.

Execution Guidance는 기존 Hound의 탐지 결과를 구조화된 형태로 설명하는 Layer이다.
