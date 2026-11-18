# Katarina P9 V2 Robust FIVE integration — 18 Nov 2026

Research-only integration to Katarina source tree. No promotion to an active trading module or live deployment.

Locked P9 V2 five engines are retained; V3 Growth/Defensive causal routing is a new research branch, not a patch to the frozen V2.
Candidate manifest in research/p9_v2_robust, pure fail-closed module in src/katarina/research/p9_v2_robust.py,
unit tests in tests/unit/test_p9_v2_robust_research.py, compiled signal observer in mt5/Experts/P9V2RobustFiveResearchShadow.mq5.

BALANCED_ROBUST: base [XAU.75%,NAS3%,EUR.5%,CHF.5%]; adaptive ADR ratio to expanding previous median: low<.9 x.75, middle x1, high>=1.3 x1.25. Normal +$1293.84/month DD5.525%; severe -0.6R +$99.88 DD6.951. Severe -0.7R -$10.49 DD8.358 with 123 vetoes.
MAX_GROWTH: [1,3,1,1]% and ADR20/ADR100 low<.8 x.5, high>=1.2 x1.25; normal +$1664.93/month, stress -0.6R +$39.59.
MAX_STRESS: [.25,3,.5,.25]% and NAS-only ADR normal ratio to expanding median, low<.9 x.5 high>=1.3 x1.5; normal +$818.92, stress -0.6R +$142.65 DD7.906.

All research weights above .25 are UNAUTHORIZED LIVE. EvidenceRiskGate WAIT. All five-method results based on historical H1/H4 stop-first bars, not native MT5 real ticks or forward evidence. No execution/orders permitted.
