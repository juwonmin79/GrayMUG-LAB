# GrayMUG-LAB

GrayMUG-LAB is the research, validation, and experimental engine lab for GrayMUG.

Current state:

```text
WhaleLab Foundation Complete.
Hellhound Shadow Node Phase Ready.
```

## 1. Project Vision

GrayMUG is not designed to maximize USDT returns as the final goal.

The final goal is:

```text
BTC Accumulation Engine
```

Every research module, engine feed, validation result, and future production candidate is judged by whether it can help increase BTC quantity over time.

Core philosophy:

- BTC accumulation comes first.
- USDT return is a tactical measurement, not the final objective.
- Halving cycle is the macro season.
- Whale Link Flow is the live capital current.
- Hound detects alt opportunities.
- Ward keeps the system alive.
- Core keeps the system pointed toward BTC accumulation.
- LAB does not replace production judgment; LAB produces validated candidates.

## 2. Architecture

GrayMUG is now organized as three layers:

```text
GrayMUG-LAB
    |
    v
Hell Engines
    |
    v
Production Engines
```

### GrayMUG-LAB

GrayMUG-LAB is the research and validation layer.

It builds:

- Lead Line Socket
- Target Intelligence Feed
- Engine Fitness Framework
- Signal Calibration Layer
- Execution Guidance API
- Hellhound validation and shadow-node plans

LAB output is not a trade command. It becomes a candidate only after validation.

### Hell Engines

Hell Engines are experimental evolution spaces.

They do not replace production. They create tested merge candidates.

```text
hell_engines/
├─ Hellcore
├─ Hellward
└─ Hellhound
```

### Production Engines

Production engines are the protected operating engines.

They are treated as source-of-truth runtime systems and must not be directly modified by LAB experiments.

Production reference:

```text
backup_GrayMUG/
```

`backup_GrayMUG` is read-only reference material.

## 3. Engine Definition

### Core

Core is the BTC accumulation engine.

Responsibilities:

- BTC accumulation direction
- Market mode context
- Main strategy authority
- Final BTC-focused operating posture

Core is not replaced by LAB.

### Ward

Ward is the survival engine.

Responsibilities:

- Risk monitoring
- Defensive context
- Emergency and survival judgment
- System protection

Ward keeps independent defensive authority.

### Hound

Hound is the alt hunting engine.

Responsibilities:

- Alt target detection
- Rotation opportunity discovery
- Production alert generation
- Hound baseline logic

Hound detection logic must not be directly modified by LAB.

## 4. Hell Engine Definition

### Hellcore

Hellcore is the Core evolution experiment space.

It is used to test BTC accumulation context, Core payloads, and future Core improvement candidates without changing Production Core.

### Hellward

Hellward is the Ward evolution experiment space.

It is used to test LAB risk hints, calibration hints, and defensive context without replacing Ward judgment.

### Hellhound

Hellhound is the Hound evolution experiment space.

It is used to test Lead Line universe priority, Target Feed, Calibration, Execution Guidance, and OracleJP-Supabase shadow-node behavior without changing Production Hound.

Important rule:

```text
Hell Engines do not replace Production.
Hell Engines create validated merge candidates.
```

## 5. WhaleLab Status

WhaleLab-005 foundation is complete through 005-G.

Completed:

- `005-A`: Lead Line API Socket
  - Exposes Whale Link Flow as an internal API socket for Core, Ward, and Hound.
- `005-B`: Engine Integration Harness
  - Builds Core / Ward / Hound state payloads without touching production engines.
- `005-C`: Target Intelligence Pipeline
  - Converts LAB context into engine-owned feeds: Core Target Feed, Ward Risk Feed, Hound Hunt Feed.
- `005-D`: Engine Fitness Framework
  - Measures whether LAB outputs improve Core judgment, Ward survival, and Hound hunting ability.
- `005-E`: LAB Signal Calibration Layer
  - Limits LAB signal strength by engine scope and prevents engine judgment replacement.
- `005-F`: Execution Guidance API
  - Produces pattern, entry style, TP/SL case, and exit trigger guidance without issuing trade commands.
- `005-G`: Hound Interface Audit
  - Maps safe Hound attachment points and confirms Hound should not be directly modified.

WhaleLab conclusion:

```text
Fixed Lead Time hypothesis: rejected
Link Flow approach: retained
Lead Line role: retained
Direct production modification: forbidden
```

## 6. Hellhound Status

Hellhound-001 is the current active track.

Completed:

- `001-A`: Validation Runner Skeleton
  - Created the minimum runner structure for comparing Production Hound Universe vs Lead Line Universe.
- `001-B`: Production Universe Loader
  - Confirmed Production Hound universe is not a static file.
  - Found dynamic generation at `backup_GrayMUG/hound/scanner.py:HoundScanner.get_top_symbols`.
- `001-C`: OracleJP-Supabase Shadow Node Plan
  - Defined Hellhound as a read-only OracleJP-Supabase shadow node.
  - Defined `hellhound_shadow_signals` and `hellhound_shadow_outcomes` schemas.
  - Confirmed Hellhound creates `shadow_signal` records only.

Current Hellhound architecture:

```text
OracleJP
  |
  v
Supabase market data read-only
  |
  v
Hellhound Shadow Node
  |
  v
LAB Context
  |
  v
hellhound_shadow_signals
  |
  v
hellhound_shadow_outcomes
```

Hellhound does not place orders and does not manage positions.

## 7. Current Roadmap

Current stage:

```text
Hellhound-001-D
Minimal Shadow Runner
```

The next implementation target is a minimal OracleJP-Supabase shadow runner that:

- Reads confirmed Supabase market tables.
- Loads LAB Lead Line universe.
- Builds Target Feed, Fitness, Calibration, and Execution Guidance context.
- Inserts only into `hellhound_shadow_signals`.
- Does not place orders.
- Does not mutate production tables.

Planned stages:

- `Hellhound-001-E`: Outcome Evaluator
  - Fill `hellhound_shadow_outcomes`.
  - Measure forward `+1h`, `+4h`, `+24h` return.
  - Measure BTC-relative return.
  - Track TP hit, SL hit, and exit trigger hit.
- `Hellhound-001-F`: Fitness Feedback Loop
  - Feed Hellhound shadow outcomes back into Engine Fitness.
  - Compare Production Hound baseline vs Hellhound shadow signals.
  - Decide which candidates deserve merge review.

## 8. Safety Rules

### backup_GrayMUG

`backup_GrayMUG` is a production reference artifact.

Rules:

- Do not modify.
- Do not delete.
- Do not move.
- Do not rename.
- Do not stage.
- Do not commit.
- Do not push.
- Do not print secrets, keys, tokens, credentials, or `.env` contents.

### Production Core / Ward / Hound

Production engines are protected.

Rules:

- Do not directly modify Production Core.
- Do not directly modify Production Ward.
- Do not directly modify Production Hound.
- Do not replace Hound detection logic.
- Do not replace Ward defense judgment.
- Do not replace Core strategy judgment.

### Experiments

All experiments run through Hell Engines first.

Rules:

- No live trading from LAB.
- No automatic orders.
- No position management.
- No Binance order endpoint calls.
- No production Supabase table update/delete.
- Shadow tables only for Hellhound shadow runs.

## 9. Project Memory

Start with these documents:

| Document | Purpose |
| :--- | :--- |
| `docs/004_PROJECT_STATE.md` | Current project state |
| `docs/005_ARCHITECTURE_MAP.md` | Architecture map |
| `docs/006_DEVELOPMENT_RULES.md` | Development and safety rules |
| `docs/014_HOUND_INTERFACE_AUDIT.md` | Hound attachment audit |
| `docs/015_PRODUCTION_ENGINE_MAP.md` | Production Core / Ward / Hound map |
| `docs/016_HELLHOUND_001_VALIDATION_PLAN.md` | Hellhound-001 validation plan |
| `docs/017_HELLHOUND_001B_PRODUCTION_UNIVERSE_LOADER.md` | Production universe loader finding |
| `docs/018_HELLHOUND_001C_ORACLEJP_SUPABASE_SHADOW_NODE_PLAN.md` | OracleJP-Supabase shadow node plan |

For WhaleLab foundation details:

| Document | Purpose |
| :--- | :--- |
| `docs/007_WHALELAB_005A_LEAD_LINE_API_SOCKET.md` | Lead Line API Socket |
| `docs/010_WHALELAB_005C_TARGET_INTELLIGENCE_PIPELINE.md` | Target Intelligence Pipeline |
| `docs/011_ENGINE_FITNESS_FRAMEWORK.md` | Engine Fitness Framework |
| `docs/012_LAB_SIGNAL_CALIBRATION_LAYER.md` | Signal Calibration Layer |
| `docs/013_EXECUTION_GUIDANCE_API.md` | Execution Guidance API |

## 10. Final Operating Definition

```text
Core accumulates BTC.
Ward keeps the system alive.
Hound hunts alts.
WhaleLab builds validated LAB context.
Hell Engines test evolution candidates.
Production Engines remain protected.
Every result must flow back to BTC quantity growth.
```
