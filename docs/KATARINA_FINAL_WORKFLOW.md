# KATARINA AI — FINAL MT5 EXECUTION WORKFLOW

**Status:** FROZEN  
**Version:** 1.2.0  
**Stage:** 02/40 — PASSED  
**Purpose:** Canonical end-to-end workflow from MT5 data capture through Katarina decisioning, risk approval, broker execution, reconciliation, position management, memory, and learning.

## 1. Authority

```text
HUMAN PROJECT OWNER
        ↓
KATARINA CONSTITUTION
        ↓
KATARINA BRAIN        decides WHAT
        ↓
RISK GOVERNOR         decides WHETHER / HOW MUCH
        ↓
EXECUTION ENGINE      decides HOW TO EXECUTE SAFELY
        ↓
MT5 / BROKER          performs ACTION
        ↓
RECONCILIATION        establishes ACTUAL STATE
```

MT5/MQL5 does not invent discretionary BUY/SELL decisions. Communication, data, or intelligence failure must not create new live risk.

## 2. Canonical Flow

```text
MT5 FAST EVENT CAPTURE
  ├─ TickEvent
  ├─ BarEvent
  ├─ AccountDelta
  ├─ PositionDelta
  └─ TradeEvent
        ↓
BOUNDED PRIORITY EVENT BUFFER
        ↓
VERSIONED BINARY CODEC
        ↓
TRANSPORT ABSTRACTION
  ├─ Live KAT1 ZeroMQ/TCP: RETIRED 2026-10-22
  ├─ Current: MetaTrader5 Python package (read-only observer;
  │           demo orders only via DemoExecutionBoundary)
  └─ Tester: TesterTransport
        ↓
KATARINA INGEST
        ↓
STATE CACHE
        ↓
IMMUTABLE SNAPSHOT BUILDER
        ↓
DATA / SEQUENCE / HEALTH VALIDATION
        ↓
KATARINA ANALYSIS
  ├─ Regime
  ├─ Multi-timeframe
  ├─ Economic/event context
  ├─ Memory
  ├─ Strategy/model ensemble
  └─ Uncertainty / OOD
        ↓
TRADE CANDIDATE
        ↓
RISK GOVERNOR
  ├─ REJECT
  ├─ REDUCE
  └─ APPROVE
        ↓
DETERMINISTIC POSITION SIZING
        ↓
EXECUTION INTENT
        ↓
MT5 EXECUTION GATEWAY
  ├─ identity / protocol validation
  ├─ freshness / price / spread validation
  ├─ duplicate / journal check
  ├─ OrderCheck
  ├─ final revalidation
  └─ OrderSend
        ↓
BROKER
        ↓
OnTradeTransaction + broker/history reconciliation
        ↓
ORDER STATE + POSITION STATE
        ↓
POSITION MANAGEMENT
        ↓
CLOSE
        ↓
TRADE EXPERIENCE / MEMORY
        ↓
RESEARCH / VALIDATION / LEARNING
```

## 3. Startup / Reconnect Gate

No new live risk is permitted immediately after startup or reconnect.

Required sequence:

1. Transport connection.
2. HELLO / protocol-version handshake.
3. Instance identity validation.
4. Account, broker, symbol, magic, EA build and mode binding.
5. Capability negotiation.
6. Complete initial account/symbol/position snapshot.
7. Durable execution journal restore.
8. Event cursor / sequence restore.
9. Broker reconciliation against open orders, positions, deals and journal.
10. Katarina health + Risk Governor readiness.
11. State becomes `READY`.

Until step 11:

```text
EXECUTION_STATE = RECOVERING
NO NEW LIVE RISK
```

## 4. Instance Identity and Capabilities

Each MT5 bridge instance must expose stable/bounded identity sufficient to prevent cross-account or wrong-instance execution.

Logical identity includes:

- account_id / broker account identity;
- broker server;
- symbol or approved symbol set;
- magic / strategy execution namespace;
- protocol version;
- EA build/version;
- stream_id persisted across boots;
- boot_id changed on each successful initialization;
- execution mode: READ_ONLY / DEMO_ARMED / LIVE_ARMED;
- supported order/filling/account modes.

A command with incompatible binding must fail closed.

## 5. Fast MT5 Event Capture

Realtime handlers must stay lightweight.

`OnTick` should:

- capture the latest tick state;
- assign/update sequence and timestamp metadata;
- enqueue/coalesce market data according to queue policy;
- return quickly.

Heavy AI work, full history transfer, blocking network calls, and model inference do not belong in `OnTick`.

`OnTradeTransaction` is used to emit authoritative broker transaction lifecycle events.

## 6. Event Priority and Backpressure

Queues are bounded. Unbounded memory growth is prohibited.

Priority order:

1. execution / TradeEvent / reconciliation events;
2. risk-critical account and position changes;
3. bar events;
4. tick events.

Allowed behavior:

- latest tick per symbol may be coalesced when backlog exists;
- redundant noncritical telemetry may be coalesced.

Forbidden behavior:

- silently dropping execution lifecycle events;
- silently dropping state changes needed for risk/reconciliation.

If critical queue integrity cannot be guaranteed:

```text
TRANSPORT_DEGRADED
→ NO NEW LIVE RISK
```

## 7. Transport and Codec

Authoritative policy:

- production hot path: versioned binary;
- flexible lower-frequency control: structured binary / MessagePack candidate;
- live KAT1 transport (ZeroMQ localhost primary, native local TCP fallback): **retired on 22 October 2026**;
  the implementation was removed from `main` and only the `protocol/` message schemas remain as the
  contract for the validation and health engines;
- current MT5 ↔ Python path: the MetaTrader5 Python package — read-only for the observer, and demo-only
  order submission through `DemoExecutionBoundary` behind the Risk Governor;
- Strategy Tester: dedicated TesterTransport;
- JSON: audit/debug/config/test fixtures only.

Katarina Brain must remain independent from transport and codec implementation.

## 8. Time, Sequence and Freshness

Every authoritative event carries enough metadata to reason about order and freshness.

Required concepts:

- event timestamp;
- receive timestamp;
- per-stream sequence number;
- stream_id;
- boot_id;
- protocol version.

Katarina must detect:

- stale events;
- sequence gaps;
- duplicated events;
- stream resets;
- unexpected boot changes.

Clock-health status is part of system health. Exact timestamp encoding and monotonic timing fields are defined in Stage 04.

## 9. State Cache and Complete Snapshot

MT5 sends deltas/events; Katarina maintains the latest state cache.

Decision snapshots are immutable and must reference a coherent set of:

- market state;
- required bars/history;
- account state;
- positions/orders;
- broker/execution health;
- sequence/stream state.

If a required native read fails, Katarina must not substitute an invented empty account/position set.

```text
INCOMPLETE SNAPSHOT
→ SNAPSHOT_UNAVAILABLE
→ NO NEW LIVE RISK
```

## 10. Traceability

The full path must remain reconstructable:

```text
snapshot_id
→ decision_id
→ risk_decision_id
→ execution_intent_id
→ order_id
→ broker order/deal/position IDs
```

A correlation_id may join the full chain.

## 11. Data Validation

Validate, at minimum:

- message/schema/protocol compatibility;
- stream and sequence consistency;
- timestamp freshness;
- complete required history;
- price/bid/ask consistency;
- spread state;
- symbol specification availability;
- account state;
- position/order state;
- transport health;
- clock health.

Critical failure means SAFE MODE / NO NEW LIVE RISK.

## 12. Katarina Decision Flow

The Brain uses validated state to evaluate:

- regime;
- multi-timeframe structure;
- economics/events;
- memory;
- strategy/model evidence;
- uncertainty;
- out-of-distribution state.

Output is a Trade Candidate, not a broker order.

A candidate contains logical equivalents of:

- symbol / direction;
- entry concept;
- invalidation;
- proposed SL / TP / exit policy;
- expected risk/reward;
- calibrated probability and/or model confidence;
- evidence for/against;
- uncertainty / OOD state;
- model/strategy version;
- snapshot_id;
- validity window.

## 13. Risk Governor

Every live capital action passes the non-bypassable Risk Governor.

It considers, as applicable:

- per-trade risk;
- aggregate risk;
- drawdown / session / daily limits;
- symbol and currency exposure;
- correlation;
- margin / leverage;
- volatility / spread;
- execution health;
- data health;
- uncertainty / OOD state.

Output: REJECT / REDUCE / APPROVE.

## 14. Deterministic Position Sizing

Exact size is computed after approval from approved risk, stop distance, tick/contract values, lot min/max/step, margin constraints, and broker specifications.

Probabilistic AI may recommend risk but does not invent the final unsupported lot.

## 15. Execution Intent

Execution Intent contains logical equivalents of:

- execution_intent_id;
- order_id;
- snapshot_id;
- decision_id;
- risk_decision_id;
- symbol / side / order type;
- final size;
- entry instruction;
- SL / TP / exit policy;
- approved risk;
- deviation/slippage policy;
- expiry;
- model/strategy version;
- instance binding.

## 16. Durable Idempotency

Before the first irreversible broker submission attempt, MT5 must durably reserve the `order_id` / client request identity with its normalized payload.

Rules:

- same ID + same payload → return known stored state, never duplicate;
- same ID + different payload → `IDEMPOTENCY_CONFLICT`;
- restart must not erase the reservation;
- journal corruption or ambiguous recovery blocks new execution until reconciled.

## 17. Pre-Execution Gate

Immediately before submission:

1. validate protocol and binding;
2. verify instruction not expired;
3. validate price deviation and spread;
4. validate symbol / market / trade permission;
5. validate lot / stops / margin / exposure inputs;
6. verify durable idempotency state;
7. run `OrderCheck`;
8. re-read critical current state after `OrderCheck`;
9. reject if freshness, exposure, capacity or price assumptions are no longer valid;
10. call `OrderSend` only once for that reserved request.

MT5 may apply only explicitly authorized deterministic safety normalization; it may not invent a different discretionary strategy.

## 18. Broker Execution Truth

The boolean return of `OrderSend` is not treated as final fill truth.

Authoritative execution state comes from:

- broker result codes;
- `OnTradeTransaction` events;
- order/deal history;
- current positions;
- reconciliation against the durable execution journal.

Possible logical order states:

```text
CREATED
RESERVED
VALIDATED
SUBMITTING
SUBMITTED
PARTIALLY_FILLED
FILLED
REJECTED
CANCELED
EXPIRED
UNKNOWN
ERROR
```

## 19. Unknown Outcome Rule

If a broker submission may have occurred but its exact result cannot be proven because of timeout, disconnect, contradictory fields, process crash, or missing transaction evidence:

```text
ORDER_STATE = UNKNOWN
AUTO-RETRY = FORBIDDEN
NEW RISK ON AFFECTED EXECUTION SCOPE = BLOCKED
RECONCILIATION = REQUIRED
```

Unknown is safer than inventing FILLED or REJECTED.

## 20. Event Journal and Replay

Execution lifecycle events are durable and ordered.

The system maintains a logical event cursor / sequence allowing Katarina to:

- detect gaps;
- request/replay missing critical events;
- restore after restart;
- prove whether execution state was fully reconciled.

Trade events cannot rely only on ephemeral realtime delivery.

## 21. Reconciliation

Reconciliation runs:

- at startup;
- after reconnect;
- after unknown outcomes;
- after sequence gaps affecting execution;
- periodically as a consistency check.

It compares:

- local durable requests/journal;
- broker open orders;
- broker positions;
- order/deal history;
- Katarina expected state.

Only reconciled state may return execution scope to READY.

## 22. Position State

Order lifecycle and position lifecycle are distinct.

```text
ORDER:
CREATED → RESERVED → SUBMITTED → PARTIAL/FILLED
                            ↘ REJECTED/CANCELED/UNKNOWN

POSITION:
CREATED → ACTIVE → MANAGING → EXITING → CLOSED
```

Katarina manages positions from actual broker state, not assumed order intent.

## 23. Position Management

Validated management actions may include:

- HOLD;
- MODIFY_SL;
- MODIFY_TP;
- PARTIAL_CLOSE;
- REDUCE_POSITION;
- CLOSE;
- policy-authorized break-even behavior.

They remain subject to safety, idempotency where applicable, and reconciliation.

## 24. Local Emergency Safety

Local deterministic safety may:

- block new entries;
- enter SAFE MODE;
- cancel invalid pending state when policy permits;
- execute predefined emergency protection.

It may not invent a new trading thesis.

```text
NO KATARINA
OR INVALID CRITICAL DATA
OR INVALID TRANSPORT
OR UNRECONCILED EXECUTION
= NO NEW LIVE RISK
```

## 25. Localhost Security Boundary

Production live messaging must bind/connect only to localhost unless a future security review explicitly approves otherwise.

Execution must require explicit arming and correct instance/account binding.

Transport exposure to a public interface is not part of the approved baseline.

## 26. Strategy Tester

TesterTransport must expose the same logical event/command contracts as live transport while remaining deterministic.

Tester-specific transport must not leak file-I/O logic into Katarina Brain.

## 27. Trade Experience and Learning

After closure, preserve:

- full decision lineage;
- risk decision;
- requested vs actual execution;
- transaction costs;
- latency/slippage;
- MAE/MFE;
- R multiple;
- outcome;
- exit reason;
- regime/evidence/model versions.

Learning path remains:

```text
OBSERVE
→ RECORD
→ EVALUATE
→ DETECT DRIFT/DEGRADATION
→ HYPOTHESIZE
→ OFFLINE TRAIN
→ BACKTEST
→ OOS
→ WALK-FORWARD
→ ROBUSTNESS
→ SHADOW/PAPER
→ COMPARE
→ APPROVED PROMOTION
→ MONITOR
→ ROLLBACK
```

## 28. Latency Observability

Measure enough components to locate delay:

- event capture;
- queue wait;
- encode;
- transport;
- decode/ingest;
- snapshot build;
- analysis/features;
- decision;
- risk;
- return transport;
- MT5 preflight;
- broker execution.

Exact budgets are set later by profiling, not guessed here.

## 29. Frozen Safety Invariants

1. MT5 cannot invent discretionary BUY/SELL decisions.
2. Every live entry needs valid Katarina decision lineage.
3. Every live entry needs Risk Governor approval.
4. Every broker mutation is idempotent.
5. Ambiguous execution is UNKNOWN, never automatically retried.
6. Startup/reconnect is fail-closed until reconciliation.
7. Critical execution events are durable/replayable.
8. Incomplete native reads cannot be converted into false empty state.
9. Critical queue/event loss means NO NEW RISK.
10. Transport/codec implementation is replaceable without changing the Brain.
11. Realtime production hot path is binary-first.
12. JSON is not required in the realtime hot path.
13. Live transport is localhost-bound in the baseline.
14. Learning cannot bypass validation.
15. Live capital is not a research sandbox.

## 30. Stage 02 Acceptance

Stage 02 is passed because the workflow now defines:

- authority boundaries;
- live vs tester transport;
- binary-first wire direction;
- fast MT5 event capture;
- state cache and immutable snapshots;
- startup/reconnect recovery;
- instance binding and capability handshake;
- queue/backpressure behavior;
- sequence/freshness logic;
- decision/risk separation;
- deterministic sizing;
- durable idempotency;
- broker truth and UNKNOWN handling;
- transaction journaling/replay;
- order/position state separation;
- reconciliation;
- fail-safe local behavior;
- end-to-end traceability;
- latency observability;
- memory/learning feedback.

Exact data fields and byte layouts are intentionally deferred to Stage 04.
