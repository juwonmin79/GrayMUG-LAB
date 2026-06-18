# GrayMUG-LAB

GrayMUG-LAB is the research and validation sandbox for GrayMUG. Its purpose is to study whale behavior, capital rotation, and market regime changes before any idea is allowed to influence the production GrayMUG Core.

This repository is documentation-first and validation-first. It does not treat a backtest result as a trading signal until the hypothesis has survived falsification, replay, and integration review.

---

## 1. Project Vision

GrayMUG exists to accumulate BTC over market cycles. The project is built around the idea that the market should be understood as layered flows rather than isolated price spikes.

Core philosophy:

* **BTC Accumulation First**: every model is ultimately judged by whether it helps accumulate more BTC, not whether it only produces USD-denominated returns.
* **BTC Count is the Final Metric**: GrayMUG does not optimize for USDT return first. Every strategy ultimately rolls back into BTC quantity.
* **Halving Cycle is the Macro Season**: the BTC halving cycle defines the long macro season and the broad background regime.
* **Whale Link Flow is the Live Capital Current**: while the halving cycle defines the season, Whale Link Flow tracks the live movement of capital across assets and sectors.
* **Hound is Detection**: Hound remains the detection and observation layer.
* **Whale Link Flow is Lead Line**: Whale Link Flow does not trade directly. It guides where Hound should look harder.

The current research direction is clear: GrayMUG should not guess a whale's inception point from a fixed time offset. It should track whether multiple live signals are improving together.

---

## 2. Current Architecture

```text
GrayMUG
|
+-- Hound
|   `-- Whale detection and observation layer
|
+-- Ward
|   `-- Risk monitoring and safety layer
|
+-- Whale Link Flow
|   |-- Cycle Layer
|   |-- Live Flow Layer
|   |-- Link Graph Layer
|   |-- Sector Flow
|   |-- Persistence
|   `-- Whale Type Classifier
|
+-- Watch Priority
|   `-- Hound observation weighting
|
+-- Event Replay
|   `-- Historical validation and replay analysis
|
`-- Future ML Core
    |-- Adaptive Whale Profile
    |-- Sector ML
    `-- Flow Forecast Layer
```

### Hound

Hound is the alt hunting engine. It tracks the Lead Line, searches for alt opportunities, and captures rotation returns. Hound only consumes the universe provided by Lead Line API Socket. GrayMUG-LAB must not directly modify Hound or its detection logic.

### Ward

Ward is the survival engine. It monitors market risk, evaluates defensive context, and keeps final defense decisions independent.

### Core

Core is the BTC mainline engine. It judges market regime, selects strategy mode, and keeps the system pointed toward BTC accumulation.

Supported Core modes:

* `BEAR_ESCAPE`
* `BTC_ACCUMULATION`
* `OBSERVE_ONLY`

### Whale Link Flow

Whale Link Flow tracks live capital movement across assets and sectors. It combines cycle context, live flow scores, link graph structure, sector rotation, persistence, and whale type classification.

It is not a trade engine. Its role is to produce a stronger observation map for Hound.

### Watch Priority

Watch Priority converts Whale Link Flow output into a ranked observation priority. The intended integration path is:

```text
Whale Link Score
    |
    v
Watch Priority
    |
    v
Hound observation 강화
```

### Lead Line API Socket

WhaleLab-005-A adds the internal API Socket layer between Whale Link Flow and GrayMUG Core consumers:

```text
Whale Link Flow
        |
        v
Lead Line API Socket
        |
        v
+------------+------------+------------+
|    Core    |   Hound    |    Ward    |
+------------+------------+------------+
```

The socket exposes Watch Priority as a shared internal contract. Core, Hound, and Ward can consume the same Lead Line payload without modifying Hound detection logic.

Whale Link Flow is not a helper for only one engine. It is the connector between Core, Hound, and Ward.

### Event Replay

Event Replay validates whether the flow model behaves sensibly during known historical shocks and macro events.

### Future ML Core

The ML Core is planned, not complete. It should extend the validated flow architecture rather than replace it.

---

## 3. Research History

GrayMUG-LAB has progressed through four major WhaleLab stages.

### WhaleLab-001: UNI Case Study

Purpose:

* Study whether whale activity begins before the visible market pump.
* Compare "whale detected" timing against possible "whale activity inception" timing.
* Use UNI as an initial case study for volume spike precursors.

Tested:

* Price slope
* Volume slope
* Rank momentum
* Relative strength

Outcome:

* Adopted: the idea that a single volume spike is too late and that earlier market footprints should be studied.
* Not yet proven: a stable physical lead time between whale activity and detection.

### WhaleLab-002: Historical Event Analysis

Purpose:

* Test the early lead time hypothesis against major market events.
* Analyze seven historical events:
  - LUNA Collapse
  - FTX Collapse
  - SVB Collapse
  - BTC ETF Approval
  - BTC Halving
  - Carry Trade Shock
  - Yoon Martial Law Shock

Tested:

* Whether the measured average lead time of about 22.61 hours represented real whale behavior.
* Whether detected inception points occurred before or after real event shocks.
* Whether random event tests produced similar lead times.

Outcome:

* Rejected: fixed Lead Time hypothesis.
* Rejected: reverse-search inception based on a fixed historical window.
* Adopted: falsification-first validation.
* Adopted: RS vs BTC decoupling and rank momentum as useful features, when interpreted as flow rather than one-candle triggers.

Key conclusion:

> The fixed 22.61-hour Lead Time was an artifact of the search window, not a reliable physical whale accumulation lag.

### WhaleLab-003: Whale Link Flow

Purpose:

* Move away from fixed-time inception guessing.
* Build a flow-based model that links assets, sectors, and whale behavior.

Built:

* Cycle Layer
* Live Flow Layer
* Link Graph Layer
* Whale Type Classifier

Tested:

* Whether capital flow can be represented as linked movement across assets.
* Whether whale behavior types can be inferred from live flow patterns.
* Whether Hound can eventually receive a better observation map instead of a direct trading signal.

Outcome:

* Adopted: Link Flow approach.
* Adopted: Whale Link Flow as a Lead Line for Hound.
* Rejected: direct conversion of research signals into production trade conditions.

### WhaleLab-004: Sector Flow, Persistence, and Watch Priority

Purpose:

* Extend Whale Link Flow into sector-level capital rotation.
* Measure whether flows persist or disappear as one-off spikes.
* Produce Watch Priority candidates for Hound observation weighting.

Built:

* Sector Flow
* Flow Persistence
* Watch Priority
* Rotation Heatmap
* Event Replay Validation

Tested:

* Seven-event replay validation over roughly 4.5 years of historical data.
* Sector inflow and outflow behavior.
* Dominant whale type during major events.
* Watch Priority top candidates.

Outcome:

* Completed: WhaleLab-004 validation.
* Adopted: Watch Priority as the current integration interface.
* Adopted: Persistence as a key filter against one-candle noise.
* Maintained: Whale Link Flow is a Lead Line, not a trade engine.

Current research position:

```text
Fixed Lead Time hypothesis: rejected
Link Flow based approach: retained
Watch Priority interface: retained
Lead Line API Socket: added in WhaleLab-005-A
Direct Hound modification from LAB: forbidden
Core strategy logic inside Whale Link Flow: forbidden
Ward decision override from Whale Link Flow: forbidden
```

### WhaleLab-005-A: Lead Line API Socket

Purpose:

* Provide Whale Link Flow as a shared internal API Socket.
* Allow Core, Hound, and Ward to consume the same Lead Line contract.
* Keep Hound detection logic unchanged.
* Keep Ward independent as the defensive layer.
* Let Core choose between survival, accumulation, and observe-only modes.

Supported modes:

* `BEAR_ESCAPE`: USDT survival / risk avoidance.
* `BTC_ACCUMULATION`: BTC-denominated accumulation.
* `OBSERVE_ONLY`: observation, learning, and non-execution.

Implemented contract:

* `get_current_lead_line(mode, top_n=12, min_priority=0.0) -> dict`
* `get_hound_universe(mode, top_n=12, min_priority=0.0) -> list[str]`
* `get_ward_context(mode) -> dict`
* `get_core_payload(mode) -> dict`

Implementation:

```text
research/whale_link_flow/lead_line_socket.py
```

### WhaleLab-005 Roadmap

* `005-A`: Lead Line API Socket. Complete.
* `005-B`: Engine Integration Harness. Complete.
* `005-C`: Core / Ward / Hound live connection validation through the Socket.
* `005-D`: Flow Forecast Dataset for current flow -> next flow learning.
* `005-E`: Graph ML using `link_edges.csv`, `watch_priority.csv`, and `sector_flow_scores.csv`.
* `005-F`: Whale Pattern ML to predict where whales are likely to go next.

---

## 4. Current Outputs

The main Whale Link Flow v0.4 outputs are stored under:

```text
outputs/whale_link_flow/
```

Key files:

| File | Role |
| :--- | :--- |
| `flow_summary_v04.md` | Human-readable validation summary for Whale Link Flow v0.4 |
| `watch_priority.csv` | Per-symbol observation priority scores for Hound weighting |
| `sector_flow_scores.csv` | Sector-level capital inflow/outflow and rotation scores |
| `whale_type_scores.csv` | Whale type classification scores and confidence values |
| `rotation_heatmap.png` | Visual heatmap of capital rotation intensity |
| `flow_network.png` | Directed network map of capital movement relationships |

Additional outputs may exist from earlier experiments, but the files above represent the current WhaleLab-004 validation set.

---

## 5. Integration Philosophy

GrayMUG-LAB is not production. It is a research, backtest, and validation environment.

The production integration path is:

```text
Research
    |
    v
Backtest
    |
    v
Validation
    |
    v
Production
```

The operational integration concept is:

```text
Input
    |
    v
Score
    |
    v
Priority
```

Whale Link Flow should preserve this structure:

* Input: price, volume, rank, relative strength, sector map, event context
* Score: live flow score, sector flow score, persistence score, whale type confidence
* Priority: Hound watch priority

Strict integration rules:

* Do not directly modify Hound from GrayMUG-LAB.
* Do not change Hound detection conditions based only on research output.
* Do not revive the fixed Lead Time hypothesis.
* Do not override Ward's internal defense judgment.
* Do not put Core strategy decisions inside Whale Link Flow.
* Do not treat Watch Priority as a buy or sell signal.
* Keep Whale Link Flow as a Lead Line.
* Preserve Hound as the detection layer.
* Preserve Ward as the risk and safety layer.

Future target:

```text
Whale Link Score
    |
    v
Watch Priority
    |
    v
Hound 감시 강화
    |
    v
Production decision under existing safety rules
```

Current internal socket contract:

```text
Whale Link Flow
    |
    v
Lead Line API Socket
    |
    v
Core / Hound / Ward
```

Core passes the operating mode. Hound consumes only the resulting universe. Ward consumes risk context but keeps final defensive authority.

---

## 6. Development Rules

All future research and development must follow these rules.

### No Look-ahead Bias

No model may use future information at the current decision point.

Examples of forbidden behavior:

* Selecting an inception candle by looking backward from a known future spike.
* Computing features with full-period statistics unavailable at the time.
* Tuning thresholds after seeing event outcomes and calling the result predictive.

### No Pre-listing Data

Do not use data from before an asset was actually tradable.

Required handling:

* Respect each asset's real listing date.
* Flag low-liquidity launch periods.
* Avoid filling pre-listing periods in a way that creates fake momentum.

### BTC-relative Alpha First

GrayMUG's target is BTC accumulation. Performance must be evaluated relative to BTC, not only in USD terms.

Required checks:

* BTC-relative return
* BTC-relative strength
* Bull, bear, and sideways market behavior
* Risk-adjusted performance versus holding BTC

### DataFrame Input / DataFrame Output

New research modules should keep a simple structured interface:

```text
DataFrame Input -> DataFrame Output
```

This keeps modules testable, replayable, and easier to integrate into GrayMUG Core later.

### GrayMUG Core Compatible

Every new module should be shaped so it can eventually integrate with GrayMUG Core without forcing production rewrites.

Required properties:

* Clear input schema
* Clear output schema
* No hidden state dependency on notebooks
* No production DB access from LAB
* No direct trading side effects

---

## 7. Current Status

Current completed stage:

```text
WhaleLab-005-B complete
```

Completed capabilities:

* UNI case study
* Lead Time hypothesis validation
* Seven-event historical analysis
* Lead Time artifact rejection
* Whale Link Flow
* Cycle Layer
* Live Flow Layer
* Link Graph Layer
* Whale Type Classifier
* Sector Flow
* Flow Persistence
* Watch Priority
* Rotation Heatmap
* Event Replay Validation
* Lead Line API Socket
* Core / Hound / Ward shared payload contract
* Engine Integration Harness
* Simulator Payload foundation

Next planned stage:

```text
WhaleLab-005-C
```

Planned research:

* Mode Router
* Core / Ward / Hound Socket connection validation
* Flow Forecast Dataset
* Graph ML
* Whale Pattern ML
* ML Core
* Adaptive Whale Profile
* Flow Forecast Layer
* Sector ML
* Whale Type ML
* Capital Rotation Forecast

The next stage should build on the validated v0.4 flow architecture. It should not revive the fixed Lead Time hypothesis, and it should not bypass the Hound/Ward production safety boundary.

Final operating definition:

```text
Core gathers BTC.
Ward keeps the system alive.
Hound hunts alts.
Whale Link Flow connects the three engines.
Every result flows back into BTC quantity growth.
```

---

## 8. Project Memory

For the current state of the project, read these documents first:

| Document | Purpose |
| :--- | :--- |
| `docs/000_PROJECT_CHARTER.md` | Mission and research target |
| `docs/001_RESEARCH_ROADMAP.md` | Research phases and historical event plan |
| `docs/002_GRAYMUG_INTEGRATION_RULES.md` | Research-to-production integration rules |
| `docs/003_WHALELAB_VALIDATION_REPORT.md` | WhaleLab validation and Lead Time falsification |
| `docs/004_PROJECT_STATE.md` | Current project state |
| `docs/005_ARCHITECTURE_MAP.md` | Architecture and module map |
| `docs/006_DEVELOPMENT_RULES.md` | Development constraints and safety rules |
| `docs/007_WHALELAB_005A_LEAD_LINE_API_SOCKET.md` | Lead Line API Socket contract |
| `docs/008_WHALELAB_005_INTEGRATION_DIRECTIVE.md` | WhaleLab-005 integration directive and roadmap |
| `docs/009_SIMULATOR_FOUNDATION.md` | Simulator philosophy and observation foundation |

These documents are the project memory layer. A new contributor should be able to read them and understand the project goal, research history, current state, and next direction without relying on chat history.
