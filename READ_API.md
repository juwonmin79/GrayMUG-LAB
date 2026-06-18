# GrayMUG LAB API Contract

## 1. Purpose

This document defines how Production engines may consume GrayMUG-LAB outputs as internal contracts.

It is not an API server specification. Do not add FastAPI, DB services, dashboard servers, or production engine rewrites from this document.

## 2. Safety Rules

- LAB does not make final engine decisions.
- Hound detection logic remains inside Hound.
- Ward defense logic remains inside Ward.
- Core strategy logic remains inside Core.
- LAB payloads are reference feeds, target hints, calibration weights, and execution guidance metadata.
- LAB output must never become automatic order execution.

## 3. Lead Line API

Source module:

- `research/whale_link_flow/lead_line_socket.py`

Functions:

- `get_current_lead_line(mode: str, top_n: int = 12, min_priority: float = 0.0) -> dict`
- `get_hound_universe(mode: str, top_n: int = 12, min_priority: float = 0.0) -> list[str]`
- `get_ward_context(mode: str) -> dict`
- `get_core_payload(mode: str) -> dict`

Supported modes:

- `BEAR_ESCAPE`
- `BTC_ACCUMULATION`
- `OBSERVE_ONLY`

Usage:

- Hound may consume `get_hound_universe()` as a universe or priority reference.
- Ward may consume `get_ward_context()` as a risk context reference.
- Core may consume `get_core_payload()` as a BTC accumulation context reference.

## 4. Target Feed API

Source modules:

- `research/targeting/target_pipeline.py`
- `research/targeting/target_schema.py`

Primary function:

- `run_target_pipeline(mode: str = "BTC_ACCUMULATION", top_n: int = 12) -> dict`

Payload fields:

- `timestamp`
- `mode`
- `source`
- `core`
- `ward`
- `hound`

Engine feeds:

- `CoreTargetFeed`: BTC accumulation reference.
- `WardRiskFeed`: survival and defense hint reference.
- `HoundHuntFeed`: target and universe candidate reference.

Usage rule:

- Each feed belongs to exactly one engine and must not replace another engine's judgment.

## 5. Fitness API

Source modules:

- `research/fitness/fitness_pipeline.py`
- `research/fitness/fitness_schema.py`

Primary output:

- `FitnessReport`

Fields:

- `timestamp`
- `core`
- `ward`
- `hound`
- `overall_score`

Usage:

- Fitness evaluates whether LAB output improves Core judgment support, Ward survival support, and Hound hunt support.
- Fitness is not a trading performance claim.
- Fitness must not be used as an automatic trade trigger.

## 6. Calibration API

Source modules:

- `research/calibration/calibration_pipeline.py`
- `research/calibration/calibration_schema.py`

Primary output:

- `CalibratedSignalPayload`

Signal fields:

- `signal_name`
- `engine`
- `signal_strength`
- `confidence`
- `application_scope`
- `max_influence`
- `final_weight`
- `reason`

Initial max influence:

- Core: `0.20`
- Ward: `0.15`
- Hound: `0.30`

Usage:

- Calibration limits how strongly LAB signals can influence each engine.
- Strong signals still cannot replace engine baseline logic.

## 7. Execution Guidance API

Source modules:

- `research/execution/execution_pipeline.py`
- `research/execution/execution_schema.py`

Primary output:

- `ExecutionGuidancePayload`

Guidance components:

- `PatternHint`
- `EntryGuidance`
- `TPSLGuidance`
- `ExitGuidance`

Supported initial pattern hints:

- `SLOW_CREEP`
- `SHOCK_PUMP`
- `DISTRIBUTION_RISK`
- `CHAIN_ROTATION`
- `BTC_HIDE`

Usage:

- Execution Guidance explains a detected target.
- It does not issue BUY or SELL commands.
- It does not calculate position size.
- It does not execute orders.

## 8. Engine Usage

### Hound

Allowed usage:

- Consume Lead Line universe as priority reference.
- Use Target Feed as target candidate metadata.
- Use Calibration final weight as a bounded priority boost.
- Attach Execution Guidance after Hound has detected or alerted a target.

Forbidden usage:

- Replace Hound scanner logic.
- Change RSI, volume, BTC relative strength, taker, MACD, or whale thresholds directly.
- Use LAB guidance to place orders.

### Ward

Allowed usage:

- Consume Ward Risk Feed as a risk context hint.
- Consume Calibration as bounded risk hint strength.
- Attach LAB risk context to alerts.

Forbidden usage:

- Replace Ward regime detection.
- Replace emergency exit rules.
- Block or force emergency exit from LAB alone.

### Core

Allowed usage:

- Consume Core Target Feed as BTC accumulation context.
- Consume Lead Line mode as operating context.
- Use Fitness and Calibration to evaluate LAB signal quality.

Forbidden usage:

- Replace Core strategy.
- Override stoploss lockdown.
- Convert LAB mode into automatic execution.

## 9. Forbidden Usage

- No production code modification from LAB contracts.
- No direct `backup_GrayMUG` changes.
- No automatic order placement.
- No position management implementation.
- No DB addition.
- No FastAPI addition.
- No dashboard addition.
- No Forecast, Graph ML, or Whale ML implementation from this contract.
