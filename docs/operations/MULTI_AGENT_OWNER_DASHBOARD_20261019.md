# Multi-Agent Owner Console (GitHub-only)

Status: **proposed in branch; NOT deployed to VPS, NOT live execution clearance**.

## Goal

Give the Owner a responsive dashboard comparable to the supplied multi-agent
video while preserving the 16 October single-brain contract. Six cards (SCAN,
ANALYST, STRATEGY, BALANCE, EXEC, AUDIT) are **capability labels, not six
workers, trading agents, executors or new processes**. The topology animation
is illustrative only. Nothing can send, arm, retry or alter broker orders.

## Source and transport

- `src/katarina/monitoring/agent_projection.py` converts the existing
  `read_runtime` report into bounded, safe lane summaries. A healthy observer
  proves only a validated snapshot. It does not attest to analytical work,
  Risk Governor operation, profit or execution.
- `src/katarina/adapters/continuous_owner_surface.py` adds `agent_board` to
  the same authenticated `POST /status` response. No separate observer, state,
  lock, socket, background queue or memory database is introduced.
- `src/katarina/adapters/owner_dialog_server.py` serves a standalone,
  responsive page at `GET /agents`. GET does not reveal any account detail;
  the browser must explicitly present Owner/analyst credentials to read
  `POST /status`. Token stays in the page input only, never URL/localStorage.
- `src/katarina/adapters/agent_dashboard_page.py` uses no external CDN,
  third-party service or synthetic market prices. Empty/unverified status
  appears as such; model and broker-profit metrics are intentionally blank.
- Existing `/` Owner dialog, `/turn`, access revocation, HTTPS enforcement,
  risk boundaries and delivery `DISABLED` are unchanged.

## Use (only after authorized deployment)

Start the **existing** canonical Owner observer with its approved config and
the same locked state directory. Open `https://AUTHORIZED_HOST/agents` over
a trusted certificate on a phone, or `http://127.0.0.1:8765/agents` on the
host. Enter the Owner token, click **Periksa sekarang**, optionally enable
30-second client polling. No browser credentials are saved.

**Do not start a second UI/observer to make /agents work.** Do not expose the
host to the internet with plain HTTP. Owner/phone TLS is a separate pending
gate from CI. No GitHub Actions or PR build should auto-deploy to VPS.

## Release gates

1. Approve source on a protected GitHub PR and pass static/unit/integration CI.
2. Verify the exact checkout and process hash before any testing on VPS.
3. Test the existing authenticated HTTP status response and /agents markup
   with mock and stale snapshots; reject fictitious metrics, worker counts or
   live-clearance claims.
4. Independently validate phone TLS, model quality and broker history before
   claiming readiness. Keep `LIVE OFF`, `orders_submitted = 0`.
5. If any test requires temporary files on VPS, place them under **an
   explicitly agreed ephemeral test-only directory**, never under source or
   active brain-memory paths, and remove them afterward.

The GitHub repository is the single source of truth. VPS is for tests and
maintenance only, not an editing surface.
