# KATARINA BINARY PROTOCOL V1

**Status:** FROZEN  
**Protocol:** KAT1  
**Version:** 1.0.0  
**Stage:** 04/40

## Purpose

KAT1 is the canonical language-neutral MT5 ↔ Katarina wire protocol.

It is designed for deterministic decoding, bounded resource use, replay/recovery, low overhead, explicit schema evolution, and identical logical semantics across live and tester transports.

## Architectural Choice

KAT1 is a custom **SBE-inspired canonical binary protocol**.

It adopts:

- fixed positional root blocks;
- explicit message IDs;
- schema version and block length on wire;
- append-only compatible evolution;
- bounded variable tails;
- cross-language golden vectors.

It intentionally does **not** use raw MQL5/Python memory structs as the wire contract and does not require the full SBE/FlatBuffers/Protobuf toolchain.

## Canonical Frame Header

Every frame begins with 52 bytes:

| Offset | Bytes | Field | Type |
|---:|---:|---|---|
| 0 | 4 | magic | bytes `KAT1` |
| 4 | 1 | wire_major | uint8 |
| 5 | 1 | wire_minor | uint8 |
| 6 | 2 | header_length | uint16 |
| 8 | 2 | message_type | uint16 |
| 10 | 2 | schema_version | uint16 |
| 12 | 2 | block_length | uint16 |
| 14 | 2 | flags | uint16 |
| 16 | 4 | frame_length | uint32 |
| 20 | 8 | sequence | uint64 |
| 28 | 8 | source_time_ns | uint64 |
| 36 | 8 | stream_id | uint64 |
| 44 | 8 | boot_id | uint64 |

Rules:

- wire version = 1.0;
- header length = 52;
- all multibyte numeric values are little-endian;
- frame_length includes header + payload + optional CRC trailer;
- max frame size = 65,536 bytes;
- block_length describes only the fixed root payload.

## Frame Flags

Canonical bits:

- 0x0001 — CRC32C_PRESENT;
- 0x0002 — CRITICAL_MESSAGE;
- 0x0004 — SNAPSHOT_TRANSACTION;
- 0x0008 — REPLAYED_FROM_DURABLE_JOURNAL.

Unknown unsupported frame flags are rejected when they can affect critical semantics.

## CRC32C

Critical/durable KAT1 frames use CRC32C Castagnoli.

Parameters:

~~~text
initial = 0xFFFFFFFF
reflected polynomial = 0x82F63B78
final xor = 0xFFFFFFFF
trailer = uint32 little-endian
coverage = header + payload, excluding trailer
~~~

CRC is mandatory for:

- critical messages;
- snapshot transaction frames;
- broker-mutating intents;
- execution lifecycle events;
- durable journal/replay records;
- golden fixtures.

CRC is optional for advisory-only TICK_EVENT, BAR_EVENT, HEARTBEAT and TRANSPORT_METRICS.

## Primitive and Decimal Rules

Canonical primitives:

- signed/unsigned 8/16/32/64-bit integers;
- finite float64 only for non-exact analytical values;
- Id128;
- bytes32;
- bounded UTF-8 tails.

Execution-sensitive values use scaled integers:

~~~text
price = price_units × 10^-price_scale
volume = volume_units × 10^-volume_scale
native_money = money_units × 10^-money_scale
~~~

No NaN/infinity sentinel is allowed. Missing and numeric zero are distinct through explicit presence flags.

## Standard and Cent Accounts

The same protocol supports both standard-like and cent-like account economics.

KAT1 preserves:

- ACCOUNT_CURRENCY;
- ACCOUNT_CURRENCY_DIGITS;
- broker-native account monetary values;
- SymbolSpec contract/tick/volume properties;
- account-unit profile revision.

No hard-coded cent multiplier is allowed.

Risk calculation may request broker-native OrderCalcProfit/OrderCalcMargin evidence through BROKER_CALC_REQUEST / BROKER_CALC_REPORT.

Cross-account learning uses normalized percent/R metrics or explicitly validated reporting conversion.

## Identity

Identity and binding rules are canonicalized in:

- `docs/architecture/KAT1_IDENTITY_BINDING_V1.md`

Execution binds to account, instrument, SymbolSpec revision, approved account/position revisions, decision/risk lineage, risk binding hash and expiry.

## Time

`source_time_ns` is Unix epoch UTC nanoseconds as a **wire unit**, not a claim of source precision.

Millisecond/second MT5 timestamps are scaled to the wire unit while source precision/provenance remains explicit where material.

Independent process monotonic clocks are not directly compared.

## Message Registry

Canonical IDs are in:

- `protocol/message_registry_v1.json`

Groups:

~~~text
0–99     system / lifecycle
100–199  market
200–299  account / broker state
300–399  execution / broker calculation
400–499  health / transport metrics
~~~

V1 includes:

- HELLO / HELLO_ACK;
- heartbeat/protocol errors;
- transactional snapshots;
- TickEvent / BarEvent / SymbolSpec / SessionState;
- account / position / order state;
- account ledger events;
- MARKET / LIMIT / STOP execution intents;
- modify/reduce/close/cancel intents;
- execution acknowledgements/trade events;
- reconciliation;
- broker profit/margin calculation requests/reports;
- health/transport metrics.

STOP_LIMIT is reserved but not production-authorized in V1.

## Hedging and Netting

Both modes are supported from V1.

Canonical rules:

- hedging may contain multiple positions per symbol;
- netting has one net position per symbol;
- POSITION_IDENTIFIER is stable lineage;
- POSITION_TICKET is a broker handle and may change on netting reversal;
- execution intents approved against a position carry its revision;
- pending LIMIT/STOP intents carry netting-state guards and become stale when material approved assumptions change.

See:

- `docs/architecture/KAT1_HEDGING_NETTING_EXECUTION.md`

## Broker-Native Protective SL

Every Katarina-owned order capable of creating live exposure must include an approved broker-native Stop Loss.

This applies to MARKET, LIMIT and STOP.

If the current broker rules cannot safely represent/accept the SL, the entry is rejected.

Manual user trades without SL may still be observed/learned from but are not considered compliant Katarina execution.

## Shared Account and Manual Learning

The live account may also contain manual trades and other observable activity.

Katarina has full account visibility for risk/reconciliation/learning, but visibility does not grant mutation authority.

Manual trading is covered by:

- `docs/architecture/MANUAL_TRADE_LEARNING_CONTRACT_V1.md`
- `protocol/manual_trade_learning_v1.json`

## Account Ledger

ACCOUNT_LEDGER_EVENT is first-class V1 data.

Raw broker deal type/reason is preserved while Katarina may normalize operations such as deposit, withdrawal, credit, charge, correction, bonus, commission, interest, dividend and tax.

Trading P/L and external cash flow must never be conflated.

## Snapshot Bootstrap

Complete state bootstrap is transactional:

~~~text
SNAPSHOT_BEGIN
SNAPSHOT_CHUNK × N
SNAPSHOT_COMMIT
~~~

Partial snapshots are never installed.

Snapshot chunks carry bounded embedded typed records and integrity values. Missing/conflicting/corrupt chunks result in snapshot failure and no new live risk until valid state is recovered.

## Schema Evolution

Compatible within wire major 1:

- append fields at root tail;
- increase block_length;
- increase schema_version;
- add message types in reserved space;
- append bounded variable fields in schema order.

Requires a major break:

- reorder existing fields;
- change primitive width;
- reinterpret unit/scale/enum meaning;
- reuse IDs for new meanings;
- remove required critical semantics.

Unknown execution-critical schema versions fail closed.

## Authoritative Machine-Readable Contracts

- `config/protocol_schema.json`
- `protocol/message_registry_v1.json`
- `protocol/kat1_message_schemas_v1.json`
- `protocol/enums_v1.json`
- `protocol/flags_v1.json`
- `protocol/capabilities_v1.json`
- `protocol/reason_codes_v1.json`
- `protocol/payload_catalog_v1.json`

## Conformance

Golden vectors:


Validation contract:


Python and MQL5 implementations must reproduce equivalent logical input as identical canonical bytes before Stage 07 can be considered conformant.

> Catatan 22 Okt 2026: implementasi transport KAT1 (codec, ZMQ/TCP, vektor golden, jembatan MT5 Stage07) dipensiunkan. Skema pesan di `protocol/` tetap menjadi kontrak validation/health engine.
