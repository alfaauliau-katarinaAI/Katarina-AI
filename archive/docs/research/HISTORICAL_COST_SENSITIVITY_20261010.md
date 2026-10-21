# KATARINA AI Brain — Cost Gate Recalculation and Expectancy (2026-10-10)

## Request and decision
Recalculate whether KATARINA's original `entry spread / ATR <= 0.15`
rule is preventing reasonable scalping research. **Result:** it rejects
99.33% of the 3,435 M1/M5 quoted technical proposals, but retrospectively
relaxing the gate does not make the tested mean 15-minute quote changes
positive. Keep the existing execution blocker and `NO_TRADE` until a
strategy has been proven after execution costs.

## Evidence and immutable historical windows (UTC)
- M1 entry / M5 closed context: 3,435 quoted prospective-like historical
  entry and 15-minute exit pairs. 74 broker catalog entries; 55 with M1
  history; 2026-08-16 through 08-31, 09-15 through 09-30, and 10-01
  through 10-09 (non-contiguous calendar windows).
- Separate M5 entry / M15 context: 588 historical pairs over the same three
  windows. These are **different signal populations**, so their mean
  returns do not establish a controlled timeframe contest.
- Every quote uses broker historical bid/ask; BUY enters ask/exits bid;
  SELL enters bid/exits ask. Full approximate round-trip quoted spreads
  are already included in the net-markout bps.
- All sample prices previously informed research choices. This is a
  **post-hoc sensitivity test**, not an untouched out-of-sample result.
  Historic broker trade permissions and point-in-time macro events are
  unavailable, and actual fills, commission, slippage, TP/SL paths and
  risk-based PnL have not been measured.

## Fixed spread/ATR sensitivity sweep — M1/M5
The threshold grid is fixed independently of the observed result:
0.15, 0.25, 0.35, 0.50, 0.75, 1, 1.5, 2, and unbounded.
No threshold can automatically change a model or trading permissions.

| Spread / entry M1 ATR maximum | Samples | BUY count | BUY mean net quote bps | SELL count | SELL mean net quote bps |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.15 (original) | 23 | 14 | -4.211 | 9 | -6.128 |
| 0.25 | 77 | 40 | -1.432 | 37 | -2.398 |
| 0.35 | 133 | 73 | -1.153 | 60 | -2.330 |
| 0.50 | 195 | 110 | -1.764 | 85 | -5.310 |
| 0.75 | 300 | 158 | -1.716 | 142 | -4.833 |
| 1.00 | 480 | 241 | -3.155 | 239 | -4.562 |
| No spread limit | 3,435 | 1,851 | -28.885 | 1,584 | -27.395 |

At 0.25, adding a purely illustrative 2 bps round-trip fee/slippage
stress (on top of historical quoted bid/ask spreads) shifts BUY to
-3.432 bps and SELL to -4.398 bps. **2 bps is a stress scenario,
NOT a verified broker fee.**

## Separate M5/M15 sensitivity
| Spread / entry M5 ATR maximum | Samples | BUY (n, mean bps) | SELL (n, mean bps) |
| --- | ---: | --- | --- |
| 0.15 | 1 | 0, no result | 1, -0.785 |
| 0.25 | 18 | 6, +1.386 | 12, -1.942 |
| 0.35 | 50 | 21, +0.472 | 29, -2.012 |
| 0.50 | 107 | 43, +0.172 | 64, -2.524 |
| 0.75 | 235 | 99, -6.216 | 136, -2.139 |
| 1.00 | 326 | 135, -7.128 | 191, -2.183 |

M5/M15 BUY at 0.25 had 6 observations across **only 3 UTC dates**.
BUY at 0.35 had 21 across only 6 dates. At 0.50, 43 BUY spanned
13 dates but averaging across different instruments; no single
instrument+side had 30 observations spanning >=10 dates. Even
illustrative extra 2 bps makes +1.386, +0.472 and +0.172 become
-0.614, -1.528 and -1.828 bps, respectively. Never promote from these
small, reused samples.

## Change the economic definition, not blindly widen the numeric gate
A one-minute ATR is not a trade's planned take-profit distance. For
candidate setup research with predefined gross TP and SL distances in the
same price units, the correct *conditional* budget is:

```
cost = full round-trip spread + round-trip commissions (price equivalent)
       + estimated total entry/exit slippage (price equivalent)
net_win  = gross_target_distance - cost
net_loss = gross_stop_distance + cost
break_even_win_probability = net_loss / (net_win + net_loss)
expectancy = (p_hit * net_win) - ((1-p_hit) * net_loss)
```

Example ONLY: spread = 0.25 ATR, target = 2 ATR, stop = 1 ATR,
zero *additional* cost. net win = 1.75 ATR; net loss = 1.25 ATR;
break-even hit probability = 41.67%. A strict 0.15-ATR spread gate
would reject the setup even though it could hypothetically be
economically viable if **an independent backtest actually demonstrates**
a stable >41.67% hit rate after additional costs. Additional fees,
slippage, early stop-outs, quote movement and market structure may
raise this requirement. An assumed target is not proof that it is reached.

The new `src/katarina/intelligence/cost_expectancy.py` implements
strictly **research-only, fail-closed** calculations. Missing
commission-equivalent or measured probability yields no computed
expectancy and never enables trading. It is not wired into live EA
orders or position sizing.

## Evidence and reproducibility
Read-only historical file:
`C:\KatarinaDev\artifacts\historical-brain\cost-sensitivity-aug16-oct9-v1.json`

To reproduce with existing immutable M1/M5 and M5/M15 broker quote
archives, from the research branch:

```text
python scripts/research/historical_cost_sensitivity.py --m1-report AUG_M1.json SEP_M1.json OCT_M1.json --m5-report AUG_M5.json SEP_M5.json OCT_M5.json --output NEW_UNIQUE_JSON
python scripts/research/summarize_cost_sensitivity.py FILE.json
```

Always retain and audit broker archives before analysing. The script
checks bid/ask mathematics, frozen original cost flag, original
and exit spread decomposition, source SHA256, broker catalogue
consistency and source window uniqueness. It refuses overwrites.
The raw archives remain on the VPS, not silently added to GitHub.

## Next engineering requirements
1. Read the broker's current contract specs and separately derive known
   actual commissions/lot, tick value, conversion and slippage assumptions
   before applying an executable position-cost calculator.
2. Decide a strategy's **predeclared** TP and SL from closed historical
   evidence, then simulate exact bid/ask tick first-hit TP/SL paths,
   with early session closes and worst-case entry/exit delays.
3. Split the study chronologically and prohibit retuning parameters on
   the final holdout. Include costs and uncertainty by symbol, direction
   and liquidity session. Reject inadequate sample sizes.
4. Only if validated expectancy is positive with margins should the
   already-separate risk execution engine be considered for review;
   current trade decision remains **NO_TRADE**.
