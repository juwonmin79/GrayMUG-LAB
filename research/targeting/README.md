# Target Intelligence Pipeline

WhaleLab-005-C turns Whale Link Flow output into engine-owned Target Feeds.

This is not a simulator, dashboard, ML, forecast, Graph ML, or Whale ML step. It is a Target Feed API pipeline that makes the existing Lead Line and Integration Harness output directly consumable by Core, Ward, and Hound.

---

## Purpose

GrayMUG-LAB is not a lab for interesting indicators. It is a Target Acquisition Lab.

Every feed must answer one question:

```text
Which engine decision does this make more accurate?
```

If a feed cannot answer that, it does not belong in the pipeline.

---

## Flow

```text
Whale Link Flow
    |
    v
Lead Line Socket
    |
    v
Engine Integration Harness
    |
    v
Target Intelligence Pipeline
    |
    v
Core / Ward / Hound Target Feed
```

---

## Feed Ownership

### Core Target Feed

Supports BTC accumulation judgment.

It does not make final buy or sell decisions.

### Ward Risk Feed

Supports survival and defensive judgment.

It provides risk hints only and does not replace Ward's final defense logic.

### Hound Hunt Feed

Supports alt target selection.

It provides universe and target candidates only and does not modify Hound detection logic.

---

## Files

* `target_schema.py`: Target Feed dataclasses.
* `core_target_feed.py`: builds Core Target Feed.
* `ward_risk_feed.py`: builds Ward Risk Feed.
* `hound_hunt_feed.py`: builds Hound Hunt Feed.
* `target_feed_builder.py`: combines engine feeds into one payload.
* `target_pipeline.py`: runnable Target Intelligence Pipeline.
* `test_target_pipeline.py`: smoke test.

---

## Run

```bash
source .venv/bin/activate && python -B research/targeting/target_pipeline.py
source .venv/bin/activate && python -B research/targeting/test_target_pipeline.py
```

The pipeline may also export a small helper file:

```text
outputs/targeting/latest_target_feed.json
```

The internal API payload is primary; file export is secondary.

---

## Future Placement

Future Forecast, Graph ML, or Whale Pattern ML can feed into this layer only after each output is clearly assigned to Core, Ward, or Hound.

LAB does not judge. LAB provides Target Feeds.
