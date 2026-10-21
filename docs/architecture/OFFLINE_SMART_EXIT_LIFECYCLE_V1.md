# Smart Exit lifecycle — pure offline feasibility (not an execution engine)

`src/katarina/intelligence/lab/research_exit_lifecycle.py`

This checks a proposed HOLD, FULL, PARTIAL or TRAIL decision against
**caller-supplied broker constraints**. It does not choose an optimal exit or
execute it.

- Uses the existing Adaptive Brain / Smart Entry/Exit research receipt; it
  never accepts a live-authorized or strategy-promoted source.
- Requires explicit symbol, BUY/SELL direction, position owner and exact
  broker volume minimum/maximum/step as well as bid/ask and broker
  stop/freeze distances. These are inputs, **not guessed defaults**.
- Uses decimal arithmetic for partial-close volume and remaining volume;
  both must be valid on the declared broker volume grid. A zero remainder is
  a FULL close, not a PARTIAL close.
- BUY trailing may only increase the stop and must be below available bid
  beyond both broker distance constraints. SELL trailing may only decrease
  the stop and stay above ask beyond the constraints.
- A position marked OWNER_MANUAL cannot be closed or modified by this
  research path. The output remains read-only.
- Every acceptable case reports `EXIT_FEASIBLE_RESEARCH_ONLY`; no broker
  ACK, net-cost proof, production risk authorization or actual order.
  The model does **not** claim the trade should be closed.
- Account portfolio optimization, expected net costs, predictive horizon,
  broker-side local execution/reconciliation, manual-owner authentication
  and Owner D3's final numerical decision semantics remain unfinished.

Tests:
`PYTHONPATH=src python -m unittest discover -s tests/unit/intelligence -p test_research_exit_lifecycle.py -v`

Production path remains NO REAL ORDERS, and the independent Risk Governor
may never be bypassed by an offline feasibility result.

## Research receipt integrity and chronology

Smart Exit never accepts a string that merely resembles a SHA256 digest.
The input Adaptive Entry/Exit research object must have a valid *matching*
canonical payload digest, a coherent WAIT or RESEARCH_CANDIDATE state,
and finite directional Entry/Stop/Target geometry. A recomputed checksum
for contradictory or forged research-ready fields remains rejected. The
source observation must not occur in the future relative to the proposed
exit review. Caller-supplied broker geometry and manual Owner protections
still apply independently.

This is a **local integrity check, not authentication**: a matching SHA256
does not certify a real broker fill or authorize live trading.
