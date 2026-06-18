# Engine Fitness Framework

WhaleLab-005-D measures whether GrayMUG-LAB outputs improve the operating ability of Core, Ward, and Hound.

This is not backtesting, live trading, Forecast, Graph ML, or Whale ML. The first version is a simple rules-based fitness layer over the Target Intelligence Pipeline.

---

## Purpose

GrayMUG-LAB is not measured by the number of indicators it creates.

It is measured by whether it improves:

* Core judgment
* Ward survival
* Hound hunting ability
* BTC quantity growth contribution

---

## Flow

```text
Whale Link Flow
    |
    v
Lead Line Socket
    |
    v
Target Feed
    |
    v
Engine Fitness Framework
    |
    v
Fitness Report
```

---

## Fitness Definitions

### Core Fitness

Evaluates whether the feed improves BTC accumulation readiness.

Initial signals:

* BTC accumulation bias
* BTC-relative alpha placeholder
* focus assets

### Ward Fitness

Evaluates whether the feed improves survival readiness.

Initial signals:

* survival score
* drawdown avoidance placeholder
* warning accuracy placeholder

### Hound Fitness

Evaluates whether the feed improves alt hunting readiness.

Initial signals:

* target presence
* forward return score placeholder
* target accuracy

---

## Future Comparison

`fitness_registry.py` is shaped so later research outputs can be compared:

* Forecast V1
* Forecast V2
* Graph ML V1
* Graph ML V2

Each future output must report Core / Ward / Hound fitness separately.

---

## Run

```bash
source .venv/bin/activate && python -B research/fitness/fitness_pipeline.py
source .venv/bin/activate && python -B research/fitness/test_fitness_pipeline.py
```

---

## Non-Goals

This layer does not add Lead Time, Forecast, Graph ML, Whale ML, DB, FastAPI, Dashboard, actual Core/Ward/Hound changes, live trading logic, or backtests.
