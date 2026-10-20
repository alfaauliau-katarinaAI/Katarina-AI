# Automatic spherical network and pair rotation

The complete network now rotates automatically about its vertical axis with a
slight viewing tilt. Pair points use a 12-position Fibonacci sphere at radius
1.16, with a separate slow angular progression; they have distinct latitudes and
full depth instead of a flat orbital ellipse. New research placements use an
isotropic volume while retaining actual ancestry relations and stable model
coordinates. Projection rotation does not create work events or new pair names.

The graph settings panel remains absent. Motion respects freshness, visibility
and reduced-motion preferences. A 24 ms frame limiter bounds continuous redraw
load. Signals follow current projected endpoints. Existing runtime and all
execution permissions are unchanged.

Actual client/Worker VM and native Canvas2D checks passed, including changing
network projection with stable graph model coordinates, pair points on a sphere,
waiting animation, frozen diagnostic pixels when motion is disabled, opaque
canvas and finite resize/projection. Render output was visually inspected;
browser/phone QA remains unavailable. Build and ESM artifact checks passed.

Edges and nodes are batched by drawing style, and text glyphs are cached, reducing
repeated work during full rotation. The final diagnostic completed 470 frames
with 410 nodes and 599 edges, confirming spherical/network motion, stable model
coordinates and frozen disabled-motion pixels. Host p50 was 17.9 ms and p95
34.0 ms; no phone/browser FPS guarantee is implied.
