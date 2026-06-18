# GrayMUG Development Rules

* **작성일**: 2026-06-18
* **범위**: GrayMUG-LAB 연구, 백테스트, 검증, Production 편입 전 단계
* **목적**: 프로젝트가 커져도 Hound/Core/Ward 안전성, 검증 절차, 데이터 무결성을 유지하기 위한 개발 규칙을 고정한다.

---

## Rule 1. Hound는 직접 수정 금지

GrayMUG-LAB에서 Hound, Core, Ward Production 코드를 직접 수정하지 않는다.

허용되는 작업:
* 오프라인 리서치
* 백테스트
* 검증 리포트 작성
* 제한된 인터페이스 제안
* Production 편입 전 설정값 또는 파라미터 후보 산출

금지되는 작업:
* LAB 코드에서 Production DB, 공유 메모리, 실거래 상태 직접 접근
* 검증되지 않은 모델의 Hound 직접 병합
* 리서치 중 실거래 로직 변경

---

## Rule 2. Whale Link Flow는 Lead Line 역할

Whale Link Flow는 거래를 직접 수행하지 않는다.

역할:
* 자금 순환의 선행 징후 추적
* 섹터별 유입/유출 강도 계산
* Flow Persistence 측정
* Whale Type 분류
* Hound 관찰 가중치 조절

표준 출력:

```text
watch_priority(symbol)
```

이 출력은 매수/매도 명령이 아니라 Hound의 관찰 우선순위 보정값이다.

---

## Rule 3. 모든 모듈은 Input -> Score -> Priority 인터페이스 유지

GrayMUG 계층은 가능한 한 다음 형태를 유지한다.

```text
Input
  |
  v
Score
  |
  v
Priority
```

### Input
* 가격
* 거래량
* Rank
* Relative Strength
* RS vs BTC Decoupling
* 섹터 맵
* 이벤트/국면 정보

### Score
* Rank Momentum
* Sector Flow Score
* Flow Persistence Score
* Whale Type Confidence
* Watch Priority Score

### Priority
* Hound 관찰 강화 대상
* 백테스트 후보
* 검증 우선순위
* Production 편입 후보

모듈이 직접 Trade Signal을 생성해야 하는 경우에는 별도 Production 설계와 검증 문서가 필요하다.

---

## Rule 4. BTC 기준 성과 측정

성과는 단순 USD 수익률만으로 판단하지 않는다.

기본 기준:
* BTC 대비 초과 성과
* BTC 대비 상대 강도
* BTC 하락장/횡보장/상승장별 성과
* BTC 보유 대비 리스크 조정 성과

GrayMUG의 최종 목표가 BTC 축적이므로, 모델의 유효성은 "BTC를 더 많이 쌓는 데 도움이 되는가"를 기준으로 평가한다.

---

## Rule 5. Look-ahead Bias 금지

어떤 백테스트나 리서치도 미래 데이터를 현재 시점 판단에 사용해서는 안 된다.

금지 예시:
* 이벤트 이후 확정된 고점/저점을 이용해 Inception을 역산
* Detection 이후의 거래량 피크를 기준으로 과거 시점 신호를 선택
* 전체 기간의 평균/표준편차를 현재 시점 피처 계산에 사용
* 결과를 알고 난 뒤 임계값을 사후 조정하고 검증으로 주장

필수 원칙:
* 모든 피처는 해당 캔들 시점에 실제로 알 수 있었던 데이터만 사용한다.
* 롤링 윈도우는 현재 시점 이전 데이터로만 계산한다.
* Detection 이후 데이터로 Inception을 고정하지 않는다.

---

## Rule 6. Pre-listing 데이터 사용 금지

상장 전 데이터, 거래 불가능 데이터, 사후 보정된 합성 데이터는 실거래 검증에 사용하지 않는다.

금지 예시:
* 거래소 상장 전 가격 시계열 사용
* 실제 체결 불가능한 인덱스 가격 사용
* 상장 전 거래량을 0으로 채운 뒤 모멘텀 계산
* 유동성 없는 기간을 정상 거래 가능 구간으로 취급

필수 원칙:
* 자산별 실제 거래 가능 시작 시점을 명시한다.
* 상장 초기 저유동성 구간은 별도 필터링하거나 위험 플래그를 부여한다.
* 섹터 비교 시 상장 기간 차이를 보정한다.

---

## Rule 7. 고정 Lead Time 가설 사용 금지

기존 "평균 22.61시간 Lead Time" 가설은 폐기한다.

검증 결과:
* 24시간 탐색 윈도우에서 평균 22.98시간
* 48시간 탐색 윈도우에서 평균 43.38시간
* Lead Time은 고래의 물리적 자금 집행 주기가 아니라 역방향 탐색 윈도우에 종속된 알고리즘 편향으로 판정됨

대체 원칙:
* 고정 시간차가 아니라 누적 개선 흐름을 탐지한다.
* Rank Momentum, RS vs BTC Decoupling, Sector Flow, Flow Persistence를 함께 본다.
* 단일 캔들 임계값 통과를 Inception으로 확정하지 않는다.

---

## Rule 8. 단일 프레임 노이즈를 신호로 확정하지 않음

Rank가 한 캔들에서 임계값을 스쳐 지나가는 현상은 신호가 아니라 노이즈일 수 있다.

신호 후보가 되려면 최소한 다음 중 복수 조건을 만족해야 한다.

* Rank Momentum 1h 개선
* Rank Momentum 2h 개선
* RS vs BTC Decoupling 강화
* Sector Flow 동행
* Flow Persistence 유지
* Whale Type Confidence 상승

---

## Rule 9. Research -> Backtest -> Validation -> Production 순서 준수

모든 전략, 피처, 모델은 아래 순서를 통과해야 한다.

```text
Research -> Backtest -> Validation -> Production
```

Production 편입 전 필수 조건:
* 역사 데이터 검증
* 수수료/슬리피지/호가창 두께 반영
* Bull, Bear, Sideways 시장별 테스트
* 최소 2주 이상 Paper Trading / Dry Run
* Tracking Error 분석
* Production 초기 자금 제한

---

## Rule 10. 문서가 코드보다 우선하는 상태를 유지

GrayMUG-LAB의 핵심 연구 방향, 폐기된 가설, 검증된 인터페이스는 문서에 먼저 고정한다.

문서화 대상:
* 새 가설
* 폐기된 가설
* 검증 리포트
* Production 편입 규칙
* 모듈 책임
* 데이터 사용 제한
* 현재 프로젝트 상태

프로젝트 담당자, AI 모델, 개발 세션이 바뀌어도 `docs/000~006`만 읽으면 현재 상태를 복구할 수 있어야 한다.

---

## Rule 11. WhaleLab-005 엔진 책임 경계 유지

WhaleLab-005 기준 엔진 책임은 다음과 같이 고정한다.

* Core는 BTC를 모은다.
* Ward는 살아남게 한다.
* Hound는 알트를 사냥한다.
* Whale Link Flow는 세 엔진을 연결한다.
* 모든 결과는 BTC 수량 증가로 환류된다.

절대 금지:

* 고정 Lead Time 가설 부활 금지
* Hound 내부 수정 금지
* Ward 내부 판단 로직 침범 금지
* Core 전략 판단을 Whale Link Flow 안에 삽입 금지

Whale Link Flow는 Core / Hound / Ward가 공통으로 소비하는 Lead Line API Socket을 제공할 뿐이며, 특정 엔진의 내부 판단을 대체하지 않는다.

---

## Rule 12. Target Feed는 반드시 단일 엔진에 귀속

WhaleLab-005-C 이후 모든 Feed는 Core / Ward / Hound 중 하나에 명확히 귀속되어야 한다.

* Core Feed는 BTC 축적 판단만 보조한다.
* Ward Feed는 생존/방어 판단만 보조한다.
* Hound Feed는 알트 사냥 타겟 지정만 보조한다.

금지:

* 재미있는 지표라는 이유만으로 Feed 추가 금지
* 한 Feed가 여러 엔진 판단을 동시에 대체하는 구조 금지
* LAB이 최종 매수/매도, 방어, 감지 판단을 수행하는 구조 금지

모든 Feed는 "이 지표가 어느 엔진의 어떤 판단을 더 정확하게 만드는가?"라는 질문을 통과해야 한다.

---

## Rule 13. 연구 성과는 Engine Fitness로 측정

GrayMUG-LAB의 연구 성과는 지표 개수로 평가하지 않는다.

평가 기준:

* Core 판단력 향상
* Ward 생존력 향상
* Hound 사냥능력 향상
* BTC 수량 증가 기여도

WhaleLab-005-D 이후 모든 주요 연구 산출물은 Core Fitness, Ward Fitness, Hound Fitness 중 어디를 개선하는지 설명할 수 있어야 한다.

금지:

* Fitness 계산을 실거래 로직으로 확장 금지
* Fitness 계산을 백테스트로 위장 금지
* Fitness 점수를 최종 매수/매도 판단으로 사용 금지

---

## Rule 14. LAB 신호는 Calibration 이후에만 적용 가능

LAB 지표는 강할수록 좋은 것이 아니다.

모든 LAB 신호는 엔진에 전달되기 전에 다음 값을 가져야 한다.

* signal_strength
* confidence
* application_scope
* max_influence
* final_weight

엔진별 최대 영향도:

* Core: `0.20`
* Ward: `0.15`
* Hound: `0.30`

금지:

* Hound 감지 로직 대체 금지
* Ward 방어 판단 대체 금지
* Core 전략 판단 대체 금지
* forbidden scope를 application scope로 사용 금지

LAB은 엔진의 핸들을 빼앗지 않는다. LAB은 신호 강도, 신뢰도, 적용 범위를 조정해 판단 보조값만 제공한다.

---

## Rule 15. Execution Guidance는 거래 명령이 아님

Execution Guidance는 Hound target 발견 후 구조화된 참고 가이드를 제공한다.

제공 가능:

* Pattern Hint
* Entry Style
* TP Case
* SL Case
* Exit Trigger

금지:

* 실거래 실행 금지
* 자동 주문 금지
* 포지션 관리 금지
* 최종 진입/청산 판단 대체 금지
* `BUY` / `SELL` 명령 생성 금지

Execution Guidance는 기존 Hound의 탐지 결과를 설명하는 Layer이며 거래 전략 생성 시스템이 아니다.
