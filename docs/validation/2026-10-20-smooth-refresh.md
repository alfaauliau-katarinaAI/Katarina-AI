# Remove worker cards and bridge refresh gaps

Removed the processing-card grid from the page, including its DOM builder and
styles. Worker facts remain available in the existing runtime evidence and graph
selection. Added a low-opacity blue shimmer on at most 40 existing research
points plus a slow center breathing ring. This is explicitly labeled presentation
animation while waiting. It creates no events, counts, node positions or work
claims. Actual event traces retain their separate timestamped signals. Ambient
motion respects pause, reduced-motion preference, page visibility, viewport and
freshness. The cached base topology is preserved; labels do not move with time.

The animation frame limiter now permits 60 Hz when the device can keep up. This
is not a phone FPS guarantee. Polling checks changed from 1000 to 750 ms with one
in-flight request. Conditional ETag requests return an empty 304 response for an
unchanged snapshot; stale snapshots still return 503 before conditional handling.
Duplicate snapshot timestamps do not rerun graph/DOM work. The existing VPS
publisher was inspected: it already coalesces changed source files with a 0.5 s
minimum and a 10 s quiet deadline. It was not restarted or changed. Faster client
checks do not guarantee 750 ms end-to-end data delivery; network and publication
work still determine arrival times.

Client VM tests cover grid removal, ambient pause, stable coordinates, event
provenance, expiry and existing touch controls. Worker tests verify conditional
304 responses and stale-data rejection even with a matching ETag, alongside
privacy and authenticated ingestion. Native Canvas2D diagnostic covers 470
frames, waiting animation without invented events/position changes, identical
paused pixels, resize/zoom and opaque background. Build and ESM artifact checks
passed. Phone/browser/CSS QA is unavailable in this environment.
