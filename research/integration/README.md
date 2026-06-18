# GrayMUG Integration Harness

WhaleLab-005-B creates the first runnable bridge from Whale Link Flow research output to GrayMUG engine states.

This is not ML research. It is the foundation for moving from a research lab structure toward an operating-system structure.

---

## Structure

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
        |
        v
Simulator Payload
```

Files:

* `state_schema.py`: dataclass state definitions for Lead Line, Core, Ward, Hound, and Simulator.
* `core_adapter.py`: converts `get_core_payload()` output into `CoreState`.
* `ward_adapter.py`: converts `get_ward_context()` output into `WardState`.
* `hound_adapter.py`: converts `get_hound_universe()` output into `HoundState`.
* `simulator_payload.py`: combines Core / Ward / Hound / Lead Line states into one payload.
* `integration_harness.py`: runnable harness for checking the connection flow.
* `test_harness.py`: smoke test for the harness contract.

---

## Data Flow

```text
Whale Event
      |
      v
Flow Analysis
      |
      v
Watch Priority
      |
      v
Lead Line API Socket
      |
      v
Core / Hound / Ward
      |
      v
Simulator Payload
```

---

## Run

```bash
python research/integration/integration_harness.py
```

If the shell does not expose `python`, use the project virtualenv:

```bash
.venv/bin/python research/integration/integration_harness.py
```

Smoke test:

```bash
.venv/bin/python research/integration/test_harness.py
```

---

## Philosophy

GrayMUG does not optimize for USDT return first. The final metric is BTC quantity growth.

* Core gathers BTC.
* Ward keeps the system alive.
* Hound hunts alts.
* Whale Link Flow connects the three engines.

---

## Future Simulator Integration

The simulator should observe state, not execute trades.

It should display:

* Core state
* Ward state
* Hound state
* Lead Line state

---

## Future Dashboard Integration

A later dashboard can consume `build_simulator_payload()` and render a GrayMUG Command Center view.

This sprint does not add a dashboard, API server, database, forecast model, Graph ML, or Whale ML.
