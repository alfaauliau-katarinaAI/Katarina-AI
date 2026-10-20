# Mobile network render and autonomous staging organization

The owner's 14.8-second recording shows a dense rotating graph and about 17 FPS.
The new renderer keeps the default camera stationary, uses a synchronized opaque
canvas, and separates cached topology from bounded event effects. Worker labels
have stable code priority; inactive depth sorting no longer competes for labels.
There are at most 160 ordinary visible edges and 16 deduplicated phase pulses.
The underlying evidence graph is retained; selecting a point shows its relations.
Reset and pause controls are available on touch devices.

Validation: actual client VM harness verifies stable coordinates, cached base
rendering, pulse deduplication, bounded edges, reset/pause, inspection, expiry and
provenance. The real Worker auth/redaction/replay/expiry test passes. Build and ESM
artifact validation pass. Sites version 36 deployed successfully. The production
HTML is checked for the new renderer. No post-change visual test on the owner's
phone was available; FPS improvement is not claimed as measured.

File housekeeping is called by the existing NetworkDoctor every five minutes.
It scans only the runtime's `housekeeping/inbox`, categorizes settled documents,
reports, images and logs, and retains unclassified JSON in review. It never deletes
files. Every move has an fsynced intent/result journal, SHA-256 and unique target;
restore refuses conflicts or changed contents. Memory, ticks, databases,
configuration, credentials and executable files are protected. Symlinks and
Windows reparse points are rejected. Five tests cover boundaries, move/undo,
conflicting restore, links, recent files and bounded scanning.

The surgical installer compiles both sources and backs up the existing doctor
before adding the hook. It preserves active runtime changes and also gives the
doctor's snapshot writes the existing bounded Windows sharing retry.

VPS activation on 2026-10-20 was guarded by LIVE/production OFF, zero broker open
positions and zero unresolved submissions. The observer restarted as PID 6848,
with 14 background workers. Its own doctor produced a CHECKED housekeeping result
at 06:42:36 UTC: zero eligible files, zero moves, zero errors. This is an actual
same-process check, not a synthetic successful-move count. Existing datasets and
memory were not relocated. The doctor still reports REVIEW_REQUIRED for other
operational issues; housekeeping does not override those diagnostics.

## Final canvas and live runtime verification, 06:58–07:04 UTC

A native Canvas 2D rasterizer was available in the managed runtime, so the actual
production page JavaScript could be exercised with a real canvas, public
production data and a minimal DOM harness. This is not a browser or CSS-layout
test. The diagnostic found three remaining boundary cases: offscreen labels
clamped onto viewport edges at high zoom, event capsules overlapping the center
letter, and a partially covered final pixel row at fractional device scale.
The final source culls labels belonging to offscreen points, starts/ends signals
outside node disks, and paints the entire backing canvas boundary.

The reproducible diagnostic is `scripts/validation/verify_network_canvas.cjs`
and accepts a saved public HTML page, saved public JSON status and output folder.
It needs the installed `@napi-rs/canvas` runtime package and emits four PNGs plus a
result JSON. Native execution with 183 actual nodes passed 470 frames: coordinates
were unchanged while event effects advanced, paused images were pixel-identical,
zoom and resize retained finite coordinates, and every canvas pixel was opaque.
The final output images were inspected. Local timing is diagnostic only and is
not a measurement of browser/phone FPS. Browser and owner-phone QA remain
unavailable in this environment. Client regression assertions also cover label
culling and minimum signal clearances.

Actual same-PID live observation from 06:58:43 to 07:03:59 UTC:

| Persisted measurement | Start | End | Change |
| --- | ---: | ---: | ---: |
| Experiments | 54,001 | 54,324 | +323 |
| Datasets | 469 | 471 | +2 |
| Hypotheses | 108 | 109 | +1 |
| Report records | 67,570 | 67,634 | +64 |
| Reviewed experiments | 53,617 | 53,681 | +64 |
| Successful Gemini calls this process | 6 | 7 | +1 |
| Failed Gemini calls this process | 0 | 0 | 0 |

PID 6848 remained verified, with LIVE/production OFF. All nine worker status files
showed EXPERIMENT_COMPLETED at 07:00:49–07:00:56 UTC. An earlier transient FAILED
event recovered; the later retained activity sample contained no failed events.
The doctor still reports DATA_GAPS_PENDING, so complete broker data, model
quality, trained model weights and trading profitability are not attested.

A new, known-content 76-byte verification report was placed in the managed inbox
and aged to satisfy the settled-file gate. The autonomous doctor moved it at
06:59:37 UTC, without a Codex invocation of organize(). The journal contained
INTENT then MOVED, the source was absent, destination SHA-256 matched the intent,
and status recorded one move and zero errors. The verification artifact was
retained in the managed reports folder. No user datasets or AI memory were moved.

Checks after the final changes: actual client regression, Worker privacy and
expiry, five housekeeping tests, and three durable-report tests pass. Build,
artifact ESM validation and diff whitespace checks pass. The final site artifact
was pushed from source commit 93c27f71fa371bf5d6bd38deb1eb4dedcf1066da.
