# KATARINA Evidence-Weighted Adaptive Risk — 13 October 2026

**Deployment status: research only / WAIT / NO LIVE.** This design does not
enable orders or authorize a live account. Its purpose is to prevent a high
indicator score or a backtested profitable subset from increasing risk.

## Evidence tiers (fraction of *account* capital, not lot units)

| Tier | Verified historical | Verified independent forward fills | Additional requirements | Research cap per idea |
| --- | ---: | ---: | --- | ---: |
| WAIT | Any | Inadequate | Any critical verification absent, uncertainty crosses zero, or negative net edge | 0% |
| CONSERVATIVE | >=150 | >=40 | PF >=1.20; stressed mean >0; confidence lower bound >0; 3 chronological positive segments | <=0.25% |
| MODERATE | >=150 | >=120 | PF >=1.30; stressed mean >=0.07R; >=2 independent regimes | <=0.50% |
| AGGRESSIVE | >=150 | >=250 | PF >=1.50; stressed mean >=0.12R; >=4 positive segments and >=3 independent regimes | <=1.00% |

These are **research policy thresholds, not proven optimized trading targets**.
Counts must be for the identical frozen strategy+symbol+side+regime, not
cross-market combinations. Proof of precommitted rules, untouched forward
holdout, causal inputs, broker fees/spread/slippage, forward order fills,
and independent audit is mandatory. Missing/NaN metrics fail closed.

## Shared-account circuit breakers

- Daily drawdown >=2%: WAIT; total peak-to-current drawdown >=10%: WAIT.
- Total peak drawdown >=5%: halve the research cap.
- Open+reserved portfolio risk must remain below 2%; same-direction
  correlated risk below 1.5%. Missing account telemetry or unhealthy market,
  broker execution health, or reconciliation: WAIT.
- Existing capital-based RiskGovernor is **not** promoted by this research.
  A later separate, audited integration must apply both gates to live orders.
- **All decision objects have live_authorized_fraction=0 and
  live_execution_authorized=false even if synthetic inputs produce AGGRESSIVE.**

## Existing VPS research snapshot — what can be verified

Frozen August 10–21 research across 17 mapped symbols:
161 candidate signals, 157 valid completed historical BID/ASK path simulations;
mean -0.315584R (including an assumed +0.15R cost), PF 0.593206.
No independently verified forward fills, real commission reconciliation,
nor verified historical clock/DST. Result: **WAIT (risk 0%)**.

The one canonical read-only MT5 observer now reports
`adaptive_evidence_risk` in its latest.json; it reads the existing private
August report without changing/overwriting that report. A missing/corrupt
report fails closed. The observer has no order gateway and MT5 trade
permission remains disabled.

## Regression verification on Windows VPS

- 11 evidence risk tests for fail-closed, tiers, absent/invalid evidence,
  positive lower bounds, cost stress, drawdowns, portfolio/correlation limits.
- 13 preexisting adaptive risk governor tests and 15 Brain V3 tests remain
  passing. Tests include synthetic positive scenarios and do NOT claim
  real-life return or broker execution quality.
- Need newly collected independent prospective proof **before** allowing
  any paper-to-real risk promotion.

## Evidence-qualified broker sizing integration

`EvidenceQualifiedResearchSizing` combines independent forward evidence,
existing capital governance, broker spread/slippage/fees, and margin/minimum
lot limits. It chooses the lower of the two risk limits. Account drawdown
and committed exposure must match the evidence snapshot.

The research wrapper remains read-only: every qualification has
`live_execution_authorized=false`. Existing legacy research sizing is not
automatically promoted to real trading. Forward broker fills and verified
trading costs are still unavailable for the August 17-market research.

VPS synthetic regression: six cross-gate tests and nine legacy sizing tests
passed. GitHub CI must pass after integration before this code is considered
deployed.
