# Protocol

This directory contains the language-neutral MT5 ↔ Katarina protocol contracts.

## Frozen Protocol

**KAT1 v1.0.0 — Stage 04 FROZEN**

~~~text
canonical binary
→ little-endian
→ 52-byte fixed frame header
→ exact versioned root layouts
→ bounded variable tails
→ scaled execution-sensitive integers
→ CRC32C policy
→ max frame 65,536 bytes
→ chunked atomic snapshots
→ golden cross-language fixtures
~~~

## Canonical Files

- `message_registry_v1.json`
- `kat1_message_schemas_v1.json`
- `enums_v1.json`
- `flags_v1.json`
- `capabilities_v1.json`
- `reason_codes_v1.json`
- `payload_catalog_v1.json`
- `manual_trade_learning_v1.json`

Human-readable specifications:

- `../docs/architecture/KATARINA_BINARY_PROTOCOL_V1.md`
- `../docs/architecture/KAT1_DATA_CONTRACT_V1.md`

## Critical Rule

The wire contract is **not** a raw MQL5/Python memory-structure dump.

Python and MQL5 implementations must encode explicit KAT1 fields using the frozen offsets, widths, byte order, version rules and conformance fixtures.

Actual Python/MQL5 codec implementation occurs in later stages.

> Catatan 22 Okt 2026: implementasi transport KAT1 (codec, ZMQ/TCP, vektor golden, jembatan MT5 Stage07) dipensiunkan. Skema pesan di `protocol/` tetap menjadi kontrak validation/health engine.
