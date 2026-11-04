# KATARINA — Explainable Market Decision V1

Status: implemented as a **read-only / research** layer. No MT5 order API, no automatic risk-governor parameter changes, no live authorization.

## Six questions answered per pair

The result is stored in DecisionObservation.decision_detail and serialized by scripts/ai/run_readonly_decisions.py.

1. Activity: TRENDING / PULLBACK / BREAKOUT / SIDEWAYS / REVERSAL_UNDER_CONFIRMATION / VOLATILITY_SHOCK / NO_CONCLUSION / UNKNOWN.
2. Direction: BULLISH, BEARISH, SIDEWAYS, UNCERTAIN, from closed M5/M15/H1 evidence.
3. Primary and alternative scenarios: conditional hypothesis, timestamp, reference price, previous-M15 support/resistance, target, invalidation, confirmation conditions. Values are **illustrative levels**, never executable stop/target orders. A geometric distance ratio is **not** predicted profit.
4. Ranked strategies and selected playbook: evidence-weighted research routing between trend pullback, range fade, breakout retest, reversal reclaim and momentum continuation. Prior weights from regime + MTF alignment + recent closed-candle body + support/resistance location. These are **not** win probabilities. The authoritative price-action router must still confirm the selected playbook before a research signal is generated.
5. Blockers and next_check: actionable WAIT reasons: unresolved structure, session closed, stale quote, unverified news context, high-impact news blackout, spread, insufficient target room or absent price confirmation. Uncertainty is not misreported as reversal; NO_CONCLUSION stays WAIT.
6. Signal and decision: RESEARCH_SETUP denotes a **hypothetical** BUY/SELL opportunity only. It does not establish positive expectancy, validated strategy or broker execution permission. live_execution_authorized stays false.

Each result contains explanations as auditable reason codes and explanations_id in Bahasa Indonesia. Market observation remains useful even when hard gates block entry.

## Soft and hard rules

Soft: multi-timeframe alignment, price location, candle pattern, regime, alternative playbook ranking. It is **not** required for EMA, RSI, ADX, Bollinger and pin bar to simultaneously agree.

Non-negotiable: invalid/future OHLC, market closure, stale quotes, news blackout, missing verified news, excessive spread, unconfirmed price structure, unsupported regime. This module never overrides the independent Risk Governor, broker preflight, correlated exposure or live authorization.

The legacy DecisionObservation.action remains a **research directional suggestion** for backward compatibility. A production consumer should instead inspect decision_detail.decision, live_execution_authorized and the authoritative execution gates. The new advisor has no connection to a broker order endpoint.

## Testing

Unit tests: PYTHONPATH=src python -m unittest tests.unit.intelligence.test_explainable_market_decision -v

Full tests: PYTHONPATH=src python -m unittest discover -s tests/unit -p test_*.py -q

The standalone VPS launcher `scripts/ai/run_readonly_decisions.py` (output under the retired `C:\KatarinaDev` layout) was removed in cleanup B1, 3 Nov 2026. The explainable decision model is exercised only through the canonical observer (`scripts/ai/run_contextual_market_observer.py`) and the unit tests above; no second MT5 acquisition path exists.

Weekend / unverified-news snapshots correctly yield WAIT, but still include the last closed price context, date, stale-data blocker and candidate scenarios.

## Remaining validation work (not claimed completed)

- Replay complete causal *decisions*, not just signals, with never-seen broker tick data and transaction-cost/margin stress.
- Freeze per-symbol playbook parameters **before** genuinely independent walk-forward periods. If no tested edge passes, remain WAIT.
- Require broker volume/stop constraints and Risk Governor approval to execute any real order.
- Separately integrate the reporting JSON into the website once data freshness, publication policy and credentials are reviewed.

**No live promotion:** Earlier mass research found no strategy meeting robust stressed criteria. Explanatory software success does not establish positive trading expectancy.