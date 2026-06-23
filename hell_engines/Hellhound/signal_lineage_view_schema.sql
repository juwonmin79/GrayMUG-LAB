-- Sprint 12C Signal Lineage View draft.
-- Design only. Do not apply from LAB without explicit approval.
--
-- Goal:
-- Given one signal_id, trace Signal -> Snapshot -> Wave -> Outcome -> MFE/MAE/Peak/Stop.
--
-- Current gap notes:
-- 1. production_hellhound_shadow.jsonl rows must expose signal_id.
-- 2. hound_wave_log uses 6h/24h/72h windows while hellhound_outcomes uses 1h/4h/24h.
-- 3. MFE/MAE JSONL rows should preserve signal_id and shadow_signal_id for direct lineage.

create or replace view signal_lineage_view as
select
  s.id::text as signal_id,
  s.id as shadow_signal_id,
  s.symbol,
  s.created_at as signal_time,
  s.shadow_action,
  s.pattern,

  mtf.id::text as mtf_snapshot_id,
  mtf.as_of_time as mtf_snapshot_time,
  mtf.timeframe as mtf_timeframe,
  mtf.candle_state,
  mtf.pre_spike_features,

  wave.wave_log_id,
  wave.signal_id as wave_signal_id,
  wave.created_at as wave_created_at,
  wave.snapshot_t0 as wave_snapshot_t0,
  wave.diff_a,
  wave.diff_b,
  wave.delta,

  outcome.id::text as outcome_id,
  outcome.evaluation_window,
  outcome.target_time,
  outcome.snapshot_time as outcome_snapshot_time,
  outcome.entry_price,
  outcome.current_price,
  outcome.return_pct,
  outcome.outcome_return,
  outcome.result as outcome_result,

  case outcome.evaluation_window
    when '24h' then wave.outcome_mfe_24h
    else null
  end as mfe_pct,
  case outcome.evaluation_window
    when '24h' then wave.outcome_mae_24h
    else null
  end as mae_pct,
  case outcome.evaluation_window
    when '24h' then wave.outcome_time_to_peak_24h
    else null
  end as time_to_peak_hours,
  case outcome.evaluation_window
    when '24h' then wave.outcome_time_to_stop_24h
    else null
  end as time_to_stop_hours,

  (
    mtf.id is not null
    and wave.signal_id is not null
    and outcome.id is not null
    and (
      outcome.evaluation_window != '24h'
      or (
        wave.outcome_mfe_24h is not null
        and wave.outcome_mae_24h is not null
        and wave.outcome_time_to_peak_24h is not null
        and wave.outcome_time_to_stop_24h is not null
      )
    )
  ) as lineage_complete
from hellhound_shadow_signals s
left join hellhound_mtf_snapshots mtf
  on mtf.symbol = s.symbol
 and mtf.as_of_time >= s.created_at - interval '15 minutes'
 and mtf.as_of_time <= s.created_at + interval '15 minutes'
left join hound_wave_log wave
  on wave.signal_id = s.id::text
left join hellhound_outcomes outcome
  on outcome.shadow_signal_id = s.id;
