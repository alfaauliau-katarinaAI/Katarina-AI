# Owner strategy — causal research candidate (21 October 2026)

Owner selected **Market Structure + Supply/Demand + Elliott Wave**. This file
documents a **provisional offline screening hypothesis**, not final trading
rules or evidence of a profitable system.

## What the implementation checks

- A confirmed structural break must be directionally consistent with BUY/SELL.
- The candidate entry must lie inside a fresh supply/demand zone.
- Elliott Wave is **approximated by a strict five-wave impulse geometry** with
  six timestamped pivots, basic wave-2/wave-3/wave-4 non-overlap rules. It is
  **not** an authoritative wave count or Elliott Wave expert system; diagonals,
  corrections, nested counts and alternative labels are NOT implemented.
- Zone creation, structure close, wave pivots, signal close and decision time
  must be causal; future information cannot be used.
- Entry, directional SL, target, verifiable evidence digest and estimated
  price-unit costs are required. Prototype cost-adjusted reward/risk >=1.5.
- The decision is only `eligible_for_offline_research`, and explicitly
  `live_execution_authorized = False` even with all checks satisfied.

## Gates NOT met by this implementation

1. Multi-timeframe definition (H1/M15/H4) and objective structural swing rules
   require agreed tests, not merely Boolean input claims.
2. Wave-label correctness and robustness against plausible alternate counts,
   zone freshness verification and tick history provenance remain unproven.
3. Historical bid/ask tick OOS testing, brokerage costs, spread/slippage, gaps,
   walk-forward and independent DEMO forward metrics have not been run for this
   candidate. Existing 55-pair Decision Brain research (8,310 hypothetical
   trades, mean -0.2051R, profit factor 0.7008) tested different strategies,
   and must **not** be reused as positive evidence.
4. Owner's requested risk 5-10% per trade exceeds the current engine's 5%
   hard trade cap at the high end. The current engine also caps total open
   risk at 8%; this prototype changes neither.
5. The 35% drawdown threshold is an entry halt, **not a maximum realized loss
   guarantee**. Existing positions must remain subject to independently
   governed risk-reducing management and emergency stop.
6. Stage 35/36/37/38 real broker, stress, strategy holdout, risk and live
   preflight receipts are still missing. No live transport is implemented.

## Promotion rule

Passing synthetic unit tests is permission to **research and backtest only**.
Any numeric expectancy, win rate, risk scaling or authorization must come from
real independent experiments with immutable source IDs and a reviewed receipt.
