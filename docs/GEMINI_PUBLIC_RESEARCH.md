# Gemini public-article research

The existing foreground VPS brain owns this capability. There is no second agent, model worker or trading executor. Use the public Gemini configuration example with `--owner-model-config` and the existing `--extended-news-research` flag. Gemini 3.5 Flash-Lite returned a valid JSON response in a real HTTPS test from the Windows VPS. The earlier 2.5 model returned HTTP 404 in that test environment.

## Data and evidence boundary

Only an allowlisted public article URL, publication/retrieval timestamps, content digest and at most 10,000 characters of its public body are sent to the model. Owner chat, recalled private memory, credentials, account/position information and tick/candle data are not sent. Owner dialog is blocked when the configured model has `PUBLIC_RESEARCH_ONLY` scope.

Outputs must match the bounded JSON schema. Supporting quotations must occur literally in the supplied excerpt. This checks provenance, not semantic correctness. Results are stored in `public_language_reviews` and appended to shared operational memory as unverified candidates. They never authorize policy/code changes, risk changes, orders or model-weight training. LIVE remains OFF.

## Scheduling and visibility

A persistent attempt ledger permits at most one call per 900 seconds and 24 attempts per UTC day, including failed calls. Successful document/digest/model combinations are deduplicated. Provider failures leave the observer running. No automatic paid fallback, billing activation, grounding or external tools are enabled. The provider project's free-tier availability is still required.

The existing RESEARCH lifecycle phase covers the actual call. The public dashboard shows bounded model call counters and process events, not raw candidate contents. Model-call counters are process-local and reset after a restart; the attempt and candidate ledgers persist in the canonical research database. Scheduled observer and publisher tasks have no 72-hour execution cutoff, but still depend on the Windows/MT5 session and valid resource/identity checks.

## Credential handling

The repository Actions secret is `GEMINI_API_KEY` (or the explicit `GOOGLE_API_KEY` alternative). The manual provisioning workflow seals it to the committed owner-VPS public key using RSA-3072 OAEP-SHA256. The existing CI can perform the same one-time operation only for an explicitly marked `[gemini-provision]` main commit; no additional push webhook is used. Only ciphertext is uploaded, with one-day retention. The private key stays in the VPS's inheritance-protected System/Administrators directory. Validate the artifact digest, decrypt locally, and keep the resulting credential file under the same restricted directory. Never print, commit or publish the key. The configuration contains only its private file path and a verified CA-bundle path.

References: https://ai.google.dev/gemini-api/docs/api-key ; https://ai.google.dev/gemini-api/docs/openai ; https://ai.google.dev/gemini-api/docs/pricing
