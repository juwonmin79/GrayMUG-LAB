create extension if not exists pgcrypto;

create table if not exists hypotheses (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  status text not null default 'active',
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table hypotheses
  drop constraint if exists hypotheses_status_active_only;

alter table hypotheses
  drop constraint if exists hypotheses_status_lifecycle;

alter table hypotheses
  add constraint hypotheses_status_lifecycle
  check (status in ('active', 'promotion_candidate', 'retired'));

insert into hypotheses (name, status, config)
values
  (
    'lead-line-watch',
    'active',
    '{
      "shadow_action": "WATCH",
      "confidence": 0.57,
      "execution_guidance": {
        "pattern": "SLOW_CREEP",
        "entry_guidance": "Observe only; no executable order.",
        "tp_case": "shadow_tp_case",
        "sl_case": "shadow_sl_case",
        "exit_triggers": ["btc_relative_weakness"],
        "shadow_action": "WATCH",
        "confidence": 0.57
      }
    }'::jsonb
  ),
  (
    'confirmation-wait',
    'active',
    '{
      "shadow_action": "WAIT_CONFIRMATION",
      "confidence": 0.49,
      "execution_guidance": {
        "pattern": "CHAIN_ROTATION",
        "entry_guidance": "Wait for confirmation; no executable order.",
        "tp_case": "shadow_confirmation_tp_case",
        "sl_case": "shadow_confirmation_sl_case",
        "exit_triggers": ["confirmation_failed"],
        "shadow_action": "WAIT_CONFIRMATION",
        "confidence": 0.49
      }
    }'::jsonb
  ),
  (
    'risk-avoid',
    'active',
    '{
      "shadow_action": "AVOID",
      "confidence": 0.36,
      "execution_guidance": {
        "pattern": "DISTRIBUTION_RISK",
        "entry_guidance": "Avoid in shadow context; no executable order.",
        "tp_case": "shadow_avoid_tp_case",
        "sl_case": "shadow_avoid_sl_case",
        "exit_triggers": ["distribution_risk"],
        "shadow_action": "AVOID",
        "confidence": 0.36
      }
    }'::jsonb
  )
on conflict (name) do update
set
  config = excluded.config;
