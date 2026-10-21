# Demo execution boundary — 2026-10-20

Status: IMPLEMENTED_AND_TESTED_COMPONENT_NOT_ARMED.

Owner authorized demo experiments with Risk Governor retained. This change does not authorize real-account execution.

## Implemented

`katarina.engines.demo_execution.DemoExecutionBoundary` connects the existing configured RiskGovernor to a demo-only submission boundary. It requires an explicit account/server binding, the installed demo constant, terminal and account permissions, fresh intent and reconciled risk evidence, a protective SL/TP, verified capital, and a broker-calculated loss that fits the approved fraction. It performs order_check and rechecks identity, permissions, stop state and expiry immediately before order_send.

The private SQLite outbox reserves an intent before submission, rejects conflicting reuse and concurrent unfinished intents, and retains accepted, partial or uncertain outcomes for reconciliation. It never retries an unknown result automatically. Broker tickets remain private; exception messages are redacted. A send acceptance is not proof of a reconciled position, successful forward test or learning improvement.

## Validation

48 unit/regression tests passed on the Windows VPS: demo boundary (12), adaptive Risk Governor, execution recovery and multi-symbol execution. Concurrent producers used separate boundary instances and a shared durable outbox. These are simulated-broker tests, not actual MT5 orders.

## Remaining before activation

- Wire the active strategy/experiment producer to freshly reconciled complete account risk. Callers must not fabricate `health_ok`, `reconciled`, capital, uncertainty or expected RR.
- Complete account-book reconciliation and lifecycle management, including matching broker fills, partial fills, close outcomes and restart recovery. The boundary intentionally exposes no method that silently clears unresolved submissions.
- Migrate the existing single-terminal observer permission contract and its public attestations to an explicit demo execution mode. Do not remove the read-only checks or report Algo Trading OFF when it is ON.
- Validate broker symbol sizing/filling, current quotes, commissions/slippage allowance and protection distances through the producer and broker check. `order_calc_profit` measures price-to-stop loss; it alone does not establish all-in fees or guaranteed loss at a stop.
- Run an end-to-end demo trial and record actual broker outcomes. No strategy is automatically promoted to real trading.

## Live audit at validation

The active account monitor reported connected DEMO, Algo Trading OFF, zero positions, zero pending orders and zero orders submitted. Its risk-verification flags are currently unconnected/false, not independent measurements of historical drawdown or costs. The existing observer and publisher were not restarted or altered. No account setting was changed and no MT5 order was sent.

References: https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py and https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py.


This initial component audit is superseded for integration status by 2026-10-20-demo-forward-integration.md. No native broker open/close-cycle proof is implied.
