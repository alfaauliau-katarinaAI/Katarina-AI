# KATARINA AI — GitHub-first status (11 October 2026)

Development source of truth: [GitHub `main`](https://github.com/alfaauliau-katarinaAI/Katarina-AI/tree/main). The repository remains public as requested.

## Completed and evidenced
- Obsolete checkout paths removed in commit `0b0658e3`, with four static regression tests.
- Windows VPS: 639 unit tests, 22 integration tests and 96 static tests passed at the recorded verification point.
- Native MetaEditor compiled 18 EA and MQL5 test targets: zero errors and zero warnings, using an isolated source/staging tree.
- Python MetaTrader5 API initialized successfully; read-only observer scanned 7 market symbols with 0 errors and 0 orders.
- Stage 10 local memory and Stage 11–40 framework/functional audits passed when run in their documented sequence, with live risk disabled.
- GitHub CI now includes a deterministic source-linkage audit (internal Python imports, project MQL includes, JSON validity, literal local website links) alongside the existing tests. Its results are not MT5 runtime evidence.

## Still blocked from live release
- Stages **14, 15, 16, 17, 38** have unfinished strategy/risk policy gates.
- Stages **35, 36, 38** require Windows runtime/testing evidence beyond successful compilation.
- Independent test proof, broker compatibility, real tick backtests/forward validation, and explicit controlled live authorization remain separate requirements.
- Never interpret `PASS_LOCAL_DEPENDENCY_LINKS`, a green GitHub build, or a successfully connected observer as a profitable strategy or permission to place orders.

## Operating rules
1. Develop from canonical GitHub `main`; use pull requests for changes likely to collide.
2. Do not force-push `main`. Verify branch refs before updating them.
3. Keep terminal credentials, broker identities, and private operational evidence out of Git.
4. Research and CI checks may run on GitHub; MT5 native compilation and runtime claims require independently captured Windows evidence.
5. Do not auto-enable live positions, scheduled observers, or increase risk limits.

For full VPS validation details, see [path and MT5 integration report](../validation/2026-10-11-paths-mt5-integration.md).
