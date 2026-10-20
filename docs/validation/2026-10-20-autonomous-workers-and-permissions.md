# Autonomous workers and separate permission scopes

The owner's MT5 Algo Trading switch was ON on a DEMO account. The read-only
observer's `delivery=DISABLED` and Katarina's LIVE permission OFF were separate
facts, but the dashboard's generic ORDER/DISABLED label conflated them. The demo
execution boundary reported DEMO_ORDER_PERMISSION_ON while rejecting an
unqualified protected variant. No LIVE permission was changed by this work.

A second actual blocker was found: all nine autonomous research loops were in
PAUSED_STORAGE_BUDGET. The jobs database was 314,650,624 bytes, above its hardcoded
256 MiB limit; the disk had about 3.14 GB free. Research capacity now includes the
DB plus WAL, allows up to 512 MiB, and preserves a 2 GiB disk reserve plus an
8 MiB write margin. It does not delete, rotate or relocate research, ticks or AI
memory. Resource exhaustion remains an explicit legitimate reason to pause.

The nine research loops already pulled their own jobs and persisted their own
results. They are threads within the scanner/brain host, not nine isolated OS
processes. The cost-review and Gemini loops also run independently in that host.
The new E01 execution service is a separate OS process with its own periodic loop,
heartbeat and singleton OS lease. The scanner disables its inline demo executor
when the explicit independent-mode marker exists. E01 uses the existing
DemoForwardRuntime and unchanged DEMO account/identity/permission/risk/SL-TP/
idempotency boundary. A root owner stop, demo stop or executor stop prevents new
work. No worker receives permission to send LIVE orders.

Windows service registration clones the existing task's principal and startup
configuration, replacing only the action and continuous runtime limit. Activation
requires LIVE/production OFF, no broker positions, no unresolved submissions, and
no owner stop. The task creator initially used Element.write instead of
ElementTree.write; this failed before stopping the old scanner. It was corrected
and covered by an activation regression test. A stale research module payload was
also detected during actual installation verification. The installer now requires
the capacity/PID integration in the payload and refuses unknown source hashes;
the actual-worker test spies on the capacity call to prevent this regression.

The read-only public monitor now independently redacts and validates worker PID,
freshness and status. It shows Algo MT5, demo permission, demo wait reason, LIVE
permission, research heartbeats and E01 cycle count separately. Pulse/edge
direction is worker-to-center for reports. E01 pulses come from increments in its
persisted check counter. Generic ORDER OFF wording has been replaced with the
correct read-only observation-path scope.

Validation:

- 12 demo execution-boundary tests passed on the test VPS, including real-account
  rejection, permission/identity changes, concurrent reservation, duplicate and
  unknown submissions, stale risk, owner stop and protection requirements.
- 22 fake-broker demo forward integration tests passed, including multi-symbol
  routing, outcomes/lessons and candidate qualification.
- 13 local tests passed for capacity, real-worker independence and integration,
  E01 independence/singleton/stop, activation, worker-runtime privacy, the actual
  client, and actual Worker transport privacy/expiry.
- Native Canvas 2D diagnostic passed 470 frames with 299 actual graph nodes,
  stable coordinates, identical paused pixels, zoom/resize and opaque canvas.
  This is not a phone/browser/CSS-layout measurement.
- Build, Worker ESM artifact validation and whitespace checks passed.

Actual VPS/public evidence, 2026-10-20:

| UTC | Scanner/brain PID | E01 PID | E01 checks | Fresh research loops | Paused loops |
| --- | ---: | ---: | ---: | ---: | ---: |
| 11:42 | 3616 | 2460 | 2 | 0 (stale payload detected) | unverified |
| 11:46 before scanner-only restart | 3616 | 2460 | 18 | — | — |
| 11:47:17 | 2876 | 2460 | 20 | 9 | 0 |
| 11:50:29 | 2876 | 2460 | 31 | 9 | 0 |

The executor was untouched during the scanner-only restart and continued its
checks. All nine research snapshots reported new completed trials from PID 2876.
Experiments rose from 56,547 while paused to 57,251 by 11:50:29 UTC. The restarted
scanner had three successful cycles. Public telemetry was verified, Algo MT5 and
demo permission were ON, LIVE was OFF. E01's last status at that sample was
WAIT_NEXT_CAUSAL_H1_ENTRY, rather than forced execution. These results demonstrate
operational concurrency, not proven model training, strategy quality or profit.
