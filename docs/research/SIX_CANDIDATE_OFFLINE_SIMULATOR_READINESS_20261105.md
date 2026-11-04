# Katarina AI — Audit kesiapan implementasi simulator OFFLINE (5 Nov 2026 WIB)

**Status rapat:** D10-K25 approved, **research design core frozen for implementation**, but **NO CODE IMPLEMENTATION, NO P/L BACKTEST, NO REGISTRATION, NO ORDERS**. Semua keputusan pada [notulen rapat](../ROADMAP_DISCUSSION.md), [spesifikasi 6 kandidat](SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md), dan [kontrak simulator](SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md). Dokumen ini **gate checklist**, bukan bukti kode telah lulus.

## 1. Scope yang sudah diputuskan dan dapat dijadikan target coding

| Komponen | Requirement |
|---|---|
| Candidate | B1/S1 M15 pivot 2+2 and same-M5 sweep/reclaim min 1 tick; B2/S2 H1 HH+HL/LH+LL and fresh H1 zone M15 first-touch confirmation; B3/S3 H1 BOS>=1tick + single M5 retest within 6 closed bars |
| Swing/zone | M15 swing TTL 96, H1 swing TTL 72, H1 zone TTL 48; origin opposite last closed H1 in 12 H1 preceding BOS, full wick; first-visit only, hybrid invalidation |
| Overlap D10-K25 | One BID tick touches N eligible zones: choose one with nearest proximal boundary, newer confirmed_at then zone_id; every other touched zone immediately CONSUMED; untouched remain FRESH; no second-chance entry |
| Execution | Chronological verified tick replay; BID touch/breach, BUY entry ASK/SELL entry BID, BUY exit BID/SELL exit ASK; no OHLC-derived fill or invented future price |
| SL/TP | Structure invalidation + max(tick, spread, 0.1 ATR14 Wilder on closed TF bars), rounded to broker tick; nearest valid structural TP, no minRR |
| Exit | B1/S1 12 M5/90min/preclose15min; B2/S2 12 M15/240min/preclose30min; B3/S3 24 M5/180min/preclose20min; earliest trigger generates intent, not automatic fill |
| Causal boundaries | M15 interval [open,close); tick at M15 close belongs to next candle. Only known/closed bars may determine signals; no lookahead |
| Isolation | One position per candidate, six independent experiments; no portfolio netting/hedging assumptions or aggregate edge |
| Validation | All blocked/WAIT/partial exit/gap outcomes in append-only auditable log; same input + code => same result. Holdout untouched |

## 2. Readiness matrix verified from repo `main` (read-only audit)

| Gate | Evidence in repository | Status | Required exit criteria |
|---|---|---|---|
| D0 — Rulebook | Decision notes D10-K1..K25 + six candidate spec | **DESIGN CORE ACCEPTED** | Event-to-rule traceable, no unspecified P/L optimization |
| D1 — Registry & statistical protocol | `src/katarina/research/validation.py`; `docs/research/VALIDATION_PROTOCOL.md`; `scripts/research/register_setup_hypothesis.py` | **EXISTS, NOT USED** | Each unique candidate has frozen spec/code SHA/split costs and preregister before P/L |
| D2 — Historical bar reader | `src/katarina/research/dev_dataset.py` M5/M15/H1, hash manifest, cutoff 2026-10-13T00:00Z | **EXISTS FOR BARS** | Tick replay input with verified UTC sequence plus bars and independent clock evidence |
| D3 — Tick replay & six strategy engine | `src/katarina/research/setups/simulator.py` only OHLC M5/H1, M5 max_hold_bars, no broker tick replay | **MISSING** | New separate pure engine implements all six with evidence-preserving event ledger |
| D4 — Structural TP/no minRR | `src/katarina/research/setups/core.py` still target_rr and min_rr>=.01 | **MISMATCH** | Simulator offline must use structural levels and no RR filter |
| D5 — Synthetic fixture acceptance | T01–T12 enumerated in contract | **NOT IMPLEMENTED/RUN** | All deterministic fixtures pass; no P/L calculations on real history in this gate |
| D6 — Broker contract and execution | Stop/freeze, fill/slippage, source tick sequence, missing data semantics not independently verified | **BLOCKED_EVIDENCE** | Signed/timestamped evidence; no synthetic fill presented as real |
| D7 — MT5 XAUUSD.vx sessions | `docs/maintenance/BROKER_SYMBOL_SESSION_EVIDENCE_20261103.md`: probe exists but not run on production terminal | **BLOCKED_OFFICIAL_SESSION** | Broker `SymbolInfoSessionQuote` AND `SymbolInfoSessionTrade` log, timezone/DST/holiday proof |
| D8 — Dev workspace frozen | Workspace `registry.jsonl`, `split.json`, `costs.json`, tick archive SHA, code hash not supplied for this audit | **UNVERIFIED** | Auditable development-only data before 2026-10-13; no holdout/Stage0-forward tuning |
| D9 — Research host | `scripts/research/export_dev_bars.py` restricts run to isolated MT5 research machine, forbids production observer VPS | **HOST NOT VERIFIED** | Explicitly authorized isolation; no code execution in observer runtime |

**Summary:** design-ready to **plan or authorize synthetic-only offline coding** on separate research branch. **NOT ready to run historical strategy evaluation or register final hypotheses**.

## 3. Proposed isolated implementation work packages (NOT STARTED)

1. **WP-R1 Schema/source validation:** candidate specs, symbol/tick/quote source contract, UTC timestamp and sequence proofs, independent clock evidence, official session interface, immutable input SHA. Fail closed if missing evidence. No MT5 or VPS access.
2. **WP-R2 Pure signal state machine:** confirmed 2+2 swing/TTL, BOS/H1 zone origin 12 bars, overlap consumed D10-K25, first-touch M15, B1/S1 wick reclaim M5, B3/S3 H1→M5 retest. Emit signal/reason, not P/L.
3. **WP-R3 Execution event reducer:** quote BID/ASK entry/exit, SL/TP order, 3 hybrid time exits, partial/missing tick and exit pending. No OHLC backfill, no event-order guessing.
4. **WP-R4 Synthetic-only tests:** T01–T12 plus overlap D10-K25 tests; deterministic, repeatable output; golden fixture for one signal each candidate, false signal, retry blocked, no quote, DST, ambiguous same-timestamp ticks.
5. **WP-R5 Diff and boundary audit:** ensure zero changes to `main`, production VPS, observer ledger, Risk Governor, live/demo configs, `holdout`; hash code and tests; show report of blocked cases; **Owner reviews coding results** before next phase.

**Independent verification track (parallel but does not automatically authorize backtest):** development tick archive and independent clock, actual XAUUSD.vx quote/trade sessions, symbol point/tick/stops specification, `costs.json`, `split.json`, evidence hashes. Broker probe on production terminal requires distinct explicit Owner permission and safe procedure.

## 3A. D10-K26 — evidence-first gate replaces immediate synthetic coding

**Owner memilih bukti broker/data/host terlebih dahulu**. Lihat [audit EV26-TICK-01 sampai EV26-ENGINE-08](D10_K26_EVIDENCE_FIRST_AUDIT_20261105.md). Paket P0-E1–E5 adalah prasyarat untuk meminta izin implementasi offline: verified pre-cutoff historical BID/ASK ticks+sequence/clock; `symbol_info` contract and dated costs; `SymbolInfoSessionQuote` & `SymbolInfoSessionTrade` evidence+holiday/DST; independent isolated research machine; hashed split/costs/manifests.

**Scope hold:** pekerjaan WP-R1–R5 yang tertulis di atas adalah **rencana**, **belum** mendapat izin coding. Compiler MQL5 staging berhasil tidak berarti probe boleh dijalankan pada VPS. Arsip observer Okt–Nov 2026 tidak boleh dipindahkan ke development sebelum 13 Okt 2026. Tidak ada otorisasi menggunakan VPS production observer, meluncurkan terminal baru, mengimpor data holdout, menulis registry atau menguji P/L.

## 4. Outstanding nonoptional choices and limits

- **Not an optimization parameter:** no new threshold based on observed P/L or forward/holdout; all outcomes must be predeclared before real trade evaluation.
- **G4 stop/fill model:** define exact broker stop trigger vs fill, stop/freeze levels, simultaneous/tick duplicate, gap/late ticks from evidence and tested fixtures; if unverified, `BLOCKED`.
- **No candidate registry yet:** code_sha256 and true dataset/cost/session evidence incomplete; registering a placeholder to claim progress is forbidden.
- **No access to broker production:** script `KatarinaBrokerSessionProbe.mq5` is available **but not executed**; its availability is not a run approval.
- **User approval next:** decide whether **authorize WP-R1–R4 synthetic-only implementation on separate branch** (no real data / MT5 / trading), or **first complete broker/data evidence**. Neither choice changes live execution permissions.

`D10-K25_APPROVED` · `DESIGN_READY_FOR_SYNTHETIC_IMPLEMENTATION` · `OFFLINE_ENGINE_NOT_CODED` · `FIXTURES_NOT_RUN` · `RESEARCH_DATA_UNVERIFIED` · `BROKER_SESSION_MISSING` · `NOT_REGISTERED` · `HOLDOUT_LOCKED` · `LIVE_OFF`.
