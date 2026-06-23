-- Hellhound Wave Engine v0 dataset table.
-- Schema draft only. Do not apply from LAB without explicit approval.

create table if not exists hound_wave_log (
    signal_id text primary key,
    snapshot_t2 jsonb not null,
    snapshot_t1 jsonb not null,
    snapshot_t0 jsonb not null,
    diff_a jsonb not null,
    diff_b jsonb not null,
    delta jsonb not null,
    created_at timestamptz not null default now(),
    outcome_mfe_6h numeric,
    outcome_mae_6h numeric,
    outcome_time_to_peak_6h numeric,
    outcome_mfe_24h numeric,
    outcome_mae_24h numeric,
    outcome_time_to_peak_24h numeric,
    outcome_mfe_72h numeric,
    outcome_mae_72h numeric,
    outcome_time_to_peak_72h numeric
);
