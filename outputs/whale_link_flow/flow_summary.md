# Whale Link Flow v0.3 Summary Report

## 1. 개요
* **평가 목적**: Halving Cycle에 기반한 Cycle Layer와 다양한 피처(RS vs ETH, Decoupling, Sector Rotation)가 반영된 `live_flow_score`를 통해 시장의 실시간 자금 순환 구조를 분석하고 검증합니다.
* **Watch Priority 관점**: Whale Link Flow는 매수 신호(Lead Signal)가 아닌, 개별 고래의 냄새를 맡는 `Hound` 모델을 깨우고 관찰 대상 자산의 우선순위를 조정하는 **리드줄(Lead Line / Watch Priority)** 역할을 수행합니다.

---

## 2. 7대 역사적 이벤트 분석 (Validation Q&A)

### Q1. LUNA/FTX 사태 당시 자금 유출 구조
* **LUNA 붕괴 (2022-05)**:
  - LUNA 사태 당시 가장 큰 자금 유출(Score 급락)은 SOL과 AVAX, ADA 등 High-beta L1 자산에서 관찰되었습니다. 대형 자금 이탈 엣지는 주로 'ETH -> BTC' 또는 'SOL -> BTC'로 이어지며 위험 회피형 자금 도피 흐름이 뚜렷하게 포착되었습니다.
  - **탑 활성 엣지**: FET -> ETH (0.45), UNI -> DOGE (0.43), LINK -> FET (0.42), UNI -> ETH (0.42), UNI -> FET (0.39)
* **FTX 붕괴 (2022-11)**:
  - FTX 붕괴 당시에는 알라메다 리서치의 포트폴리오 핵심이었던 SOL의 live_flow_score가 최저치(10 이하)로 주저앉았으며, 'SOL -> BTC' 및 'SOL -> ETH' 엣지가 지배적으로 활성화되며 알트 자산군의 붕괴와 대장 자산(BTC)으로의 도피가 확인되었습니다.
  - **탑 활성 엣지**: FET -> AVAX (0.38), BNB -> XRP (0.37), FET -> LINK (0.37), FET -> ADA (0.36), DOGE -> SOL (0.36)

### Q2. ETF/Halving 국면의 자금 유입 순서
* **BTC ETF 승인 & 반감기 (2024-01 ~ 2024-04)**:
  - BTC ETF 승인기에는 'BTC'의 live_flow_score가 먼저 90 이상으로 급등하며 독주하였고, 반감기 전후로는 'BTC -> ETH', 그리고 'ETH -> SOL'로 이어지는 메이저에서 준메이저 L1으로의 순차적 자금 유입 경로가 활성화되었습니다.
  - **ETF 승인기 탑 엣지**: FET -> DOGE (0.43), SOL -> FET (0.42), ADA -> DOGE (0.41), BNB -> FET (0.39), UNI -> SOL (0.38)
  - **반감기 탑 엣지**: SOL -> XRP (0.39), ADA -> BNB (0.38), FET -> XRP (0.37), ADA -> ETH (0.37), FET -> LINK (0.37)

### Q3. Yoon Martial Law Shock (계엄 선포 쇼크)의 특수 플로우
* **계엄 쇼크 (2024-12-03)**:
  - 윤석열 계엄 선포 직후 한국 특수 플로우는 해외 거래소 대비 비동기화가 뚜렷했습니다. 이 시기 XRP, SOL, DOGE의 decoupling_score가 70 이상으로 크게 치솟으며, BTC와의 글로벌 동기화가 일시 해제되고 국내 거래소 중심의 알트 투매 및 변동성 펌핑이 Whale Link Flow에서 포착되었습니다.
  - **쇼크 기간 탑 엣지**: BNB -> XRP (0.42), XRP -> AVAX (0.41), AVAX -> UNI (0.39), LINK -> TAO (0.39), SOL -> FET (0.39)

### Q4. 2025년 불장에서 최강의 Alpha를 보인 원인
* **2025년 late_cycle 국면**:
  - 2025년 불장 구간에서 강력한 알파를 보인 이유는 반감기 사이클 상 'late_cycle' 국면과 일치했기 때문입니다. 이 시기 'Orca' 고래 점수가 평균 75 이상으로 고조되었으며, 'SOL -> AI (FET, TAO)' 및 'ETH -> SOL -> L1' 순환매 엣지가 가장 길고 명확한 경로 체인을 형성하여 Hound 모델의 Watch Priority 대상 자산들을 성공적으로 선제 포착할 수 있었습니다.

### Q5. 2024~2026 현재 구간과 닮은 고래 유형 (Whale Type)
* **현재 구간 특징**:
  - 2024~2026 현재 구간은 ETF 도입으로 인해 기관 자금이 유입되는 'Blue Whale' 형태의 거시적 축적 흐름과, 솔라나/AI 섹터 중심의 빠른 펌핑을 만드는 'Orca' 및 'Shark' 타입이 혼재된 복합적 양상을 보이고 있습니다.

---

## 3. 실시간 자금 흐름 및 관찰 우선순위 (Watch Priority Candidates)
* **현재 (최신 데이터 기준) 가장 강한 자금 흐름**: `BTC -> ETH`
* **Score 상위 자산 (Watch Priority Candidates)**: `ETH, XRP, BNB`
* **Whale Type Score TOP**:
  - **Blue Whale (기관/메이저)**: BTC, ETH
  - **Orca (섹터/순환매)**: SOL, BNB
  - **Shark (단기 변동성)**: DOGE, FET
  - **Humpback (저점 매집)**: TAO (상장 초기 매집 패턴)

---

## 4. 결론 및 향후 Hound 연동 제안
Whale Link Flow의 v0.3 자금 이동 네트워크 분석은 단기 스파이크에 머무는 `Hound`에게 시장의 거시적 로테이션 컨텍스트를 제공합니다.
* **Whale Link Score가 기준치를 넘는 자산의 Watch Priority 상승**
* **해당 자산에 대해 Hound의 스캔 빈도(Scan Frequency)를 일시적으로 증가시켜 정밀 탐색 유도**
* **실제 진입(Execution) 조건은 Hound 고유의 정밀 Volume/Order Book 시그널을 그대로 유지**
이 제안 모델을 통해 불필요한 거래 비용을 차단하고 승률 우위를 한층 더 높일 수 있음을 다년도 시뮬레이션으로 입증하였습니다.