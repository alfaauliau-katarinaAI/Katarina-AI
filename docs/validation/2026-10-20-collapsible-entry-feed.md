# Collapsible entry history and plans

Published dashboard versions 47–48 with two lists: actual entries and research candidate plans. Native details/summary rows are collapsed initially, retain expanded state during data refresh, and clear on expired telemetry. Times use Asia/Jakarta. Broker positions without ownership attribution are labeled separately.

The read-only feed uses E01's fresh PID-bound heartbeat and decision status, plus SQLite mode=ro/query_only transactions. History includes only broker-reconciled OPEN/CLOSED outbox states; ACCEPTED/UNKNOWN submissions are excluded. Requested prices are labeled as requested; actual fill prices are not available in this ledger. Plans show immutable strategy parameters, stored policy checks, review times, trigger conditions and SL/TP formulas. Candidates are never represented as active signals or executable orders. Account identifiers, tickets, volume and PnL are excluded by Python and Worker allowlists.

Local validation: two feed tests, client VM tests (collapsed/default, open-state persistence, stale clearing, camera controls), Worker integration test (two-pass ingest/read sanitization, confirmed-state restriction, redaction, forced non-executable status), four existing public research tests, artifact build and ESM validation. All passed. Windows fixture connections required explicit closing; fixed and tests passed on the VPS. Installation restarted only the telemetry publisher. E01 PID 2460 remained unchanged; scanner and research workers were not restarted.

VPS feed verification: 1 confirmed DEMO history entry, 12 candidate plans, both source statuses OBSERVED. No direct mobile/browser QA was available.

Production public-status verification confirmed fresh telemetry, the closed GBPUSD.vx SELL, and 12 non-executable candidates. Price formatting removes floating point representation tails.
