# Missed BTC Case Review

## Purpose

This document fixes the recent BTC rise as a standing review case.

The case exists to force Hellhound evolution around the real question:

```text
Before the rise, what did Hellhound see and what did Hellhound miss?
```

## Event

Recent BTC rise occurred.

Hellhound failed to detect it early.

This is a missed case.

## Review Fields

For every update to this case, capture:

- Hound Scan result
- Shadow JSONL result
- Hellhound Score
- Promotion Status
- Structure Classification

## Core Questions

Before the rise:

- What did Hellhound see?
- What did Hellhound miss?

## Forbidden Explanations

- No excuses.
- No blaming data shortage.
- No treating the case as noise without review.

## Registry

Missed cases are stored append-only at:

```text
outputs/hellhound_missed_cases.jsonl
```

The registry module is:

```text
hell_engines/Hellhound/missed_case_registry.py
```

This BTC missed case remains a benchmark dataset for future Hellhound evolution.
