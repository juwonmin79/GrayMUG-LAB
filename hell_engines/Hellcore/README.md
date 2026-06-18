# Hellcore

Hellcore is the experimental Core attachment space for GrayMUG-LAB.

Purpose:

- Test LAB Core payload consumption without modifying Production Core.
- Evaluate BTC accumulation context and operating mode reference payloads.
- Preserve Core's independent strategy and stoploss behavior.

Initial attachment candidates:

- BTC accumulation context.
- Core payload reference.
- BEAR_ESCAPE / BTC_ACCUMULATION / OBSERVE_ONLY mode context.
- Hound result feedback context measured against BTC accumulation.

Rules:

- Do not copy Production Core code into this folder.
- Do not replace Core strategy decisions.
- Do not override stoploss or lockdown behavior.
- Do not add automatic orders, sizing, or position management.
