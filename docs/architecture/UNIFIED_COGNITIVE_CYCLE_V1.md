# Unified Self-Evolving Brain V1 — cognitive loop acceptance (14 October 2026)

Scope: **the existing Katarina intelligence and one canonical contextual observer**.
This is **not** a parallel AI, new Management team, additional scheduled task,
production self-code writer, trading order source, or external LLM impersonation.

## Full research cycle (implemented)

1. **Observasi:** the existing `ProspectiveShadowBook` receives completed broker
   bid/ask *virtual* quote observations, with explicit gaps and timestamps.
2. **Episodic memory:** `unified_cognitive_cycle.py` preserves a bounded,
   chronological, immutable sample of matured events (including losses)
   with a digest covering the full rolling observation window.
3. **Semantic memory:** research cohorts are indexed independently by
   `symbol/method/BUY-or-SELL/regime`, recording uncertainty, mature counts,
   quote path gaps, evidence thresholds and the result status.
4. **World model:** descriptive per-regime conditional outcomes and observed
   regime transitions are computed from past events only. This is **not**
   a calibrated forecast model and cannot claim actual executable edge.
5. **Causal reasoning:** the loop produces falsifiable associations, competing
   explanations (macro regime, spread/costs, missing quote bias) and explicit
   disconfirmation tests. An association is **not** proof of causality.
6. **Artificial Curiosity:** a deterministic evidence-gap planner ranks
   investigative questions across instrument, method, direction and regime.
   The next existing virtual research sampler uses these priorities while
   preserving the broker, geometry, threshold, idempotency and portfolio gates.
7. **Scientific experimentation:** the existing self-evolution lab tests
   score thresholds chronologically using train/held-out virtual samples.
   The new loop records proposed next tests, train-vs-holdout diagnostics,
   evidence gaps, and the obligatory production action `WAIT`.
8. **Metacognition:** detects train/holdout sign reversals, incomplete paths,
   absent official news, unverified costs, missing broker fills and causal
   uncertainty; recommends rejection/replication rather than self-approval.
9. **Continual learning:** every new matured observation changes the
   deterministic fingerprint, causing one append-only SHA256 checkpoint;
   reprocessing an unchanged snapshot or restarting does not duplicate it.
   No watch/cron/daemon has been enabled by this change.
10. **Rollback and Owner control:** `rollback_cognitive_research` requires
    explicit `owner_approved=True`, records a hash-chained `ROLLBACK` event,
    and keeps all previous evidence intact. Replaying an existing rolled-back
    snapshot **pauses further virtual proposals** until genuinely new closed
    evidence arrives. No broker positions or production policy are rolled back.
11. **Feedback:** the canonical observer runs exactly one loop after settling
    existing virtual quotes and before selecting the next virtual observation.
    Brain curiosity can change only experimental sample priority. The existing
    Risk Governor, Profit Lock, Owner positions, live authorization and
    market order execution paths are not modified.

## Validation

```powershell
$env:PYTHONPATH = "src;."
py -3 -B -m unittest tests.unit.intelligence.test_unified_cognitive_cycle -q
py -3 -B -m unittest tests.integration.test_unified_katarina_stack -q
py -3 -B scripts/ai/verify_unified_katarina.py --shadow-db "C:\Katarina\state\readonly-observer\context.sqlite3"
```

The checker and optional shadow DB probe are **strictly read-only** and never
start MT5. The cognitive ledger does not appear in the original data unless
the already-existing canonical observer is *independently authorized and
actually invoked* with terminal trading disabled.

The 14 Oct 2026 persistence evidence (an isolated SQLite backup of 7 research
observations, **not** live broker execution) lived in the old VPS layout
`C:\KatarinaDev\artifacts\cognitive-v1-20261014\`, which no longer exists. On the
current VPS the observer state is `C:\Katarina\state\readonly-observer\`; the probe
above only reads it and never changes the original `context.sqlite3`.

## Release acceptance constraints

- Timestamp-aware, past-only; no future outcomes, random profit claims,
  fabricated trades, external AI agent credentials, or live market orders.
- Cognitive LEARN/ROLLBACK ledger timestamps must be timezone-aware and
  nondecreasing. A restarted or backdated observer cannot append a checkpoint
  earlier than its last persisted event, even if the virtual evidence differs.
  A rewritten earlier ledger timestamp is rejected on history verification.
  Read-only previews are unaffected and no clock correction is fabricated.
- SHA256 ledger integrity and source fingerprint are verified before
  appending any memory. Schema/tamper failures block the observer.
- Existing research persists through a restart; rollback is visible and
  cannot silently resample an already rejected result.
- No autonomous code rewrite, no autonomous model promotion, no Owner risk
  threshold changes. Risk max 5% per entry and 8% open, Profit Lock 25%
  remain in the existing protected subsystem.
- Backtesting and synthetic test success **does not** establish positive
  forward expectancy. The separate broker authentication, real cost,
  prospective forward and demo release gates remain BLOCKED.
- Memory is rolling-window bounded (last 3,500 shadow records) and individual
  episode previews keep up to 64 samples; older checkpoint receipts remain in
  the ledger. Do not interpret this as unlimited long-term knowledge.
- Management and its 11 specialist roles were removed by Owner on 2026-10-15;
  their scripts, workplan and workflow hooks are absent from the current tree.

The User's `GAS EKSEKUSI` authorized this *Poin 1* engineering change;
it did **not** authorize enabling live trading or creating scheduled tasks.
