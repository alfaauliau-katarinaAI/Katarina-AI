# Stable free technical monitor

The VPS remains the test observer host. The dashboard relay is a separate free Render web service with a stable onrender.com address, not an expiring SSH URL.
The relay never runs MT5, a model, Owner tools, account access or strategy execution.
Only a bounded technical projection and up to 80 canonical lifecycle events are sent by the outbound publisher. AI databases, tick datasets, credentials and account identifiers stay on the VPS.

Observer events are emitted around the actual calls in the canonical pipeline: CONNECT, NEWS, SENSORS, TECHNICAL per symbol, MEMORY, RISK_AUDIT, WAIT_ACK, PUBLISH and WAITING.
They are not model neurons. STARTED/DONE/FAILED distinguish work in progress, completed calls and failures.
The graph flashes once only when an event key changes, and exposes the event timestamp and symbol result. No event means no claimed activity.

The relay requires a random private ingest token of at least 32 characters, stored only in the service environment and VPS private config. Browser viewing requires no token. All control endpoints are unavailable on the relay.
Ingest is size-bounded, rejects replays and future/old captures, and re-applies the public allowlist.
If no new capture arrives for 120 seconds, /public-status returns 503 and the UI clears the old evidence.
A fresh transport capture does not override the observer snapshot freshness or LIVE-OFF gates.

Deploy the merged, validated GitHub source as Python with:
- Build: python -m compileall -q src services
- Start: python services/monitor_relay.py
- Instance: free; one instance; no disk or paid datastore
- Environment: KATARINA_MONITOR_INGEST_TOKEN (private), PYTHONPATH=src
- PORT: provided by Render, binding 0.0.0.0

On the VPS, run the approved scripts/ai/publish_runtime_monitor.py with --state-dir and a private --config containing endpoint, token and the trusted CA bundle path. Default send interval is 15 seconds, with bounded retry backoff.
Only use the actual returned HTTPS service hostname. Do not commit runtime secrets or user-specific ingress configuration.
Free hosting has cold starts and quota limits; a stable hostname is not an uptime guarantee.
