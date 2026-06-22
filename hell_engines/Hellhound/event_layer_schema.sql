-- Draft only. Do not apply until the Hellhound event writer is implemented.
-- updated_at has no automatic refresh trigger in this draft.

create extension if not exists pgcrypto;

create table if not exists hellhound_events (
  event_id uuid primary key,
  symbol text not null,
  event_start_bucket timestamptz,
  max_gap_hours numeric not null default 24,
  first_seen_time timestamptz not null,
  last_seen_time timestamptz not null,
  event_age_hours numeric not null default 0,
  observation_count integer not null default 0,
  observation_timeframe_hint text,
  event_state text not null default 'new',
  hypotheses jsonb not null default '[]'::jsonb,
  shadow_actions jsonb not null default '[]'::jsonb,
  patterns jsonb not null default '[]'::jsonb,
  classification jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists hellhound_event_observations (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references hellhound_events(event_id) on delete cascade,
  shadow_signal_id uuid references hellhound_shadow_signals(id) on delete set null,
  symbol text not null,
  source_time timestamptz not null,
  hypothesis text not null,
  dedupe_key text not null,
  raw_signal jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint hellhound_event_observations_unique_dedupe
    unique (event_id, dedupe_key)
);

create table if not exists hellhound_mtf_snapshots (
  id uuid primary key default gen_random_uuid(),
  event_id uuid references hellhound_events(event_id) on delete cascade,
  symbol text not null,
  as_of_time timestamptz not null,
  snapshot_schema_version text not null default 'hellhound_mtf_snapshot_v1',
  timeframe text not null,
  candle_state jsonb not null default '{}'::jsonb,
  pre_spike_features jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint hellhound_mtf_snapshots_timeframe
    check (timeframe in ('1m', '15m', '1h', '4h', '1d', '1w'))
);

create index if not exists idx_hellhound_events_symbol_first_seen
  on hellhound_events(symbol, first_seen_time);

create index if not exists idx_hellhound_event_observations_symbol_source
  on hellhound_event_observations(symbol, source_time);

create index if not exists idx_hellhound_mtf_snapshots_event_timeframe
  on hellhound_mtf_snapshots(event_id, timeframe);
