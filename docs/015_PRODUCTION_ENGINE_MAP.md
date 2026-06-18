# Production Engine Map

## 1. Purpose

This document maps the read-only `backup_GrayMUG` production reference so GrayMUG-LAB can attach Lead Line, Target Feed, Calibration, and Execution Guidance layers without changing production Core, Ward, or Hound logic.

This is an audit and design document only. It is not an implementation plan for direct production edits.

## 2. Source Safety Rules

- `backup_GrayMUG` is a production reference artifact.
- Do not modify, delete, move, rename, stage, commit, or push files under `backup_GrayMUG`.
- Do not print `.env`, key, token, credential, or secret values.
- LAB layers may be mapped against production contracts, but production code must remain untouched.
- Hell engines are the only approved experimental surface for PoC work.

## 3. Production Directory Summary

Observed production reference paths:

- `backup_GrayMUG/backend/`: Core runtime, strategy, exchange adapter, stoploss guardian, notifier, recorder.
- `backup_GrayMUG/core/`: regime detector.
- `backup_GrayMUG/hound/`: Hound scanner, runner, relative strength, and Hound execution engine.
- `backup_GrayMUG/ward/`: Ward watcher and emergency exit.
- `backup_GrayMUG/model/`: existing model artifacts and feature metadata.
- `backup_GrayMUG/deploy/systemd/`: production service entrypoints.
- `backup_GrayMUG/scripts/`: utility script area.

Service entrypoints:

- Hound: `python -m hound.run_hound`
- Ward: `python -m ward.watcher`
- Core: `python main.py` from `backup_GrayMUG/backend`

## 4. Hound Map

### Files

- `backup_GrayMUG/hound/run_hound.py`
- `backup_GrayMUG/hound/scanner.py`
- `backup_GrayMUG/hound/relative_strength.py`
- `backup_GrayMUG/hound/engine.py`
- `backup_GrayMUG/model/hound_model.pkl`
- `backup_GrayMUG/model/hound_features.json`

### Entry Point

`hound.run_hound.main()` creates `HoundScanner(notifier=notifier, quote="USDT")`, runs a 15 minute scan loop, sends entry alerts, and calls Hound execution functions for accepted entries unless the kill switch is active.

Runtime flow:

```text
run_hound.main()
  -> run_one_cycle()
  -> HoundScanner.scan()
  -> entry / whale classification
  -> notify_entry()
  -> hound.engine.enter_position()
  -> hound.engine.monitor_positions()
```

### Input Contract

Current Hound inputs:

- Universe: `HoundScanner.get_top_symbols()` builds top symbols from Binance tickers.
- Quote asset: `quote`, initialized as `USDT` by `run_hound.py`.
- Universe size: `top_n`, default 30.
- Exclusions: BTC, stable assets, and configured reserve bases.
- Market data: OHLCV from exchange, daily, 15m, and 1h.
- BTC context: BTC OHLCV, BTC 1h regime/drop check, BTC taker buy ratio.
- Scan interval: `SCAN_INTERVAL_SEC = 15 * 60`.
- Thresholds: volume multiplier, whale multiplier, RSI range, minimum quote volume, BTC drop limit, reset window.
- IPC input from Supabase control tables: kill switch and available USDT.

### Baseline Logic

Baseline Hound logic must not be replaced.

Observed conditions and components:

- Volume spike condition using average volume ratio.
- RSI range condition.
- BTC relative strength rising condition from `relative_strength.compute_rs_pair()`.
- Taker buy ratio condition.
- Candle tail / pump exhaustion filter.
- 15m MACD condition.
- 1h trend condition.
- 15m EMA trend condition.
- BTC 1h crash/regime guard.
- BTC weather guard.
- Reset window guard.
- FNG is fetched and logged, but not used as a hard entry condition in the current scanner path.
- Whale alert condition uses a higher volume multiplier.
- Existing model artifacts exist under `backup_GrayMUG/model/`, but the observed scanner path is rule-based.

### Output Contract

Primary Hound outputs:

- `ScanResult` dataclass from `hound/scanner.py`.
- Entry candidates where `passes_entry` is true.
- Whale alerts where `is_whale` is true.
- Telegram messages through notifier helpers.
- Supabase writes:
  - `hound_scan_log`
  - `hound_watchlist`
  - `hound_watchlist_history`
  - `hound_positions`
  - `hound_daily_stats`
- Hound execution calls:
  - `enter_position()`
  - `monitor_positions()`
  - `execute_kill()`
  - `execute_resume()`

### ML / Score Components

Observed production reference contains:

- `backup_GrayMUG/model/hound_model.pkl`
- `backup_GrayMUG/model/hound_features.json`
- `backup_GrayMUG/model/regime_model.pkl`
- `backup_GrayMUG/model/regime_features.json`

No LAB layer should replace existing score/model behavior. Any future LAB score must remain a reference feed or priority hint.

### LAB Attachment Candidates

Candidate A: Before Universe Build

- Possible: technically possible through a pre-filter or external universe provider.
- Advantage: can reduce scan surface early.
- Risk: high risk of hiding symbols from Hound before Hound's baseline market filter runs.
- Recommendation: not primary.

Candidate B: After Universe Build / Before Scanner

- Possible: yes.
- Advantage: preserves Hound universe construction and baseline detection while allowing Lead Line priority or watch priority overlay.
- Risk: priority handling must not rewrite RSI, volume, RS, taker, MACD, or BTC guard thresholds.
- Recommendation: primary attachment point.

Candidate C: After Signal / Before Alert

- Possible: yes.
- Advantage: LAB can annotate candidate signals without changing detection.
- Risk: if used to suppress alerts, LAB would start replacing Hound judgment.
- Recommendation: allowed only for metadata enrichment, not for gating.

Candidate D: After Alert / Execution Guidance Attachment

- Possible: yes.
- Advantage: Execution Guidance can explain pattern, entry style, TP/SL case, and exit triggers after Hound has detected a target.
- Risk: must not become automatic order, position sizing, or stop override.
- Recommendation: secondary attachment point.

## 5. Ward Map

### Files

- `backup_GrayMUG/ward/watcher.py`
- `backup_GrayMUG/ward/emergency_exit.py`
- `backup_GrayMUG/core/regime.py`
- `backup_GrayMUG/model/regime_model.pkl`
- `backup_GrayMUG/model/regime_features.json`

### Entry Point

`ward.watcher.main()` runs `WardWatcher.run_one_cycle()` every 60 seconds.

Runtime flow:

```text
ward.watcher.main()
  -> WardWatcher.run_one_cycle()
  -> sync Hound watchlist from Supabase
  -> check BTC MA200 breach
  -> RegimeDetector.detect()
  -> maybe emergency exit
  -> maybe reentry notification
```

### Risk Logic

Observed Ward risk logic:

- Fixed BTC monitoring.
- Dynamic watchlist derived from `hound_watchlist` and reserve candidates.
- BTC daily close vs MA200 breach check.
- FNG fetch with fail-open sentinel.
- `RegimeDetector` classifies `BULL`, `BEAR`, and `RECOVERY`.
- Emergency exit only after BEAR regime confirmation and safety gates.
- Reentry notification after RECOVERY when prior emergency exit happened.
- Persistent latches in `ward_state` prevent repeated alerts.

`backup_GrayMUG/ward/emergency_exit.py` performs liquidation and service stop behavior. LAB must not interfere with or replace this decision layer.

### Output Contract

Primary Ward outputs:

- Telegram warnings for BTC MA200 breach.
- Regime warning logs.
- Emergency exit execution result.
- Reentry signal notification.
- Supabase latch state updates in `ward_state`.
- Service stop attempts for Core and Hound during emergency exit.

### LAB Attachment Candidates

Candidate A: Risk Context Reference

- Possible: yes.
- Advantage: Calibration and Target Feed risk hints can be presented as reference context.
- Risk: must not alter Ward's final BEAR/RECOVERY or emergency decision.
- Recommendation: allowed.

Candidate B: Before Emergency Exit as Hint

- Possible: yes as metadata only.
- Advantage: LAB can describe whether Lead Line or Execution Guidance agrees with elevated risk.
- Risk: using LAB to block or force emergency exit would violate Ward independence.
- Recommendation: allowed only as a non-binding hint.

Candidate C: Alert Payload Risk Hint

- Possible: yes.
- Advantage: Ward alerts can include LAB risk context for operators or downstream consumers.
- Risk: alert text must not imply LAB made the defense decision.
- Recommendation: secondary allowed point.

## 6. Core Map

### Files

- `backup_GrayMUG/backend/main.py`
- `backup_GrayMUG/backend/engine.py`
- `backup_GrayMUG/backend/strategy.py`
- `backup_GrayMUG/backend/stoploss.py`
- `backup_GrayMUG/core/regime.py`
- `backup_GrayMUG/backend/trade_recorder.py`

### Entry Point

The systemd Core service starts `python main.py` from `backup_GrayMUG/backend`.

Runtime flow:

```text
backend/main.py
  -> Settings / logger / notifier / exchange
  -> CoreStrategy
  -> StopLossGuardian
  -> Engine.run()
  -> Engine.run_once()
  -> build_snapshot()
  -> stoploss check
  -> strategy.generate_signal()
  -> open / close / hold
```

### Regime Logic

Core trading logic is centered on `CoreStrategy`, which uses confirmed weekly RSI for the configured symbol, defaulting to BTC/USDT. `RegimeDetector` separately defines:

- `BULL`: BTC at or above MA200.
- `BEAR`: BTC below MA200 before recovery confirmation.
- `RECOVERY`: after bottom flag and FNG recovery threshold.

Core strategy behavior:

- BUY when confirmed RSI is below or equal to the configured buy threshold.
- SELL when confirmed RSI is above or equal to the configured sell threshold.
- HOLD otherwise.

Stoploss behavior:

- Independent guardian thread.
- Entry loss lockdown.
- BTC 24h crash lockdown.
- Lockdown blocks future Engine signals until manually unlocked.

### Output Contract

Primary Core outputs:

- `TradeSignal` from strategy to engine.
- Position state in `Engine.position`.
- Notifier messages for entry, close, engine start, and shutdown.
- Trade recorder rows through the recorder protocol.
- Lockdown behavior from `StopLossGuardian`.

### LAB Attachment Candidates

Candidate A: BTC_ACCUMULATION Reference

- Possible: yes.
- Advantage: Core can consume Core Target Feed as context for BTC accumulation bias.
- Risk: must not replace RSI strategy, stoploss, or order execution.
- Recommendation: allowed as read-only reference.

Candidate B: BEAR_ESCAPE / OBSERVE_ONLY Mode Reference

- Possible: yes.
- Advantage: Lead Line Socket mode can clarify operating posture.
- Risk: LAB cannot choose Core strategy mode directly in production.
- Recommendation: allowed as context, not command.

Candidate C: Hound Result BTC Feedback Context

- Possible: yes.
- Advantage: Core can see whether Hound alt rotation contributes to BTC accumulation objective.
- Risk: feedback must not become automatic position switching.
- Recommendation: future Hellcore experiment only.

## 7. Secret / Key Handling

- No `.env` content was read or printed for this audit.
- Files that may contain settings or credential wiring were treated as contract references only.
- API key, token, secret, and credential values must never be logged in LAB documentation.
- `backup_GrayMUG/` is ignored by git so production reference files do not appear in normal staging.

## 8. Recommended Hell Engine Scaffold

Recommended experimental areas:

- `hell_engines/Hellhound/`: Lead Line Universe Priority and Execution Guidance Attachment PoC.
- `hell_engines/Hellward/`: LAB risk hint and calibration hint PoC.
- `hell_engines/Hellcore/`: BTC accumulation context and Core payload PoC.

Rules:

- Do not copy production code into Hell engines.
- Use contracts and adapters instead of direct production edits.
- Keep LAB outputs as reference payloads unless a future explicit attachment plan upgrades them.

## 9. Next Step

WhaleLab-005-H should define the first live attachment plan against Hellhound only:

- Primary: after Hound universe build / before scanner execution.
- Secondary: after Hound alert / Execution Guidance attachment.
- No threshold replacement.
- No automatic orders.
- No Ward or Core decision replacement.
