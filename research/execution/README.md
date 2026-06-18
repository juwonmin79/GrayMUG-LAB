# Execution Guidance API

WhaleLab-005-F creates structured execution guidance when Hound finds a target.

This is not live trading, automatic ordering, position management, Forecast, Graph ML, Whale ML, DB, FastAPI, Dashboard, or engine modification work.

---

## Purpose

LAB does not issue buy or sell commands.

LAB provides:

* Pattern Hint
* Entry Style
* TP Case
* SL Case
* Exit Trigger

The final entry or exit decision remains with the engine or the user.

---

## Pattern Hints

Initial rule-based patterns:

* `SLOW_CREEP`
* `SHOCK_PUMP`
* `DISTRIBUTION_RISK`
* `CHAIN_ROTATION`
* `BTC_HIDE`

No ML is used in this layer.

---

## TP / SL Templates

Templates:

* Case A: TP 5%, SL 3%
* Case B: TP 10%, SL 5%
* Case C: TP Dynamic, SL Dynamic

These are templates only, not position management.

---

## Exit Triggers

Initial triggers:

* `WARD_RISK_UP`
* `BTC_HIDE`
* `DISTRIBUTION_SPIKE`
* `LEAD_LINE_BREAK`

---

## Future ML Connection

Future ML can improve pattern classification only after the guidance contract remains non-executing and engine-safe.

Execution Guidance explains Hound target context; it does not replace Hound, Ward, or Core decisions.
