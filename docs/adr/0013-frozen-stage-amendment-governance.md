# ADR-0013 — Frozen-Stage Amendment Governance

**Status:** ACCEPTED  
**Date:** 2026-10-04  
**Scope:** Stage 01–06 and any later stage after it becomes frozen

## Context

Katarina uses staged freezes to preserve architectural safety and reproducibility.
A frozen stage must not become a barrier to correcting a proven integration defect,
but changing frozen behavior without explicit governance would invalidate prior
evidence and make later stages impossible to audit.

## Decision

Frozen source may be amended only when a later-stage integration proves that the
frozen contract itself must change.

An amendment MUST:

1. identify the exact frozen invariant or implementation that is changing;
2. explain why extension outside the frozen stage is insufficient;
3. preserve prior freeze evidence as historical evidence;
4. bump the frozen stage version;
5. add an amendment record instead of rewriting the old freeze record;
6. rerun every compile, static, runtime, and safety gate affected by the change;
7. create new evidence bound to the amended commit SHA;
8. update downstream stages that depend on the changed contract;
9. keep live-risk disabled unless the owning later stage explicitly authorizes it.

## Preferred order

Before modifying a frozen stage, use this order:

1. extend through a later-stage adapter or implementation;
2. add a compatibility shim;
3. add an automated cross-stage contract guard;
4. only then amend the frozen stage if the contract itself is incompatible.

## Current Stage-06 / Stage-07 decision

No Stage-06 source amendment is required at this time.

Stage 06 already:

- uses the terminal-native chart symbol via `_Symbol`;
- keeps broker-native observed position/order symbols;
- exposes the `TransportPort` boundary;
- remains execution-disarmed and fail-closed.

Stage 07 extends that contract through:

- `CKatStage07Transport`;
- localhost ZeroMQ/TCP communication;
- KAT1 handshake/recovery/sequence logic.

A Stage-07 CI contract guard now checks that the Stage-07 bridge does not weaken
Stage-06 timer budgets, queue limits, execution-disarmed behavior, symbol binding,
or broker-order-submission restrictions.

## Amendment trigger examples

A Stage-06 amendment WOULD be required if, for example:

- `TransportPort` lacks an operation that cannot safely be introduced by a
  Stage-07 extension;
- Stage-06 identity semantics conflict with the frozen KAT1 wire identity;
- Stage-06 symbol handling rewrites broker-native names;
- Stage-06 timer/backpressure semantics make the live transport impossible to
  operate safely;
- a safety defect exists in Stage-06 code itself.

In that event, Stage 06 becomes:

~~~text
FROZEN v1.0.0
→ AMENDMENT IN REVIEW
→ requalified
→ FROZEN v1.1.0
~~~

The v1.0.0 freeze record remains immutable historical evidence.

## Safety

This ADR does not authorize discretionary MT5 decisions, broker order submission,
or live-risk readiness. It governs how frozen implementation defects may be
corrected without losing auditability.
