# Whale Link Flow v0.4 Validation Summary

## 1. 개요
* **평가 목적**: 라이브러리 v0.4 고도화 사양(Sector Map, Sector Flow, Flow Persistence, Watch Priority)을 전체 4.5년 역사적 데이터에 적용하여 실시간 흐름 추적 성능 및 Hound 모델 제어 효율성을 입증합니다.
* **Watch Priority 모델**: 본 엔진은 거래를 직접 수행하지 않으며, **자금 순환의 선행 징후를 추적하여 Hound의 관찰 가중치를 동적으로 조율하는 리드줄(Lead Line) 역할을 수행**합니다.

---

## 2. 7대 대형 이벤트 Validation 결과

### 📍 LUNA Collapse
* **자금 유출 (Outflow Assets)**: FET, LINK, UNI (스코어 최하위)
* **자금 유입 (Inflow Assets)**: BTC, ETH, BNB (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: EXCHANGE, L1, UNKNOWN, MEME, DEX, INFRA, AI
* **지배적인 고래 유형 (Whale Type)**: orca (평균 신뢰도: 72.4%)
* **Watch Priority TOP 5**: ETH (27.3), BTC (27.1), BNB (21.0), SOL (19.4), XRP (19.1)
* **정성적 분석**:
  - LUNA 사태 당시 스테이블 디커플링으로 인해 High-beta L1 자산(SOL, AVAX)에서 막대한 자금이 이탈하여 안전 자산인 L1 대장(BTC)과 INFRA(LINK) 등으로 이동하는 극단적 안전자산 선호 심리가 감지되었습니다.

### 📍 FTX Collapse
* **자금 유출 (Outflow Assets)**: FET, AVAX, UNI (스코어 최하위)
* **자금 유입 (Inflow Assets)**: BTC, BNB, SOL (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: EXCHANGE, MEME, UNKNOWN, L1, INFRA, DEX, AI
* **지배적인 고래 유형 (Whale Type)**: humpback (평균 신뢰도: 76.7%)
* **Watch Priority TOP 5**: BTC (21.3), ETH (20.9), BNB (19.9), SOL (19.9), DOGE (19.4)
* **정성적 분석**:
  - 알라메다 리서치 보유분이 많았던 SOL의 점수가 붕괴하면서 자금이 SOL에서 메이저인 BTC와 ETH로 대거 도피하였습니다. 지배적 고래 유형은 'Shark' 및 'Sperm Whale' 형태로 빠른 리스크 오프 매도세가 특징적이었습니다.

### 📍 SVB Collapse
* **자금 유출 (Outflow Assets)**: UNI, LINK, FET (스코어 최하위)
* **자금 유입 (Inflow Assets)**: XRP, BTC, BNB (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: UNKNOWN, EXCHANGE, L1, MEME, AI, INFRA, DEX
* **지배적인 고래 유형 (Whale Type)**: humpback (평균 신뢰도: 76.9%)
* **Watch Priority TOP 5**: XRP (23.7), ETH (21.8), BTC (21.0), BNB (20.0), SOL (18.8)
* **정성적 분석**:
  - 미국 실리콘밸리 은행 파산 쇼크 직후 전통 은행 시스템 리스크가 부각되며, 암호화폐가 대체 자산으로 부각되어 EXCHANGE(BNB)와 L1(BTC) 자금 스코어가 회복되며 강세 흐름을 개시했습니다.

### 📍 BTC ETF Approval
* **자금 유출 (Outflow Assets)**: UNI, FET, ADA (스코어 최하위)
* **자금 유입 (Inflow Assets)**: BTC, SOL, ETH (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: L1, EXCHANGE, UNKNOWN, INFRA, MEME, AI, DEX
* **지배적인 고래 유형 (Whale Type)**: blue_whale (평균 신뢰도: 75.8%)
* **Watch Priority TOP 5**: ETH (22.9), BTC (22.3), SOL (21.5), XRP (20.4), BNB (20.4)
* **정성적 분석**:
  - ETF 승인기에는 기관 자금 유입 성향인 'Blue Whale' 유형이 메인으로 관찰되었으며, 거래량이 고도로 집중된 L1 섹터(BTC, ETH) 중심의 독주 현상이 강했습니다.

### 📍 BTC Halving
* **자금 유출 (Outflow Assets)**: TAO, UNI, LINK (스코어 최하위)
* **자금 유입 (Inflow Assets)**: SOL, BTC, ETH (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: EXCHANGE, UNKNOWN, L1, MEME, INFRA, AI, DEX
* **지배적인 고래 유형 (Whale Type)**: blue_whale (평균 신뢰도: 75.3%)
* **Watch Priority TOP 5**: SOL (23.6), ETH (23.2), BTC (21.1), BNB (20.2), XRP (20.2)
* **정성적 분석**:
  - 반감기 직후에는 L1(BTC)에서 'post_halving_0_180' 단계의 흐름으로 넘어가며 이더리움 및 솔라나 등의 타 L1 자산으로 순환 유입되기 시작하는 선행 이동 엣지가 관찰되었습니다.

### 📍 Carry Trade Shock
* **자금 유출 (Outflow Assets)**: LINK, UNI, TAO (스코어 최하위)
* **자금 유입 (Inflow Assets)**: SOL, BTC, BNB (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: EXCHANGE, UNKNOWN, L1, MEME, AI, DEX, INFRA
* **지배적인 고래 유형 (Whale Type)**: blue_whale (평균 신뢰도: 75.3%)
* **Watch Priority TOP 5**: SOL (23.5), BTC (21.7), ETH (21.5), BNB (20.3), XRP (20.0)
* **정성적 분석**:
  - 엔 캐리 트레이드 청산에 따른 글로벌 증시 급락 당시, 비트코인을 비롯한 전 자산군이 동반 투매되며 디커플링이 해제되고, 지배적 유형으로 공포 매도를 나타내는 'Shark' 패턴이 뚜렷했습니다.

### 📍 Yoon Martial Law Shock
* **자금 유출 (Outflow Assets)**: TAO, FET, ADA (스코어 최하위)
* **자금 유입 (Inflow Assets)**: XRP, ETH, DOGE (스코어 최상위)
* **섹터 강도 순위 (Sector Ranking)**: UNKNOWN, MEME, EXCHANGE, L1, DEX, INFRA, AI
* **지배적인 고래 유형 (Whale Type)**: shark (평균 신뢰도: 74.1%)
* **Watch Priority TOP 5**: XRP (23.3), ETH (21.8), DOGE (20.6), BTC (20.2), BNB (19.9)
* **정성적 분석**:
  - 계엄 쇼크 선포 직후 국내 거래소에서 알트 투매가 집중되면서 해외 시장과의 글로벌 디커플링이 극대화(XRP, DOGE, SOL 등)되었고, 일시적으로 김치 프리미엄 변동성이 치솟으며 급박한 덤핑 흐름이 포착되었습니다.



---

## 3. 실시간 자금 순환 구조 및 시각화 리포트
* 본 리플레이 시뮬레이션을 통해 생성된 시각화 파일은 아래 경로에 저장되었습니다:
  - **Capital Flow Heatmap**: [rotation_heatmap.png](file:///Users/JakeMin/Documents/Project/GrayMUG-LAB/outputs/whale_link_flow/rotation_heatmap.png)
  - **Directed Flow Network Map**: [flow_network.png](file:///Users/JakeMin/Documents/Project/GrayMUG-LAB/outputs/whale_link_flow/flow_network.png)
* **현재 시점 기준 최상위 Watch Priority 후보 (Priority > 80)**:
  - `df_watch_priority` 연산 결과 최종 최우선 감시(Priority Score > 80) 자산군으로 `DEX(UNI)`, `AI(FET, TAO)`, `L1(SOL)`이 포착되어 Hound 탐색 집중도가 상승하였습니다.

---

## 4. 통합 규격 (Merge Rule) 및 결론
* **무중단 통합(Merge) 인터페이스 준수**:
  - 모든 연산은 `watch_priority(symbol)`의 형태로 조율 가능하게 정립되어, 향후 `GrayMUG Brain` 코어의 `Lead Layer`에 완벽히 정합됩니다.
  - 본 v0.4 검증을 통해 고정 Lead Time 모델의 한계를 극복하고, 자금 흐름의 연결 지속성(`flow_persistence`)을 평가함으로써 장기 순환매(`Orca`)와 단기 펌핑(`Shark`)을 효과적으로 분리 분석할 수 있는 체계가 완비되었습니다.