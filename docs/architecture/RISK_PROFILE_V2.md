# Katarina — Unified Owner Risk Policy (14 October 2026)

This supersedes previous **drawdown mode boundaries** of daily 10% halt and
total 20% halt. The independent Risk Governor still protects account-wide
exposure and never delegates hard limits to the trading brain.

## Final drawdown behavior

- **0–below 10%:** NORMAL, evidence-qualified entries.
- **10–below 23%:** CAUTION, risk reduced; no compulsory lot increases.
- **23–below 35%:** RECOVERY_FACTOR_ONLY, no standard entries.
  A Recovery Factor entry needs genuine independent positive-edge evidence,
  execution costs, spread/slippage, equity/margin headroom and risk budgets.
  The Recovery Factor performance statistic alone is not a trade signal.
- **35% or more caused by Katarina or unknown cause:** EMERGENCY_LOCKDOWN
  for the remainder of that trading day, even if Owner later manually enters.
- **35% or more demonstrably CAUSED by manual Owner activity:** Katarina may
  assess EXTREME_SURVIVAL / EXTREME_RECOVERY **the same day**. It can create
  new positions only when the independent governor approves validated
  exposure, equity, margin and recovery edge. Otherwise survival is
  protection-only, with zero new risk.
- If Katarina first locked itself, and Owner worsened the loss afterward,
  the next trading day can assess Owner Extreme Recovery, never unlock same
  day. Existing manual Owner positions remain solely under Owner authority.

Drawdown uses account-wide equity and cashflow-adjusted high-water accounting.
Verified Owner-origin realized **and floating** P/L must be included.
Large lots or a manual-looking origin tag alone are not proof of causation;
uncertain attribution fails closed. Clock/day must reflect the verified
broker-server trading session; current KAT1 day-key is UTC and needs
separate broker-session verification.

## Safety constraints

- 5% hard maximum per entry, **8% aggregate open risk** (manual positions and
  pending orders included), before more conservative adaptive sizing.
- Any unknown or unbounded exposure, missing stop, missing currency/broker
  spec, no healthy margin or unreliable account reconciliation blocks risk.
- No martingale or obligatory lot escalation. Broker fills/slippage/gaps
  mean a threshold cannot guarantee a precise maximum realized DD.
- Only Katarina-owned positions may be modified or closed by Katarina.
  Owner manual position commands require explicit Owner authorization.
- Deposits are not realized profits. The Profit Lock is a **logical accounting
  reserve**, not money already withdrawn into a separate safe account.
- Live execution stays OFF until verified data, independent reconciled origin
  attribution, forward testing and explicit release approval exist.

Existing `OwnerDrawdownTracker` is an offline deterministic policy component.
An independent real account/broker P/L attribution feed has **not** yet been
verified as connected; never mark Owner Extreme Recovery ready for live
trading merely because these unit tests pass.

Historical backtest research documents are retained as historical evidence;
their old assumptions do not override this final Owner policy.

## Safety implementation phase — 14 October 2026

- The existing broker P/L risk module now has a conservative **arithmetic** P/L attribution reconciler, with unknown-origin veto and verification of account equity delta after cash flows.
- Recovery entry coordination requires a `BrokerSessionEvidence` object whose timestamp and observed server UTC offset reproduce the broker day; UTC fallback is not accepted as proof of broker trading day. Its `broker_clock_authenticated` field must be bound to a real authenticated broker clock provider before live use.
- The per-position realized/floating provider does not yet exist in frozen KAT1 events. To prevent a forged Owner loss flag from authorizing leverage, the existing `AccountRiskCoordinator` **always pauses EXTREME_RECOVERY** until an authenticated broker adapter is implemented and tested. Offline `OwnerDrawdownTracker` classification still preserves the agreed rule, but it is not live trading authority.
- On restart, old reserve 30% or old DD-limit snapshots are rejected **before any runtime state is modified**. No silent migration or cash reserve release takes place.
- Still blocked: broker-native per-position deal/mark data, authenticated broker-server timezone/session, approved migration of legacy capital states, MT5 adapter verification and actual demo forward validation. Trading live stays disarmed.

## Capital restart safety and legacy migration preview (14 October 2026)

- Capital snapshot restoration now validates every field and the realized balance / active / reserve accounting identity **before mutating state**. NaN, infinity, impossible capital splits and type errors refuse restore.
- Runtime snapshot restoration dry-runs component rehydration on detached copies **before any live account risk reservation is changed**, preventing a later invalid capital or broker-risk record from partially resetting previous risk state.
- `CapitalCompoundingEngine.preview_legacy_migration(...)` is a **pure offline preview**, not an activation path. A historic 30% reserve is preserved **in full** when generating a candidate 25% policy snapshot; next milestone cannot be lowered below the old policy's target or the last reached realized balance milestone doubled. This does not physically withdraw funds, authorize reserve release, or modify saved VPS files.
- **Existing old snapshots remain blocked** by `RuntimeStatePersistence` until a separate reviewed and authorized migration has been verified against authoritative broker cash flows. Do not auto-apply the proposed preview to production memory.

## Unified Brain prospective feedback (14 October 2026)

The **existing** self-evolution lab is now connected back to the **existing**
single contextual market observer and ProspectiveShadowBook. It does not create
a second worker, replace the original decision brain, or require symmetrical
BUY/SELL strategies.

After a cycle settles matured past-only virtual observations, the lab learns a
per-symbol / per-method / per-side / per-regime score threshold from
chronological training and held-out quote diagnostics. The following virtual
research proposal uses that threshold, and its receipt/digest is reported.
Positive-held-out cohorts may increase the sampled score floor; loss-heavy
cohorts are conservatively quarantined at 0.78; insufficient-evidence cohorts
retain baseline 0.62. No threshold is reduced by learning.

Corrupt or future-dated learning evidence blocks new shadow hypotheses.
This is **real feedback to research sampling**, not a profitable execution
model, broker order recommendation, risk-authorized signal, or genuine forward
edge claim. The one virtual-position limit and existing Owner Risk Governor
protections remain. The Owner-cancelled automation stays OFF.

Independent prospective performance, broker fills/costs and healthy runtime
must be verified before any strategy may progress beyond research.

## Profil DEMO dan Stage 38 (22 Okt 2026)

Profil risiko utama tetap **satu** untuk backtest, demo, dan riil (`config/risk_governor_v2.json`, termasuk stop
entry baru di drawdown harian 35%; bagian `stage38` menyatakan `uses_same_risk_profile_as_backtest_and_demo`).
Roadmap (`docs/ROADMAP.md`, Tahap 3) menambahkan **profil DEMO sebagai lapisan pembatas tambahan**, bukan
pengganti: ia dievaluasi setelah Risk Governor dan hanya boleh mengecilkan atau menolak keputusan (mis. usulan
0,5% per trade dan stop harian 3%). Profil utama, batas 35%, dan Stage 38 sebagai gerbang otorisasi eksekusi riil
tidak berubah. Evaluasi ulang batas 35% sebelum akun riil memakai hasil DEMO.

