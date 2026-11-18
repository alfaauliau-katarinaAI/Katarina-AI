# Katarina AI — P9 V2 Balanced + V3 Robust hybrid backtest
Date: 2026-11-19 | Status: HISTORICAL RESEARCH COMPLETE; NOT LIVE-APPROVED.

## Scope
320 method/risk combinations plus 864 causal ADR gating combinations screened on the same 27 full months Aug2024–Oct2026.
2024-25 used for historical selection; 2026 is ALREADY MINED, not a genuinely untouched out-of-sample set.
Synthetic starting balance USD 10,000; H1/H4 broker OHLC conservative SL-first replay with current broker-margin snapshot.

## Best balance: V2 Balanced risk, V2+V3 condition mix
XAU H1 BUY V3; XAU H4 BUY V2; NAS100 H4 SELL V3; EURJPY H4 BUY and USDCHF H4 BUY core shared.
USDCHF H4 SELL V3 only when 0.80 <= previous-completed-day ADR20/ADR100 <1.20; 12 candidate signals.
EURJPY H1 SELL OFF; XAU H1 SELL OFF; NAS BUY OFF. Max2 open independent symbol families; one per family.
Research base-risk %: XAU0.75, NAS3.00, EUR0.50, CHF0.50, with separate ADR20/prior expanding-median scaling:
ADR risk <0.9 multiplier0.75; 0.9..below1.3 multiplier1; >=1.3 multiplier1.25.
Risk halves at closed DD>=4%, blocks new trades at >=8%; no floating equity protection verified.

## Matched cost stress comparison, US dollars monthly
| Extra adverse R | V2 Balanced | V3 Robust | Hybrid | Hybrid max closed DD | Hybrid veto count |
|---|---:|---:|---:|---:|---:|
| 0.0 | +1,293.84 | +1,373.05 | +1,349.21 | 5.667% | 0 |
| 0.4 | +361.90 | +408.71 | +374.15 | 7.458% | 0 |
| 0.5 | +158.81 | +234.73 | +178.62 | 7.739% | 0 |
| 0.6 | +99.88 | +131.49 | +121.78 | 6.984% | 0 |
| 0.7 | -10.49 | -2.85 | -4.12 | 8.547% | 99 |
| 1.0 | -36.10 | -31.64 | -30.94 | 8.355% | 217 |

V2 normal 27mo net USD +34,933.57
Hybrid normal 27mo net USD +36,428.78; closing balance USD 46,428.78
Hybrid gain vs V2 normal USD +1,495.21 on 27 full months.
Under extra -0.7R the hybrid DD exceeds 8% and blocks new entries. No safety guarantee.

## Annual historical PnL comparison (USD)
| Period | V2 Balanced | V3 Robust | Hybrid |
|---|---:|---:|---:|
| 2024 | +3,232.97 | +2,823.27 | +3,254.33 |
| 2025 | +13,977.86 | +15,131.43 | +14,976.07 |
| 2026 | +17,722.74 | +19,117.73 | +18,198.38 |
2024 is Aug-Dec; 2026 Jan-Oct.

## Monthly modeled profit
| Month | V2 Balanced USD | V3 Robust USD | Hybrid USD |
|---|---:|---:|---:|
| 2024-08 | +694.41 | +743.34 | +694.41 |
| 2024-09 | +591.69 | +303.30 | +640.28 |
| 2024-10 | -41.59 | -117.19 | -68.83 |
| 2024-11 | +622.96 | +613.87 | +622.96 |
| 2024-12 | +1,365.50 | +1,279.95 | +1,365.50 |
| 2025-01 | +1,731.82 | +1,972.32 | +1,731.82 |
| 2025-02 | +1,135.90 | +1,176.92 | +1,135.90 |
| 2025-03 | +382.99 | +548.03 | +643.46 |
| 2025-04 | +1,717.81 | +1,785.11 | +1,841.85 |
| 2025-05 | +1,603.12 | +1,631.91 | +1,633.55 |
| 2025-06 | -298.73 | +200.51 | +216.44 |
| 2025-07 | +599.71 | +778.14 | +591.92 |
| 2025-08 | +1,374.74 | +1,005.20 | +1,421.78 |
| 2025-09 | +577.89 | +428.36 | +300.61 |
| 2025-10 | +1,014.72 | +784.90 | +1,069.14 |
| 2025-11 | +1,781.57 | +2,315.17 | +1,823.82 |
| 2025-12 | +2,356.32 | +2,504.85 | +2,565.77 |
| 2026-01 | +3,202.10 | +2,861.00 | +3,297.59 |
| 2026-02 | +1,749.08 | +1,758.55 | +1,803.94 |
| 2026-03 | +2,530.97 | +3,233.10 | +2,617.02 |
| 2026-04 | -1,260.42 | -1,274.48 | -1,321.60 |
| 2026-05 | -374.93 | -596.65 | -434.17 |
| 2026-06 | +1,148.59 | +1,559.22 | +1,214.64 |
| 2026-07 | +841.96 | +643.33 | +908.41 |
| 2026-08 | +4,711.96 | +4,745.96 | +4,801.75 |
| 2026-09 | +1,385.70 | +1,989.62 | +1,453.51 |
| 2026-10 | +3,787.72 | +4,198.08 | +3,857.29 |

## Per-symbol concentration
| Symbol | Completed fills | 27mo PnL USD |
|---|---:|---:|
| XAUUSD.vx | 107 | +10,372.73 |
| NAS100.vx | 26 | +21,980.03 |
| EURJPY.vx | 45 | +2,450.69 |
| USDCHF.vx | 37 | +1,625.33 |

## Native <=0.25% risk research checks
Strict native-cap profile (XAU .05%, NAS .25%, EUR .05%, CHF .05% STATIC) => normal USD +21.79/month; extra -0.6R USD +6.44/month; max closed DD stress 0.62%.
Normal high-profit profile above uses NAS3..3.75% per entry in research, which is 12x..15x the native .25% cap. NEVER approved live.
Data mines 2024-26 and selected across 1184 variants; this may substantially overfit.
Not a native MT5 Every tick based on real ticks test. No prospective forward, floating-equity DD, historical margin or real execution validation.

## Artifacts and deployment
HYBRID_P9_V2_V31_STAGE1_FULL_GRID.json
HYBRID_P9_V2_V31_ADR_REGIME_GRID.json
FINAL_HYBRID_MATCHED_SCENARIOS_AND_CAP025.json
HYBRID_OPTIMAL_MONTHLY_V2_V3_COMPARISON.csv
hybrid_p9_v2_v31_robust_grid.py
test_causal_adr_gated_hybrid.py
verify_optimal_hybrid_against_baselines.py
No changes to repo, MT5 order/risk configuration, locked P9 V2/P7, or GitHub. EvidenceRiskGate WAIT.
