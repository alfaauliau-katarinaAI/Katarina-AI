# Brain research: diagnose losses, compare entries, then select by expected R

This work extends the offline research brain. It is not live trading approval.
Parent branch: research/indicator-combinations-20261010, dc51f00.
All work and real-tick tests run on the user's Windows VPS.

## Baseline diagnosis

The original August/September XAUUSD.vx M1 baseline has 264 trades:
195 stop losses and 69 take profits, net -165.32 USD, cash profit factor 0.81,
maximum reported equity drawdown 214.10 USD (2.14% of 10,000 USD).
BUY: 126 trades, -69.10 USD, win rate 27.78%.
SELL: 138 trades, -96.22 USD, win rate 24.64%.

Mean cash win is 10.0733 USD and mean cash loss 4.4122 USD. Their realized
break-even win rate is 30.46%, versus actual 26.14%. This is descriptive,
not a calibrated forecast. Reported commissions and swaps are zero; spread is
already reflected in fills. Mean spread / initial risk is about 7.44%.

The revised instrumented EA exactly reproduces those 264 trades and net P&L.
It measures MAE/MFE from bid/ask exit-side tick prices and includes the exit fill.
46 of 195 losing trades reached +1R before closing. That motivates testing exits
but does not prove lower targets or wider stops will be profitable. The log
stops at actual position closure and cannot measure recovery after a stop.

The new journal records actual fill time rather than the prior signal-bar open,
which corrects holding durations by roughly one M1 bar. It also records closing
deal reason and sums entry/exit profit, commission, swap and fee for the position.
The EA has no partial-close strategy; partial-close extensions require separate
position-state/journal handling.

## Hypotheses fixed before the experiment

18 separate MT5 development executions:
3 entry families x 2 directions x 3 exit profiles.

- Trend pullback: existing EMA/RSI pullback, minimum ADX 20.
- Support/resistance rejection: previous confirmed swing and directional close
  in the outer 40% of the signal bar, with explicit ATR touch/penetration bounds.
  The pivot must have been confirmed before the signal bar. Minimum ADX is 0.
  This is a swing-level rejection, not an unproven fresh supply/demand detector.
- Breakout/retest: bar 2 closes beyond the range of bars 3..22 by 0.1 ATR;
  bar 1 retests with bounded penetration and closes back on the breakout side.
  Minimum ADX is 20. This is one exact causal pattern definition.

Exit profiles change one quantity relative to baseline:
- baseline: SL 1.3 ATR, target 2.2R;
- wider_stop: SL 2.0 ATR, target 2.2R;
- nearer_target: SL 1.3 ATR, target 1.5R.

Lot 0.01, starting balance 10,000 USD, leverage 1:100, maximum spread 0.12 ATR.
Same-lot wider stops risk more cash; comparison uses net R as well as cash P&L.
These are 18 configurations, not an exhaustive search.

Each run uses the existing dedicated ALFA research terminal, a separate Expert
path and unique runner/config/report identifiers. No pre-existing terminal
process is terminated. The EA refuses execution outside Strategy Tester.
The runner disables live trading and closes only its own terminal process.

## New brain path

KatarinaAIBrain.train_strategy_selector delegates to StrategySelectionBrain.
It compares estimated net R after an additional 0.1R/trade stress within each
BUY/SELL and M15 UP/DOWN/MIXED state. These are empirical estimates, not calibrated
probabilities or guaranteed future returns. A fixed 55% win-probability cutoff
is not used on this research path: reward/loss magnitude matters.

Chronology:
- June 2026: development fit;
- July 2026: candidate selection, no refit;
- August/September 2026: later diagnostic audit of frozen choices only;
- October 1-9: reserved, not read for development selection.

Labels crossing either development boundary are purged. Candidate admission
requires 30 training and 20 selection trades, five days in each window, positive
stressed R in both windows, and selection R-profit-factor at least 1.1.
Ranking maximizes the weaker window's stressed mean R with deterministic ties.
No eligible candidate for a side/regime means NO_TRADE.
Unknown regime and insufficient history also yield NO_TRADE.
All outputs remain research-only and cannot authorize live risk.

An estimated daily-mean minus 2 standard errors is reported descriptively.
Days are not proven independent; no statistical significance is claimed.
18 candidates across six state cells creates multiple-testing risk.
Aug/Sep market history was previously inspected in other experiments, so this
later audit is not a pristine prospective test. Rejected final candidates must
not be replaced by selecting against the same final outcomes.

Per-state filtering of a family journal cannot reproduce a combined router's
position availability. The selected routing policy received its own full execution run below.
Untouched-period or forward-demo validation remains necessary for any future
surviving candidate.

## Opportunity evidence

Each run logs valid closed-bar signal flags for all three families in both
directions, observation time, M15-independent EMA direction, ADX, method admission,
spread admission and position occupancy. Signals are logged even while an existing
position prevents entry. Failed data loads are counted in EA diagnostics; they are
not silently synthesized into valid observations. Current presets use all sessions.

The baseline records 58,980 valid bar observations; development covers 61,407 per
run. Repeated runs observe the same market bars and must not be treated as new
independent data. This first opportunity schema stores signal/gate states, not a
complete OHLC/tick snapshot or counterfactual outcome. Unexecuted opportunities
have UNKNOWN outcomes, never fabricated wins or losses. Tick data remains on VPS.

## Verification

- 36 Python research tests including ten new selector tests.
- Six existing AI/scalper integration tests pass.
- All 18 MQL targets compile with zero errors/warnings in successful build
  b844f11282c843968765eb5c2c2849cb (development) and
  a7dbd3f4121641e0b331c628a13ca413 (7.134 context-gated execution).
- Real-tick baseline reproduction is identical in count and net result.
- Per-run report/journal totals, real-tick quality, hashes and distinct run tags
  are checked before observations can enter the selector.
- Research serialization now avoids FileWrite's argument-count limit.
- Feature data uses closed bars; right-side swing confirmation precedes signals.


## Completed experiment and final decision

21 actual MT5 executions completed: one baseline reproduction, 18 development
configurations, one whole-family later audit, and one frozen context-gated audit.
All reports used 100% real ticks and reconciled with their trade journals.

The June/July selector admitted only SELL support/resistance rejection with a
2.0 ATR stop and 2.2R target in M15 DOWN conditions. Stressed expected R was
+0.14424 (77 June trades) and +0.13148 (34 July trades).
All other side/state cells returned NO_TRADE.

August/September whole-family execution produced 263 trades and +40.03 USD,
cash PF 1.03. That is not the selected routing policy. Post-filtering its DOWN
rows produced 81 trades and -22.39679 stressed R.

The definitive context gate was then applied BEFORE entry in MQL 7.134:
91 trades, 24 TP and 67 SL, net -141.11 USD, cash PF 0.73,
maximum equity drawdown 192.56 USD (1.92%).
Additional 0.1R/trade stress gives -23.95704 R, expected -0.26326 R/trade,
R-profit-factor 0.6813. The difference from 81 filtered trades demonstrates
why filtering a journal does not reproduce position availability.

Final decision: **NO_TRADE**. No candidate is promoted or replaced using final
outcomes. October data remains unused. The selector's development recommendation
is a research hypothesis; the final execution audit vetoes promotion.
No live strategy or classifier threshold was changed.

### Development matrix (June and July combined)

Cash P&L below is descriptive; selection used separate months and stressed R.
Wider stops at the same lot size carry greater cash risk.

| Candidate | Trades | Net USD | Cash PF |
|---|---:|---:|---:|
| pullback_BUY_baseline | 486 | -436.88 | 0.74 |
| pullback_BUY_wider_stop | 353 | -360.30 | 0.80 |
| pullback_BUY_nearer_target | 539 | -540.34 | 0.68 |
| pullback_SELL_baseline | 555 | 166.53 | 1.10 |
| pullback_SELL_wider_stop | 370 | 301.22 | 1.18 |
| pullback_SELL_nearer_target | 634 | 110.28 | 1.07 |
| sr_rejection_BUY_baseline | 393 | -37.40 | 0.97 |
| sr_rejection_BUY_wider_stop | 308 | -129.65 | 0.92 |
| sr_rejection_BUY_nearer_target | 411 | -38.97 | 0.97 |
| sr_rejection_SELL_baseline | 378 | -58.70 | 0.95 |
| sr_rejection_SELL_wider_stop | 280 | 223.62 | 1.17 |
| sr_rejection_SELL_nearer_target | 396 | -55.17 | 0.95 |
| breakout_retest_BUY_baseline | 109 | -151.60 | 0.64 |
| breakout_retest_BUY_wider_stop | 99 | -144.60 | 0.74 |
| breakout_retest_BUY_nearer_target | 110 | -108.87 | 0.71 |
| breakout_retest_SELL_baseline | 114 | -14.37 | 0.96 |
| breakout_retest_SELL_wider_stop | 110 | 24.99 | 1.04 |
| breakout_retest_SELL_nearer_target | 122 | -99.73 | 0.75 |

The rejected configurations remain reproducible research records; none is added
to the active trading path. Removing their evidence would conceal unsuccessful
trials and make selection bias harder to assess.

## Primary references reviewed

- https://www.metatrader5.com/en/terminal/help/algotrading/testing_report
  MAE/MFE interpretation and report diagnostics.
- https://www.metatrader5.com/en/terminal/help/algotrading/testing
  Full strategy execution testing versus optimization.
- https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
  Ordered time-series validation and temporal gaps; our trade-label purging also
  checks when the outcome becomes known, not just observation order.
- https://scikit-learn.org/stable/modules/calibration.html
  Probability calibration is distinct from classification and expected payoff.
- https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
  Fitting and calibration samples must be disjoint; no calibration quality is claimed here.
- https://escholarship.org/uc/item/4w1110bb
  Bailey et al., The Probability of Backtest Overfitting: holdout alone does not
  eliminate selection bias from repeated investment strategy searches.

No external trading code was copied or new ML dependency installed.
