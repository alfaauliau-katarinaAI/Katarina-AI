# Unified adaptive Entry/Exit Owner review — offline contract

This increment joins the existing `KatarinaAdaptiveBrainV2` research proposal
with `StructuralExitPlan` in
`src/katarina/intelligence/cognition/unified_research_handoff.py`.

The output is a deterministic, immutable, read-only Owner research receipt:
symbol, BUY/SELL, regime, playbook, structural stop/target (if consistent),
source SHA-256, observation timestamp, reason(s), and optional Cloud Hand ID.

Every proposal remains **research only**. A matching Entry and Exit yields
`RESEARCH_CANDIDATE`, never execution approval. A missing or contradictory
exit, invalid price geometry, unready entry, source or time validation issue
yields WAIT or rejects malformed inputs.

A Cloud Hand ID is explicitly **unverified telemetry metadata**, not a
credential or trusted sender. Owner view contains no commands. No network
listener, broker connection, trade modification, strategy promotion, or
Live-mode activation is provided or implied.

Remaining Owner design gaps: actual brokerage order lifecycle, predictive
HOLD/FULL/PARTIAL/TRAIL behavior, authenticated transport, Owner emergency
controls, cloud offline survival, and the six deferred design topics.

Test via GitHub Actions Body CI; focused check:
`PYTHONPATH=src python -m unittest discover -s tests/unit/intelligence -p test_unified_research_handoff.py -v`.
