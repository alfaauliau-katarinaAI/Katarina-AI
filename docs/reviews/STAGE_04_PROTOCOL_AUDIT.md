# STAGE 04 — DATA PROTOCOL / SCHEMAS AUDIT

**Stage:** 04/40  
**Status:** PASSED / FROZEN  
**Reviewed:** 2026-10-02  
**Protocol:** KAT1 v1.0.0

## Scope Reviewed

Stage 04 now defines the canonical MT5 ↔ Katarina data language, including:

- framing;
- byte order;
- message IDs;
- exact fixed-root payload layouts;
- bounded variable fields;
- scaled execution-sensitive numeric representation;
- account/symbol identity and revision binding;
- standard + cent account-unit handling;
- Hedging + Netting semantics;
- MARKET + LIMIT + STOP entry semantics;
- broker-native protective Stop Loss requirement;
- account ledger events;
- shared-account/manual-trade learning observation;
- snapshot transaction;
- execution lineage/idempotency;
- reconciliation;
- capability/flag/reason registries;
- CRC32C policy;
- golden conformance vectors.

## References Incorporated

Stage 04 research reviewed mature binary/protocol patterns and MT5 behavior.

Important design findings incorporated:

1. fixed message IDs, schema version and block length support deterministic binary evolution;
2. raw native memory layout must not become the external wire contract;
3. MT5 account mode is an account fact and both hedging/netting require distinct position semantics;
4. POSITION_IDENTIFIER is required as stable position lineage because position ticket may change on netting reversal;
5. MT5 broker order/deal reasons allow manual desktop/mobile/web/expert and SL/TP/StopOut origin evidence to be preserved;
6. balance/credit/charge/correction and other non-trading deal types must be separated from trading P/L;
7. broker profit/margin calculation evidence is expressed in account currency and improves cross-account sizing validation;
8. symbol contract/tick/volume rules must be broker-provided, not hard-coded.

## Owner Requirements Frozen

~~~text
SHARED ACCOUNT                         YES
MANUAL TRADE LEARNING                 YES
FULL ACCOUNT VISIBILITY               YES

HEDGING                               YES
NETTING                               YES

MARKET ENTRY                          YES
LIMIT ENTRY                           YES
STOP ENTRY                            YES
STOP-LIMIT V1                         NO / RESERVED

BROKER-NATIVE SL FOR KATARINA ENTRY   REQUIRED

ACCOUNT LEDGER                        REQUIRED

STANDARD ACCOUNT                      REQUIRED
CENT ACCOUNT                          REQUIRED
~~~

## Machine Consistency Audit

Repository contracts were parsed and checked programmatically.

Result:

~~~text
message registry entries : 30
message schemas          : 30
golden vectors           : 13

duplicate message IDs    : 0
registry/schema gaps     : 0
name mismatches          : 0
critical-flag mismatches : 0
field offset errors      : 0
root-size errors         : 0
golden frame-size errors : 0
golden CRC32C errors     : 0
owner decisions pending  : 0
critical blockers        : 0
~~~

The golden audit recalculated CRC32C over each canonical fixture and matched both the wire trailer and fixture metadata.

## Canonical Stage 04 Files

### Protocol

- `docs/architecture/KATARINA_BINARY_PROTOCOL_V1.md`
- `config/protocol_schema.json`
- `protocol/message_registry_v1.json`
- `protocol/kat1_message_schemas_v1.json`
- `protocol/enums_v1.json`
- `protocol/flags_v1.json`
- `protocol/capabilities_v1.json`
- `protocol/reason_codes_v1.json`

### Data and Execution Semantics

- `docs/architecture/KAT1_DATA_CONTRACT_V1.md`
- `protocol/payload_catalog_v1.json`
- `docs/architecture/KAT1_HEDGING_NETTING_EXECUTION.md`
- `docs/architecture/STANDARD_CENT_ACCOUNT_COMPATIBILITY.md`
- `docs/architecture/KAT1_IDENTITY_BINDING_V1.md`

### Manual Learning

- `docs/architecture/MANUAL_TRADE_LEARNING_CONTRACT_V1.md`
- `protocol/manual_trade_learning_v1.json`

### Conformance


## Deferred Implementation

The following are intentionally **not** Stage 04 work:

- Python production codec implementation — Stage 05/07;
- MQL5 encoder/decoder and EA bridge — Stage 06/07;
- actual queue capacities and latency budgets — later implementation/performance stages;
- persistence/database engine — Stage 10;
- Risk Governor policy thresholds — Stage 16;
- production position sizing implementation — Stage 17;
- execution state-machine implementation — Stage 18;
- automated CI enforcement — Stage 33;
- Strategy Tester integration — Stage 35;
- broker-specific demo/live certification — Stages 36–38;
- performance monitoring/tuning — Stage 39.

## Important Limitation

Stage 04 freezes an **architectural and wire compatibility contract**.

It does not claim that every broker's cent/standard account, filling mode, pending-order policy, or symbol configuration has already passed production validation.

Broker-specific capability negotiation and later demo/micro-risk validation remain mandatory.

## Acceptance

No Stage 04 architecture/data-schema blocker remains.

**STAGE 04 PASSED / FROZEN — KAT1 v1.0.0.**

Next: **Stage 05 — Katarina Core / Orchestrator.**


## Post-Freeze Recheck — 2026-10-02

A second repository-wide Stage 04 consistency review was performed before advancing to Stage 05.

Two **documentation-only** inconsistencies were found and corrected:

1. `KAT1_CONFORMANCE_V1.md` still referenced the superseded `message_registry_v1_draft.json`; it now references `message_registry_v1.json`.
2. `STANDARD_CENT_ACCOUNT_COMPATIBILITY.md` still displayed its pre-freeze draft status/version; it is now marked FROZEN / Stage 04 v1.0.0.

No wire/schema bytes, message IDs, owner trading requirements, or execution semantics were changed by those corrections.

Re-validation after correction:

~~~text
canonical Stage-04 JSON files parsed successfully
registry messages             : 30
message schemas               : 30
golden positive vectors       : 13
golden negative cases         : 9
duplicate message IDs         : 0
registry/schema mismatches     : 0
field offset/root-size errors : 0
golden frame-length errors    : 0
CRC32C mismatches             : 0
owner decisions pending       : 0
stale draft refs in canonical Stage-04 docs : 0
critical blockers             : 0
~~~

Repository state at recheck:

~~~text
open pull requests : 0
latest commit checks: none configured / no failing status reported
~~~

**POST-FREEZE RECHECK: PASS.**

Stage 05 may begin without reopening Stage 04.

> Catatan 22 Okt 2026: implementasi transport KAT1 (codec, ZMQ/TCP, vektor golden, jembatan MT5 Stage07) dipensiunkan. Skema pesan di `protocol/` tetap menjadi kontrak validation/health engine.
