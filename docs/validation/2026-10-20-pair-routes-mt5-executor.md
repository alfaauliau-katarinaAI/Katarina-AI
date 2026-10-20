# Pair routes and independent MT5 executor status

Pair identifiers and lifecycle timestamps are now an explicitly permitted public
scope at the owner's request. A bounded reader takes only symbol, phase, state,
sequence and UTC timestamp from the actual scanner host's lifecycle file. It
requires matching process identity, recent source events and existing public
telemetry attestation. The latest completed observation supplies pair roster
identifiers only; no quotes, prices, ticks, balances, account identifiers or
credentials are exported. Up to 64 pair identifiers, 80 recent events and 24
active tasks are retained. The hosted Worker independently validates and redacts
this scope, including process/freshness checks.

The graph has up to 12 recent pair branches in stable side columns; the compact
selector can focus any currently attested pair. Pair-to-worker relations come
from actual phase/symbol events, and completed scan observations have separate
report relations. Timestamped signals follow those paths. Existing worker loops
retain their independent schedules; these display routes do not issue commands
or assert that every pair is busy simultaneously. Market broker access remains
owned by the scanner; historical testing/validation and the E01 process operate
alongside it. No processing-card grid was restored.

## MT5 root cause

The local TSV writer sourced demo status from the scanner's old inline executor
and compared its PID to the scanner PID. After E01 became independent, this gave
age 999999 and bound 0 despite E01 having a fresh heartbeat. The writer now reads
E01's DEMO/independent descriptor, validates its own PID, state and timestamp,
and separately validates the demo-decision PID and freshness. An old decision
cannot refresh permission; a stale E01 cannot fall back to the old inline owner.
The existing 17-column MT5 format and read-only chart EA remain compatible.

A guarded test installer backs up exact known sources, compiles replacements and
requires LIVE/production OFF, no owner stops, independent mode, fresh demo status,
zero broker positions and zero unresolved submissions. It restarts only the
scanner and telemetry publisher. E01 is not restarted or duplicated.

## Evidence

Before repair, MT5 TSV showed executor age 999999/bound 0 while E01 PID 2460 was
RUNNING. After repair, scanner PID changed from 2876 to 6160, E01 retained PID 2460
and reached 665 checks. The actual common-file TSV had 17 columns, executor age 0,
bound 1 and WAIT_NEXT_CAUSAL_H1_ENTRY. The existing chart EA's receipt was 1.14 s
old, proving the chart continued executing and reading the format. This verifies
the status transport and predicate; no visual MT5 screenshot was available.

Actual pair telemetry from PID 6160 contained 32 pair identifiers and 64 recent
pair events. Both pair-reader/privacy and MT5 independent/stale/PID/permission
regression tests passed on the Windows test VPS. The actual hosted Worker/client
VM tests passed, including pair route selection and price/account redaction.
Native Canvas2D rendered 424 nodes/613 edges over 470 frames with stable
coordinates, working waiting animation, identical paused pixels and finite
zoom/resize. The rendered pair columns were visually inspected. This is not a
browser/phone CSS test or proof of profitable execution. Build/artifact checks
passed. No trading guard or LIVE permission was changed.
