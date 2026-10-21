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
| A | dipakai runtime/operasional atau workflow | 214 |
| B | hanya dipakai tests | 19 |
| C | hanya dipakai script non-operasional (riset dll.) | 35 |
| D | tidak terjangkau dari root mana pun | 2 |

Total modul: 270. Dari kategori A, 40 hanya terjangkau lewat workflow (CI/riset terjadwal), bukan entry point runtime atau launcher.

## Root yang dipakai

- **runtime** (5): `katarina_pc.py`, `scripts/ai/publish_runtime_monitor.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_independent_demo_worker.py`
- **ops** (17): `katarina_pc.py`, `ops/bridge/katarina_agent.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_readonly_decisions.py`, `scripts/body/audit_body_framework.py`, `scripts/body/audit_cross_stage_pipeline.py`, `scripts/body/audit_functional_body.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/pc/bind_portable_runtime.py`, `scripts/pc/run_pretrial_acceptance.py`, `scripts/research/probe_current_market_analogs.py`, `scripts/stage07/audit_stage07_final.py`, `scripts/stage07/profile_stage07_transport.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`
- **workflow** (51): `katarina_pc.py`, `scripts/ai/audit_autonomous_shadow.py`, `scripts/ai/audit_self_evolution_runner.py`, `scripts/ai/hf_archive_sync.py`, `scripts/ai/hf_storage_smoke.py`, `scripts/ai/install_hf_archive_test.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/seal_gemini_secret.py`, `scripts/ai/seal_hf_secret.py`, `scripts/ai/verify_unified_katarina.py`, `scripts/body/audit_body_framework.py`, `scripts/body/audit_functional_body.py`, `scripts/governance/audit_alpha_regime_program.py`, `scripts/governance/audit_branch_inventory.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/governance/audit_dependency_links.py`, `scripts/governance/audit_repo_hygiene.py`, `scripts/governance/audit_stage14_15_research.py`, `scripts/governance/audit_stage16_17_synthetic.py`, `scripts/governance/clean_orphaned_workflow_catalog.py`, `scripts/governance/guarded_branch_cleanup.py`, `scripts/pc/build_pc_test_package.py`, `scripts/pc/verify_environment_recovery.py`, `scripts/protocol/validate_kat1_vectors.py`, `scripts/research/audit_private_alpha_holdout.py`, `scripts/research/broker_entry_diagnostics_v9.py`, `scripts/research/broker_multitf_risk_v10.py`, `scripts/research/frozen_xau_sell_tick_verdict.py`, `scripts/research/github_replay.py`, `scripts/research/public_github_sample_tournament.py`, `scripts/research/public_market_tournament.py`, `scripts/research/run_adaptive_walkforward.py`, `scripts/research/run_autonomous_strategy_discovery.py`, `scripts/research/summarize_public_tournament.py`, `scripts/stage07/audit_stage07_final.py`, `scripts/stage07/audit_stage07_preclearance.py`, `scripts/stage07/configure_mt5_network_allowlist.py`, `scripts/stage07/profile_stage07_transport.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`, `scripts/stage_all/audit_stage_11_40.py`, `scripts/update_hot_news.py`, `src/katarina/adapters/transport/kat1_codec.py`, `src/katarina/adapters/transport/recovery.py`, `src/katarina/adapters/transport/session.py`, `src/katarina/adapters/transport/tcp.py`, `src/katarina/adapters/transport/zmq.py`, `src/katarina/governance/external_model_bridge.py`, `src/katarina/governance/multi_model_evolution_review.py`, `src/katarina/intelligence/self_evolution_lab.py`

## Modul otak lama (bahan Tahap 2)

| Modul | Kategori | via | Diimpor modul src |
|---|---|---|---|
| `katarina.intelligence.brain` | C | research, scripts, tests | `katarina.research.independent_audit`, `katarina.research.mt5_journal` |
| `katarina.intelligence.adaptive_brain_v2` | A | runtime, ops, workflow, research, scripts, tests | `katarina.intelligence.market_decision_pipeline`, `katarina.intelligence.unified_adaptive_research_cycle`, `katarina.intelligence.unified_research_handoff` |
| `katarina.intelligence.market_decision_brain_v3` | A | runtime, ops, workflow, research, scripts, tests | `katarina.intelligence.causal_market_replay`, `katarina.intelligence.contextual_decision_intelligence`, `katarina.intelligence.unified_brain` |
| `katarina.intelligence.multi_market_brain` | C | research, scripts, tests | `katarina.intelligence.brain`, `katarina.intelligence.market_regime_intelligence`, `katarina.intelligence.scalp_pattern_candidates`, `katarina.intelligence.symbol_playbooks` |
| `katarina.intelligence.brain_observer` | A | runtime, ops, workflow, scripts, tests | `katarina.intelligence.continuous_observation`, `katarina.intelligence.unified_brain` |

## A — dipakai runtime/operasional atau workflow (214)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina` | runtime, ops, workflow, research, scripts, tests | 162 | 282 |
| `katarina.adapters` | runtime, ops, workflow, scripts, tests | 23 | 38 |
| `katarina.adapters.agent_dashboard_page` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.adapters.automatic_connection` | runtime, ops, workflow, scripts, tests | 4 | 14 |
| `katarina.adapters.brain_feedback` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.adapters.continuous_owner_surface` | runtime, ops, workflow, scripts, tests | 0 | 3 |
| `katarina.adapters.demo_permissions` | runtime, ops, workflow, scripts, tests | 7 | 2 |
| `katarina.adapters.dialog_model` | runtime, ops, workflow, scripts, tests | 2 | 9 |
| `katarina.adapters.mt5_account_pnl` | workflow, scripts, tests | 0 | 3 |
| `katarina.adapters.mt5_readonly_market` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.adapters.owner_access` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.adapters.owner_dialog_server` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.adapters.paper` | workflow, scripts, tests | 0 | 4 |
| `katarina.adapters.pc_simulation` | runtime, ops, workflow, scripts, tests | 0 | 4 |
| `katarina.adapters.readonly_cloud` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.adapters.research_sources` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.adapters.tester` | workflow, scripts, tests | 0 | 3 |
| `katarina.adapters.transport` | ops, workflow, scripts, tests | 4 | 4 |
| `katarina.adapters.transport.kat1_codec` | ops, workflow, scripts, tests | 5 | 4 |
| `katarina.adapters.transport.memory` | ops, workflow, scripts, tests | 1 | 2 |
| `katarina.adapters.transport.recovery` | workflow, tests | 0 | 1 |
| `katarina.adapters.transport.session` | workflow, tests | 0 | 1 |
| `katarina.adapters.transport.tcp` | ops, workflow, tests | 0 | 2 |
| `katarina.adapters.transport.zmq` | workflow, tests | 0 | 1 |
| `katarina.body` | ops, workflow, scripts, tests | 34 | 10 |
| `katarina.body.component` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.body.contracts` | ops, workflow, scripts, tests | 34 | 2 |
| `katarina.body.functional` | ops, workflow, scripts, tests | 30 | 5 |
| `katarina.body.registry` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.runtime` | ops, workflow, scripts, tests | 1 | 0 |
| `katarina.body.stage11` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage12` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage13` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage14` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage15` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage16` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage17` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage18` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage19` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage20` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage21` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage22` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage23` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage24` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage25` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage26` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage27` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage28` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage29` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage30` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage31` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage32` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage33` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage34` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage35` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage36` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage37` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage38` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage39` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.body.stage40` | ops, workflow, scripts, tests | 2 | 0 |
| `katarina.contracts` | runtime, ops, workflow, research, scripts, tests | 10 | 18 |
| `katarina.contracts.runtime` | runtime, ops, workflow, research, scripts, tests | 11 | 18 |
| `katarina.core` | runtime, ops, workflow, research, scripts, tests | 5 | 8 |
| `katarina.core.component` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.core.lifecycle` | runtime, ops, workflow, research, scripts, tests | 3 | 1 |
| `katarina.core.message_bus` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.core.orchestrator` | runtime, ops, workflow, research, scripts, tests | 2 | 3 |
| `katarina.core.queue` | runtime, ops, workflow, research, scripts, tests | 1 | 1 |
| `katarina.core.readiness` | runtime, ops, workflow, research, scripts, tests | 5 | 5 |
| `katarina.core.state` | runtime, ops, workflow, research, scripts, tests | 1 | 0 |
| `katarina.engines` | runtime, ops, workflow, research, scripts, tests | 23 | 48 |
| `katarina.engines.adaptive_risk` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.engines.adaptive_scalper` | runtime, ops, workflow, research, scripts, tests | 2 | 7 |
| `katarina.engines.broker_aware_sizing` | workflow, tests | 0 | 3 |
| `katarina.engines.capital` | runtime, ops, workflow, research, scripts, tests | 1 | 7 |
| `katarina.engines.decision` | workflow, research, scripts, tests | 1 | 7 |
| `katarina.engines.demo_execution` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.engines.evaluation` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.execution` | workflow, scripts, tests | 3 | 7 |
| `katarina.engines.execution_recovery` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.engines.exposure` | workflow, scripts, tests | 2 | 3 |
| `katarina.engines.manual_risk` | runtime, ops, workflow, research, scripts, tests | 6 | 9 |
| `katarina.engines.portfolio` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.position` | runtime, ops, workflow, scripts, tests | 3 | 8 |
| `katarina.engines.risk` | runtime, ops, workflow, research, scripts, tests | 7 | 26 |
| `katarina.engines.scalper_entry` | workflow, research, scripts, tests | 3 | 8 |
| `katarina.engines.sizing` | workflow, research, scripts, tests | 0 | 7 |
| `katarina.engines.stress` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance` | runtime, ops, workflow, scripts, tests | 2 | 10 |
| `katarina.governance.ci` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.constitution` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.evolution` | workflow, scripts, tests | 0 | 4 |
| `katarina.governance.external_model_bridge` | workflow, tests | 0 | 1 |
| `katarina.governance.live_validation` | workflow, scripts, tests | 0 | 5 |
| `katarina.governance.models` | workflow, scripts, tests | 0 | 3 |
| `katarina.governance.multi_model_evolution_review` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.health` | runtime, ops, workflow, scripts, tests | 1 | 6 |
| `katarina.health.engine` | runtime, ops, workflow, scripts, tests | 2 | 6 |
| `katarina.host` | runtime, ops, workflow, scripts, tests | 2 | 7 |
| `katarina.intelligence` | runtime, ops, workflow, research, scripts, tests | 63 | 189 |
| `katarina.intelligence.adaptive_brain_v2` | runtime, ops, workflow, research, scripts, tests | 3 | 6 |
| `katarina.intelligence.adaptive_regime` | runtime, ops, workflow, research, scripts, tests | 5 | 10 |
| `katarina.intelligence.adaptive_strategy_library` | workflow, research, tests | 0 | 5 |
| `katarina.intelligence.adaptive_walkforward` | workflow, research, tests | 1 | 5 |
| `katarina.intelligence.analog_feature_schema` | ops, research, tests | 1 | 1 |
| `katarina.intelligence.assistant_cycle` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.intelligence.auto_calibration` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.autonomous_research` | runtime, ops, workflow, scripts, tests | 2 | 10 |
| `katarina.intelligence.autonomous_strategy_discovery` | workflow, research, tests | 0 | 3 |
| `katarina.intelligence.brain_observer` | runtime, ops, workflow, scripts, tests | 2 | 9 |
| `katarina.intelligence.brain_runtime_control` | runtime, ops, workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.broker_account_monitor` | runtime, ops, workflow, scripts, tests | 3 | 5 |
| `katarina.intelligence.broker_clock_alignment` | runtime, ops, workflow, research, scripts, tests | 1 | 6 |
| `katarina.intelligence.broker_history_coverage` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.broker_scan_universe` | runtime, ops, workflow, research, scripts, tests | 3 | 8 |
| `katarina.intelligence.causal_broker_quotes` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.causal_seasonality` | runtime, ops, workflow, research, scripts, tests | 1 | 2 |
| `katarina.intelligence.closed_swing_structure` | runtime, ops, workflow, research, scripts, tests | 2 | 2 |
| `katarina.intelligence.contextual_decision_intelligence` | runtime, ops, workflow, research, scripts, tests | 3 | 2 |
| `katarina.intelligence.contextual_observation_journal` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.continuous_observation` | runtime, ops, workflow, scripts, tests | 0 | 5 |
| `katarina.intelligence.continuous_research_lab` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.data_recovery` | runtime, ops, workflow, scripts, tests | 4 | 5 |
| `katarina.intelligence.demo_account` | runtime, ops, workflow, scripts, tests | 1 | 0 |
| `katarina.intelligence.demo_forward` | runtime, ops, workflow, scripts, tests | 2 | 4 |
| `katarina.intelligence.demo_strategy` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.directional_consensus` | runtime, ops, workflow, research, scripts, tests | 1 | 1 |
| `katarina.intelligence.economics` | workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.evidence_risk` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.explainable_market_decision` | runtime, ops, workflow, research, scripts, tests | 1 | 0 |
| `katarina.intelligence.file_housekeeping` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.foundation_readiness` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.historical_analog_memory` | ops, research, tests | 0 | 6 |
| `katarina.intelligence.independent_demo_worker` | runtime, scripts, tests | 0 | 2 |
| `katarina.intelligence.learning` | workflow, scripts, tests | 0 | 3 |
| `katarina.intelligence.market` | workflow, scripts, tests | 0 | 4 |
| `katarina.intelligence.market_article_context` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.market_decision_brain_v3` | runtime, ops, workflow, research, scripts, tests | 3 | 4 |
| `katarina.intelligence.market_decision_pipeline` | runtime, ops, workflow, research, scripts, tests | 7 | 17 |
| `katarina.intelligence.network_doctor` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.intelligence.news_intelligence` | runtime, ops, workflow, research, scripts, tests | 6 | 6 |
| `katarina.intelligence.observational_associations` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.official_cache_provenance` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.owner_research_review` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.parallel_storage` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.prospective_shadow_book` | runtime, ops, workflow, scripts, tests | 2 | 8 |
| `katarina.intelligence.prospective_shadow_review` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.public_context` | runtime, ops, workflow, scripts, tests | 4 | 8 |
| `katarina.intelligence.public_language_research` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.intelligence.regime` | workflow, research, scripts, tests | 3 | 8 |
| `katarina.intelligence.research_agenda` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.research_capacity` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.intelligence.research_news_collection` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.research_reports` | runtime, ops, workflow, scripts, tests | 2 | 8 |
| `katarina.intelligence.runtime_evidence` | runtime, ops, workflow, scripts, tests | 2 | 6 |
| `katarina.intelligence.self_evolution_lab` | runtime, ops, workflow, scripts, tests | 3 | 5 |
| `katarina.intelligence.semantic_setup_truth` | runtime, ops, workflow, research, scripts, tests | 2 | 4 |
| `katarina.intelligence.session_gaps` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.simple_ml` | workflow, research, scripts, tests | 1 | 3 |
| `katarina.intelligence.structural_entry_quality` | runtime, ops, workflow, research, scripts, tests | 2 | 6 |
| `katarina.intelligence.structure_exit_plan` | runtime, ops, workflow, research, scripts, tests | 3 | 7 |
| `katarina.intelligence.timeframe` | workflow, scripts, tests | 0 | 4 |
| `katarina.intelligence.unified_adaptive_research_cycle` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.intelligence.unified_brain` | runtime, ops, workflow, scripts, tests | 1 | 19 |
| `katarina.intelligence.unified_cognitive_cycle` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.intelligence.unified_research_handoff` | runtime, ops, workflow, scripts, tests | 4 | 4 |
| `katarina.intelligence.verified_policy_context` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.intelligence.xauusd` | workflow, research, scripts, tests | 1 | 4 |
| `katarina.memory` | runtime, ops, workflow, research, scripts, tests | 7 | 16 |
| `katarina.memory.neuro_link` | runtime, ops, workflow, research, scripts, tests | 3 | 1 |
| `katarina.memory.runtime_state` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.memory.store` | runtime, ops, workflow, research, scripts, tests | 7 | 11 |
| `katarina.monitoring` | runtime, ops, workflow, scripts, tests | 22 | 39 |
| `katarina.monitoring.activity_trace` | runtime, ops, workflow, scripts, tests | 6 | 9 |
| `katarina.monitoring.agent_projection` | runtime, ops, workflow, scripts, tests | 3 | 7 |
| `katarina.monitoring.dashboard` | workflow, scripts, tests | 0 | 3 |
| `katarina.monitoring.entry_feed` | runtime, scripts, tests | 2 | 5 |
| `katarina.monitoring.learning_evidence` | runtime, scripts, tests | 1 | 5 |
| `katarina.monitoring.monitor_publisher` | runtime, tests | 0 | 3 |
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
| `katarina.persistence.recovery` | ops, workflow, scripts, tests | 1 | 0 |
| `katarina.persistence.sqlite_common` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.sqlite_journal` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.stores` | ops, workflow, scripts, tests | 2 | 1 |
| `katarina.policies` | ops, workflow, scripts, tests | 1 | 3 |
| `katarina.policies.risk` | ops, workflow, scripts, tests | 1 | 1 |
| `katarina.policies.strategy` | ops, workflow, scripts, tests | 1 | 2 |
| `katarina.ports` | ops, workflow, scripts, tests | 4 | 2 |
| `katarina.ports.transport` | ops, workflow, scripts, tests | 5 | 2 |
| `katarina.research` | workflow, research, scripts, tests | 3 | 15 |
| `katarina.research.alpha_survival` | workflow, research, tests | 0 | 3 |
| `katarina.research.backtest` | workflow, scripts, tests | 1 | 3 |
| `katarina.research.research` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.robustness` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.shadow` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.walkforward` | workflow, scripts, tests | 0 | 3 |
| `katarina.validation` | runtime, ops, workflow, research, scripts, tests | 4 | 11 |
| `katarina.validation.engine` | runtime, ops, workflow, research, scripts, tests | 5 | 11 |

## B — hanya dipakai tests (19)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.adapters.transport.kat1_execution` | tests | 0 | 1 |
| `katarina.engines.account_risk_state` | tests | 2 | 8 |
| `katarina.engines.broker_risk` | tests | 0 | 3 |
| `katarina.engines.multi_symbol_execution` | tests | 0 | 1 |
| `katarina.intelligence.cost_expectancy` | tests | 0 | 1 |
| `katarina.intelligence.economic_feed` | tests | 0 | 2 |
| `katarina.intelligence.flow_efficiency_index` | tests | 0 | 1 |
| `katarina.intelligence.forward_outcomes` | tests | 0 | 3 |
| `katarina.intelligence.news_consensus` | tests | 0 | 1 |
| `katarina.intelligence.offline_hand_telemetry` | tests | 1 | 1 |
| `katarina.intelligence.regime_research_router` | tests | 0 | 1 |
| `katarina.intelligence.research_exit_lifecycle` | tests | 0 | 1 |
| `katarina.intelligence.strategy_drift` | tests | 1 | 2 |
| `katarina.memory.quarantined_research_memory` | tests | 0 | 1 |
| `katarina.monitoring.operational_dashboard` | tests | 0 | 2 |
| `katarina.research.experimental_strategy_evidence_portfolio` | tests | 0 | 1 |
| `katarina.research.indicator_combinations` | tests | 0 | 1 |
| `katarina.research.owner_structure_candidate` | tests | 0 | 1 |
| `katarina.research.real_tick` | tests | 0 | 1 |

## C — hanya dipakai script non-operasional (riset dll.) (35)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.adapters.mt5_shadow_read_only` | scripts, tests | 2 | 2 |
| `katarina.engines.opportunity` | research, scripts, tests | 3 | 4 |
| `katarina.engines.setup_quality` | research, scripts, tests | 1 | 2 |
| `katarina.intelligence.alternative_symbol_playbooks` | research, tests | 0 | 2 |
| `katarina.intelligence.brain` | research, scripts, tests | 2 | 5 |
| `katarina.intelligence.calendar_history` | research, tests | 0 | 3 |
| `katarina.intelligence.causal_market_replay` | research, tests | 1 | 4 |
| `katarina.intelligence.causal_tick_reconciliation` | research, tests | 0 | 3 |
| `katarina.intelligence.closed_bar_failure_forensics` | research, tests | 0 | 3 |
| `katarina.intelligence.intraday_scalp_research` | research, tests | 1 | 5 |
| `katarina.intelligence.market_regime_intelligence` | research, scripts, tests | 1 | 3 |
| `katarina.intelligence.market_universe` | research, scripts, tests | 2 | 3 |
| `katarina.intelligence.mt5_shadow_cycle` | scripts, tests | 0 | 2 |
| `katarina.intelligence.multi_market_brain` | research, scripts, tests | 4 | 8 |
| `katarina.intelligence.multi_pair_arbitrator` | scripts, tests | 0 | 2 |
| `katarina.intelligence.precommitted_setup_research` | research, tests | 0 | 4 |
| `katarina.intelligence.replay_cost_diagnostics` | research, tests | 0 | 2 |
| `katarina.intelligence.research_readiness_gate` | research, tests | 0 | 2 |
| `katarina.intelligence.research_signal_ablation` | research, tests | 0 | 2 |
| `katarina.intelligence.scalp_pattern_candidates` | research, tests | 0 | 2 |
| `katarina.intelligence.shadow_gold_intraday` | scripts, tests | 1 | 1 |
| `katarina.intelligence.shadow_hypotheses` | research, tests | 1 | 3 |
| `katarina.intelligence.shadow_journal` | scripts, tests | 4 | 3 |
| `katarina.intelligence.shadow_manifest` | scripts, tests | 0 | 2 |
| `katarina.intelligence.shadow_paper_book` | scripts, tests | 2 | 2 |
| `katarina.intelligence.shadow_research_evaluation` | scripts, tests | 0 | 2 |
| `katarina.intelligence.strategy_evidence` | scripts, tests | 3 | 3 |
| `katarina.intelligence.strategy_selector` | research, scripts, tests | 1 | 4 |
| `katarina.intelligence.symbol_playbooks` | research, scripts, tests | 2 | 6 |
| `katarina.intelligence.technical_regime` | research, scripts, tests | 3 | 3 |
| `katarina.intelligence.unified_intraday_gate` | research, tests | 0 | 2 |
| `katarina.monitoring.monitor_relay` | scripts, tests | 0 | 2 |
| `katarina.research.independent_audit` | scripts, tests | 0 | 2 |
| `katarina.research.loss_diagnostics` | research | 0 | 2 |
| `katarina.research.mt5_journal` | research, scripts, tests | 2 | 5 |

## D — tidak terjangkau dari root mana pun (2)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.domain` | — | 0 | 0 |
| `katarina.entrypoints` | — | 0 | 0 |
