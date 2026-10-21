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
| A | dipakai runtime/operasional atau workflow | 222 |
| B | hanya dipakai tests | 21 |
| C | hanya dipakai script non-operasional (riset dll.) | 38 |
| D | tidak terjangkau dari root mana pun | 96 |

Total modul: 377. Dari kategori A, 40 hanya terjangkau lewat workflow (CI/riset terjadwal), bukan entry point runtime atau launcher.

## Root yang dipakai

- **runtime** (5): `katarina_pc.py`, `scripts/ai/publish_runtime_monitor.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_independent_demo_worker.py`
- **ops** (17): `katarina_pc.py`, `ops/bridge/katarina_agent.py`, `scripts/ai/run_contextual_market_observer.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/run_readonly_decisions.py`, `scripts/body/audit_body_framework.py`, `scripts/body/audit_cross_stage_pipeline.py`, `scripts/body/audit_functional_body.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/pc/bind_portable_runtime.py`, `scripts/pc/run_pretrial_acceptance.py`, `scripts/research/probe_current_market_analogs.py`, `scripts/stage07/audit_stage07_final.py`, `scripts/stage07/profile_stage07_transport.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`
- **workflow** (51): `katarina_pc.py`, `scripts/ai/audit_autonomous_shadow.py`, `scripts/ai/audit_self_evolution_runner.py`, `scripts/ai/hf_archive_sync.py`, `scripts/ai/hf_storage_smoke.py`, `scripts/ai/install_hf_archive_test.py`, `scripts/ai/run_hf_archive_sync.py`, `scripts/ai/seal_gemini_secret.py`, `scripts/ai/seal_hf_secret.py`, `scripts/ai/verify_unified_katarina.py`, `scripts/body/audit_body_framework.py`, `scripts/body/audit_functional_body.py`, `scripts/governance/audit_alpha_regime_program.py`, `scripts/governance/audit_branch_inventory.py`, `scripts/governance/audit_constitution_guard.py`, `scripts/governance/audit_dependency_links.py`, `scripts/governance/audit_repo_hygiene.py`, `scripts/governance/audit_stage14_15_research.py`, `scripts/governance/audit_stage16_17_synthetic.py`, `scripts/governance/clean_orphaned_workflow_catalog.py`, `scripts/governance/guarded_branch_cleanup.py`, `scripts/pc/build_pc_test_package.py`, `scripts/pc/verify_environment_recovery.py`, `scripts/protocol/validate_kat1_vectors.py`, `scripts/research/audit_private_alpha_holdout.py`, `scripts/research/broker_entry_diagnostics_v9.py`, `scripts/research/broker_multitf_risk_v10.py`, `scripts/research/frozen_xau_sell_tick_verdict.py`, `scripts/research/github_replay.py`, `scripts/research/public_github_sample_tournament.py`, `scripts/research/public_market_tournament.py`, `scripts/research/run_adaptive_walkforward.py`, `scripts/research/run_autonomous_strategy_discovery.py`, `scripts/research/summarize_public_tournament.py`, `scripts/stage07/audit_stage07_final.py`, `scripts/stage07/audit_stage07_preclearance.py`, `scripts/stage07/configure_mt5_network_allowlist.py`, `scripts/stage07/profile_stage07_transport.py`, `scripts/stage08/audit_stage08_final.py`, `scripts/stage09/audit_stage09_final.py`, `scripts/stage10/audit_stage10_final.py`, `scripts/stage_all/audit_stage_11_40.py`, `scripts/update_hot_news.py`, `src/katarina/adapters/transport/kat1_codec.py`, `src/katarina/adapters/transport/recovery.py`, `src/katarina/adapters/transport/session.py`, `src/katarina/adapters/transport/tcp.py`, `src/katarina/adapters/transport/zmq.py`, `src/katarina/governance/external_model_bridge.py`, `src/katarina/governance/multi_model_evolution_review.py`, `src/katarina/intelligence/cognition/self_evolution_lab.py`

## Otak canonical dan bekas otak berversi

| Modul | Kategori | via | Diimpor modul src |
|---|---|---|---|
| `katarina.intelligence.cognition.unified_brain` | A | runtime, ops, workflow, scripts, tests | `katarina.intelligence.cognition.continuous_observation`, `katarina.intelligence.unified_brain` |
| `katarina.intelligence.cognition.adaptive_observation` | A | runtime, ops, workflow, research, scripts, tests | `katarina.intelligence.adaptive_brain_v2`, `katarina.intelligence.cognition.market_decision_pipeline`, `katarina.intelligence.cognition.unified_adaptive_research_cycle`, `katarina.intelligence.cognition.unified_research_handoff` |
| `katarina.intelligence.cognition.market_decision` | A | runtime, ops, workflow, research, scripts, tests | `katarina.intelligence.cognition.contextual_decision_intelligence`, `katarina.intelligence.cognition.unified_brain`, `katarina.intelligence.lab.causal_market_replay`, `katarina.intelligence.market_decision_brain_v3` |
| `katarina.intelligence.perception.screening` | C | research, scripts, tests | `katarina.intelligence.multi_market_brain`, `katarina.intelligence.perception.market_regime_intelligence`, `katarina.intelligence.perception.scalp_pattern_candidates`, `katarina.intelligence.perception.symbol_playbooks` |
| `katarina.intelligence.cognition.observer` | A | runtime, ops, workflow, scripts, tests | `katarina.intelligence.brain_observer`, `katarina.intelligence.cognition.continuous_observation`, `katarina.intelligence.cognition.unified_brain` |

## A — dipakai runtime/operasional atau workflow (222)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina` | runtime, ops, workflow, research, scripts, tests | 262 | 274 |
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
| `katarina.core` | runtime, ops, workflow, research, scripts, tests | 5 | 9 |
| `katarina.core.component` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.core.lifecycle` | runtime, ops, workflow, research, scripts, tests | 3 | 1 |
| `katarina.core.message_bus` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.core.orchestrator` | runtime, ops, workflow, research, scripts, tests | 2 | 3 |
| `katarina.core.queue` | runtime, ops, workflow, research, scripts, tests | 1 | 2 |
| `katarina.core.readiness` | runtime, ops, workflow, research, scripts, tests | 5 | 5 |
| `katarina.core.state` | runtime, ops, workflow, research, scripts, tests | 1 | 0 |
| `katarina.engines` | runtime, ops, workflow, research, scripts, tests | 22 | 47 |
| `katarina.engines.adaptive_risk` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.engines.adaptive_scalper` | runtime, ops, workflow, research, scripts, tests | 2 | 7 |
| `katarina.engines.broker_aware_sizing` | workflow, tests | 0 | 3 |
| `katarina.engines.capital` | runtime, ops, workflow, research, scripts, tests | 1 | 7 |
| `katarina.engines.decision` | workflow, scripts, tests | 0 | 6 |
| `katarina.engines.demo_execution` | runtime, ops, workflow, scripts, tests | 1 | 1 |
| `katarina.engines.evaluation` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.execution` | workflow, scripts, tests | 3 | 7 |
| `katarina.engines.execution_recovery` | runtime, ops, workflow, scripts, tests | 1 | 3 |
| `katarina.engines.exposure` | workflow, scripts, tests | 2 | 3 |
| `katarina.engines.manual_risk` | runtime, ops, workflow, research, scripts, tests | 6 | 9 |
| `katarina.engines.portfolio` | workflow, scripts, tests | 0 | 3 |
| `katarina.engines.position` | runtime, ops, workflow, scripts, tests | 3 | 8 |
| `katarina.engines.risk` | runtime, ops, workflow, research, scripts, tests | 7 | 26 |
| `katarina.engines.scalper_entry` | workflow, scripts, tests | 3 | 7 |
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
| `katarina.intelligence` | runtime, ops, workflow, research, scripts, tests | 164 | 183 |
| `katarina.intelligence.broker` | runtime, ops, workflow, research, scripts, tests | 17 | 21 |
| `katarina.intelligence.broker.auto_calibration` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.broker.broker_account_monitor` | runtime, ops, workflow, scripts, tests | 4 | 4 |
| `katarina.intelligence.broker.broker_clock_alignment` | runtime, ops, workflow, research, scripts, tests | 2 | 6 |
| `katarina.intelligence.broker.broker_history_coverage` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.broker.broker_scan_universe` | runtime, ops, workflow, research, scripts, tests | 4 | 8 |
| `katarina.intelligence.broker.causal_broker_quotes` | runtime, ops, workflow, scripts, tests | 4 | 3 |
| `katarina.intelligence.broker.data_recovery` | runtime, ops, workflow, scripts, tests | 5 | 1 |
| `katarina.intelligence.cognition` | runtime, ops, workflow, research, scripts, tests | 37 | 50 |
| `katarina.intelligence.cognition.adaptive_observation` | runtime, ops, workflow, research, scripts, tests | 4 | 7 |
| `katarina.intelligence.cognition.assistant_cycle` | runtime, ops, workflow, scripts, tests | 2 | 0 |
| `katarina.intelligence.cognition.brain_runtime_control` | runtime, ops, workflow, scripts, tests | 2 | 3 |
| `katarina.intelligence.cognition.contextual_decision_intelligence` | runtime, ops, workflow, research, scripts, tests | 4 | 2 |
| `katarina.intelligence.cognition.continuous_observation` | runtime, ops, workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.cognition.explainable_market_decision` | runtime, ops, workflow, research, scripts, tests | 2 | 0 |
| `katarina.intelligence.cognition.market_decision` | runtime, ops, workflow, research, scripts, tests | 4 | 5 |
| `katarina.intelligence.cognition.market_decision_pipeline` | runtime, ops, workflow, research, scripts, tests | 8 | 17 |
| `katarina.intelligence.cognition.observer` | runtime, ops, workflow, scripts, tests | 3 | 10 |
| `katarina.intelligence.cognition.owner_research_review` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.cognition.self_evolution_lab` | runtime, ops, workflow, scripts, tests | 4 | 5 |
| `katarina.intelligence.cognition.unified_adaptive_research_cycle` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.cognition.unified_brain` | runtime, ops, workflow, scripts, tests | 2 | 20 |
| `katarina.intelligence.cognition.unified_cognitive_cycle` | runtime, ops, workflow, scripts, tests | 4 | 7 |
| `katarina.intelligence.cognition.unified_research_handoff` | runtime, ops, workflow, scripts, tests | 5 | 4 |
| `katarina.intelligence.demo` | runtime, ops, workflow, scripts, tests | 8 | 8 |
| `katarina.intelligence.demo.demo_account` | runtime, ops, workflow, scripts, tests | 2 | 0 |
| `katarina.intelligence.demo.demo_forward` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.demo.demo_strategy` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.demo.independent_demo_worker` | runtime, scripts, tests | 1 | 2 |
| `katarina.intelligence.lab` | runtime, ops, workflow, research, scripts, tests | 33 | 48 |
| `katarina.intelligence.lab.adaptive_strategy_library` | workflow, research, tests | 1 | 5 |
| `katarina.intelligence.lab.adaptive_walkforward` | workflow, research, tests | 2 | 5 |
| `katarina.intelligence.lab.autonomous_research` | runtime, ops, workflow, scripts, tests | 3 | 8 |
| `katarina.intelligence.lab.autonomous_strategy_discovery` | workflow, research, tests | 1 | 3 |
| `katarina.intelligence.lab.continuous_research_lab` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.lab.evidence_risk` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.lab.research_capacity` | runtime, ops, workflow, scripts, tests | 4 | 6 |
| `katarina.intelligence.lab.research_reports` | runtime, ops, workflow, scripts, tests | 3 | 3 |
| `katarina.intelligence.news` | runtime, ops, workflow, research, scripts, tests | 22 | 21 |
| `katarina.intelligence.news.market_article_context` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.news.news_intelligence` | runtime, ops, workflow, research, scripts, tests | 7 | 5 |
| `katarina.intelligence.news.official_cache_provenance` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.news.public_context` | runtime, ops, workflow, scripts, tests | 5 | 8 |
| `katarina.intelligence.news.public_language_research` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.news.research_agenda` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.intelligence.news.research_news_collection` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.intelligence.news.verified_policy_context` | runtime, ops, workflow, scripts, tests | 4 | 2 |
| `katarina.intelligence.operations` | runtime, ops, workflow, scripts, tests | 10 | 8 |
| `katarina.intelligence.operations.file_housekeeping` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.operations.foundation_readiness` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.operations.network_doctor` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.operations.parallel_storage` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.operations.runtime_evidence` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.intelligence.perception` | runtime, ops, workflow, research, scripts, tests | 52 | 63 |
| `katarina.intelligence.perception.adaptive_regime` | runtime, ops, workflow, research, scripts, tests | 6 | 10 |
| `katarina.intelligence.perception.analog_feature_schema` | ops, research, tests | 2 | 1 |
| `katarina.intelligence.perception.causal_seasonality` | runtime, ops, workflow, research, scripts, tests | 2 | 2 |
| `katarina.intelligence.perception.closed_swing_structure` | runtime, ops, workflow, research, scripts, tests | 3 | 2 |
| `katarina.intelligence.perception.directional_consensus` | runtime, ops, workflow, research, scripts, tests | 2 | 1 |
| `katarina.intelligence.perception.economics` | workflow, scripts, tests | 2 | 4 |
| `katarina.intelligence.perception.historical_analog_memory` | ops, research, tests | 1 | 6 |
| `katarina.intelligence.perception.learning` | workflow, scripts, tests | 1 | 3 |
| `katarina.intelligence.perception.market` | workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.perception.observational_associations` | runtime, ops, workflow, scripts, tests | 2 | 2 |
| `katarina.intelligence.perception.regime` | workflow, scripts, tests | 3 | 7 |
| `katarina.intelligence.perception.semantic_setup_truth` | runtime, ops, workflow, research, scripts, tests | 3 | 4 |
| `katarina.intelligence.perception.session_gaps` | runtime, ops, workflow, scripts, tests | 3 | 1 |
| `katarina.intelligence.perception.simple_ml` | workflow, scripts, tests | 1 | 3 |
| `katarina.intelligence.perception.structural_entry_quality` | runtime, ops, workflow, research, scripts, tests | 3 | 6 |
| `katarina.intelligence.perception.structure_exit_plan` | runtime, ops, workflow, research, scripts, tests | 4 | 7 |
| `katarina.intelligence.perception.timeframe` | workflow, scripts, tests | 1 | 4 |
| `katarina.intelligence.perception.xauusd` | workflow, scripts, tests | 2 | 4 |
| `katarina.intelligence.shadow` | runtime, ops, workflow, research, scripts, tests | 21 | 20 |
| `katarina.intelligence.shadow.contextual_observation_journal` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.intelligence.shadow.prospective_shadow_book` | runtime, ops, workflow, scripts, tests | 3 | 8 |
| `katarina.intelligence.shadow.prospective_shadow_review` | runtime, ops, workflow, scripts, tests | 3 | 2 |
| `katarina.memory` | runtime, ops, workflow, scripts, tests | 6 | 16 |
| `katarina.memory.neuro_link` | runtime, ops, workflow, scripts, tests | 2 | 1 |
| `katarina.memory.runtime_state` | runtime, ops, workflow, scripts, tests | 1 | 2 |
| `katarina.memory.store` | runtime, ops, workflow, scripts, tests | 7 | 11 |
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
| `katarina.persistence.recovery` | ops, workflow, scripts, tests | 1 | 0 |
| `katarina.persistence.sqlite_common` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.sqlite_journal` | ops, workflow, scripts, tests | 3 | 1 |
| `katarina.persistence.stores` | ops, workflow, scripts, tests | 2 | 1 |
| `katarina.policies` | ops, workflow, scripts, tests | 1 | 3 |
| `katarina.policies.risk` | ops, workflow, scripts, tests | 1 | 1 |
| `katarina.policies.strategy` | ops, workflow, scripts, tests | 1 | 2 |
| `katarina.ports` | ops, workflow, scripts, tests | 4 | 2 |
| `katarina.ports.transport` | ops, workflow, scripts, tests | 5 | 2 |
| `katarina.research` | workflow, research, scripts, tests | 1 | 9 |
| `katarina.research.alpha_survival` | workflow, research, tests | 0 | 3 |
| `katarina.research.backtest` | workflow, scripts, tests | 1 | 3 |
| `katarina.research.research` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.robustness` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.shadow` | workflow, scripts, tests | 0 | 3 |
| `katarina.research.walkforward` | workflow, scripts, tests | 0 | 3 |
| `katarina.validation` | runtime, ops, workflow, research, scripts, tests | 4 | 11 |
| `katarina.validation.engine` | runtime, ops, workflow, research, scripts, tests | 5 | 11 |

## B — hanya dipakai tests (21)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.adapters.transport.kat1_execution` | tests | 0 | 1 |
| `katarina.engines.account_risk_state` | tests | 2 | 8 |
| `katarina.engines.broker_risk` | tests | 0 | 3 |
| `katarina.engines.multi_symbol_execution` | tests | 0 | 1 |
| `katarina.engines.opportunity` | tests | 2 | 3 |
| `katarina.engines.setup_quality` | tests | 0 | 1 |
| `katarina.intelligence.demo.forward_outcomes` | tests | 1 | 3 |
| `katarina.intelligence.lab.offline_hand_telemetry` | tests | 2 | 1 |
| `katarina.intelligence.lab.regime_research_router` | tests | 1 | 1 |
| `katarina.intelligence.lab.research_exit_lifecycle` | tests | 1 | 1 |
| `katarina.intelligence.lab.strategy_selector` | tests | 1 | 1 |
| `katarina.intelligence.news.economic_feed` | tests | 1 | 2 |
| `katarina.intelligence.news.news_consensus` | tests | 1 | 1 |
| `katarina.intelligence.perception.cost_expectancy` | tests | 1 | 1 |
| `katarina.intelligence.perception.flow_efficiency_index` | tests | 1 | 1 |
| `katarina.intelligence.shadow.strategy_drift` | tests | 2 | 2 |
| `katarina.memory.quarantined_research_memory` | tests | 0 | 1 |
| `katarina.monitoring.operational_dashboard` | tests | 0 | 2 |
| `katarina.research.experimental_strategy_evidence_portfolio` | tests | 0 | 1 |
| `katarina.research.owner_structure_candidate` | tests | 0 | 1 |
| `katarina.research.real_tick` | tests | 0 | 1 |

## C — hanya dipakai script non-operasional (riset dll.) (38)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.adapters.mt5_shadow_read_only` | scripts, tests | 2 | 2 |
| `katarina.intelligence.autonomous_research` | scripts | 0 | 2 |
| `katarina.intelligence.broker.mt5_shadow_cycle` | scripts, tests | 1 | 2 |
| `katarina.intelligence.broker_account_monitor` | scripts | 0 | 1 |
| `katarina.intelligence.continuous_observation` | scripts | 0 | 1 |
| `katarina.intelligence.data_recovery` | scripts | 0 | 4 |
| `katarina.intelligence.demo_forward` | scripts | 0 | 1 |
| `katarina.intelligence.file_housekeeping` | scripts | 0 | 1 |
| `katarina.intelligence.lab.causal_market_replay` | research, tests | 2 | 4 |
| `katarina.intelligence.lab.causal_tick_reconciliation` | research, tests | 1 | 3 |
| `katarina.intelligence.lab.closed_bar_failure_forensics` | research, tests | 1 | 3 |
| `katarina.intelligence.lab.intraday_scalp_research` | research, tests | 2 | 5 |
| `katarina.intelligence.lab.precommitted_setup_research` | research, tests | 1 | 4 |
| `katarina.intelligence.lab.replay_cost_diagnostics` | research, tests | 1 | 2 |
| `katarina.intelligence.lab.research_readiness_gate` | research, tests | 1 | 2 |
| `katarina.intelligence.lab.research_signal_ablation` | research, tests | 1 | 2 |
| `katarina.intelligence.lab.unified_intraday_gate` | research, tests | 1 | 2 |
| `katarina.intelligence.network_doctor` | scripts | 0 | 1 |
| `katarina.intelligence.perception.alternative_symbol_playbooks` | research, tests | 1 | 2 |
| `katarina.intelligence.perception.calendar_history` | research, tests | 1 | 3 |
| `katarina.intelligence.perception.market_regime_intelligence` | research, scripts, tests | 2 | 3 |
| `katarina.intelligence.perception.market_universe` | research, scripts, tests | 3 | 2 |
| `katarina.intelligence.perception.multi_pair_arbitrator` | scripts, tests | 1 | 2 |
| `katarina.intelligence.perception.scalp_pattern_candidates` | research, tests | 1 | 2 |
| `katarina.intelligence.perception.screening` | research, scripts, tests | 4 | 9 |
| `katarina.intelligence.perception.symbol_playbooks` | research, scripts, tests | 3 | 6 |
| `katarina.intelligence.perception.technical_regime` | research, scripts, tests | 4 | 3 |
| `katarina.intelligence.research_capacity` | scripts | 0 | 1 |
| `katarina.intelligence.research_reports` | scripts | 0 | 5 |
| `katarina.intelligence.runtime_evidence` | scripts | 0 | 4 |
| `katarina.intelligence.shadow.shadow_gold_intraday` | scripts, tests | 2 | 1 |
| `katarina.intelligence.shadow.shadow_hypotheses` | research, tests | 2 | 3 |
| `katarina.intelligence.shadow.shadow_journal` | scripts, tests | 5 | 3 |
| `katarina.intelligence.shadow.shadow_manifest` | scripts, tests | 1 | 2 |
| `katarina.intelligence.shadow.shadow_paper_book` | scripts, tests | 3 | 2 |
| `katarina.intelligence.shadow.shadow_research_evaluation` | scripts, tests | 1 | 2 |
| `katarina.intelligence.shadow.strategy_evidence` | scripts, tests | 4 | 3 |
| `katarina.monitoring.monitor_relay` | scripts, tests | 0 | 2 |

## D — tidak terjangkau dari root mana pun (96)

| Modul | via | Importir src | Importir lain |
|---|---|---|---|
| `katarina.domain` | — | 0 | 0 |
| `katarina.entrypoints` | — | 0 | 0 |
| `katarina.intelligence.adaptive_brain_v2` | — | 0 | 0 |
| `katarina.intelligence.adaptive_regime` | — | 0 | 0 |
| `katarina.intelligence.adaptive_strategy_library` | — | 0 | 0 |
| `katarina.intelligence.adaptive_walkforward` | — | 0 | 0 |
| `katarina.intelligence.alternative_symbol_playbooks` | — | 0 | 0 |
| `katarina.intelligence.analog_feature_schema` | — | 0 | 0 |
| `katarina.intelligence.assistant_cycle` | — | 0 | 0 |
| `katarina.intelligence.auto_calibration` | — | 0 | 0 |
| `katarina.intelligence.autonomous_strategy_discovery` | — | 0 | 0 |
| `katarina.intelligence.brain_observer` | — | 0 | 0 |
| `katarina.intelligence.brain_runtime_control` | — | 0 | 0 |
| `katarina.intelligence.broker_clock_alignment` | — | 0 | 0 |
| `katarina.intelligence.broker_history_coverage` | — | 0 | 0 |
| `katarina.intelligence.broker_scan_universe` | — | 0 | 0 |
| `katarina.intelligence.calendar_history` | — | 0 | 0 |
| `katarina.intelligence.causal_broker_quotes` | — | 0 | 0 |
| `katarina.intelligence.causal_market_replay` | — | 0 | 0 |
| `katarina.intelligence.causal_seasonality` | — | 0 | 0 |
| `katarina.intelligence.causal_tick_reconciliation` | — | 0 | 0 |
| `katarina.intelligence.closed_bar_failure_forensics` | — | 0 | 0 |
| `katarina.intelligence.closed_swing_structure` | — | 0 | 0 |
| `katarina.intelligence.contextual_decision_intelligence` | — | 0 | 0 |
| `katarina.intelligence.contextual_observation_journal` | — | 0 | 0 |
| `katarina.intelligence.continuous_research_lab` | — | 0 | 0 |
| `katarina.intelligence.cost_expectancy` | — | 0 | 0 |
| `katarina.intelligence.demo_account` | — | 0 | 0 |
| `katarina.intelligence.demo_strategy` | — | 0 | 0 |
| `katarina.intelligence.directional_consensus` | — | 0 | 0 |
| `katarina.intelligence.economic_feed` | — | 0 | 0 |
| `katarina.intelligence.economics` | — | 0 | 0 |
| `katarina.intelligence.evidence_risk` | — | 0 | 0 |
| `katarina.intelligence.explainable_market_decision` | — | 0 | 0 |
| `katarina.intelligence.flow_efficiency_index` | — | 0 | 0 |
| `katarina.intelligence.forward_outcomes` | — | 0 | 0 |
| `katarina.intelligence.foundation_readiness` | — | 0 | 0 |
| `katarina.intelligence.historical_analog_memory` | — | 0 | 0 |
| `katarina.intelligence.independent_demo_worker` | — | 0 | 0 |
| `katarina.intelligence.intraday_scalp_research` | — | 0 | 0 |
| `katarina.intelligence.learning` | — | 0 | 0 |
| `katarina.intelligence.market` | — | 0 | 0 |
| `katarina.intelligence.market_article_context` | — | 0 | 0 |
| `katarina.intelligence.market_decision_brain_v3` | — | 0 | 0 |
| `katarina.intelligence.market_decision_pipeline` | — | 0 | 0 |
| `katarina.intelligence.market_regime_intelligence` | — | 0 | 0 |
| `katarina.intelligence.market_universe` | — | 0 | 0 |
| `katarina.intelligence.mt5_shadow_cycle` | — | 0 | 0 |
| `katarina.intelligence.multi_market_brain` | — | 0 | 0 |
| `katarina.intelligence.multi_pair_arbitrator` | — | 0 | 0 |
| `katarina.intelligence.news_consensus` | — | 0 | 0 |
| `katarina.intelligence.news_intelligence` | — | 0 | 0 |
| `katarina.intelligence.observational_associations` | — | 0 | 0 |
| `katarina.intelligence.official_cache_provenance` | — | 0 | 0 |
| `katarina.intelligence.offline_hand_telemetry` | — | 0 | 0 |
| `katarina.intelligence.owner_research_review` | — | 0 | 0 |
| `katarina.intelligence.parallel_storage` | — | 0 | 0 |
| `katarina.intelligence.precommitted_setup_research` | — | 0 | 0 |
| `katarina.intelligence.prospective_shadow_book` | — | 0 | 0 |
| `katarina.intelligence.prospective_shadow_review` | — | 0 | 0 |
| `katarina.intelligence.public_context` | — | 0 | 0 |
| `katarina.intelligence.public_language_research` | — | 0 | 0 |
| `katarina.intelligence.regime` | — | 0 | 0 |
| `katarina.intelligence.regime_research_router` | — | 0 | 0 |
| `katarina.intelligence.replay_cost_diagnostics` | — | 0 | 0 |
| `katarina.intelligence.research_agenda` | — | 0 | 0 |
| `katarina.intelligence.research_exit_lifecycle` | — | 0 | 0 |
| `katarina.intelligence.research_news_collection` | — | 0 | 0 |
| `katarina.intelligence.research_readiness_gate` | — | 0 | 0 |
| `katarina.intelligence.research_signal_ablation` | — | 0 | 0 |
| `katarina.intelligence.scalp_pattern_candidates` | — | 0 | 0 |
| `katarina.intelligence.self_evolution_lab` | — | 0 | 0 |
| `katarina.intelligence.semantic_setup_truth` | — | 0 | 0 |
| `katarina.intelligence.session_gaps` | — | 0 | 0 |
| `katarina.intelligence.shadow_gold_intraday` | — | 0 | 0 |
| `katarina.intelligence.shadow_hypotheses` | — | 0 | 0 |
| `katarina.intelligence.shadow_journal` | — | 0 | 0 |
| `katarina.intelligence.shadow_manifest` | — | 0 | 0 |
| `katarina.intelligence.shadow_paper_book` | — | 0 | 0 |
| `katarina.intelligence.shadow_research_evaluation` | — | 0 | 0 |
| `katarina.intelligence.simple_ml` | — | 0 | 0 |
| `katarina.intelligence.strategy_drift` | — | 0 | 0 |
| `katarina.intelligence.strategy_evidence` | — | 0 | 0 |
| `katarina.intelligence.strategy_selector` | — | 0 | 0 |
| `katarina.intelligence.structural_entry_quality` | — | 0 | 0 |
| `katarina.intelligence.structure_exit_plan` | — | 0 | 0 |
| `katarina.intelligence.symbol_playbooks` | — | 0 | 0 |
| `katarina.intelligence.technical_regime` | — | 0 | 0 |
| `katarina.intelligence.timeframe` | — | 0 | 0 |
| `katarina.intelligence.unified_adaptive_research_cycle` | — | 0 | 0 |
| `katarina.intelligence.unified_brain` | — | 0 | 0 |
| `katarina.intelligence.unified_cognitive_cycle` | — | 0 | 0 |
| `katarina.intelligence.unified_intraday_gate` | — | 0 | 0 |
| `katarina.intelligence.unified_research_handoff` | — | 0 | 0 |
| `katarina.intelligence.verified_policy_context` | — | 0 | 0 |
| `katarina.intelligence.xauusd` | — | 0 | 0 |
