# Sites runtime monitor

The initial free Render web-service request was rejected by the provider because its account requires payment information. No card or paid plan was added.

The supported Sites Worker serves the same technical dashboard at its stable HTTPS origin.
Its only stored object is current-snapshot.json in the Site's logical BUCKET binding.
It contains a fresh allowlisted technical projection and up to 80 bounded canonical process events; no AI database, tick dataset, account information, Owner token or ingest secret is stored in that object.
R2 overwrite uses conditional writes to prevent an older simultaneous request replacing a newer snapshot.
Captures expire after 120 seconds. All Owner control endpoints are unavailable.

The ingest credential is a secret environment entry, never source or browser data.
Viewing is public and token-free under the owner's explicit test-access request.
The outbound VPS publisher reads canonical state files and uses HTTPS with certificate validation.
The browser polls every five seconds while visible; the VPS sends roughly every 15 seconds.
Event time and the last observed phase show the actual progress; the display is not a neuron-activation measurement.

Canonical application source and changes are committed in GitHub. A byte-identical approved Site source subtree is mirrored only for hosting packaging and deployment.
The observer, AI memory and MT5 data stay on the VPS test host. LIVE remains OFF.
