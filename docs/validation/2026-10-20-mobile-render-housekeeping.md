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
