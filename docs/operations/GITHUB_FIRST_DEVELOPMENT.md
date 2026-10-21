# KATARINA AI — GitHub-First Development & VPS Verification Gate

**Effective date:** 2026-10-10  
**Status:** Active operating policy (supersedes the older VPS-first development loop).

## Execution order

1. **GitHub is the sole development source of truth.** All source changes start on a short-lived branch. Use pull requests for review and track the exact commit SHA.
2. **GitHub-hosted Actions do the implementation checks.** Compile Python, run unit/static/integration regressions, Stage 10 memory audit, Constitution Guard, Stage 11–40 framework audit and functional-body audit. Check the recorded outputs, not merely a green badge.
3. **Windows-specific reproducible tests run on GitHub-hosted Windows runners** whenever they do not require the owner's MT5 terminal, broker login or private data. Existing stage-specific Windows/MetaEditor workflows remain available for relevant changes or manual dispatch.
4. **Only after GitHub evidence passes**, escalate a *specific unanswered validation question* to the VPS. Capture test scope, triggering commit SHA, expected evidence, and rollback procedure in the request.
5. **VPS use is verification-only** for now: read-only broker/environment preflight, terminal-specific compile/runtime checks, historical tester inputs, symbol/account-specific behavior and compatibility evidence. Do not make the VPS the default editing or build workspace.
6. **No automatic live trading.** Stage 38 and any broker-mutating action require explicit owner authorization plus the normal risk/safety approvals. Passing GitHub CI cannot authorize live execution.

## GitHub gate

The canonical repository-wide GitHub-hosted gate is **KATARINA Body CI**:

- Trigger: pull request, push to `main`, or manual dispatch.
- Security: read-only `GITHUB_TOKEN` permissions; no VPS labels or self-hosted runners.
- Checks: Python compile, unit, static, integration, Stage 10, Constitution Guard, Stage 11–40 framework, and functional-body audits.
- Evidence: JSON reports uploaded as the `katarina-body-gate-<run-id>` Actions artifact.
- Fail-closed: audit results must match PASS markers and all audited `live_risk_ready` values must remain false.
- Any failed check blocks **declaring the change validated**. Fix the GitHub branch and rerun before external validation.

Other stage-specific workflows can provide additional verification, but they do not replace the Constitution Guard or the broker-specific validation boundary.

## VPS escalation requirements

Before dispatching VPS work, record:

| Field | Requirement |
| --- | --- |
| GitHub SHA | Exact source commit that passed relevant CI |
| Reason | Test that cannot be completed on GitHub-hosted runners |
| Scope | Explicit allowlisted, read-only action wherever possible |
| Preconditions | Terminal, data, account type and safety state |
| Expected evidence | Timestamped results and applicable log/artifact IDs |
| Rollback | How to leave the host in the original safe state |


## Public repository hygiene

- Never commit passwords, API keys, GitHub tokens, broker account IDs, credentials, `.env` files or proprietary client data; move needed credentials to GitHub Actions Secrets or a secure local store.
- Treat entire **Git history** as public, not only current files. Rotate any credential that was ever committed; deleting the current file alone is not sufficient.
- Do not publish VPS logs/artifacts that contain account or other sensitive fields; redact before upload.
- Pull-request jobs must not use sensitive secrets or execute on the private VPS.
- Public repository GitHub-hosted Actions have favorable free-minute terms, **not unlimited API calls, disk storage or concurrent jobs**. Avoid heartbeat-style commits and prefer one artifact per validation cycle.

## Completion definitions

- **GitHub-validated:** relevant hosted CI and audits pass on the exact commit, with inspectable evidence and no safety regression.
- **VPS-verified:** external, read-only checks pass for the same source SHA on the target host.
- **Production/live-ready:** never implied by either result; requires independent, explicit approval and Stage 36/38 evidence.

If external evidence is unnecessary, complete the work entirely on GitHub and do not contact the VPS.
