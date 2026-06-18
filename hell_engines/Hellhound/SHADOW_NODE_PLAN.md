# Hellhound Shadow Node Plan

Hellhound runs as a shadow node beside Production Hound.

Runtime position:

```text
OracleJP
  -> Supabase market data read-only
  -> Hellhound Shadow Node
  -> LAB Context
  -> hellhound_shadow_signals
  -> hellhound_shadow_outcomes
```

Rules:

- Do not modify Production Hound.
- Do not modify `backup_GrayMUG`.
- Do not place orders.
- Do not manage positions.
- Do not call Binance order endpoints.
- Do not update/delete production Supabase tables.
- Insert only into shadow tables.

Next implementation step:

- Hellhound-001-D Minimal Shadow Runner.

Full plan:

- `docs/018_HELLHOUND_001C_ORACLEJP_SUPABASE_SHADOW_NODE_PLAN.md`
