# Whale Link Flow (WhaleLab-003)

고래의 개별 트레이드 스파이크(Volume Spike)를 탐지하는 기존의 `Hound` 방식에서 나아가, 고래 자금이 시장 내에서 어떻게 회전하며 이동하는지(Capital Rotation & Sector Flow) 추적하고 이를 노드와 엣지로 이루어진 그래프 형태로 모델링하는 리서치 프로젝트입니다.

---

## 🏗️ 시스템 아키텍처

```
[ Raw Flow Dataset ] 
        │
        ▼
[ Feature Builder ] ──> RS vs BTC, Volume Rank, Rank Momentum, Price/Vol Slope, Vol Expansion
        │
        ▼
[ Scoring Engine ]  ──> Node Whale Link Score (0 - 100)
        │
        ▼
[ Flow Graph Builder ] ──> Cross-Asset Lead-Lag Correlation & Relative Strength Rotation Matrix
        │
        ▼
[ Path Finder / Alert ] ──> Whale Link Rotation Alert Output (e.g., BTC -> ETH -> SOL -> FET)
```

---

## 🧮 수학적 설계 및 모델링

### 1. Whale Link Score (노드 점수)
개별 자산의 고래 자금 밀집도를 0~100 사이의 점수로 환산합니다:
* **Volume Rank (40%)**: 동시간대 12대 자산 중 거래량 순위. 1위는 40점, 2-3위는 35점, 4-6위는 25점 등.
* **Rank Momentum (20%)**: 1시간 동안의 Volume Rank 개선 속도 ($\text{Rank}_{t-k} - \text{Rank}_t$).
* **RS vs BTC Z-Score (15%)**: BTC 대비 상대적 강도 지표의 24시간 롤링 Z-Score.
* **Volatility Expansion (15%)**: 1시간 롤링 변동성 대비 24시간 평균 변동성의 확장 비율.
* **Price Slope (10%)**: 가격의 1.5시간 선형 회귀 기울기.

### 2. Capital Flow Edge Weight (엣지 가중치)
자산 $X$에서 자산 $Y$로의 자금 이동 가능성 $Weight(X \to Y)$을 계산합니다:
* **Lead-Lag Cross-Correlation**:
  $X$의 1시간 전 Rank Momentum $RM_X(t-\tau)$와 $Y$의 현재 Rank Momentum $RM_Y(t)$ 간의 교차 상관 계수를 계산하여 자금 이동 선행성($X$가 먼저 개선되고 $Y$가 나중에 개선됨)을 탐지합니다.
  $$W_{corr} = \max_{\tau \in [1, 4]} Corr(RM_X(t-\tau), RM_Y(t))$$
* **Relative Strength Divergence (Rotation Factor)**:
  $X$의 상대강도가 감소하는 동시에 $Y$의 상대강도가 증가하며 $Y$의 거래량이 상승하는 경우 회전 가중치 $W_{rot}$를 0.5로 부여합니다.
* **Combined Flow Probability**:
  $$Weight(X \to Y) = 0.7 \cdot W_{corr} + 0.3 \cdot W_{rot}$$
  가중치가 임계값(Default: 0.35) 이상인 경우 활성화된 Directed Edge로 그래프에 연결됩니다.

---

## 📁 파일 구조 및 설명
* `schemas.py`: `AssetFeatures`, `FlowEdge`, `FlowGraphState`, `WhaleLinkAlert` 등의 데이터 스키마 정의.
* `feature_builder.py`: 15분/1시간 단위 캔들로부터 6가지 핵심 피처 계산.
* `scoring.py`: 자산별 고래 점수(Whale Link Score) 계산.
* `flow_graph.py`: 교차 상관 관계 및 로테이션 지표에 기반한 인접 행렬 생성 및 DFS 기반 자금 이동 경로 탐색.
* `flow_engine.py`: 전체 파이프라인 조율 및 시뮬레이션 엔진.
* `examples/run_replay.py`: 실데이터를 입력받아 역사적 자금 이동(예: majors -> alt 로테이션)을 리플레이하고 시각화하는 실행 예제.
