# Katarina AI — P9 V2 Robust FIVE, 18 November 2026
STATUS: completed research and isolated Katarina codebase integration. No live deployment.
Five original P9 V2 methods, routed Growth/Defensive via previous closed H4 ATR threshold; no new SELL/BUY opposites.
Historical H1/H4 OHLC first-touch broker Valetax, Aug2024–Oct2026 27 complete months; initial USD10000.
Not genuine untouched OOS, not MT5 native real ticks, does not verify floating equity DD.

## Research optimization
15 ADR rules x378 allocation vectors =5670 tests; 884 provisional and 847 passed normal/-0.4/-0.5/-0.6R guards.
|Model|Base risk XAU/NAS/EUR/CHF|Normal USD per month|Closed DD normal|Extra -0.4R per month|Extra -0.5R|Extra -0.6R|DD -0.6R|Extra -0.7R|DD veto -0.7R|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BALANCED_ROBUST | 0.75,3.0,0.5,0.5 | 1293.84 | 5.525% | 361.9 | 158.81 | 99.88 | 6.951% | -10.49 | 123 |
| MAX_GROWTH | 1.0,3.0,1.0,1.0 | 1664.93 | 5.805% | 324.5 | 160.54 | 39.59 | 7.83% | -26.9 | 160 |
| MAX_STRESS | 0.25,3.0,0.5,0.25 | 818.92 | 4.917% | 277.05 | 201.03 | 142.65 | 7.906% | 25.29 | 87 |

## Selected default: BALANCED_ROBUST (paper only)
Base risk XAU0.75%, NAS3%, EUR0.5%, CHF0.5%; ADR20 divided by prior expanding median of ADR20.
ADR ratio below .9 uses x.75 risk; from .9 to below1.3 uses x1; >=1.3 uses x1.25.
Risk is halved at closed DD4%, and new entries blocked after closed DD8% (not floating limit).
Simulated profit across 27 complete months USD34933.57 producing closed balance USD44933.57.
Per-year paper gains: {'2024': 3232.97, '2025': 13977.86, '2026': 17722.74}.
The candidate still FAILS at additional -0.7R cost: DD8.358%, 123 new entry vetoes.
NAS high ADR risk3.75% per entry far above active .25% live cap. Live RiskGate WAIT.

## Repo integration paths on VPS
C:/Katarina/code/research/p9_v2_robust/P9_V2_ROBUST_RESEARCH_CANDIDATES.json
C:/Katarina/code/src/katarina/research/p9_v2_robust.py
C:/Katarina/code/tests/unit/test_p9_v2_robust_research.py
C:/Katarina/code/mt5/Experts/P9V2RobustFiveResearchShadow.mq5 and .ex5
C:/Katarina/code/docs/research/P9_V2_ROBUST_FIVE_INTEGRATION_20261118.md
MT5 MetaEditor compile: 0 errors, 0 warnings. Six unit tests: PASS.
Locked P9 V2 SHA5/P7 SHA5 validated and promotion_lock 25 active hashes unchanged.
GitHub source is version-controlled independently of live deployment. No MT5 chart attach. No order functions in OnTick.
Backtest evidence in P9_V2_ROBUST_FIVE_ADR_RISK_SCAN.json; monthly comparison in P9_V2_ROBUST_FIVE_MONTHLY_COMPARE.csv.
