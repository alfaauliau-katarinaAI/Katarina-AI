# Peta stage body 11–40

Modul body diberi nama fungsi pada perapian Tahap 4 (21 Oktober 2026). Nomor stage tetap menjadi
identitas tata kelola: manifest `config/stages/stageNN.json` tidak diganti nama karena dimuat per
nomor, dan freeze record/dokumen riset tetap memakai nomor. Sumber kebenaran pemetaan di kode adalah
`katarina.body.STAGE_MODULES`; `tests/unit/body/test_stage_modules.py` memastikan konstanta itu,
`implementation_module` di manifest, dan `SPEC` modul selalu sama.

Modul `katarina.body.stageNN` lama masih ada sebagai alias (`sys.modules` + `DeprecationWarning`)
selama satu rilis, lalu dihapus. Generator `scripts/body/upgrade_functional_body.py` menulis berkas
sesuai `implementation_module` di manifest.

Stage 01–10 bukan modul body (konstitusi, workflow, arsitektur, protokol, core, bridge MT5, transport,
validasi, health/safety, memori); lihat `docs/stages/STAGE_01_40_MANIFEST.json` dan `docs/reviews/`.

| Stage | Nama | Modul | Alias lama | Manifest | Referensi |
|---|---|---|---|---|---|
| 11 | Market Intelligence Engine | `katarina.body.market_intelligence` | `katarina.body.stage11` | `config/stages/stage11.json` | `docs/research/stages/STAGE_11_GITHUB_REFERENCES.md` |
| 12 | Multi-Timeframe Engine | `katarina.body.multi_timeframe` | `katarina.body.stage12` | `config/stages/stage12.json` | `docs/research/stages/STAGE_12_GITHUB_REFERENCES.md` |
| 13 | Market Regime Engine | `katarina.body.market_regime` | `katarina.body.stage13` | `config/stages/stage13.json` | `docs/research/stages/STAGE_13_GITHUB_REFERENCES.md` |
| 14 | XAUUSD Specialist V1 | `katarina.body.xauusd_specialist` | `katarina.body.stage14` | `config/stages/stage14.json` | `docs/research/stages/STAGE_14_GITHUB_REFERENCES.md` |
| 15 | Decision Engine | `katarina.body.decision` | `katarina.body.stage15` | `config/stages/stage15.json` | `docs/research/stages/STAGE_15_GITHUB_REFERENCES.md` |
| 16 | Risk Governor | `katarina.body.risk_governor` | `katarina.body.stage16` | `config/stages/stage16.json` | `docs/research/stages/STAGE_16_GITHUB_REFERENCES.md` |
| 17 | Position Sizing Engine | `katarina.body.position_sizing` | `katarina.body.stage17` | `config/stages/stage17.json` | `docs/research/stages/STAGE_17_GITHUB_REFERENCES.md` |
| 18 | Execution Engine | `katarina.body.execution` | `katarina.body.stage18` | `config/stages/stage18.json` | `docs/research/stages/STAGE_18_GITHUB_REFERENCES.md` |
| 19 | Position Manager | `katarina.body.position_manager` | `katarina.body.stage19` | `config/stages/stage19.json` | `docs/research/stages/STAGE_19_GITHUB_REFERENCES.md` |
| 20 | Trade Evaluation Engine | `katarina.body.trade_evaluation` | `katarina.body.stage20` | `config/stages/stage20.json` | `docs/research/stages/STAGE_20_GITHUB_REFERENCES.md` |
| 21 | Research Engine | `katarina.body.research` | `katarina.body.stage21` | `config/stages/stage21.json` | `docs/research/stages/STAGE_21_GITHUB_REFERENCES.md` |
| 22 | Backtesting Engine | `katarina.body.backtesting` | `katarina.body.stage22` | `config/stages/stage22.json` | `docs/research/stages/STAGE_22_GITHUB_REFERENCES.md` |
| 23 | Out-of-Sample + Walk-Forward | `katarina.body.walk_forward` | `katarina.body.stage23` | `config/stages/stage23.json` | `docs/research/stages/STAGE_23_GITHUB_REFERENCES.md` |
| 24 | Monte Carlo / Robustness | `katarina.body.robustness` | `katarina.body.stage24` | `config/stages/stage24.json` | `docs/research/stages/STAGE_24_GITHUB_REFERENCES.md` |
| 25 | Tester Evaluation | `katarina.body.tester_evaluation` | `katarina.body.stage25` | `config/stages/stage25.json` | `docs/research/stages/STAGE_25_GITHUB_REFERENCES.md` |
| 26 | Learning Engine | `katarina.body.learning` | `katarina.body.stage26` | `config/stages/stage26.json` | `docs/research/stages/STAGE_26_GITHUB_REFERENCES.md` |
| 27 | Machine Learning V1 | `katarina.body.machine_learning` | `katarina.body.stage27` | `config/stages/stage27.json` | `docs/research/stages/STAGE_27_GITHUB_REFERENCES.md` |
| 28 | Model Promotion & Rollback | `katarina.body.model_promotion` | `katarina.body.stage28` | `config/stages/stage28.json` | `docs/research/stages/STAGE_28_GITHUB_REFERENCES.md` |
| 29 | Economic Intelligence Engine | `katarina.body.economic_intelligence` | `katarina.body.stage29` | `config/stages/stage29.json` | `docs/research/stages/STAGE_29_GITHUB_REFERENCES.md` |
| 30 | Portfolio & Multi-Pair Engine | `katarina.body.portfolio` | `katarina.body.stage30` | `config/stages/stage30.json` | `docs/research/stages/STAGE_30_GITHUB_REFERENCES.md` |
| 31 | Correlation & Global Exposure Engine | `katarina.body.exposure` | `katarina.body.stage31` | `config/stages/stage31.json` | `docs/research/stages/STAGE_31_GITHUB_REFERENCES.md` |
| 32 | Dashboard | `katarina.body.dashboard` | `katarina.body.stage32` | `config/stages/stage32.json` | `docs/research/stages/STAGE_32_GITHUB_REFERENCES.md` |
| 33 | Automated Testing / CI | `katarina.body.automated_testing` | `katarina.body.stage33` | `config/stages/stage33.json` | `docs/research/stages/STAGE_33_GITHUB_REFERENCES.md` |
| 34 | Constitution Guard | `katarina.body.constitution_guard` | `katarina.body.stage34` | `config/stages/stage34.json` | `docs/research/stages/STAGE_34_GITHUB_REFERENCES.md` |
| 35 | MT5 Strategy Tester Integration | `katarina.body.strategy_tester` | `katarina.body.stage35` | `config/stages/stage35.json` | `docs/research/stages/STAGE_35_GITHUB_REFERENCES.md` |
| 36 | Live Environment Preflight | `katarina.body.live_preflight` | `katarina.body.stage36` | `config/stages/stage36.json` | `docs/research/stages/STAGE_36_GITHUB_REFERENCES.md` |
| 37 | Stress Test | `katarina.body.stress_test` | `katarina.body.stage37` | `config/stages/stage37.json` | `docs/research/stages/STAGE_37_GITHUB_REFERENCES.md` |
| 38 | Live Micro-Risk Validation | `katarina.body.live_micro_risk` | `katarina.body.stage38` | `config/stages/stage38.json` | `docs/research/stages/STAGE_38_GITHUB_REFERENCES.md` |
| 39 | Performance Monitoring | `katarina.body.performance_monitoring` | `katarina.body.stage39` | `config/stages/stage39.json` | `docs/research/stages/STAGE_39_GITHUB_REFERENCES.md` |
| 40 | Continuous Evolution | `katarina.body.continuous_evolution` | `katarina.body.stage40` | `config/stages/stage40.json` | `docs/research/stages/STAGE_40_GITHUB_REFERENCES.md` |
