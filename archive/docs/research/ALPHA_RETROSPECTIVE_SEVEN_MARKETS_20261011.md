# KATARINA — 7-market retrospective research gate (11 Oct 2026)

**Confidentiality boundary:** Aggregate conclusions only. All tick data, account identifiers, broker evidence, private proprietary setup parameters, and raw event records remain outside the public GitHub repository. SHA256 below identifies private research files without publishing their contents.

## Verified descriptive observations, NOT validated alpha

| Symbol | 2025 screen-passing configurations (400 tested/symbol) | Positive 2026 reused diagnostic among 2025 passes | Action |
| --- | ---: | ---: | --- |
| XAUUSD.vx | 18 | 6 | Research candidate only, independent forward proof required |
| NAS100.vx | 0 | 0 | NO TRADE for this tested family |
| US30.vx | 1 | 0 | NO TRADE; apparent development candidate did not persist |
| JPN225.vx | 0 | 0 | NO TRADE |
| EURUSD.vx | 0 | 0 | NO TRADE |
| GBPUSD.vx | 0 | 0 | NO TRADE |
| USDJPY.vx | 0 | 0 | NO TRADE |

Results are for an **exploratory strategy family on 2025 training with reused 2026 diagnostics**, NOT proof that an instrument can never produce alpha. There were 2,800 parameter cells across the seven-symbol research matrix, with numerous correlated attempts. The 2026 sample was previously inspected, so must not be called a clean unseen test. Trade outcomes include model assumptions about fills, commissions and spread; the simulated source is NOT evidence of achieved broker execution.

The separate, narrower asset-specific 2025–2026 index/FX research also did not prove an independent, broker-cost-verified edge. Do not promote a visually good single configuration.

## Private evidence fingerprints (SHA256)

- Research matrix: `katarina_intraday_tool_matrix_2025_2026.json` — `7d0e6db9aeefa79e5245ca97e25943a3c6d06283aa799a6be6295e3ec242e4cc`
- Asset-family diagnostics: `katarina_distinct_index_fx_intraday_2025_2026.json` — `d6fb44767b8679e4ca7b73f367fdc2c5a8780110beaf028484d90827b3063a87`
- XAUUSD confluence ablation: `katarina_xau_method_tick_ablation_2025_2026.json` — `0655e03af231f3250ce076cb15b1a77f96586e657f8304402187d8d1eb6dc29a`

The files remain private on the Windows research workstation. Their hashes alone do not establish source authenticity, broker costs, no-lookahead execution or statistical alpha.

## Rules for sustainable operations

1. The regime classifier proposes **hypotheses**, and must not force a trade where net expectancy is unverified.
2. XAUUSD is the **only provisional high-priority investigation**, not a live tradable edge. Pair research remains open to distinct, independently tested methods in future.
3. Enforce separate BUY and SELL testing, one hard initial stop-loss, independent chronological windows, multiple-testing adjustment, week-block uncertainty, long loss-streak and cost stress.
4. Broker contract, standard-vs-cent units, margin, spread and slippage must be independently attested before research qualification can be considered complete.
5. Protected reserve and adaptive Risk Governor are capital *safety* features, not returns generators. No averaging down or martingale to meet operational cash costs.
6. KATARINA operating expenses should be financed from nontrading revenue until realized results withstand independent review.

**Verified live-trading alpha count: 0. Live execution authorization: FALSE.**

## Private ingestion (research only)

Use `scripts/research/audit_private_alpha_holdout.py` with a local evidence manifest, raw broker source and event-level net-R JSONL, all *outside this public repository*. The script SHA256-hashes source bytes; requires the frozen 70-cell research protocol, independent-period/cost/contract assertions, correct closed-event chronology and explicit signal side; then applies `alpha_survival.assess`. A successful run can at most reach `PASS_SHADOW_RESEARCH_ONLY`. It **cannot** establish that human attestations are genuine and never grants live execution.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/research/audit_private_alpha_holdout.py --repo-root . --manifest "C:\\private\\holdout-manifest.json" --raw-source "C:\\private\\broker-bid-ask.bin" --outcomes "C:\\private\\closed-outcomes.jsonl" --output "C:\\private\\alpha-holdout-report.json"
```

Do NOT commit the source files, manifest, outcome records, or privately identifying audit output to GitHub.

**Validated scholarly context:** Moskowitz, Ooi & Pedersen (2012), DOI 10.1016/j.jfineco.2011.11.003, is evidence for *longer-horizon futures trend following*, not CFD intraday. White (2000), DOI 10.1111/1468-0262.00152, details data snooping, and Park & Irwin (2007), DOI 10.1111/j.1467-6419.2007.00519.x, discuss mixed strategy results and transaction cost limitations.
