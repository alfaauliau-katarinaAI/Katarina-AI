# KATARINA MT5 BRIDGE EA — DRAFT

**Status:** IN REVIEW  
**Version:** 0.5.0  
**Stage:** 06/40

## 1. Role

The MT5 Bridge is a sensor plus deterministic safety/execution gateway. It is not a discretionary strategy.

~~~text
BROKER / MT5
     ↓
Katarina Bridge EA
     ├─ capture broker facts
     ├─ capture manual/Katarina trade lifecycle
     ├─ build complete native snapshots
     ├─ enforce local execution invariants
     └─ report actual broker state
     ↓
Stage-07 Transport
     ↓
Katarina Core / Brain
~~~

## 2. Single Bridge Instance

Baseline V1 uses one logical bridge instance per account/execution namespace.

Reasons:

- one execution journal namespace;
- one stream_id / boot_id;
- one account-wide snapshot/reconciliation owner;
- one idempotency authority;
- easier manual-trade learning across the whole account;
- avoids independent chart EAs racing to mutate the same account.

The bridge may observe multiple symbols later; it must not require one independent trading brain per chart.

## 3. Event Handler Rules

### OnInit

Responsibilities:

- validate local terminal/account prerequisites;
- initialize bridge state;
- create new boot identity;
- initialize event buffers;
- start timer;
- enter RECOVERING / NOT ARMED.

If mandatory local initialization fails, return an initialization failure code.

### OnTick

Allowed:

- capture latest tick;
- capture local timestamp;
- update a coalesced latest-tick slot;
- return.

Forbidden:

- network blocking;
- AI/model inference;
- complete account scans;
- history scans;
- order execution;
- reconciliation.

### OnTradeTransaction

Allowed:

- copy fields needed for later interpretation;
- assign local capture ID;
- enqueue into the lossless-required transaction buffer;
- set critical-integrity failure if the buffer cannot accept the event;
- return.

Forbidden:

- assuming transaction arrival order;
- treating one event as full order truth;
- long history/reconciliation work;
- blocking transport calls.

### OnTimer

Bounded housekeeping owner:

- drain captured transaction events;
- publish/coalesce latest market state later through Stage-07 transport;
- sample account/permission health;
- process bounded transport work later;
- process bounded command work later;
- maintain heartbeat/status.

### OnDeinit

- disable new execution;
- stop timer;
- mark stopping;
- release resources.

## 4. Local Bridge State

~~~text
BOOTING
RECOVERING
READY_READONLY
READY_ARMABLE
BLOCKED
STOPPING
STOPPED
~~~

Stage 06 remains effectively read-only for external commands until communication/execution wiring is added.

## 5. Critical Integrity State

Local flags include:

- critical_event_integrity_ok;
- account_binding_ok;
- symbol_spec_ok;
- terminal_connected;
- terminal_trade_allowed;
- mql_trade_allowed;
- snapshot_available;
- transport_ready;
- reconciled;
- execution_armed.

Any critical-integrity failure closes new-risk admission.

## 6. Capture Architecture

~~~text
OnTradeTransaction
        ↓
fixed bounded critical queue
        ↓
OnTimer bounded drain
        ↓
Stage-07 transport port
~~~

~~~text
OnTick
   ↓
latest tick slot (coalesced)
   ↓
OnTimer bounded publish
~~~

Trade lifecycle is lossless-required. Ticks are latest-state/coalescible when backlogged.

Stage-06 local_capture_id is only an internal observation identifier. It must not be serialized as KAT1 sequence. Stage 07 assigns the canonical frame sequence after permitted coalescing.

## 7. Manual Trades

Manual desktop/mobile/web activity is observable where MT5 exposes raw broker reason/type fields.

Bridge rule:

- capture raw broker reason/type;
- do not destructively relabel raw evidence;
- normalized origin classification stays separate;
- manual orders/positions are read-only by default.

## 8. Snapshot Builder

A complete native snapshot must distinguish:

~~~text
VALID COMPLETE EMPTY STATE
vs
READ FAILED / SNAPSHOT UNAVAILABLE
~~~

The bridge must never convert read failure into false empty positions/orders.

Snapshot scope includes account state, symbol specs, positions, pending/open orders, relevant history watermarks, and permissions/terminal health.

## 9. Execution Gateway

Stage 06 defines the local gateway boundary but does not yet enable external live execution.

When later enabled, the sequence remains:

~~~text
binding
→ expiry/freshness
→ symbol/account capability
→ idempotency reservation
→ lot/stops/margin/exposure preflight
→ OrderCheck
→ reread critical state
→ material-change rejection
→ OrderSend once
→ OnTradeTransaction/history reconciliation
~~~

OrderSend true is never treated as final fill truth.

## 10. Mandatory Native SL

Every Katarina-owned exposure-creating MARKET/LIMIT/STOP request must already contain approved broker-native SL.

The bridge must later reject missing/invalid SL, stale SymbolSpec, unsupported order types, invalid volume rules, and binding/revision mismatches.

## 11. Hedging / Netting

The bridge reports native account mode and raw order/position facts.

Hedging may have multiple positions per symbol. Netting has one net position per symbol, with POSITION_IDENTIFIER as stable lineage and ticket as current broker handle.

## 12. Standard / Cent

The EA reports broker-native values. It performs no hard-coded cent conversion.

## 13. Transport Boundary

~~~text
Bridge
   ↓
IKatTransport
   ├─ Null / development
   ├─ ZeroMQ        Stage 07
   ├─ native TCP    Stage 07
   └─ Tester        Stage 35
~~~

Event handlers do not know concrete transport implementation details.

## 14. Failure Policy

Examples forcing BLOCKED / no new risk:

- critical transaction queue overflow;
- account identity mismatch;
- required SymbolSpec unavailable;
- invalid trade permissions;
- incomplete snapshot;
- unresolved execution outcome;
- transport/reconciliation/journal failure later.

## 15. Current Physical Layout

~~~text
mt5/
├─ Experts/
│  └─ KatarinaBridgeEA.mq5
├─ Include/
│  └─ Katarina/
│     ├─ BarSource.mqh
│     ├─ BridgeIdentity.mqh
│     ├─ BridgeState.mqh
│     ├─ BrokerCalc.mqh
│     ├─ BrokerReason.mqh
│     ├─ DealHistory.mqh
│     ├─ EventBuffer.mqh
│     ├─ ExecutionPreflight.mqh
│     ├─ HealthSample.mqh
│     ├─ InstanceGuard.mqh
│     ├─ NativeFacts.mqh
│     ├─ NativeSnapshot.mqh
│     ├─ SessionState.mqh
│     ├─ SymbolRegistry.mqh
│     ├─ TestEvidence.mqh
│     └─ TransportPort.mqh
└─ Tests/
   ├─ KatarinaStage06SelfTest.mq5
   └─ KatarinaStage06AccountProbe.mq5
~~~

Python static source checks also exist at:

- tests/static/test_stage06_mt5_bridge.py

## 16. Stage 06 Acceptance Target

Before freeze, Stage 06 should prove:

- valid MQL5 event-handler architecture;
- handler work remains capture-oriented;
- critical overflow is fail-closed;
- no discretionary signal logic exists;
- transport implementation is absent/replaceable;
- startup is not live-armed;
- manual trades are observable;
- account-wide state ownership is unambiguous;
- Stage 04 KAT1 fields can be sourced from MT5.

Stage 06 is not yet frozen.


## 17. Stage 06 v0.2 Additions

### Complete Native Snapshot Source

The bridge now has a bounded-retry native snapshot builder for:

- account facts;
- every current open position;
- every current order.

A failed read is not converted into a false empty state.

The snapshot is marked dirty by OnTradeTransaction and rebuilt later from OnTimer, never inside the transaction callback.

### Duplicate-Instance Guard

A terminal-global lease uses GlobalVariableSetOnCondition for atomic ownership inside one MT5 terminal/account context.

Lease loss blocks the bridge.

This is only local-terminal protection. Cross-terminal duplicate-account protection remains a Stage-07 identity/stream responsibility.

### Symbol Registry

The bridge distinguishes:

- execution-approved symbols;
- account-observed symbols.

The chart symbol is the only execution-approved realtime symbol in Stage 06. Symbols discovered from open positions/orders are observed for account-wide risk visibility but are not automatically granted execution authority.

### Manual-Trade Evidence

Raw ORDER_REASON, DEAL_REASON and POSITION_REASON are preserved where available.

Reason/history lookups are deliberately deferred out of OnTradeTransaction.

### Session / Health Facts

The bridge now sources:

- terminal connectivity and trade permissions;
- MQL/account trade permissions;
- terminal ping;
- broker server time;
- current trading-session schedule state;
- last tick time.

### Standard / Cent Native Facts

Account and SymbolSpec readers now include the frozen Stage-04 economic fields required for account-native sizing/reporting, including margin/stopout, symbol margin, swap mode/values, and weekday swap ratios.

### Deal History

A bounded complete history-range reader preserves raw deal type/reason and money components.

If a requested range exceeds its configured maximum, it reports failure/overflow rather than silently truncating.

### Execution Preflight Surface

The bridge now has a local validation surface for:

- approved symbol;
- broker trade direction;
- MARKET/LIMIT/STOP capability;
- volume range/step;
- mandatory broker-native SL;
- pending-price relation and minimum pending distance;
- stop side/distance;
- TP capability, side and minimum distance.

It still returns EXECUTION_DISABLED at the end of a valid Stage-06 preflight. There is no OrderSend path.

### KAT1 Source Mapping

The MT5 source for frozen KAT1 facts is documented in:

- docs/architecture/KAT1_MT5_FIELD_SOURCE_MAPPING_DRAFT.md

## 18. Remaining Freeze Blockers

Code/design work is substantially complete, but Stage 06 must remain IN REVIEW until:

1. MetaEditor successfully compiles the EA/includes/self-test;
2. the MQL self-test is run;
3. repository static test is run from a real checkout;
4. any compile/runtime corrections are applied;
5. final Stage-06 audit is completed.

Stage 07 must not rely on an uncompiled bridge.


## 19. Bridge Identity

Stage 06 now creates:

- a persistent nonzero stream_id scoped to broker server + login;
- a new nonzero boot_id on every successful bridge initialization.

The stream ID is stored as two exact uint32 halves in terminal global variables and reconstructed as uint64.

The two-half storage avoids precision loss from putting a full uint64 into one double-valued terminal global variable.

A stream ID disappearing after external cleanup/long inactivity is treated as a new stream on the next boot, which later forces normal Stage-07 recovery/reconciliation behavior.

account_id derivation and HELLO/HELLO_ACK encoding remain Stage 07.


### Single-Symbol Realtime Scope Correction

The draft briefly exposed an input for multiple execution-approved symbols while the EA's realtime OnTick source only covers its chart symbol.

That could have implied market-data coverage that did not actually exist.

Stage 06 now enforces:

- chart symbol = the only execution-approved realtime market symbol;
- all other account symbols = observable through account-wide positions/orders/trade events;
- future multi-symbol execution approval = forbidden until an explicit multi-symbol tick source is implemented and validated.


## 21. Stage 06 v0.3 Static Candidate

Continued review added the following hardening before compiler proof:

- duplicate-instance lease is scoped by broker server + login, not login alone;
- persistent stream identity can recover from a partially written two-part value by creating a new stream boundary;
- raw zero leverage is preserved as broker fact rather than making the whole account snapshot unavailable;
- MqlTradeTransaction fields are copied according to transaction type with an explicit validity bitmap;
- request/result evidence remains exclusive to TRADE_TRANSACTION_REQUEST;
- pending-order preflight now validates minimum market distance;
- optional TP now validates broker capability, direction and minimum distance;
- static regression tests expanded to cover sequence naming, type-aware transactions, single-symbol realtime scope, identity storage, duplicate-guard primitives, and all include modules.

The repository is now a **static Stage-06 candidate**.

It is not a frozen or production-certified bridge until the actual MetaEditor compiler and MT5 runtime proof pass.


## 22. Modern Windows Validation Baseline

The current Stage-06 certification path deliberately targets modern 64-bit Windows first.

Preferred proof hosts:

- Windows Server 2022 x64;
- Windows 11 x64.

Additional compatibility-validation hosts:

- Windows Server 2019 x64;
- Windows Server 2016 x64;
- Windows 10 x64.

Deferred:

- Windows Server 2012 R2 x64.

Windows Server 2012 R2 is no longer a Stage-06 freeze blocker.

The project will first produce a clean modern-Windows bridge and only revisit Server 2012 R2 after the finished system is stable, if that deployment target is still needed.

The modern validation path may not weaken Core/Bridge safety invariants merely to preserve legacy compatibility.

Machine-readable baseline:

- `config/windows_compatibility_stage06.json`

Operational procedure:

- `docs/operations/STAGE_06_WINDOWS_COMPATIBILITY.md`
- `scripts/mt5/check_stage06_host.ps1`
- `scripts/mt5/compile_stage06.ps1`

### Strict compiler evidence

The modern-Windows compile proof now requires:

~~~text
MetaEditor actual compile
+
explicit UTF-16LE log parsing
+
0 errors
+
0 warnings
+
fresh non-empty EX5 artifact
+
SHA-256 source/artifact evidence
~~~

Old EX5 artifacts are removed before compilation so a stale binary cannot satisfy the proof.

The compiler proof produces:

- `build/mt5/stage06_compile_evidence.json`

This evidence becomes an input to the final Stage-06 audit.


## 23. Stage 06 v0.5 Source / Design Completion

A final GitHub prior-art review identified four Stage-06 hardening gaps that were still worth closing before compiler proof.

### Count + Time Bounded Timer Work

The timer now has both:

~~~text
max drained items = 64
timer budget      = 2000 microseconds
~~~

Transport pumping receives the remaining microsecond budget.

Critical events are serviced before snapshot work.

A snapshot rebuild starts only when:

- the critical trade queue is empty;
- at least the configured timer reserve remains.

Individual MT5 API calls are not preemptible. Therefore runtime metrics record actual maximum timer elapsed time and budget-exhaustion count rather than making a false hard-realtime claim.

### Backpressure Observability

The bridge now records:

- trade queue high-watermark;
- rejected critical trade-event total;
- tick capture total;
- tick coalescing total;
- timer budget exhaustion total;
- maximum timer elapsed microseconds.

Critical trade-event rejection remains fail-closed.

### Numeric / Tick-Grid Preflight

The local execution-disabled preflight now also rejects:

- invalid side;
- invalid/non-finite numeric values via MathIsValidNumber;
- invalid broker point/tick-size facts;
- pending, SL or TP price not aligned to SYMBOL_TRADE_TICK_SIZE.

No broker mutation path is enabled.

### Runtime Evidence

MQL tests now emit FILE_COMMON evidence:

~~~text
Katarina_Stage06_self_test_result.txt
Katarina_Stage06_account_probe_STANDARD_LIKE.txt
Katarina_Stage06_account_probe_CENT_LIKE.txt
~~~

The account class is explicitly supplied by the operator; Katarina does not infer standard/cent from a marketing label or currency convention.

Runtime evidence is collected with:

- `scripts/mt5/collect_stage06_runtime_evidence.ps1`

Final runtime manifest:

- `build/mt5/stage06_runtime_evidence.json`

GitHub research and adoption decisions are documented in:

- `docs/reviews/STAGE_06_GITHUB_REFERENCE_AUDIT.md`

At v0.5.0, **Stage-06 source/design work is complete**.

Remaining work is external proof:

- actual MetaEditor compile;
- actual MQL self-test;
- standard-like account probe;
- cent-like account probe;
- evidence collection;
- final freeze audit.

> Catatan 22 Okt 2026: jalur ZeroMQ/TCP Stage 07 di draf ini sudah dipensiunkan dan kodenya dihapus dari `main`.
> Python membaca MT5 lewat paket MetaTrader5 (observer read-only); order hanya ke akun demo lewat `DemoExecutionBoundary`.
