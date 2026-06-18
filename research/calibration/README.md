# LAB Signal Calibration Layer

WhaleLab-005-E standardizes LAB signal strength, confidence, and application scope before any engine consumes the signal.

This is not Forecast, Graph ML, Whale ML, Execution Guidance, DB, FastAPI, Dashboard, or engine modification work.

---

## Purpose

LAB signals must not replace Core, Ward, or Hound judgment.

The calibration layer exists to answer:

* How strong is the LAB signal?
* How confident is the LAB signal?
* Which engine may consume it?
* What is the maximum allowed influence?

---

## Engine Policy

### Core

Allowed scope:

```text
BTC_ACCUMULATION_REFERENCE
```

Forbidden:

```text
FINAL_STRATEGY_DECISION
```

Max influence: `0.20`

### Ward

Allowed scope:

```text
RISK_HINT
```

Forbidden:

```text
FINAL_DEFENSE_DECISION
```

Max influence: `0.15`

### Hound

Allowed scope:

```text
TARGET_PRIORITY_BOOST
```

Forbidden:

```text
DETECTION_LOGIC_REPLACEMENT
```

Max influence: `0.30`

---

## Rule

```text
final_weight = signal_strength * confidence * max_influence
```

The result is clamped to `0.0 ~ 1.0`, and must never exceed the engine's max influence.

---

## Future Execution Guidance

Future Execution Guidance can consume calibrated weights only after the engine scope is explicit.

Calibration does not execute, decide, trade, defend, detect, forecast, or replace engine logic.
