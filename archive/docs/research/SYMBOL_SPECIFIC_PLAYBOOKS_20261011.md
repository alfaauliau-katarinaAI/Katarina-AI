# KATARINA AI — Symbol-specific research playbooks (11 October 2026 WIB)

## Decision and objective

**Research-only. Live trading remains NO_TRADE.** Stop assuming a single
EMA/ADX/sweep strategy, TP/SL, and session applies across metals, index
CFDs, and FX. This improvement directly replaces the automatic universal
shadow proposal in the scheduled market observer with a broker-symbol
registry that fails closed for unidentified/unprepared instruments.
Volatility-based broker-universe rankings are still *observation only*;
they are not entry strategies or order authorizations.

## Distinct predeclared market contracts

| Broker symbol | Family | Concept and target/stop | Maximum hold |
| --- | --- | --- | --- |
| XAUUSD.vx | gold_sweep_shift_confirm_v1 | 20-bar liquidity sweep then directional displacement and confirming M1 candle; structural stop beyond sweep extreme; prior 75-bar liquidity target | 35 min |
| NAS100.vx | nas_trend_pullback_continuation_v1 | US New York session M1 pullback/EMA20 reclaim with fully closed M5 trend and ADX >=24; stop beyond preceding 6-bar extreme, target 1.65x structural risk | 45 min |
| US30.vx | dow_ny_opening_range_break_v1 | NY 09:30–10:00 *local* opening range, directional 10:00–12:30 local breakout; stop 0.85 M1 ATR inside break level, target 1.4x risk | 50 min |
| JPN225.vx | nikkei_tokyo_range_retest_v1 | JST 09:00–09:30 opening range, retest confirmation, stop 0.5 M1 ATR beyond range boundary, 1.25x risk | 50 min |
| EURUSD.vx | eur_london_asian_range_break_v1 | London 08:00 local breakout of overnight Asia extremes, closes beyond range; stop 0.8 ATR inside range, target 1.3x risk | 50 min |
| GBPUSD.vx | gbp_london_asian_sweep_fade_v1 | London 08:00–11:30 local false breakout of Asia high/low then reversal toward Asian midpoint; stop outside swept wick | 55 min |
| USDJPY.vx | uj_tokyo_open_range_momentum_v1 | Tokyo 09:00–09:30 JST opening range breakout aligned with completed M5 EMA50; stop 0.75 ATR inside boundary, 1.5x risk | 70 min |

The research script uses the correct US and UK seasonal UTC offsets
when setting local NY/London hours. UTC midnight–opening time is the
Asia-window contract for the corresponding GBP/EUR strategies. Every
proposal is calculated using completed bars only; no future-formed
pivot or market-specific signal is transferred to a different symbol.

**Important:** explicitly registered rules are hypotheses, NOT
guaranteed alpha. Do not force another instrument to trade when its
historical spread or data do not support its own setup.

## Historical tick trial and brokerage constraints

Broker: Valetax International Limited demo, .vx symbol catalogue.
Price evidence: historical broker M1/M5 closed OHLC and tick-level
bid/ask quotes returned by the installed read-only MetaTrader 5 ALFA
terminal, no market-open waiting required. M1 directional structural
entry *price* is used to choose stop and TP, but the actual entry
side assumes broker ASK for BUY and BID for SELL after 250ms dispatch
delay and a <=30sec quote window.

The new experimental stop targets are structural per symbol rather
than identical ATR TP2/SL1 applied everywhere. A quote must satisfy:
positive return/stop geometry; >= current broker minimum stop
distance + four broker ticks; spread / estimated target <=30%;
individual research spread/ATR cap from the symbol registry; no
same-symbol overlapping 35–70min research position within a
single instrument. Only first broker quote that hits TP or SL is
used; favorable TP crossing capped, unfavorable stop gaps charged
at worse quote. Missing or >180sec-gapped quote paths are not
silently converted into wins. Market impact, actual fill latency,
commissions and slippage remain unknown, so 0,1,3 tick *adverse*
entry and exit stress is applied. No actual orders or PnL claim.

Prices dated July 2026 through October were not a pristine untouched
dataset in the wider KATARINA project. The additional July NAS test
used *the frozen existing playbook code*, but was still evaluated
after inspecting Aug/Sep/Oct and cannot be treated as genuinely
independent prospective validation.

## Actual historical results from VPS
Files (not yet published to GitHub):

C:\KatarinaDev\artifacts\historical-brain\
- distinct-xau-dow-playbooks-pilot-v1.json and -audit.json
- distinct-nas-nikkei-playbooks-pilot-v1.json and -audit.json
- distinct-fx-playbooks-pilot-v1.json and -audit.json
- distinct-nas-locked-july-v1.json and -audit.json
- distinct-playbook-fixed-rule-summary-v1.json
- per-symbol-mirror-control-v1.json
- distinct-nas-locked-june-v1.json (missing data, **NOT an outcome**)

All 7 registered playbooks were replayed against broker history for
the frozen windows 2026-08-16–31, 2026-09-15–30 and 2026-10-01–09 UTC.
NAS was additionally tested on 2026-07-01–31 without retuning.
Research summaries use one extra adverse broker tick *per side*:

| Symbol | 1-tick-sides priced entry paths | Mean R | Finding |
| --- | ---: | ---: | --- |
| NAS100.vx | 61 | **+0.2240 R**, profit factor **1.465** | July +0.292 (32), Aug +0.544 (7), Sep +0.0118 (15), Oct +0.0473 (7); insufficient evidence, no validation |
| US30.vx | 31 | **-0.2263 R**, PF **0.664** | Negative in all three windows |
| XAUUSD.vx | 1 | +0.155 R | Too few candidates; no statistical meaning |
| JPN225.vx | 0 | n/a | No qualifying entry on the predeclared rules |
| EURUSD.vx | 0 | n/a | 68 technical setups; all blocked by original symbol-specific spread/ATR affordability cap |
| GBPUSD.vx | 0 | n/a | 17 technical setups; all blocked by GBPUSD cost threshold |
| USDJPY.vx | 0 | n/a | 6 technical setups; all blocked by USDJPY cost threshold |

June NAS100 *cannot* be used: MT5 returned only ONE M1 bar
(timestamp 2026-07-01T02:25Z) for a May28–July1 query, while
6,576 M5 bars were returned for that range. This is a genuine missing
data constraint, not a negative or zero-trade June result.

### NAS100 uncertainty and paired negative control
Across its 61 closed paths, the daily block bootstrap 95% CI of
the *absolute* expectancy is [-0.0571, +0.4759] R — crosses zero.
Thus positive estimated expectancy is not statistically established.

As a fairer question about **direction choice**, the same 61 entry
timestamps/tick streams were also replayed on the **opposite side**,
same nominal risk and reward price distances, same broker bid/ask
and one adverse tick per side. This **mirror-direction placebo** is
not a clock-random or independently fitted strategy:
- Original NAS direction mean +0.2240 R.
- Mirrored direction mean -0.3557 R.
- Paired direction lift +0.5797 R, day-block-bootstrap 95% CI
  +0.1016 to +0.9861 R.
- US30 original -0.2263 R, mirror -0.2233 R; no directional lift.
- XAU original +0.155 R against mirror -1.004 R, only one
  sample and therefore no statistical inference.

The positive NAS directional lift is worth further investigation,
but its CI is not multiple-testing-adjusted and the historical
windows may have previously influenced past project strategy search.
It does not establish independent profitable executable trades.

## Observer integration, not live EA activation

The 5-minute Windows task
Katarina-MarketBrain-Observer continues collecting/observing
the broker-approved symbol universe.

- It no longer uses trend_impulse_break_v1 as a universal shadow
  entry proposal for all 74 broker symbols; its original module
  remains only as an archived stand-alone research control.
- On registered symbols only, new research proposals are based on
  their specific historical bar and local session context. Intraday
  M1 session bars are only fetched for the seven registered symbols
  and removed before persistent observations to reduce DB bloat.
- The observer independently checks current broker side permission,
  broker stops and tick size, bounded spread relative to actual
  proposed target, closed-candle freshness and available data.
- Missing day session for US30/JPN225/FX means abstention.
- Unknown broker symbols are **not assigned any default playbook**.
- The live action remains NO_TRADE, live_execution_enabled=false,
  model_promotion_allowed=false and no order submission.
- Model promotion is NOT an automatic byproduct of favorable backtests.

## References and next checks

- Official MT5 tick history: https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py
- Official MT5 Python symbol metadata: https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py
- Bailey & López de Prado, selection bias and multiple testing:
  https://doi.org/10.2139/ssrn.2460551
- Iwatsubo et al., intraday seasonality in gold futures:
  https://www.sciencedirect.com/science/article/pii/S2405851318300102

Next: independent NAS real-time shadow evidence (or unused premium
historical tick dataset), time-of-day matched random/control,
measured real broker commissions and slippage and independent
contract-size/currency-conversion confirmation. Check NAS
profit after spread and fees under worst adverse slippage,
other session regimes and same-symbol risk concurrency before
any real or demo automated trading.
