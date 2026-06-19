create extension if not exists pgcrypto;

create table if not exists hellhound_outcomes (
  id uuid primary key default gen_random_uuid(),
  shadow_signal_id uuid not null references hellhound_shadow_signals(id) on delete cascade,
  symbol text not null,
  evaluation_window text not null,
  entry_price numeric,
  current_price numeric,
  return_pct numeric,
  snapshot_time timestamptz,
  outcome_return numeric,
  result text not null default 'PENDING',
  created_at timestamptz not null default now(),
  constraint hellhound_outcomes_window
    check (evaluation_window in ('1h', '4h', '24h')),
  constraint hellhound_outcomes_result
    check (result in ('PENDING', 'SUCCESS', 'FAIL', 'INCONCLUSIVE')),
  constraint hellhound_outcomes_unique_window
    unique (shadow_signal_id, evaluation_window)
);

create index if not exists idx_hellhound_outcomes_signal_id
  on hellhound_outcomes(shadow_signal_id);

create index if not exists idx_hellhound_outcomes_symbol_created
  on hellhound_outcomes(symbol, created_at);
