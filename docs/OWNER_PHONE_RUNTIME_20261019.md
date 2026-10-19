# Owner phone dashboard: real runtime evidence

The existing single observer and existing /status bearer authentication remain canonical.
No additional AI workers, execution transports or order callbacks are introduced.

## Evidence displayed
- Actual server PID and equality with the fresh snapshot's observer PID.
- Fresh MT5 tick time; actual observation and successful-cycle counters.
- Per-symbol technical method, market state and action from the existing deterministic engine.
- Actual broker book read status and position/pending-order counts.
- Configured language-model state and adapter success/failure counts. A configured model,
  a successful JSON response and model quality are separate claims.
- Missing, stale, malformed and unsafe evidence is withheld. Risk clearance and live
  authorization remain false. Broker profit is not invented.

The network illustration was removed. Six cards describe existing capabilities of one
brain, not six independently running agents. Technical rows do not assert LLM activity.

## Model choice (official documentation checked 19 October 2026)
Recommended provider: OpenAI; routine work gpt-6.1-sol, deep requested work gpt-6-astra.
The first balances cost/intelligence; the second is the flagship reasoning option.
https://developers.openai.com/api/docs/models
Anthropic Claude Opus 5.5 and Fable 5.1 were compared using:
https://platform.claude.com/docs/en/models/overview

Use config/dialog_model.openai-responses.example.json as a non-secret template.
The Responses protocol is explicitly selected; old chat configurations still work.
Credentials are read only from the named environment variable. No key is committed,
exported to the dashboard or stored in model-call telemetry. Provider activation and
real-model acceptance remain pending until an Owner credential is configured.
No paid requests have been made by these fixture tests. No claim of a universally
best trading model is made without a Katarina-specific evaluation.

## Phone transport gate
Cloudflared 2026.10.1 downloaded from its official GitHub release and matched its
published SHA-256, but cannot execute on this Windows Server 2012 R2 host. It must
not be replaced by an unverified binary merely to obtain a URL.

An SSH HTTPS tunnel via localhost.run is a possible temporary testing transport:
https://localhost.run/docs/
Its launch is currently blocked by automatic approval review because the Owner has
not approved this third-party destination for the private dashboard. Do not retry
that action through another tool, another tunnel or an indirect launcher.
Before launch, obtain explicit Owner approval for forwarding the bearer-protected
127.0.0.1:8765 service through localhost.run. No public listener is opened meanwhile.
A stable custom hostname and managed production access require a separate domain setup.

LIVE OFF is required during every local or phone test.
