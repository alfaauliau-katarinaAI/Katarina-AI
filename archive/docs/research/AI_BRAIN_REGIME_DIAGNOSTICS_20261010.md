# AI Brain: causal ADX regime research (2026-10-10)

## Scope
The broker-wide read-only observer now derives Wilder ADX(14), +DI(14),
and -DI(14) from **fully closed** M1 and M5 candles. It checks finite and
nonnegative tick volume, then uses the closed M5 snapshot to label a
research-only regime: TREND_UP, TREND_DOWN, RANGE, TRANSITION or UNKNOWN.

- TREND_UP / TREND_DOWN require ADX >= 25, M5 directional efficiency >= 0.30,
  aligned EMA20/EMA50 direction, and matching dominant directional index.
- RANGE requires ADX <= 18 and directional efficiency <= 0.25.
- All other valid measurements are TRANSITION; missing/invalid inputs UNKNOWN.
- Stale quotes, stale bars and disconnected brokers force UNKNOWN rather than
  presenting historical patterns as current market conditions.
- These thresholds are **hypotheses only**, not tuned performance parameters.

The previous `regime` output is retained for compatibility. The new
`regime_detail` is preserved with immutable entry context in the forward
quote ledger and appears in the read-only report. Older rows lacking this
field appear as UNKNOWN. This is not a reconstructed historical regime.

## Safety and limitations
Research watchlist ranking and the existing live risk veto are unchanged.
Every observed symbol still has action=NO_TRADE. Quotes are not fills;
forward markouts are neither realized PnL nor independent trades. ADX and
volatility indicators do not establish expected profit. No trade API,
model promotion, margin sizing, or live strategy change is introduced.

Before any strategy promotion: verify ADX numerical parity with MT5 iADX
on broker data, stratify forward observations by symbol/side/regime and
market session on prospective data, account for spread/commission/slippage,
then test pre-registered rules using purged walk-forward windows. Block
promotion when evidence is sparse or the result is not net profitable.
