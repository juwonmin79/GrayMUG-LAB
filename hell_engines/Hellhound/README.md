# Hellhound

Hellhound is the experimental Hound attachment space for GrayMUG-LAB.

Purpose:

- Test LAB integration without modifying Production Hound.
- Validate Lead Line Universe Priority as a safe pre-scan overlay.
- Validate Execution Guidance Attachment after Hound has already detected a target.

Initial attachment candidates:

- Lead Line Universe Priority.
- Watch Priority overlay.
- Execution Guidance metadata attached after alert generation.

Rules:

- Do not copy Production Hound code into this folder.
- Do not modify Hound detection logic.
- Do not replace RSI, volume, BTC relative strength, taker, MACD, or whale alert conditions.
- Do not add automatic orders or position management.

## Hellhound-001-D Minimal Shadow Runner

Status: completed.

`shadow_runner.py` is the isolated minimal OracleJP-Supabase shadow runner.

Flow:

```text
OracleJP-style payload
  -> Hellhound shadow signal normalization
  -> hellhound_shadow_signals insert
```

Runtime environment:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
SHADOW_RUNNER_DRY_RUN
```

Dry-run:

```bash
SHADOW_RUNNER_DRY_RUN=1 python3 hell_engines/Hellhound/shadow_runner.py
```

Safety notes:

- Shadow runner is isolated from production.
- It does not import or modify Production Hound, Ward, Core, or production loaders.
- It inserts only into `hellhound_shadow_signals`.
- Dry-run prints the normalized shadow signal and performs no Supabase insert.
- Missing Supabase environment skips insertion without crashing production callers.
