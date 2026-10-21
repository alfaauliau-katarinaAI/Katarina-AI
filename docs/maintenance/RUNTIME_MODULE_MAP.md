# Peta modul runtime `src/katarina`

Dibuat otomatis oleh `scripts/governance/runtime_import_map.py` (analisis statis, tanpa
menjalankan kode). Jangan disunting manual; jalankan ulang:

```bash
python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md
```

Kolom *via* menyebut kelompok root yang menjangkau modul: `runtime` (entry point utama),
`ops` (dipanggil launcher .bat/.ps1/.sh/service/config), `workflow` (dipanggil
`.github/workflows`), `research` (`scripts/research`), `scripts` (script lain yang tidak
dipanggil apa pun), `tests`. Import dinamis di luar registry stage tidak terlihat, jadi
kategori D adalah kandidat untuk dicek manual, bukan bukti tidak terpakai.

## Ringkasan

| Kategori | Arti | Jumlah |
|---|---|---|
| A | dipakai runtime/operasional atau workflow | 212 |
| B | hanya dipakai tests | 24 |
| C | hanya dipakai script non-operasional (riset dll.) | 17 |
| D | tidak terjangkau dari root mana pun | 5 |

Total modul: 258. Dari kategori A, 77 hanya terjangkau lewat workflow (CI/riset terjadwal), bukan entry point runtime atau launcher.

## Root yang dipakai

- **runtime** (5): `katarina_pc.py`, `scripts/ai/publish_runtime_monitor.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_independent_demo_worker.py`
- **ops** (8): `katarina_pc.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_readonly_decisions.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`
- **workflow** (35): `katarina_pc.py`, `scripts/ai/audit_autonomous_shadow.py`, `scripts/ai/audit_self_evolution_runner.py`, `scripts/ai/hf_archive_sync.py`, `scripts/ai/hf_storage_smoke.py`, `scripts/ai/install_hf_archive_test.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/seal_gemini_secret.py`, `scripts/ai/seal_hf_secret.py`, `scripts/ai/verify_unified_katarina.py`, `scripts/body/audit_body_framework.py`, `scripts/body/audit_functional_body.py`, `scripts/governance/audit_alpha_regime_program.py`, `scripts/governance/audit_branch_inventory.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/governance/audit_dependency_links.py`, `scripts/governance/audit_repo_hygiene.py`, `scripts/governance/audit_stage14_15_research.py`, `scripts/governance/audit_stage16_17_synthetic.py`, `scripts/governance/clean_orphaned_workflow_catalog.py`, `scripts/governance/guarded_branch_cleanup.py`, `scripts/pc/build_pc_test_package.py`, `scripts/pc/verify_environment_recovery.py`, `scripts/research/audit_private_alpha_holdout.py`, `scripts/research/run_adaptive_walkforward.py`, `scripts/research/run_autonomous_strategy_discovery.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`, `scripts/stage_all/audit_stage_11_40.py`, `scripts/update_hot_news.py`, `src/katarina/governance/external_model_bridge.py`, `src/katarina/governance/multi_model_evolution_review.py`, `src/katarina/governance/self_evolution_audit.py`, `src/katarina/intelligence/cognition/self_evolution_lab.py`

## Otak canonical dan bekas otak berversi

| Modul | Kategori | via | Diimpor modul src |
|---|---|---|---|
| `katarina.intelligence.cognition.unified_brain` | A | runtime, ops, workflow, scripts, tests | `katarina.governance.unified_verification`, `katarina.intelligence.cognition.continuous_observation` |
| `katarina.intelligence.cognition.adaptive_observation` | A | runtime, ops, workflow, scripts, tests | `katarina.intelligence.cognition.market_decision_pipeline`, `katarina.intelligence.cognition.unified_adaptive_research_cycle`, `katarina.intelligence.cognition.unified_research_handoff` |
| `katarina.intelligence.cognition.market_decision` | A | runtime, ops, workflow, scripts, tests | `katarina.governance.unified_verification`, `katarina.intelligence.cognition.contextual_decision_intelligence`, `katarina.intelligence.cognition.unified_brain`, `katarina.intelligence.lab.causal_market_replay` |
| `katarina.intelligence.perception.screening` | C | scripts, tests | `katarina.intelligence.perception.market_regime_intelligence`, `katarina.intelligence.perception.scalp_pattern_candidates`, `katarina.intelligence.perception.symbol_playbooks` |
| `katarina.intelligence.cognition.observer` | A | runtime, ops, workflow, scripts, tests | `katarina.governance.unified_verification`, `katarina.intelligence.cognition.continuous_observation`, `katarina.intelligence.cognition.unified_brain` |

## A — dipakai runtime/operasional atau workflow (212)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina` | runtime, ops, workflow, research, scripts, tests | 148 | 223 |
| `katarina.adapters` | runtime, ops, workflow, scripts, tests | 19 | 34 |
| `katarina.adapters.agent_dashboard_page` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.adapters.automatic_connection` | runtime, ops, workflow, scripts, tests | 4 | 14 |
| `katarina.adapters.brain_feedback` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.adapters.continuous_owner_surface` | runtime, ops, workflow, scripts, tests | 0 | 3 |
| `katarina.adapters.demo_permissions` | runtime, ops, workflow, scripts, tests | 7 | 2 |
| `katarina.adapters.dialog_model` | runtime, ops, workflow, scripts, tests | 2 | 9 |
| `katarina.adapters.mt5_account_pnl` | workflow, scripts, tests | 1 | 2 |
| `katarina.adapters.mt5_readonly_market` | runtime, ops, workflow, scripts, tests | 3 | 0 |
| `katarina.adapters.owner_access` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.adapters.owner_dialog_server` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.adapters.paper` | workflow, scripts, tests | 0 | 4 |
| `katarina.adapters.pc_simulation` | runtime, ops, workflow, scripts, tests | 0 | 4 |
| `katarina.adapters.readonly_cloud` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.adapters.research_sources` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.adapters.tester` | workflow, scripts, tests | 0 | 3 |
| `katarina.body` | workflow, scripts, tests | 34 | 10 |
| `katarina.body.automated_testing` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.backtesting` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.component` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.constitution_guard` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.continuous_evolution` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.contracts` | workflow, scripts, tests | 34 | 1 |
| `katarina.body.dashboard` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.decision` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.economic_intelligence` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.execution` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.exposure` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.functional` | workflow, scripts, tests | 30 | 5 |
| `katarina.body.learning` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.live_micro_risk` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.live_preflight` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.machine_learning` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.market_intelligence` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.market_regime` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.model_promotion` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.multi_timeframe` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.performance_monitoring` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.portfolio` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.position_manager` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.position_sizing` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.registry` | workflow, scripts, tests | 2 | 0 |
| `katarina.body.research` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.risk_governor` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.robustness` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.runtime` | workflow, scripts, tests | 1 | 0 |
| `katarina.body.strategy_tester` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.stress_test` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.tester_evaluation` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.trade_evaluation` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.walk_forward` | workflow, scripts, tests | 3 | 0 |
| `katarina.body.xauusd_specialist` | workflow, scripts, tests | 3 | 0 |
| `katarina.contracts` | runtime, ops, workflow, scripts, tests | 11 | 17 |
| `katarina.contracts.runtime` | runtime, ops, workflow, scripts, tests | 12 | 17 |
| `katarina.core` | runtime, ops, workflow, scripts, tests | 6 | 8 |
| `katarina.core.component` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.core.lifecycle` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.core.message_bus` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.core.orchestrator` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.core.queue` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.core.readiness` | runtime, ops, workflow, scripts, tests | 5 | 5 |
| `katarina.core.state` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.engines` | runtime, ops, workflow, scripts, tests | 19 | 40 |
| `katarina.engines.adaptive_risk` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.engines.adaptive_scalper` | runtime, ops, workflow, scripts, tests | 2 | 6 |
| `katarina.engines.broker_aware_sizing` | workflow, tests | 0 | 3 |
| `katarina.engines.capital` | runtime, ops, workflow, scripts, tests | 2 | 5 |
| `katarina.engines.decision` | workflow, scripts, tests | 0 | 6 |
| `katarina.engines.demo_execution` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.engines.evaluation` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.execution` | workflow, scripts, tests | 1 | 6 |
| `katarina.engines.execution_recovery` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.engines.exposure` | workflow, scripts, tests | 1 | 3 |
| `katarina.engines.manual_risk` | runtime, ops, workflow, scripts, tests | 5 | 8 |
| `katarina.engines.portfolio` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.position` | runtime, ops, workflow, scripts, tests | 2 | 8 |
| `katarina.engines.risk` | runtime, ops, workflow, scripts, tests | 8 | 22 |
| `katarina.engines.scalper_entry` | workflow, scripts, tests | 2 | 5 |
| `katarina.engines.sizing` | workflow, scripts, tests | 0 | 6 |
| `katarina.engines.stress` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance` | runtime, ops, workflow, scripts, tests | 3 | 13 |
| `katarina.governance.ci` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.constitution` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.evolution` | workflow, scripts, tests | 0 | 4 |
| `katarina.governance.external_model_bridge` | workflow, tests | 0 | 1 |
| `katarina.governance.live_validation` | workflow, scripts, tests | 0 | 5 |
| `katarina.governance.models` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.multi_model_evolution_review` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.governance.self_evolution_audit` | workflow | 0 | 1 |
| `katarina.governance.unified_verification` | workflow, scripts, tests | 0 | 3 |
| `katarina.health` | runtime, ops, workflow, scripts, tests | 2 | 5 |
| `katarina.health.engine` | runtime, ops, workflow, scripts, tests | 3 | 5 |
| `katarina.host` | runtime, ops, workflow, scripts, tests | 2 | 7 |
| `katarina.intelligence` | runtime, ops, workflow, research, scripts, tests | 60 | 138 |
| `katarina.intelligence.broker` | runtime, ops, workflow, research, scripts, tests | 9 | 16 |
| `katarina.intelligence.broker.auto_calibration` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.broker.broker_account_monitor` | runtime, ops, workflow, scripts, tests | 3 | 4 |
| `katarina.intelligence.broker.broker_clock_alignment` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.intelligence.broker.broker_history_coverage` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.broker.broker_scan_universe` | runtime, ops, workflow, research, scripts, tests | 3 | 4 |
| `katarina.intelligence.broker.causal_broker_quotes` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.broker.data_recovery` | runtime, ops, workflow, scripts, tests | 4 | 1 |
| `katarina.intelligence.cognition` | runtime, ops, workflow, scripts, tests | 24 | 43 |
| `katarina.intelligence.cognition.adaptive_observation` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.intelligence.cognition.assistant_cycle` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.intelligence.cognition.brain_runtime_control` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.cognition.contextual_decision_intelligence` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.intelligence.cognition.continuous_observation` | runtime, ops, workflow, scripts, tests | 0 | 4 |
| `katarina.intelligence.cognition.explainable_market_decision` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.intelligence.cognition.market_decision` | runtime, ops, workflow, scripts, tests | 4 | 3 |
| `katarina.intelligence.cognition.market_decision_pipeline` | runtime, ops, workflow, scripts, tests | 7 | 12 |
| `katarina.intelligence.cognition.observer` | runtime, ops, workflow, scripts, tests | 3 | 9 |
| `katarina.intelligence.cognition.owner_research_review` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.cognition.self_evolution_lab` | runtime, ops, workflow, scripts, tests | 5 | 3 |
| `katarina.intelligence.cognition.unified_adaptive_research_cycle` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.cognition.unified_brain` | runtime, ops, workflow, scripts, tests | 2 | 19 |
| `katarina.intelligence.cognition.unified_cognitive_cycle` | runtime, ops, workflow, scripts, tests | 4 | 6 |
| `katarina.intelligence.cognition.unified_research_handoff` | runtime, ops, workflow, scripts, tests | 4 | 4 |
| `katarina.intelligence.demo` | runtime, ops, workflow, scripts, tests | 3 | 8 |
| `katarina.intelligence.demo.demo_account` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.intelligence.demo.demo_forward` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.demo.demo_strategy` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.demo.independent_demo_worker` | runtime, scripts, tests | 0 | 2 |
| `katarina.intelligence.lab` | runtime, ops, workflow, research, scripts, tests | 13 | 30 |
| `katarina.intelligence.lab.adaptive_walkforward` | workflow, research, tests | 1 | 4 |
| `katarina.intelligence.lab.autonomous_research` | runtime, ops, workflow, scripts, tests | 2 | 8 |
| `katarina.intelligence.lab.autonomous_strategy_discovery` | workflow, research, tests | 0 | 2 |
| `katarina.intelligence.lab.continuous_research_lab` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.lab.evidence_risk` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.intelligence.lab.research_capacity` | runtime, ops, workflow, scripts, tests | 3 | 6 |
| `katarina.intelligence.lab.research_reports` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.news` | runtime, ops, workflow, scripts, tests | 11 | 19 |
| `katarina.intelligence.news.market_article_context` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.news.news_intelligence` | runtime, ops, workflow, scripts, tests | 5 | 3 |
| `katarina.intelligence.news.official_cache_provenance` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.news.public_context` | runtime, ops, workflow, scripts, tests | 4 | 8 |
| `katarina.intelligence.news.public_language_research` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.news.research_agenda` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.news.research_news_collection` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.news.verified_policy_context` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.intelligence.operations` | runtime, ops, workflow, scripts, tests | 5 | 9 |
| `katarina.intelligence.operations.file_housekeeping` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.operations.foundation_readiness` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.operations.network_doctor` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.intelligence.operations.parallel_storage` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.operations.runtime_evidence` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.perception` | runtime, ops, workflow, research, scripts, tests | 23 | 38 |
| `katarina.intelligence.perception.adaptive_regime` | runtime, ops, workflow, scripts, tests | 5 | 8 |
| `katarina.intelligence.perception.causal_seasonality` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.perception.closed_swing_structure` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.perception.directional_consensus` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.perception.economics` | workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.perception.learning` | workflow, scripts, tests | 0 | 3 |
| `katarina.intelligence.perception.market` | workflow, scripts, tests | 0 | 4 |
| `katarina.intelligence.perception.observational_associations` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.perception.regime` | workflow, scripts, tests | 2 | 7 |
| `katarina.intelligence.perception.semantic_setup_truth` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.perception.session_gaps` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.perception.simple_ml` | workflow, scripts, tests | 0 | 3 |
| `katarina.intelligence.perception.structural_entry_quality` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.perception.structure_exit_plan` | runtime, ops, workflow, scripts, tests | 3 | 6 |
| `katarina.intelligence.perception.timeframe` | workflow, scripts, tests | 0 | 4 |
| `katarina.intelligence.perception.xauusd` | workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.shadow` | runtime, ops, workflow, scripts, tests | 10 | 16 |
| `katarina.intelligence.shadow.contextual_observation_journal` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.shadow.prospective_shadow_book` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.intelligence.shadow.prospective_shadow_review` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.memory` | runtime, ops, workflow, scripts, tests | 7 | 15 |
| `katarina.memory.neuro_link` | runtime, ops, workflow, scripts, tests | 3 | 0 |
| `katarina.memory.runtime_state` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.memory.store` | runtime, ops, workflow, scripts, tests | 8 | 10 |
| `katarina.monitoring` | runtime, ops, workflow, scripts, tests | 22 | 39 |
| `katarina.monitoring.activity_trace` | runtime, ops, workflow, scripts, tests | 6 | 9 |
| `katarina.monitoring.agent_projection` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.monitoring.dashboard` | workflow, scripts, tests | 0 | 3 |
| `katarina.monitoring.entry_feed` | runtime, scripts, tests | 2 | 5 |
| `katarina.monitoring.learning_evidence` | runtime, scripts, tests | 1 | 5 |
| `katarina.monitoring.monitor_publisher` | runtime, scripts, tests | 0 | 3 |
| `katarina.monitoring.mt5_dashboard` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.monitoring.pair_activity` | runtime, scripts, tests | 1 | 5 |
| `katarina.monitoring.performance` | workflow, scripts, tests | 0 | 3 |
| `katarina.monitoring.position_feed` | runtime, scripts, tests | 1 | 4 |
| `katarina.monitoring.public_research` | runtime, scripts, tests | 1 | 6 |
| `katarina.monitoring.public_runtime` | runtime, scripts, tests | 1 | 9 |
| `katarina.monitoring.research_growth` | runtime, scripts, tests | 1 | 5 |
| `katarina.monitoring.research_health` | runtime, scripts, tests | 1 | 2 |
| `katarina.monitoring.research_lab_status` | runtime, scripts, tests | 1 | 6 |
| `katarina.monitoring.research_soak` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.monitoring.runtime_details` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.monitoring.snapshot_io` | runtime, ops, workflow, scripts, tests | 13 | 6 |
| `katarina.monitoring.worker_runtime` | runtime, ops, workflow, scripts, tests | 5 | 6 |
| `katarina.persistence` | ops, workflow, scripts, tests | 5 | 4 |
| `katarina.persistence.boundaries` | ops, workflow, scripts, tests | 4 | 1 |
| `katarina.persistence.canonical` | ops, workflow, scripts, tests | 4 | 0 |
| `katarina.persistence.records` | ops, workflow, scripts, tests | 3 | 0 |
| `katarina.persistence.recovery` | ops, workflow, scripts, tests | 1 | 1 |
| `katarina.persistence.sqlite_common` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.sqlite_journal` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.stores` | ops, workflow, scripts, tests | 2 | 1 |
| `katarina.policies` | workflow, scripts, tests | 1 | 3 |
| `katarina.policies.risk` | workflow, scripts, tests | 1 | 1 |
| `katarina.policies.strategy` | workflow, scripts, tests | 1 | 2 |
| `katarina.research` | workflow, research, scripts, tests | 0 | 6 |
| `katarina.research.alpha_survival` | workflow, research, tests | 0 | 3 |
| `katarina.research.backtest` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.research` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.robustness` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.shadow` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.walkforward` | workflow, scripts, tests | 0 | 3 |
| `katarina.validation` | runtime, ops, workflow, scripts, tests | 4 | 11 |
| `katarina.validation.engine` | runtime, ops, workflow, scripts, tests | 5 | 11 |

## B — hanya dipakai tests (24)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.engines.account_risk_state` | tests | 1 | 7 |
| `katarina.engines.broker_risk` | tests | 0 | 3 |
| `katarina.engines.multi_symbol_execution` | tests | 0 | 1 |
| `katarina.engines.opportunity` | tests | 1 | 2 |
| `katarina.intelligence.demo.forward_outcomes` | tests | 0 | 3 |
| `katarina.intelligence.lab.adaptive_strategy_library` | tests | 0 | 1 |
| `katarina.intelligence.lab.causal_market_replay` | tests | 1 | 2 |
| `katarina.intelligence.lab.causal_tick_reconciliation` | tests | 0 | 1 |
| `katarina.intelligence.lab.closed_bar_failure_forensics` | tests | 0 | 1 |
| `katarina.intelligence.lab.intraday_scalp_research` | tests | 1 | 2 |
| `katarina.intelligence.lab.offline_hand_telemetry` | tests | 1 | 1 |
| `katarina.intelligence.lab.precommitted_setup_research` | tests | 0 | 1 |
| `katarina.intelligence.lab.replay_cost_diagnostics` | tests | 0 | 1 |
| `katarina.intelligence.lab.research_exit_lifecycle` | tests | 0 | 1 |
| `katarina.intelligence.lab.research_readiness_gate` | tests | 0 | 1 |
| `katarina.intelligence.lab.research_signal_ablation` | tests | 0 | 1 |
| `katarina.intelligence.lab.unified_intraday_gate` | tests | 0 | 1 |
| `katarina.intelligence.news.economic_feed` | tests | 0 | 2 |
| `katarina.intelligence.perception.alternative_symbol_playbooks` | tests | 0 | 1 |
| `katarina.intelligence.perception.calendar_history` | tests | 0 | 1 |
| `katarina.intelligence.shadow.shadow_hypotheses` | tests | 1 | 1 |
| `katarina.intelligence.shadow.strategy_drift` | tests | 0 | 1 |
| `katarina.memory.quarantined_research_memory` | tests | 0 | 1 |
| `katarina.monitoring.operational_dashboard` | tests | 0 | 2 |

## C — hanya dipakai script non-operasional (riset dll.) (17)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.adapters.mt5_shadow_read_only` | scripts, tests | 2 | 2 |
| `katarina.intelligence.broker.mt5_shadow_cycle` | scripts, tests | 0 | 2 |
| `katarina.intelligence.perception.analog_feature_schema` | research, tests | 1 | 0 |
| `katarina.intelligence.perception.historical_analog_memory` | research, tests | 0 | 2 |
| `katarina.intelligence.perception.market_regime_intelligence` | scripts, tests | 1 | 1 |
| `katarina.intelligence.perception.market_universe` | scripts, tests | 2 | 2 |
| `katarina.intelligence.perception.multi_pair_arbitrator` | scripts, tests | 0 | 2 |
| `katarina.intelligence.perception.screening` | scripts, tests | 3 | 6 |
| `katarina.intelligence.perception.symbol_playbooks` | scripts, tests | 2 | 2 |
| `katarina.intelligence.perception.technical_regime` | scripts, tests | 3 | 1 |
| `katarina.intelligence.shadow.shadow_gold_intraday` | scripts, tests | 1 | 1 |
| `katarina.intelligence.shadow.shadow_journal` | scripts, tests | 4 | 3 |
| `katarina.intelligence.shadow.shadow_manifest` | scripts, tests | 0 | 2 |
| `katarina.intelligence.shadow.shadow_paper_book` | scripts, tests | 2 | 2 |
| `katarina.intelligence.shadow.shadow_research_evaluation` | scripts, tests | 0 | 2 |
| `katarina.intelligence.shadow.strategy_evidence` | scripts, tests | 2 | 2 |
| `katarina.monitoring.monitor_relay` | scripts, tests | 0 | 2 |

## D — tidak terjangkau dari root mana pun (5)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.domain` | — | 0 | 0 |
| `katarina.entrypoints` | — | 0 | 0 |
| `katarina.intelligence.perception.cost_expectancy` | — | 0 | 0 |
| `katarina.intelligence.perception.scalp_pattern_candidates` | — | 0 | 0 |
| `katarina.ports` | — | 0 | 0 |
