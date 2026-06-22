# GrayMUG-LAB Governance

## Mission

Mission is Boss.

The final goal is BTC-denominated performance improvement.

Hellhound exists to answer one question:

```text
Why did we fail to detect accumulation before the force moved?
```

Every Sprint, dataset, validation result, missed case, and future ML candidate is judged by whether it improves that answer.

## Repository Structure

### Production

```text
~/GrayMUG
```

Owner:

```text
Claude + Octopus
```

Roles:

- Hound
- Ward
- Core
- Telegram
- Binance Execution

Goal:

```text
Live trading operation.
```

### LAB

```text
~/GrayMUG-LAB
```

Owner:

```text
GPT + Codex
```

Roles:

- Hellhound
- Event Layer
- Lead Line
- Validation
- MFE/MAE
- Future ML Engine

Goal:

```text
Develop the judgment engine that moves before live trading.
```

## Boundary

LAB:

```text
Must not control Production.
```

Production:

```text
May request LAB judgment.
```

Hellhound output is advisory and research-oriented unless Production explicitly consumes a validated stable interface.

## Non Negotiable Rules

- Do not modify `backup_GrayMUG`.
- Do not directly modify Production Core.
- Do not directly modify Production Ward.
- Do not directly modify Production Hound.
- Do not access Binance order/trading endpoints from LAB.
- Do not create orders.
- Do not control positions.
- Do not delete DB rows.
- Do not update DB rows.
- Prefer append-only persistence.
- Default output is `is_trade_command=false`.
- Documentation update is required at Sprint close.

## Pre-ML Operating Rule

ML is postponed until Hellhound has enough real observation records.

Do not start:

- LSTM
- Transformer
- Deep Learning
- Embedding DB
- Vector Search
- Fine-tuning
- GPU training
- Feature explosion

Current objective:

```text
Systematically record what Hellhound missed, what Hellhound caught, and how late Hellhound was.
```
