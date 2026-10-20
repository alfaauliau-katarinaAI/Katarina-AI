# Flexible sphere controls

Restored direct manipulation of the research sphere without restoring settings panels or worker cards. One pointer rotates with short decaying inertia; two pointers pinch zoom and pan. Pointer cancellation clears gesture state. Automatic sphere and pair rotation pause during manipulation and for 1.8 seconds afterward, then resume without resetting the view. Double tap or Home restores fit. Mouse wheel and arrow keys also work.

Validation: actual client JavaScript VM exercises drag, pinch/pan, transition from two pointers to one, cancellation, delayed automatic rotation, wheel, Home, and double tap. Client and server Worker unit suites passed. Artifact build and ESM validation passed. Native Canvas2D diagnostic passed 470 frames at 410 nodes / 599 edges, with unchanged model coordinates, rotating network and pair projections, ambient animation, opaque background, and identical paused pixels. Native rendering p50 18.47 ms, p95 32.81 ms; these are not browser or phone FPS measurements. Canvas output inspected visually. No direct mobile/browser validation was available.

This change only affects display controls; VPS execution, research workers, and order permissions are unchanged.
