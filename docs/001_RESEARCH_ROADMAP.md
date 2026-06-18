# GrayMUG-LAB Research Roadmap

본 로드맵은 실거래 코드 수정 없이 오직 연구 목적으로 시장에서 고래의 흔적(Footprint)을 사전에 발굴하고 프로토타이핑하는 단계적 계획입니다.

---

## Phase 1: UNI Case Study
* **핵심 질문**: "고래가 발견된 시점" vs "고래가 실제로 작업을 개시한 시점"의 차이를 정의하고 포착할 수 있는가?
* **연구 대상**: Uniswap (UNI) 토큰 거래량 급증(Volume Spike) 이전의 선행 징후 탐색.
* **주요 탐색 지표 후보**:
  1. **Price Slope**: 가격 변화 기울기의 미세한 상승 추세 전환.
  2. **Volume Slope**: 거래량 누적 변화 추이의 기울기 가속화.
  3. **Rank Momentum**: 주요 시장참여자들의 거래 대금/거래 횟수 순위 모멘텀.
  4. **Relative Strength**: 전체 시장 대비 UNI의 상대적 강세 지표.

---

## Phase 2: Historical Event Dataset
* **목표**: 고래들이 급격한 포지션 조정이나 작업을 수행하는 역사적인 블랙스완/이벤트 시점의 원본 데이터를 구축하고 분석.
* **주요 역사적 이벤트**:
  * **LUNA Collapse**: 테라-루나 사태 및 알고리즘 스테이블코인 붕괴 전후.
  * **FTX Collapse**: FTX 거래소 파산 선언에 따른 시장 패닉 전후.
  * **SVB Collapse**: 실리콘밸리은행 파산에 따른 금융 불안 및 스테이블코인 디페깅 전후.
  * **BTC ETF Approval**: 비트코인 현물 ETF 승인 전후의 자금 유입 및 고래 포지션 변동.
  * **BTC Halving**: 반감기 전후의 채굴자 및 장기 보유자 거동 분석.
  * **Yoon Martial Law Shock**: 대한민국 비상계엄 선포에 따른 김치 프리미엄 변동 및 국내 거래소 투매 현상 분석.
  * **Carry Trade Shock**: 엔 캐리 트레이드 청산 우려로 인한 글로벌 자산 급락 및 암호화폐 시장 반응.

---

## Phase 3: Regime Similarity Engine
* **목표**: 현재의 시장 상황(변동성, 거래량, 가격 흐름, 오더북 상태 등)이 과거 역사적 시점 중 어느 시기와 가장 유사한지 실시간으로 비교 분석하는 엔진 구축.
* **핵심 알고리즘**:
  * 다차원 시계열 피처 추출 및 거리 측정 (Dynamic Time Warping, Cosine Similarity 등).
  * 국면 분류(Regime Classification) 모델 구축.

---

## Phase 4: Whale Lifecycle Model
* **목표**: 고래의 전체 자금 집행 주기를 모형화하여 각 단계별 진입과 이탈 시점을 탐지.
* **4단계 생애주기**:
  1. **Accumulation (매집)**: 조용한 자금 유입, 오더북 압박 최소화, 거래량의 미세 변화.
  2. **Expansion (확장/발산)**: 본격적인 가격 상승 유도, 리테일 참여 유도, Vol Spike 시작.
  3. **Distribution (분산/차익실현)**: 고점에서의 물량 분산, 대량 거래량 동반, 호가 지지선 구축.
  4. **Exit (이탈/정리)**: 포지션 청산 완료 또는 쇼트 헤징 완료 후 급락 유도.
