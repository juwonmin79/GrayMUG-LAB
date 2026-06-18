# GrayMUG Integration Rules (GrayMUG-LAB 검증 및 편입 규칙)

본 문서는 GrayMUG-LAB(연구소)에서 진행된 연구 결과물이 실제 프로덕션 환경(Hound/Core/Ward)에 안전하고 신뢰할 수 있게 편입되기 위한 규칙을 정의합니다.

---

## 1. Sandbox Isolation (샌드박스 절대 격리)
* **Research Only**: GrayMUG-LAB은 순수 오프라인/리서치 및 백테스트 샌드박스입니다.
* **실거래 코드 수정 금지**: 리서치 과정에서 어떠한 경우에도 `GrayMUG Production` (Hound, Core, Ward) 코드를 직접 수정하거나 공유 메모리/DB를 침범해서는 안 됩니다.

---

## 2. Integration Pipeline (4단계 편입 파이프라인)

GrayMUG-LAB에서 발굴한 알고리즘이나 피처가 프로덕션에 적용되기 위해서는 반드시 아래의 4단계 파이프라인을 거쳐야 합니다.

```
[ Research ] ──> [ Backtest ] ──> [ Validation ] ──> [ Production ]
```

### 1단계: Research (연구)
* 아이디어 제안 및 가설 검증.
* 오프라인 역사 데이터(Historical Dataset)를 통한 피처 유효성 입증.
* 탐색 대상: 가격/거래량 슬로프, 랭크 모멘텀, 상대 강도 등.

### 2단계: Backtest (백테스트)
* 수수료, 슬리피지, 호가창 두께를 반영한 백테스트 시뮬레이션 수행.
* 과최적화(Overfitting) 여부 판정 및 다양한 시장 상황(Bull, Bear, Sideways)에서의 성과 리포트 작성.

### 3단계: Validation (포워드 테스트 및 검증)
* **Paper Trading / Dry Run**: 실시간 데이터 스트림을 사용하여 모의 거래 환경에서 2주 이상 실행.
* 실시간 데이터 지연(Latency) 및 API 제한 환경에서의 정상 작동 여부 검증.
* 백테스트 성과와 모의 거래 성과의 괴리율(Tracking Error) 분석.

### 4단계: Production (실거래 편입)
* 검증이 완전히 통과된 피처 또는 모델 파라미터를 GrayMUG Production(Hound/Core/Ward) 환경의 설정으로 편입.
* 초기 진입 자금은 소액으로 제한하며 점진적으로 한도 상향.
