# Locked automatic pair orbit

Removed the entire graph control panel: pair selector/summary, reset button,
pause button and gesture hints. Camera settings are fixed. Drag, pinch, wheel and
keyboard camera/pause handlers are removed; canvas touch behavior permits normal
vertical page scrolling. A tap can still inspect a point's evidence.

Attested pair points slowly orbit the network, one revolution in approximately
57 seconds. This is a cosmetic display transform on pair coordinates only. It
does not change graph records, work states, schedules, discovered pair names or
result counters. The short coordinate caption labels the orbit as visual and
actual activity as VPS evidence. Real pair routes and event signals continue to
use the current positions. Pair edges/labels have a separate dynamic drawing pass;
the underlying research topology and worker labels remain cached and stable.
Motion respects data freshness, visibility, viewport and reduced-motion settings.

Validation: actual client and Worker VM tests passed. The native Canvas2D test on
an actual public pair packet passed 470 frames, 410 nodes and 599 edges: pair
coordinates advanced, non-pair coordinates stayed fixed, paused diagnostic pixels
matched, waiting animation worked and background remained opaque. Projection and
resize remained finite. Render output was visually inspected. Frame p50 was
7.0 ms, p95 13.6 ms on the diagnostic host; these are not phone/browser FPS
measurements. Build, ESM artifact and whitespace checks passed. No VPS runtime,
MT5 configuration or execution permissions changed for this presentation edit.
