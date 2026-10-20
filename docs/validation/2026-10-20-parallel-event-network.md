# Parallel work and the reference network

The original 19 October reference video was recovered and visually inspected. It
shows a dense, branched 3D network with several concurrent activity streams in a
dark trading dashboard. Katarina's public graph remains grounded in persisted
research records and actual VPS events; it is not access to Gemini's internal
neuron activations.

The previous client collapsed each received batch into only the last event per
phase, capped at 16 signals. Fast tasks frequently finished between publisher
updates, so multiple real events and concurrent loops appeared inactive.

The client now keeps up to 80 distinct recent events per batch, with a 96-signal
queue bound and original cross-phase timestamp alignment. A recent trace is
replayed over at most 6.5 seconds; each signal lasts 1.8 seconds. Exact event
identities are deduplicated, and events older than 20 seconds do not create new
signals. The display explicitly calls these timestamped event traces. Only actual
STARTED telemetry is shown as currently processing. Heartbeats do not manufacture
workload. The executor's separate sequence is namespaced by phase.

Each observed event has a distinct short-lived point and phase branch. Completed
results travel toward the center. Real document/paragraph and instrument/dataset/
experiment ancestry controls local spatial branching. Positions of existing
points remain stable across clock updates. Real source relations are retained,
with a 640-edge draw budget and cached static topology. No proximity-only links or
invented workers are added. A compact parallel panel shows W01–W12, sensor,
technical, memory and E01 evidence independently, including capacity pauses.

Validation on an actual public packet: 425 points, 572 displayed edges, 470 frames;
no coordinate shift during stationary camera, identical paused pixels, opaque
canvas and finite zoom/resize coordinates. Native Canvas2D frame p50 was about
2.1 ms and p95 6.9 ms on the diagnostic host. This is not phone/browser/CSS QA.
Client VM tests cover per-phase multiple events, exact deduplication, aligned
concurrent timestamps, stale-event rejection, resource pause visibility and graph
provenance. Worker transport/privacy tests and ESM build/artifact checks passed.

Published Site version 41, source 5f2d5408a1dcbe45725235b2c4d53aece7dd9332.

## Actual resource blocker

At 13:55 and 14:08 UTC, scanner/brain PID 2876 and E01 PID 2460 were independently
running, but all nine research loops correctly reported PAUSED_LOW_DISK. Research
was unchanged at 63,304 trials since 12:27:44 UTC; E01 rose from 479 to 524 checks.
The C: volume was the only volume, with approximately 2.12 GB free, below the 2 GiB
plus 8 MiB write reserve. The current research DB was about 352 MB, below its
512 MiB ceiling. The disk reserve and all execution permissions were preserved.

Cold dated experiment dependency binaries were selected for reversible NTFS
compression, without deleting or relocating any files. The maintenance script
only selects .dll/.pyd files under explicit old test dependency directories and
compares SHA-256 for every selected file before and after compression. It does not
select tick data, datasets, databases, memory or configuration. This is a bounded
maintenance action, not a promise of unlimited disk capacity.

At 14:17:56 UTC, all nine research snapshots were fresh and reported completed
new experiments. Their individual counters increased from the 13:55 baseline:

| Worker | Before | After |
| --- | ---: | ---: |
| W01 | 7205 | 7252 |
| W02 | 7201 | 7249 |
| W03 | 6944 | 6990 |
| W04 | 7113 | 7159 |
| W05 | 6884 | 6932 |
| W06 | 6999 | 7042 |
| W07 | 6914 | 6959 |
| W08 | 7148 | 7190 |
| W09 | 6896 | 6942 |

Persisted experiments rose to 63,704 (+400). Scanner/brain PID remained 2876,
with 115 successful cycles. E01 retained PID 2460 and reached 556 checks. The
retained STARTED/DONE event stream independently showed nine simultaneously
started phases at 14:17:50.005963 UTC. This is a lower bound from the retained
event window, not a count inferred from animations. No scanner/executor restart
was needed for the research loops to resume. LIVE remained OFF.

The final native-canvas diagnostic on this resumed-work packet also passed
470 frames: 414 points, 574 edges, unchanged coordinates, identical paused pixels,
opaque canvas and finite camera/resize; p50 2.43 ms, p95 4.39 ms on the diagnostic
host. Browser and phone verification remain unavailable.

Lossless compression completed with exit code 0: all 377 selected dependency
binaries passed their before/after SHA-256 comparisons (199 in the old deps tree,
178 in the old venv package tree). Free space after the verified pass was
2,185,199,616 bytes. Some first-tree compression had already occurred before that
pass's 2,165,506,048-byte baseline. No research files were deleted or relocated.
The volume still has limited headroom; its capacity guard remains active and will
pause new research again if the reserve is exhausted. This work does not provide
unbounded storage or claim that a running loop is permanently busy.
