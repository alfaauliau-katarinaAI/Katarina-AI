# KATARINA Adaptive Risk Governor — 2026-10-11

## Decision and activation

A new decreasing risk curve is **implemented and tested on the VPS research branch**. It is an **opt-in component**: create the account risk coordinator with `AccountRiskCoordinator.with_adaptive_risk(state_engine,capital=capital_engine)`. It is not an authorization to go live or an activation of any MT5 trader. The baseline `RiskGovernor()` behavior and pre-existing live human-approval requirements remain unchanged. The new config contains an adaptive profile but does **not** auto-activate it on legacy callers. KATARINA's Stage 36/38 gates must still be satisfied separately.

The attached `config/risk_governor_v2.json` keeps the original hard limits, now with `adaptive_risk.enabled=true` for **explicitly instantiated** adaptive governors. The opt-in constructor reads those settings; a missing or unverified currency, balance or floating equity **pauses approval**.

## Smooth decreasing risk schedule

| Usable capital USD-equivalent | Default risk | Nominal risk cash |
|---:|---:|---:|
| $100 | 2.00% | $2 |
| $250 | 1.75% | $4.375 |
| $500 | 1.50% | $7.50 |
| $1,000 | 1.25% | $12.50 |
| $2,500 | 1.00% | $25 |
| $10,000 | 0.75% | $75 |
| $50,000 | 0.50% | $250 |
| $100,000 | 0.40% | $400 |
| $250,000 | 0.30% | $750 |

Values between knots are log-interpolated, continuous and monotonically nonincreasing, bottoming at 0.30% for balances above $250,000. For amounts below $100, cap percentage at 2% — this is **not** permission to over-size minimum lot positions.

The current budget is based on `MIN(active_trading_balance, current_equity)` and excludes compounding reserves. The risk-percentage reference is `MAX(usable capital, persistent peak account equity)`, so it cannot increase after drawdown, nor after the reserve allocation at a 100%-profit milestone. The peak equity already belongs to the existing restorable risk state. This is a conservative cap, not a guaranteed broker exposure accounting model.

## Currency normalization

- `USD`: 1 native USD = 1 USD.
- `USC`: 100 cent units = 1 USD, **only if the broker's account reports and confirms USC as USD cents**.
- Do not infer by a symbol suffix or by a displayed number. Any unknown currency currently returns PAUSE until a verified conversion is supplied.

**$100 standard gold example:** 0.01 lot with standard 100 oz/lot and a $10 stop implies ~$10 loss, far above $2 limit. The existing PositionSizingEngine returns `below_min_volume`; no trading.

**$100 cent example:** if and only if a cent broker really uses a gold contract size 1 oz/lot, then 10,000 USC is equivalent to $100, and a nominal 0.2 cent lots × 1 oz/lot × $10 stop has ~$2 gross stop risk. Real spread, slippage, commissions and broker specifications must be incorporated before execution; therefore **0.2 is an illustration, not a trading recommendation nor a verified actual lot**.

## Same hard safety ceilings

- Hard single-order risk <= 5%.
- Shared-account total committed risk (manual positions + pending + reserved + bot) <= 8%.
- Daily drawdown at 10%: PAUSE new risk.
- Total drawdown at 20%: REJECT new risk.
- Extra adaptive soft thresholds: when daily DD >=5% OR total DD >=10%, halve the otherwise approved *adaptive target*. This only reduces risk.
- Failed health/reconciliation, unknown risk exposures, unknown currency, stale/invalid capital: PAUSE; nonpositive expected RR or uncertainty >=0.75: REJECT.
- Actual broker worst-case loss including entry-to-SL and cost buffers must fit risk cash. Never round minimum volume **up** to force a position.
- One globally shared risk profile for tests/demo/real; no relaxed live exception. New code is **research-only until the existing live evidence gate approves deployment**.

## Architecture

`src/katarina/engines/adaptive_risk.py`: immutable quote, monotonic interpolation, finite-value validation, USC/USD conversion and soft drawdown reduction.

`src/katarina/engines/risk.py`: `RiskGovernor.from_config(path)` reads adaptive policy and enforces it inside `evaluate`, `evaluate_state` or `evaluate_account` when instantiated. Default legacy governor still works (preserves older callers/tests).

`src/katarina/engines/account_risk_state.py`: `AccountRiskCoordinator.with_adaptive_risk(...)`, and new optional `account_currency` at authorization. Risk base uses the existing reserve-aware capital engine and persistent peak equity. Missing currency fails closed in adaptive mode.

`tests/unit/engines/test_adaptive_risk_governor.py`: 13 tests plus full project regression suite.

`scripts/research/audit_adaptive_risk_tiers_2026.py`: USD/USC risk budget audit and illustrative lot math. Output `C:\KatarinaDev\artifacts\historical-brain\adaptive_risk_profile_audit_20261011.json`.

## Remaining work before real-money use

1. Confirm broker native contract, tick value, currency, conversion, minimum volume, commissions, freeze levels, actual spread and margin; calculate max money-at-SL using broker native semantics including plausible adverse slippage.
2. Re-run old 2025–2026 historical simulations on the **adaptive risk path**, counting rejected micro positions and portfolio risks in full, before comparing profit, drawdown and margin survival; results under fixed 1% risk do not carry over.
3. Test compounding reserve and withdrawal/rebase across restarts, manual/foreign positions, mixed cent/standard account environments, risk reservations and extreme drawdown scenarios.
4. Do not alter user-defined Stage36/38 authorization requirements; live stays disarmed.

The goal is **drawdown survival**, not a fixed return every day/week.
