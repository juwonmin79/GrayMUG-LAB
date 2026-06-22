# GrayMUG Ecosystem Architecture

## System Structure

```text
Jake
  |
  v
GrayMUG-LAB
(GPT + Codex)
  |
  v
Hellhound
  |
  v
Production Interface
  |
  v
GrayMUG
(Claude + Octopus)
  |
  v
Hound
  |
  v
Telegram / Binance
```

## Role Separation

### Claude

- Production Guardian
- Protects live trading integrity.
- Owns Production safety posture.

### GPT

- Hellhound Architect
- Defines research direction, judgment design, and missed-case questions.
- Keeps Mission aligned with BTC-denominated improvement.

### Codex

- Sprint Builder
- Implements LAB modules, tests, and documentation.
- Enforces append-only and non-trade output contracts.

### Jake

- Mission Owner
- Decides whether LAB evidence is meaningful.
- Keeps Production and LAB aligned without merging their authority.

## Current State

Production Shadow Pipeline:

```text
Built and verified.
```

Flow:

```text
Production Hound
  |
  v
Hellhound
  |
  v
production_hellhound_shadow.jsonl
```

Status:

- JSONL generation complete.
- Verification complete.
- LAB can now convert Production Shadow output into research datasets.

## Boundary

Hellhound is a judgment engine, not an execution engine.

Production owns:

- Runtime
- Telegram output
- Binance execution
- Final trading authority

LAB owns:

- Hellhound research
- Event Layer
- Lead Line
- Validation
- MFE/MAE
- Missed and success case collection
- Future ML design after enough observation data exists
