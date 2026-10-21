# KATARINA Operational Hardening V1

This package closes the main gaps between strategy logic and durable account operation.

Implemented:
- account-wide position + pending-order + in-flight reservation risk;
- manual/foreign pending exposure included in the same 8% open-risk budget;
- 5% per-entry ceiling preserved;
- stateful 35% daily drawdown (Owner stop for new entries) with deposit/withdrawal neutrality and day reset;
- 35% total drawdown tracking;
- broker-native OrderCalcProfit evidence book;
- append-only restart persistence for reservations, pending risk, RR peak-R, broker-risk evidence and execution recovery;
- partial-close / SL execution recovery with no duplicate command while in-flight and remainder retry after partial fills;
- tick-by-tick execution simulator using bid/ask, commission, slippage and the same RR 80% partial / 30% high-water SL logic;
- validation suite combining backtest metrics, walk-forward and Monte Carlo;
- fail-closed economic calendar gate;
- operational dashboard schema covering risk capacity, manual risk, pending risk, reservations, RR state, PF and Recovery Factor.

## External evidence boundary

This implementation does not invent historical XAUUSD ticks or economic-calendar credentials. Real performance numbers require an actual broker tick dataset / MT5 Strategy Tester run. The economic gate remains fail-closed until a fresh provider snapshot is supplied.

## Safety invariants

Manual positions/orders remain non-mutable by default. Pending and reserved exposure can reduce or eliminate capacity for a new KATARINA entry. Restart recovery may restore desired state but all broker mutation still requires fresh reconciliation and normal execution authorization.
