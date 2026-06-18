# GrayMUG-LAB Project Charter

## 1. Mission
* **최종 목표**: BTC 20개 축적
* **핵심 과제**: 고래 행동 연구를 통해 일반적인 "고래가 펌핑을 시작한 시점"이 아닌, **"고래가 작업을 시작한 시점(Whale Activity Inception Point)"**을 포착하는 연구 환경을 구축한다.

---

## 2. Research Target (고래 행동 연구)

### A. Mirror Pattern
* 고래의 지갑 이동, 특정 계좌 간의 연쇄 이체 패턴 및 자산 흐름 분석.
* 온체인 거래의 거울상(Mirroring)을 추적하여 실거래에 매칭할 수 있는 프록시 지표 발굴.

### B. Micro Pattern (Minute-level Whale Footprint)
* 분 단위(Minute-level) 오더북 및 거래량 변화 속에서 고래가 흔적을 남기는 미시적 패턴 분석.
* 체결 강도 변화, 호가창 잔량의 불균형, 순간적인 체결 속도(Velocity)의 비정상적 변화 연구.

### C. Macro Pattern (Event/Regime Footprint)
* 거시적 이벤트(Event) 및 시장 국면(Regime)별 고래의 포지션 전환과 매집/분산 양상 분석.
* 시장의 대전환기(예: 규제 변화, 해킹, 블랙스완 등) 전후에 나타나는 고래들의 거동 탐색.

---

## 3. Operations Pipeline & Rules
* **직행 금지**: Research 단계에서 개발된 모델이나 전략은 절대로 Production(Hound/Core/Ward) 환경에 직행할 수 없다.
* **프로세스**: 
  $$\text{Research} \longrightarrow \text{Validation} \longrightarrow \text{Production}$$
  반드시 충분한 백테스트 및 검증(Validation) 단계를 거쳐 단계별 승인을 획득해야만 실거래에 편입한다.
