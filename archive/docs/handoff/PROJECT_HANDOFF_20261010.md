# Katarina AI — Current Project Handoff

**Updated:** 2026-10-10
**Purpose:** Persistent cross-chat handoff for continuing development after a chat is deleted or replaced.

> **Current operating rule (2026-10-10): GitHub-first.** Develop, run tests, and audit on GitHub-hosted Actions. Do not access the VPS until a specific GitHub-validated change needs read-only terminal/broker/environment verification. Prior VPS-first implementation notes below are historical. See [GitHub-First Development](../operations/GITHUB_FIRST_DEVELOPMENT.md).

## Current roadmap position

- Stage 01 — Constitution & North Star: FROZEN
- Stage 02 — MT5-to-Execution Workflow: FROZEN
- Stage 03 — Repository Architecture: FROZEN
- Stage 04 — KAT1 Data Protocol / Schemas: FROZEN v1.0.0
- Stage 05 — Katarina Core / Orchestrator: FROZEN
- Stage 06 — MT5 Bridge EA: FINALIZED / FROZEN v1.0.0; Bridge design v0.5.0; governed Windows Server 2022 compile + MQL self-test + final audit PASS
- Stage 07 — MT5 ↔ Python Communication: FINALIZED / FROZEN v1.0.0; governed final clearance PASS on Windows Server 2022; ZeroMQ primary + native TCP fallback frozen\n- Stage 08 — Data Validation Engine: FINALIZED / FROZEN v1.0.0; `PASS_STAGE08_FINAL_CLEARANCE`
- Stage 09 — Health & Safety Engine: FINALIZED / FROZEN v1.0.0; `PASS_STAGE09_FINAL_CLEARANCE`
- Stage 10 - Database & Memory V1: LOCAL FREEZE CANDIDATE; PASS_STAGE10_LOCAL_FINAL_CLEARANCE; governed freeze pending

## VPS bridge status

Implementation status: **LIVE END-TO-END CONNECTED**

- Agent: `katarina-vps-2012r2-01`.
- Windows Server 2012 R2 uses the legacy outbound-HTTPS PowerShell polling agent.
- ChatGPT → GitHub request queue → VPS task execution → GitHub result write-back has been proven with multiple `HOST_INVENTORY` requests.
- Stage-07 VPS control work introduced sparse transition-only GitHub health telemetry, compact result bundles, local watchdog/guardian recovery and low-memory batching. Recent proven request receipts use agent v1.4.6; repository agent source has later low-memory changes. The VPS remains an operational/compatibility lab rather than the Stage-07 freeze-qualified host.
- Request execution remains allowlisted; arbitrary shell commands are not accepted.
- Results remain text-only and secret-redacted before upload.
- No inbound VPS command port is required.
- Deep host discovery is enabled.

Detected on the real VPS:

- Windows Server 2012 R2 Standard x64
- PowerShell 4.0
- MetaTrader 5 ALFA:
  - `C:\Program Files\MetaTrader 5 ALFA\terminal64.exe`
  - `C:\Program Files\MetaTrader 5 ALFA\metaeditor64.exe`
- MetaTrader 5 generic / MetaQuotes:
  - `C:\Program Files\MetaTrader 5\terminal64.exe`
  - `C:\Program Files\MetaTrader 5\metaeditor64.exe`
- Two valid MT5 terminal data folders with `MQL5` and `Tester`.
- MT5 Common data path detected under the Administrator profile.
- Python executable: not detected.
- Git CLI: not detected.

Operational note:

- Keep request IDs compact on the legacy host and prefer local/batched execution for heavy work. GitHub is now used as a sparse command/evidence bus rather than a heartbeat database, reducing write volume and avoiding unnecessary process pressure.

## Stage 06 final status

Status: **FINALIZED / FROZEN v1.0.0**
Bridge design: **v0.5.0**

Governed freeze evidence:

- freeze-qualified host: Windows Server 2022 x64
- host class: PREFERRED
- GitHub Actions run: `37139117641`
- evidence head SHA: `4e4f27461bb77e1bcf61fd707f649dc0dfe74def`
- MetaEditor: 5.0.0.6235
- `KatarinaBridgeEA.mq5`: 0 errors / 0 warnings / EX5 created
- `KatarinaStage06SelfTest.mq5`: 0 errors / 0 warnings / EX5 created
- `KatarinaStage06AccountProbe.mq5`: 0 errors / 0 warnings / EX5 created
- modern-host MQL self-test: PASS
- Stage-06 static regressions: 35/35 PASS
- complete MQL source-manifest binding: PASS
- final audit result: `PASS_STAGE06_FINAL_CLEARANCE`
- freeze artifact: `stage06-final-freeze-evidence`
- artifact digest: `sha256:1157e48bb8f84cf15536bb74e64673446017efc4d7461737a8d34d8c31da03fc`
- permanent freeze record: `docs/reviews/STAGE_06_FREEZE_RECORD.md`

Account-compatibility boundary:

- real STANDARD_LIKE broker validation: deferred to Stage 36/38
- real CENT_LIKE broker validation: deferred to Stage 36/38
- this is intentional under ADR-0010 and the frozen Stage-04 contract
- Stage 06 makes no broker-by-broker production compatibility claim

2012 R2 exploratory evidence remains useful but is not freeze-qualified:

- both MT5 installations compile Stage-06 MQL with 0 errors / 0 warnings
- auto gold-symbol discovery resolved `XAUUSD.vx`
- both MT5 terminals currently expose the same saved Valetax account identity, so automatic STANDARD/CENT classification correctly stops as ambiguous
- this ambiguity is not a Stage-06 freeze blocker

Windows Server 2012 R2 remains DEFERRED for freeze proof.

## Stage 07 final status

Status: **FINALIZED / FROZEN v1.0.0**

Governed final evidence:

- freeze-qualified host: Windows Server 2022 x64
- GitHub Actions run: `37209799384`
- evidence head SHA: `f83ab5eb6f57b2c30428122f69a807c9ace673f1`
- artifact: `stage07-final-clearance-evidence`
- artifact ID: `11306007351`
- artifact digest: `sha256:d95c9f12816017ea87291582ffdded60c0d298035ca82bc55c689e1f94df2532`
- final audit: `PASS_STAGE07_FINAL_CLEARANCE`
- permanent record: `docs/reviews/STAGE_07_FREEZE_RECORD.md`

Frozen Stage-07 capabilities:

- Python localhost ZeroMQ ROUTER primary / MT5 DEALER peer;
- one raw KAT1 frame per ZeroMQ message;
- native localhost TCP fallback with KAT1 frame-length framing and no secondary envelope;
- 13/13 frozen KAT1 MQL5 golden vectors PASS;
- fail-closed binding and session supervision;
- atomic snapshot/reconciliation recovery PASS;
- directional persistent sequence lanes with duplicate/gap rejection;
- cross-process reconnect preserves stream sequence continuity;
- native TCP cross-language MQL5 ↔ Python byte equality PASS;
- 37/37 Stage-07 regression tests PASS;
- bounded backpressure/critical-frame retry PASS;
- TCP loopback p99 0.202 ms and codec decode p99 290.3 µs on the freeze-qualified run;
- Stage-06 2000 µs timer budget preserved;
- no broker order submission introduced;
- `live_risk_ready=false`.

Governance:

- ADR-0009 is accepted after primary ZeroMQ, native TCP fallback, reconnect and fail-closed binding proofs passed.
- ADR-0011 and ADR-0012 remain accepted.
- Stage-07 changes now require governed review.
- Windows Server 2012 R2 remains useful for compatibility/operations, but Windows Server 2022 evidence is the freeze-qualified basis.

## Stage 08 final status

Status: **FINALIZED / FROZEN v1.0.0**

Governed evidence:

- GitHub Actions run: `37211163352`
- evidence head SHA: `66fb7958416c13ca5bc16b7c38510cd71bdf86b3`
- 37/37 validation tests PASS
- final audit: `PASS_STAGE08_FINAL_CLEARANCE`
- artifact: `stage08-final-clearance-evidence`
- artifact ID: `11306556690`
- artifact digest: `sha256:adf3e17aadf7d6ad674e722d0a41781e511aeb5407541e7c7339c9500db25f3d`
- `ready_for_stage09=true`
- `live_risk_ready=false`
- permanent record: `docs/reviews/STAGE_08_FREEZE_RECORD.md`

## Stage 09 final status

Status: **FINALIZED / FROZEN v1.0.0**

Governed evidence:

- GitHub Actions run: `37211508723`
- evidence head SHA: `5fed0dec3caaf689e149e0b34e25fa749e773caa`
- 20/20 health/safety tests PASS
- final audit: `PASS_STAGE09_FINAL_CLEARANCE`
- artifact: `stage09-final-clearance-evidence`
- artifact ID: `11306568221`
- artifact digest: `sha256:b008f10ae53fedb2fc018e384437ef7eea7fac6c85ebe27ad7ee20dfa0fbd690`
- `ready_for_stage10=true`
- `live_risk_ready=false`
- permanent record: `docs/reviews/STAGE_09_FREEZE_RECORD.md`

## Next recommended action

Proceed with Stage 10 — Database & Memory V1:

1. define durable event/memory boundaries;
2. implement append-only durable records with deterministic IDs;
3. separate operational state from learned/trade experience memory;
4. add idempotent writes and restart recovery;
5. add schema/version migrations and integrity checks;
6. build final evidence-bound audit.

## Project invariant reminders

- Python is the central intelligence.
- MT5 is sensor + deterministic safety + execution/reporting layer.
- MT5 does not invent discretionary BUY/SELL decisions.
- NO TRADE is a valid decision.
- Risk Governor is absolute.
- live-risk readiness is separate from transport connectivity.
- Stage 04 KAT1 is authoritative.
- Stage 06 is frozen and remains fail-closed by contract; later stages must not weaken its safety invariants.\n- Stage 07 is frozen; later stages must preserve its localhost-only transport, KAT1 framing, recovery, binding and sequence invariants.

## 2026-10-05 Stage 10-40 VPS implementation update

- Stage 10 durable SQLite memory baseline: PASS.
- Stages 11-40 implementation modules: present on VPS and covered by staged tests.
- Full discovery: 117 unit tests PASS.
- Static suite: 45 tests PASS.
- Stage 11-40 integration: 3 tests PASS.
- Stage 11-40 audit: `PASS_STAGE11_40_IMPLEMENTATION_BASELINE`.
- Stage 06 exploratory compile on Server 2012 R2: 0 errors / 0 warnings, not freeze-qualified by policy.
- Stage 07 MQL compile suite: PASS.
- Stage 07 Python communication regression: 37/37 PASS.
- Stage 36 Live Environment Preflight is implemented as a read-only gate; broker mutation is not permitted by the preflight.
- Stage 38 Live Micro-Risk Validation remains fail-closed until explicit owner approval and required external evidence; no preflight stage may authorize broker mutation.
- Continuous evolution cannot autonomously promote live models or alter the Constitution.

Next external-validation sequence: tester evidence -> read-only live-environment preflight -> stress/broker compatibility/reconciliation proof -> explicit owner authorization for live micro-risk validation.
