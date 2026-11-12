# MT5 universal account execution

The existing forward worker and continuous observer accept `universal_execution: true`
in the local ConnectionConfig JSON. Keep `demo_experiments: true`, `priority: ["local"]`
and the explicit terminal path for compatibility with existing launchers. These
legacy option names no longer restrict the universal worker to DEMO accounts.
`expected_login` and `expected_server` remain required for legacy tools; universal
execution obtains its active identity from MT5, never from these labels.

Provide `execution_authorizations` as a list of owner-approved records:

```json
{
  "mode": "REAL",
  "login": 123456,
  "server": "Actual MT5 server",
  "strategies": ["REPLACE_WITH_VALIDATED_APPROVED_64_CHARACTER_STRATEGY_SHA256"],
  "max_risk_fraction": 0.001,
  "max_margin_fraction": 0.25,
  "expires_at": 1800000000
}
```

This is a schema example, not an authorization. Supply the actual account identity,
validated strategy hashes, approved risk limits and UTC Unix expiry. DEMO, REAL and
CONTEST each require their own record. No wildcard approval or automatic strategy
promotion exists. Reload the worker after changing the configuration. The global
`continuous.stop`, `demo-forward/demo.stop` and independent worker `executor.stop`
remain available. Terminal/account trade permission is rechecked for each send.

A changed mode, login or server pauses one cycle, discards the active runtime and
requires fresh authorization, account ledger reconciliation, position/pending-order
inspection, strategy qualification, symbol volume validation, margin calculation,
and Risk Governor approval. State under `accounts/<identity hash>/demo-forward`
is isolated per identity and reused on return, preserving loss history, pending
submissions, deduplication and position ownership. The enrollment ledger still
requires an empty book for an account without a baseline; it does not assume an
existing portfolio is risk-free. Existing ledger currency support remains USD/USC.

The same submission and position-management implementation serves all account
modes. Legacy callers without an authorization retain their explicitly enrolled
DEMO permission only. REAL authorization never derives from demo enrollment.
Universal new entries also require an empty current position and pending-order book,
including a second check after broker order validation. Existing owned positions
continue through the shared management path.

Internal `DEMO_` status names and SQLite table names remain for compatibility.
The universal worker identifies itself as UNIVERSAL and publishes its active status
to `demo-forward/status.json` without refreshing cached decision timestamps.
The Python dashboard recognizes the universal worker. The legacy MT5 chart EA
still contains DEMO-specific labels and static binding display; it is not an
authorization signal or proof of REAL readiness.

ResearchPool continues separately, with the shared experiment database and market
clock read from the original research root. Candidate qualification is necessary
but insufficient: the exact strategy hash must also be in the account's approval.
Observing an account with Algo Trading enabled grants no order permission.

Validation uses simulated MT5 brokers; no live orders are sent by the tests.
Account identity is checked again immediately before native `order_send`, including
after `order_check`. The MT5 Python API does not provide atomic "send only if login
still equals X" semantics. An external terminal switch in the interval between
that last check and native submission cannot be ruled out by Python code. Operate
one controlled terminal per executor and prevent external switching while a send
is in flight for that stronger guarantee; a terminal-side execution protocol would
be needed to enforce it beyond this process.


## Preparing a software candidate

The source builder refuses a dirty checkout by default so it cannot silently ship
an older committed engine. For a reviewed working-tree candidate:

```text
python scripts/pc/build_pc_test_package.py --working-tree --output <candidate.zip>
```

`SOURCE_REVISION.json` identifies the base commit, the working-tree snapshot and
the hash of every packaged file. Untracked configuration and private state are
excluded. Changes to tracked configuration require review; the promotion lock is
accepted only after its referenced validation record and source hashes pass.
The kit includes the independent executor launcher and Windows broker dependency
requirements. It contains source only, not Python, the terminal, credentials or
an account authorization.

On the destination Windows host, install the pinned requirements with the project's
Python 3.12 runtime and verify the exact terminal path. Start with an empty
`execution_authorizations` list and the worker's `--audit-only` flag. Account reads
and research can then be checked without granting order rights. Verify terminal
connection, broker identity, permissions, clock evidence, kill switches, restart
and status freshness before enabling any owner-approved account/strategy record.
Keep the old release and its account state for rollback; do not reset loss ledgers
or copy one account's database into another account's directory.

The software promotion record authorizes the requested code capability only.
It neither approves a strategy nor grants execution permission to an MT5 account.


When upgrading an existing DEMO installation, finish and reconcile its legacy
`demo-forward/orders.sqlite3` positions with the old executor before enabling the
universal worker. Back up the old release and state after stopping it. The new
account-scoped folders do not automatically adopt legacy positions or loss
baselines. Do not run the old and new executor together against the same account.
A destination with an unresolved legacy book is not ready for universal execution.
