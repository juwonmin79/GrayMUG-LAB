create extension if not exists pgcrypto;

create table if not exists hellhound_universe_snapshots (
  id uuid primary key default gen_random_uuid(),
  exchange_name text not null,
  exchange_testnet boolean not null default false,
  generated_at timestamptz not null default now(),
  top_n integer not null default 30,
  candidates_count integer not null default 0,
  symbols text[] not null,
  universe_payload jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_hellhound_universe_snapshots_generated
  on hellhound_universe_snapshots(generated_at desc);

