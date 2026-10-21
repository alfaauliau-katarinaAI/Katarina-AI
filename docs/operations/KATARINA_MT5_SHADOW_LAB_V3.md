> Historical offline research, integrated 2026-10-15. Claims below describe the original experiment, not current VPS or live readiness. Production strategy and Risk Governor remain unchanged. The portfolio experiment uses `katarina.research.experimental_strategy_evidence_portfolio`; it is not registered in production.

# KATARINA Brain V3 — MT5 Shadow Trading Lab

**2026-10-11 | Research only, zero live order authorization.**

The goal is a reproducible LIVE-OBSERVED **paper** loop from a real MT5 terminal. Source code and Python tests live in GitHub; test against broker MetaTrader5 only on the separate VPS/MT5 lane. The new code does not import the trading/order execution API or call `order_send`.

## Implemented components

- `src/katarina/adapters/mt5_shadow_read_only.py`: read-only MetaTrader5 module injected into an adapter. Checks live tick freshness, valid Bid/Ask, account currency, symbol volume step/min/max, closed-only M5/H1/H4, broker-native `order_calc_profit` and `order_calc_margin`. Does not submit/modify/cancel orders.
- `src/katarina/intelligence/shadow/shadow_gold_intraday.py`: two explicitly versioned *research* hypotheses (Gold H1/H4 + ADX opening range and rolling six-hour quote-volume mean reclaim). Causally uses only completed candles, UTC 06–07 opening range and 07–09 entry research period. **Not asserted identical to the older 2025–2026 optimized backtest implementation** and not automatically approved as profitable.
- `src/katarina/intelligence/shadow/shadow_paper_book.py`: immutable, O_EXCL/fsynced paper opens on disk. Uses current ASK to open BUY and current BID to close it (opposite for SELL), always requires SL/TP and a deadline, closes at actually observed quote (worse if stop gaps), checks exposure group, and reconstructs outstanding paper positions after restart without counting a close twice.
- `src/katarina/intelligence/shadow/shadow_journal.py`: append-only ACCEPT/REJECT/NO_TRADE and aggregated cost ledger. Can reject duplicate trade IDs, unverified costs and corruption.
- `src/katarina/intelligence/shadow/shadow_manifest.py`: prevents accidental combination of different broker accounts, paper bankrolls, frozen strategy versions or Risk Governor configs in the same shadow ledger.
- `src/katarina/intelligence/broker/mt5_shadow_cycle.py`: read-only cycle: check active paper position exits → calculate hypothetical account equity/closed drawdown → two closed-bar Gold hypotheses → Adaptive Risk Governor → broker-native minimum-lot/margin sizing → write paper position/journal. Exits/entries are NEVER sent to MetaTrader5.
- `scripts/ai/mt5_shadow_lab.py`: one-shot/controlled polling operator CLI, exclusive lock, JSON stdout.

## Example on Windows VPS, **test only**

Run only after completing normal broker account authorization for **read-only data**. Choose one designated study directory per terminal/account/config and do not reuse it for different settings.

```powershell
$PY = 'C:\KatarinaDev\brain-runtime\Scripts\python.exe'
$ROOT = 'C:\KatarinaDev\repo-shadow-review'
& $PY "$ROOT\scripts\ai\mt5_shadow_lab.py" `
  --terminal "C:\Program Files\MetaTrader 5 ALFA\terminal64.exe" `
  --state-root "C:\KatarinaShadowData\research-v1" `
  --symbol "XAUUSD.vx" `
  --risk-config "$ROOT\config\risk_governor_v2.json" `
  --version "GOLD_SHADOW_V1_20261011" `
  --frozen-at "2026-10-11T00:00:00+00:00" `
  --initial-paper-balance-native 1000 `
  --cycles 1
```

The default blocks new entries because the project still lacks a **verified news-clearance feed**. This is intentional safety. To research signal generation on raw broker data before a news adapter exists, an operator may use `--ignore-news-for-paper`; the output is paper research only and **cannot be treated as verified forward alpha**. The journal marks PAPER costs unverified even if `--commission-per-lot` is supplied manually. Broker fills, swap, rollovers, fee schedule and realtime news policy are NOT independently attested. No trade may be promoted on those incomplete outcomes.

A sample of `--cycles 1` on a **closed/weekend market** may fail closed for stale tick or insufficient closed candles, which is correct; it is not a broken live execution engine.

The state root contains `manifest.json`, `journal/*.json`, `paper/*.json`, and a temporary writer lock. If an interrupted run leaves a stale lock, inspect the process and journal integrity before manual lock removal. Do not clear/reinitialize state to hide a conflicting study or an incomplete signal.

## Known constraints and gates before operational completion

- No genuine new out-of-sample period exists yet. The inspected 2025–2026 backtests are not forward results. The new Gold rule is a separate, frozen candidate and must be evaluated from first observation on.
- MT5 price quotes must be fresh; no paper order is created on stale/missing/crossed ticks. A weekend/read-only smoke test validates connectivity but not live-data fill behavior.
- Paper open-to-SL loss is computed in broker account currency, including price-side spread. Money units for cent accounts follow the broker terminal output; no inferred 100× conversion is allowed. Commission, swap, and slippage are still *assumed* until reconciled with broker specs/fills.
- Risk Governors cap per-position and open risk. The paper-only controller uses **a separate virtual account** and must not be confused with actual live equity or existing manual account positions. Stage36/38 live-gates are unchanged.
- Positive simulated profits are NOT evidence of profitable real execution. ForwardStrategyEvidenceGate remains fail-closed on paper records with unverified fees.
- Exclusive group currently applies to ALL shadow paper positions in the study, so use a dedicated state root for the GOLD research. A truly independent multi-asset portfolio requires group-scoped risk ledger with dated aligned returns and cross-market book reconciliation.
- **No automated news/calendar source**. Default `NO_TRADE` for all setups without acknowledged research-only override.
- A running process has ONE writer; journal SHA256 protects accidental corruption, not a malicious actor. Follow-up Issue #31 must implement verified news and broker fee sources, real forward audit, synthetic stop gap stress, and default strict admission before a production integration.

## Verification

GitHub PR #30 CI includes Python compilation, unit tests, full baseline, operational hardening, Stage35 safety, and explicit regression tests for lot sizing, native account currency, Stop Loss/Take Profit, true bid/ask close side, gap overrun, locked correlated gold exposure, paper-journal crash recovery and disarmed live order path.

**Release policy:** keep the change in Draft PR while broker-dependent live tick read-only smoke validation and source attestation are outstanding. Never treat a green CI as proven trading profitability.

References: [MT5 copy_rates_from_pos](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py), [copy_ticks_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py), [order_calc_profit](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py).

## First real MT5 read-only smoke: October 11, 2026, 15:25 UTC

The independent test worktree on the authorized Windows VPS successfully called only MetaTrader5 initialization, account currency/symbol reads, quote/candle reads, `order_calc_profit`, `order_calc_margin`, and shutdown. Account login/credentials were not printed and no deal/order was sent.

| Verified broker observation | Result |
|---|---|
| Terminal connection | PASS |
| XAUUSD.vx quote/spec exists | PASS |
| Account currency | USD |
| Broker contract size | 100 oz per lot |
| Minimum volume / step | 0.01 / 0.01 |
| One 0.01-lot paper BUY, $10 adverse price stop | $10 theoretical stop loss before fees |
| `order_calc_profit` and `order_calc_margin` available | PASS |
| M5/H1/H4 rates accessible | 114 / 81 / 56 bars queried |
| Quote freshness | FAIL CLOSED, approx. 142,203 seconds old on Sunday |
| Actual new live paper signal | NONE, due stale quote |
| Broker orders submitted | ZERO |

This is a valid **read-only terminal-adapter / data-quality fail-closed smoke**, NOT an open-market streaming fill test or successful continuous shadow-running proof. Re-test while XAUUSD market is open with current bid/ask and independently verified commission/calendar feed before asserting operational readiness.
