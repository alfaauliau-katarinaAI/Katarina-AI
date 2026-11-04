# Indeks reason code Katarina

Dibuat ulang dengan `python scripts/governance/reason_code_index.py --output docs/maintenance/REASON_CODE_INDEX.md`
(analisis statis, tanpa broker/jaringan). Cari satu kode: `python scripts/governance/reason_code_index.py --find KODE`.

## Cara menelusuri error

1. Ambil kode dari log/laporan (`reason`, `error`, `status`, `blocking_reasons`, pesan exception).
2. Cari kode di tabel ini atau dengan `--find`: kolom **Sumber** menunjuk `file:line` yang menghasilkan kode,
   kolom **Tes** menunjuk tes yang memeriksanya. Kode berakhiran `_*` adalah prefiks dinamis (mis. `SHADOW_EVALUATION_FAILED_<Tipe>`).
3. Perbaikan wajib menambah/memperbarui tes yang menyebut kode itu, lalu dicatat di `docs/REPAIR_HISTORY.md` (ID temuan, commit, tes).

Severity mengikuti area sumber: **P0** = risk, eksekusi, broker/jam/identitas, adapter, governance;
**P1** = observer/kognisi, operasi Tahap 0, persistence/memory, demo/shadow, script runtime; **P2** = riset, lab, berita, monitoring, tooling.
Pesan exception mentah tidak dicatat (hanya kode/tipe) agar kredensial tidak bocor.

Ringkasan: 573 kode — P0 101, P1 244, P2 228; 219 disebut di tes, 354 belum.

| Kode | Sev | Area | Sumber | Tes |
|---|---|---|---|---|
| `ACCOUNT_BALANCE_UNAVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_history_coverage.py:45` | `tests/unit/intelligence/test_broker_history_coverage.py` |
| `ACCOUNT_BINDING_NOT_CONFIGURED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:218` | `tests/integration/test_automatic_connection.py` |
| `ACCOUNT_OR_TRADING_PERMISSION_CHANGED` | P0 | intelligence.broker, intelligence.cognition | `src/katarina/intelligence/broker/auto_calibration.py:55`<br>`src/katarina/intelligence/broker/data_recovery.py:83`<br>`src/katarina/intelligence/cognition/continuous_observation.py:179`<br>`src/katarina/intelligence/cognition/continuous_observation.py:249` (+1) | `tests/integration/test_continuous_observation.py`<br>`tests/unit/intelligence/test_data_recovery.py` |
| `ACKNOWLEDGED_LIVE_OFF` | P0 | adapters.brain_feedback, intelligence.cognition | `src/katarina/adapters/brain_feedback.py:40`<br>`src/katarina/intelligence/cognition/unified_brain.py:224` | `tests/integration/test_assistant_pretrial.py`<br>`tests/unit/intelligence/test_runtime_evidence.py` |
| `ACTIVE_RECOVERY` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:47`<br>`src/katarina/intelligence/broker/data_recovery.py:139` | — |
| `AMBIGUOUS_WINDOW_ALIGNMENT` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:138` | `tests/integration/test_auto_calibration.py` |
| `BID_CHART_SOURCE_NOT_VERIFIED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:87` | — |
| `BLOCKED_EXTERNAL_MODEL_PUBLIC_ONLY` | P0 | adapters.continuous_owner_surface | `src/katarina/adapters/continuous_owner_surface.py:21` | `tests/unit/test_public_language_research.py` |
| `BLOCKED_MODEL_NOT_CONFIGURED` | P0 | adapters.continuous_owner_surface | `src/katarina/adapters/continuous_owner_surface.py:25` | `tests/integration/test_unified_owner_surface.py` |
| `BOUNDARY_ERROR` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:146` | — |
| `BROKER_ACCOUNT_SNAPSHOT_DEGRADED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_account_monitor.py:135` | `tests/unit/intelligence/test_broker_account_monitor.py` |
| `BROKER_ACCOUNT_SNAPSHOT_UNVERIFIED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_account_monitor.py:30` | — |
| `BROKER_CATALOG_UNAVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/observer_universe.py:61` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `BROKER_CLOCK_SHIFT_UNVERIFIED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/causal_broker_quotes.py:83` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `BROKER_SERVER_EPOCH_INVALID` | P0 | intelligence.broker | `src/katarina/intelligence/broker/causal_broker_quotes.py:90` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `CALIBRATION_BARS_UNAVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:104` | — |
| `CALIBRATION_STORAGE_REVIEW_REQUIRED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:61` | — |
| `CALIBRATION_WINDOWS_OVERLAP` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:107` | — |
| `CLOCK_BROKER_IDENTITY_MISSING` | P0 | intelligence.broker | `src/katarina/intelligence/broker/live_clock_probe.py:42` | `tests/static/test_reason_code_index.py`<br>`tests/unit/intelligence/test_live_clock_probe.py` |
| `CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:180` | `tests/unit/intelligence/test_clock_evidence_wp13.py` |
| `CLOCK_EVIDENCE_MISSING_OR_INVALID` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:176` | `tests/unit/intelligence/test_clock_evidence_wp13.py` |
| `CLOCK_SNAPSHOT_TOO_LARGE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:81` | — |
| `CLOUD_CAPABILITIES_REJECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:142` | — |
| `CLOUD_CREDENTIAL_UNAVAILABLE` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:89` | — |
| `CLOUD_HTTP_REJECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:108` | — |
| `CLOUD_NOT_CONFIGURED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:200` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `CLOUD_NOT_CONNECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:149`<br>`src/katarina/adapters/readonly_cloud.py:161` | — |
| `CLOUD_READ_REJECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:167` | — |
| `CLOUD_REDIRECT_REJECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:82` | — |
| `CLOUD_RESPONSE_TOO_LARGE` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:111` | — |
| `CLOUD_SESSION_FAULTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:116` | — |
| `CLOUD_SESSION_REJECTED` | P0 | adapters.readonly_cloud | `src/katarina/adapters/readonly_cloud.py:132` | — |
| `CONFLICTING_WINDOW_EVIDENCE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:153` | `tests/integration/test_auto_calibration.py`<br>`tests/integration/test_network_doctor.py` |
| `CONNECTION_LOST_DURING_PASS` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:242` | — |
| `CURRENT_CLOCK_REFERENCE_UNVERIFIED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:85` | — |
| `DEAL_FIELDS_OBSERVED_NOT_FULL_RISK_LEDGER` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_history_coverage.py:80` | `tests/unit/intelligence/test_broker_history_coverage.py`<br>`tests/unit/intelligence/test_foundation_readiness.py` |
| `DEMO_*` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:219` | `tests/integration/test_assistant_pretrial.py`<br>`tests/integration/test_brain_owned_workflow.py`<br>`tests/integration/test_demo_forward_runtime.py` (+16) |
| `DEMO_BINDING_REQUIRED` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:58` | — |
| `DEMO_BOOK_RECONCILED` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:297` | — |
| `DEMO_CLOSE_*` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:350`<br>`src/katarina/engines/demo_execution.py:350` | — |
| `DEMO_CLOSE_ALREADY_RESERVED` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:328` | — |
| `DEMO_CLOSE_BOOK_UNAVAILABLE` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:320` | — |
| `DEMO_CLOSE_EVIDENCE_INVALID` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:313` | — |
| `DEMO_OWNERSHIP_UNVERIFIED` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:317`<br>`src/katarina/engines/demo_execution.py:323` | — |
| `DUPLICATE_*` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:187` | `tests/unit/engines/test_demo_execution.py`<br>`tests/unit/intelligence/test_prospective_shadow_book.py`<br>`tests/unit/research/test_demo_readiness.py` (+1) |
| `EXPLICIT_UTC_REQUIRED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:51` | — |
| `FX_MARKET_CLOSED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:170` | `tests/unit/intelligence/test_clock_evidence_wp13.py`<br>`tests/unit/intelligence/test_synthetic_clock_fixture.py` |
| `HISTORICAL_ANCHOR_NOT_AVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:99` | — |
| `HISTORICAL_DEALS_UNAVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_history_coverage.py:21` | `tests/unit/intelligence/test_foundation_readiness.py` |
| `HISTORICAL_SHIFT_REQUIRES_PROOF` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:90` | — |
| `HISTORY_RESEARCH_ONLY` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:122` | `tests/unit/intelligence/test_data_recovery.py` |
| `HOST_UTC_STEP_DETECTED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/live_clock_probe.py:48`<br>`src/katarina/intelligence/broker/live_clock_probe.py:87` | `tests/unit/intelligence/test_host_clock_probe.py`<br>`tests/unit/intelligence/test_live_clock_probe.py` |
| `IDENTITY_CHECK_FAILED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:102` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INPUTS_READY_AWAIT_OBSERVATION` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:115` | — |
| `INPUTS_READY_RECHECK` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:115` | — |
| `INSUFFICIENT_FRESH_QUOTES` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:216` | `tests/unit/intelligence/test_clock_evidence_wp13.py` |
| `INTEGRATED_OFFLINE_ENGINEERING_ONLY` | P0 | governance.unified_verification | `src/katarina/governance/unified_verification.py:264` | `tests/integration/test_master_design_traceability.py`<br>`tests/integration/test_unified_katarina_stack.py` |
| `INVALID_OBSERVER_CORE_SYMBOLS` | P0 | intelligence.broker | `src/katarina/intelligence/broker/observer_universe.py:29` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INVALID_OBSERVER_ROTATING_SLOTS` | P0 | intelligence.broker | `src/katarina/intelligence/broker/observer_universe.py:33` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INVALID_OBSERVER_ROTATION` | P0 | intelligence.broker | `src/katarina/intelligence/broker/observer_universe.py:72` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INVALID_OBSERVER_UNIVERSE` | P0 | adapters.automatic_connection, intelligence.broker, intelligence.cognition | `src/katarina/adapters/automatic_connection.py:215`<br>`src/katarina/intelligence/broker/observer_universe.py:59`<br>`src/katarina/intelligence/cognition/continuous_observation.py:47`<br>`src/katarina/intelligence/cognition/unified_brain.py:109` (+1) | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INVALID_OBSERVER_UNIVERSE_CONFIG` | P0 | intelligence.broker | `src/katarina/intelligence/broker/observer_universe.py:41`<br>`src/katarina/intelligence/broker/observer_universe.py:46` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `INVALID_OR_NONCAUSAL_TICKS` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:19` | — |
| `INVALID_PRICE_GRID` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:24` | — |
| `LIVE_FEED_CLOCK_VERIFIED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/live_clock_probe.py:118`<br>`src/katarina/intelligence/broker/live_clock_probe.py:119` | `tests/unit/intelligence/test_live_clock_probe.py` |
| `LOCAL_BINDING_UNAVAILABLE` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:141` | — |
| `LOCAL_CONNECT_FAILED` | P0 | adapters.automatic_connection, intelligence.cognition | `src/katarina/adapters/automatic_connection.py:129`<br>`src/katarina/intelligence/cognition/continuous_observation.py:245` | `tests/integration/test_continuous_observation.py`<br>`tests/unit/adapters/test_p0_reason_codes_production_path.py`<br>`tests/unit/intelligence/test_data_health.py` (+2) |
| `LOCAL_FEEDBACK_REJECTED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:163` | — |
| `LOCAL_NOT_CONNECTED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:152`<br>`src/katarina/adapters/automatic_connection.py:175` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `LOCAL_READ_FAILED` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:189` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `MALFORMED_DEAL_HISTORY` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_history_coverage.py:60`<br>`src/katarina/intelligence/broker/broker_history_coverage.py:63` | `tests/unit/intelligence/test_broker_history_coverage.py` |
| `MATCHED_WINDOW_ALIGNMENT` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:136` | `tests/integration/test_auto_calibration.py` |
| `MODEL_CONTEXT_TOO_LARGE` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:142` | — |
| `MODEL_CREDENTIAL_REQUIRED` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:107` | — |
| `MODEL_CREDENTIAL_UNAVAILABLE` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:105` | `tests/unit/test_public_language_research.py` |
| `MODEL_HTTP_*` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:122`<br>`src/katarina/adapters/dialog_model.py:122` | `tests/unit/test_model_provider_concurrency.py` |
| `MODEL_REDIRECT_REJECTED` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:24` | — |
| `MODEL_REQUEST_FAILED` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:128` | — |
| `MODEL_REQUEST_TIMEOUT` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:126` | — |
| `MODEL_RESPONSE_INVALID` | P0 | adapters.dialog_model | `src/katarina/adapters/dialog_model.py:172` | — |
| `MORE_BROKER_EVIDENCE_REQUIRED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:139`<br>`src/katarina/intelligence/broker/auto_calibration.py:143` | `tests/integration/test_auto_calibration.py` |
| `NOT_ATTESTED` | P0 | intelligence.broker, intelligence.lab, monitoring.entry_feed, monitoring.learning_evidence, monitoring.pair_activity, monitoring.position_feed, monitoring.public_research, monitoring.public_runtime, monitoring.research_growth, monitoring.research_health, monitoring.research_lab_status | `src/katarina/intelligence/broker/broker_account_monitor.py:39`<br>`src/katarina/intelligence/broker/data_recovery.py:135`<br>`src/katarina/intelligence/broker/data_recovery.py:138`<br>`src/katarina/intelligence/broker/data_recovery.py:144` (+22) | `tests/unit/intelligence/test_data_recovery.py`<br>`tests/unit/test_agent_projection.py`<br>`tests/unit/test_entry_feed.py` (+8) |
| `NO_CALIBRATION_TARGETS` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:63` | — |
| `NO_TRUSTED_HOST_CLOCK` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:154`<br>`src/katarina/intelligence/broker/broker_clock_alignment.py:163`<br>`src/katarina/intelligence/broker/live_clock_probe.py:71` | `tests/integration/test_continuous_observation.py`<br>`tests/unit/intelligence/test_clock_evidence_wp13.py`<br>`tests/unit/intelligence/test_live_clock_probe.py` (+1) |
| `NO_VALID_CONFIGURED_CONNECTION` | P0 | adapters.automatic_connection | `src/katarina/adapters/automatic_connection.py:247` | `tests/unit/adapters/test_p0_reason_codes_production_path.py` |
| `OBSERVER_STATE_NOT_CONFIGURED` | P0 | adapters.continuous_owner_surface | `src/katarina/adapters/continuous_owner_surface.py:42` | — |
| `OWNER_STOP_REQUEST` | P0 | intelligence.broker, intelligence.cognition | `src/katarina/intelligence/broker/auto_calibration.py:53`<br>`src/katarina/intelligence/broker/auto_calibration.py:113`<br>`src/katarina/intelligence/cognition/continuous_observation.py:106` | `tests/integration/test_auto_calibration.py`<br>`tests/integration/test_continuous_observation.py`<br>`tests/integration/test_demo_forward_runtime.py` (+1) |
| `QUARANTINED_UNEXPLAINED_SHIFT_JUMP` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_clock_alignment.py:230`<br>`src/katarina/intelligence/broker/live_clock_probe.py:111`<br>`src/katarina/intelligence/broker/live_clock_probe.py:113` | `tests/unit/intelligence/test_clock_evidence_wp13.py`<br>`tests/unit/intelligence/test_live_clock_probe.py` |
| `RETRY_SCHEDULED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:87` | — |
| `RISK_GOVERNOR_*` | P0 | engines.demo_execution | `src/katarina/engines/demo_execution.py:169` | `tests/unit/engines/test_demo_execution.py` |
| `SENSOR_READ_FAILED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:87` | — |
| `STALE_CLOSED_BARS` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:114` | `tests/unit/intelligence/test_data_recovery.py` |
| `STALE_QUOTES` | P0 | intelligence.broker | `src/katarina/intelligence/broker/live_clock_probe.py:97`<br>`src/katarina/intelligence/broker/live_clock_probe.py:100` | `tests/unit/intelligence/test_data_health.py`<br>`tests/unit/intelligence/test_live_clock_probe.py`<br>`tests/unit/intelligence/test_stage0_breakdown.py` |
| `SYMBOL_CLOSE_ONLY` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:95` | `tests/unit/intelligence/test_data_recovery.py` |
| `SYMBOL_DISABLED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:94` | `tests/unit/intelligence/test_data_recovery.py` |
| `TICK_COVERAGE_UNAVAILABLE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:14` | — |
| `UNAVAILABLE_OR_OVERSIZE` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:63` | — |
| `UNKNOWN_TRADE_DEAL_ENTRY` | P0 | intelligence.broker | `src/katarina/intelligence/broker/broker_history_coverage.py:71` | — |
| `WAIT_BROKER_PERMISSION` | P0 | intelligence.broker | `src/katarina/intelligence/broker/data_recovery.py:121` | `tests/unit/intelligence/test_data_recovery.py` |
| `WAIT_CALIBRATION_INTERVAL` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:58` | `tests/integration/test_auto_calibration.py` |
| `WINDOW_NOT_CLOSED` | P0 | intelligence.broker | `src/katarina/intelligence/broker/auto_calibration.py:13` | — |
| `ALL_PROPOSALS_DUPLICATE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:265` | `tests/unit/intelligence/test_prospective_shadow_book.py` |
| `ANONYMOUS_ACCESS_ALLOWED` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:54` | — |
| `ANONYMOUS_CHECK_INCONCLUSIVE` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:57` | — |
| `ANSWERED_UNVERIFIED_MODEL_TEXT` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/assistant_cycle.py:73` | `tests/integration/test_dialog_readiness_kit.py` |
| `ARCHIVE_CHECKSUM_MISMATCH` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:218`<br>`scripts/ai/hf_archive_sync.py:250`<br>`scripts/ai/hf_archive_sync.py:256` | — |
| `ARCHIVE_SIZE_EXCEEDED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:238` | — |
| `ARCHIVE_STREAM_INCOMPLETE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:248` | — |
| `ARCHIVE_WAITING_DISK_RESERVE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:353` | — |
| `AS_OF_MUST_BE_AFTER_CUTOFF` | P1 | scripts/ai | `scripts/ai/diagnose_stage0_cutoff.py:42` | — |
| `AWAIT_MATURE_PROSPECTIVE_OUTCOMES` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:332` | — |
| `BACKUP_CURRENT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:553` | — |
| `BACKUP_INTEGRITY_FAILED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:465` | — |
| `BACKUP_SOURCE_MISSING` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:550` | — |
| `BACKUP_WAITING_DISK_RESERVE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:445` | — |
| `BRAIN_FEEDBACK_ACK_REJECTED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:221` | — |
| `BROKER_CATALOG_NOT_FOUND` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:301` | — |
| `BROKER_NOT_CONNECTED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:117`<br>`src/katarina/intelligence/cognition/unified_brain.py:283` | — |
| `BROKER_SHIFT_CHANGED_DURING_DAY` | P1 | intelligence.operations | `src/katarina/intelligence/operations/observation_ledger.py:619` | `tests/unit/intelligence/test_clock_evidence_wp13.py`<br>`tests/unit/intelligence/test_observation_ledger.py`<br>`tests/unit/operations/test_stage0_cutoff_triage.py` |
| `BROKER_TICK_DAYS_TABLE_MISSING` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:720` | — |
| `BROKER_TICK_RECONCILED` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/contextual_observation_journal.py:116` | `tests/unit/intelligence/test_contextual_observer_news.py` |
| `CANDIDATE_BAR_TIMES_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:92` | — |
| `CANDIDATE_BLOCKERS_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:108` | — |
| `CANDIDATE_CARD_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:89` | — |
| `CANDIDATE_CYCLE_MISSING` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:84` | — |
| `CANDIDATE_INPUT_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:79` | — |
| `CANDIDATE_LOOKAHEAD_FORBIDDEN` | P1 | intelligence.operations, scripts/research | `scripts/research/export_candidates.py:157`<br>`src/katarina/intelligence/operations/candidate_ledger.py:95` | — |
| `CANDIDATE_NUMERIC_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:52` | — |
| `CANDIDATE_QUOTE_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:101`<br>`src/katarina/intelligence/operations/candidate_ledger.py:104` | — |
| `CANDIDATE_SIDE_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:111` | — |
| `CANDIDATE_SPREAD_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:116` | — |
| `CANDIDATE_TIME_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/candidate_ledger.py:60`<br>`src/katarina/intelligence/operations/candidate_ledger.py:66` | — |
| `CHECKSUM_MISMATCH` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:48` | — |
| `CLASSIFIED_STAGING_FILE` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:95` | — |
| `CLOCK_EVIDENCE_MISSING_FOR_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:878`<br>`src/katarina/intelligence/operations/data_health.py:878` | — |
| `CLOUD_RATE_LIMITED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:152`<br>`scripts/ai/hf_archive_sync.py:164` | `tests/unit/test_hf_archive_sync.py` |
| `CONFIG_MUST_LIVE_IN_PRIVATE_BASE` | P1 | scripts/ai | `scripts/ai/run_hf_archive_sync.py:18` | — |
| `CONTEXTUAL_OBSERVER_ALREADY_RUNNING` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:70` | `tests/unit/operations/test_wp6_startup.py` |
| `CONTEXT_DB_NOT_FOUND` | P1 | scripts/ai | `scripts/ai/diagnose_stage0_cutoff.py:166` | — |
| `CORE_SYMBOL_UNAVAILABLE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:374` | `tests/integration/test_wp1_observer_universe.py` |
| `CREDENTIAL_PERMISSIONS_REQUIRED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:51` | `tests/unit/test_hf_portable_deployment.py` |
| `CREDENTIAL_SYMLINK_FORBIDDEN` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:48` | — |
| `CROSSED_MARKET` | P1 | validation.engine | `src/katarina/validation/engine.py:507` | `tests/unit/validation/test_stage08_validation.py` |
| `CYCLE_FAILURE_WITHOUT_REASON` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:478` | — |
| `CYCLE_GAP_EXCEEDED_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:500`<br>`src/katarina/intelligence/operations/data_health.py:500` | — |
| `DATASET_FILE_MISSING_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:851`<br>`src/katarina/intelligence/operations/data_health.py:851` | — |
| `DATA_GAPS_TABLE_MISSING` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:746` | — |
| `DATA_GAP_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:737`<br>`src/katarina/intelligence/operations/data_health.py:737` | — |
| `DECISION_SHADOW_TABLE_MISSING` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:803` | — |
| `DEMO_ACCOUNT_BALANCE_NOT_RECONCILED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:66` | — |
| `DEMO_ACCOUNT_BASELINE_INVALID` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:74` | — |
| `DEMO_ACCOUNT_BOOK_UNAVAILABLE` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:25` | — |
| `DEMO_ACCOUNT_EPOCH_BINDING_CHANGED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:36` | — |
| `DEMO_ACCOUNT_HISTORY_INVALID` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:45` | — |
| `DEMO_ACCOUNT_HISTORY_UNAVAILABLE_OR_LIMIT` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:43` | — |
| `DEMO_CAPITAL_EXHAUSTED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:30` | — |
| `DEMO_CAPITAL_UNVERIFIED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:28` | — |
| `DEMO_CLOCK_SHIFT_NOT_INTEGER_HOUR` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:147` | — |
| `DEMO_CLOCK_SNAPSHOT_TOO_LARGE` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:138` | — |
| `DEMO_CURRENCY_UNVERIFIED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:32` | — |
| `DEMO_CURRENT_CLOCK_REFERENCE_UNVERIFIED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:146` | — |
| `DEMO_DEAL_COST_FIELDS_UNAVAILABLE` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:59` | — |
| `DEMO_DUPLICATE_DEAL_RECORDS` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:54` | — |
| `DEMO_ENROLMENT_REQUIRES_EMPTY_ACCOUNT_BOOK` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:48` | — |
| `DEMO_EXECUTOR_ALREADY_RUNNING` | P1 | intelligence.demo | `src/katarina/intelligence/demo/independent_demo_worker.py:29` | — |
| `DEMO_FILLING_UNSUPPORTED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:163` | — |
| `DEMO_FILLING_UNVERIFIED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:160` | — |
| `DEMO_FROZEN_DATASET_MISSING` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:119` | — |
| `DEMO_QUOTE_MISSING_OR_STALE` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:155` | — |
| `DEMO_SYMBOL_SPEC_MISSING` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:176` | — |
| `DEMO_UNCLASSIFIED_ACCOUNT_OPERATION` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_account.py:61` | — |
| `DOCTOR_STOP_TIMEOUT` | P1 | intelligence.operations | `src/katarina/intelligence/operations/network_doctor.py:29` | — |
| `DPAPI_FAILED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:128` | — |
| `EVICTION_NOT_ALLOWLISTED_OR_NOT_COLD` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:319` | — |
| `EXPLICIT_LOCAL_DEMO_CONFIGURATION_REQUIRED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_forward.py:30`<br>`src/katarina/intelligence/demo/independent_demo_worker.py:38` | — |
| `FAIL_CLOSED_TRADING_MUST_BE_DISABLED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:121`<br>`src/katarina/intelligence/cognition/unified_brain.py:287` | `tests/integration/test_observer_activity.py` |
| `FAIL_CLOSED_TRADING_PERMISSION_CHANGED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:236` | — |
| `FILE_HASH_MISMATCH_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:861`<br>`src/katarina/intelligence/operations/data_health.py:861` | `tests/unit/operations/test_data_audit_wp14.py`<br>`tests/unit/research/test_context_export.py`<br>`tests/unit/research/test_private_alpha_holdout.py` (+1) |
| `GEMINI_SECRET_FORMAT_INVALID` | P1 | scripts/ai | `scripts/ai/seal_gemini_secret.py:13` | `tests/unit/test_gemini_secret_sealing.py` |
| `GEMINI_SECRET_NOT_CONFIGURED` | P1 | scripts/ai | `scripts/ai/seal_gemini_secret.py:11` | `tests/unit/test_gemini_secret_sealing.py` |
| `GEMINI_SECRET_SEAL_FAILED` | P1 | scripts/ai | `scripts/ai/seal_gemini_secret.py:38` | — |
| `HELD_OUT_VIRTUAL_SCORE_THRESHOLD_REVIEW_ONLY` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:339` | — |
| `HF_ENCRYPTION_FAILED` | P1 | scripts/ai | `scripts/ai/seal_hf_secret.py:16` | — |
| `HF_TOKEN_MISSING` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:19` | — |
| `HF_TOKEN_MISSING_OR_INVALID` | P1 | scripts/ai | `scripts/ai/seal_hf_secret.py:7` | — |
| `HISTORY_INCOMPLETE` | P1 | validation.engine | `src/katarina/validation/engine.py:219` | `tests/unit/validation/test_stage08_validation.py` |
| `HISTORY_INSTRUMENT_MISMATCH` | P1 | validation.engine | `src/katarina/validation/engine.py:251` | — |
| `HISTORY_SEQUENCE_GAP` | P1 | validation.engine | `src/katarina/validation/engine.py:281` | `tests/unit/validation/test_stage08_validation.py` |
| `HISTORY_SPEC_REVISION_MISMATCH` | P1 | validation.engine | `src/katarina/validation/engine.py:260` | — |
| `HISTORY_TIMEFRAME_MISMATCH` | P1 | validation.engine | `src/katarina/validation/engine.py:269` | `tests/unit/validation/test_stage08_validation.py` |
| `HISTORY_TIME_NOT_INCREASING` | P1 | validation.engine | `src/katarina/validation/engine.py:294` | — |
| `HISTORY_WRONG_TOPIC` | P1 | validation.engine | `src/katarina/validation/engine.py:234` | — |
| `HOLDOUT_INSUFFICIENT` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:184` | `tests/unit/intelligence/test_unified_adaptive_research_cycle.py` |
| `HOST_RESOURCE_OR_STATE_BLOCKED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/continuous_observation.py:159`<br>`src/katarina/intelligence/cognition/continuous_observation.py:239` | — |
| `HOUSEKEEPING_CONTROL_LINK` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:53` | — |
| `HOUSEKEEPING_LINK` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:123` | — |
| `HOUSEKEEPING_LINK_OR_NON_DIRECTORY` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:48` | — |
| `HOUSEKEEPING_TARGET_LINK` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:84` | — |
| `HTTP_429` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:163` | `tests/unit/test_model_provider_concurrency.py` |
| `INSUFFICIENT_EVIDENCE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:131` | `tests/integration/test_unified_katarina_stack.py`<br>`tests/unit/intelligence/test_research_reports.py`<br>`tests/unit/intelligence/test_self_evolution_lab.py` (+1) |
| `INSUFFICIENT_SAMPLE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_review.py:55` | `tests/unit/intelligence/test_continuous_research_lab.py`<br>`tests/unit/intelligence/test_observational_associations.py`<br>`tests/unit/intelligence/test_prospective_shadow_review.py` (+3) |
| `INVALID_ACCOUNT_CURRENCY_DIGITS` | P1 | validation.engine | `src/katarina/validation/engine.py:663` | — |
| `INVALID_ACCOUNT_ID` | P1 | validation.engine | `src/katarina/validation/engine.py:626`<br>`src/katarina/validation/engine.py:715`<br>`src/katarina/validation/engine.py:850` | — |
| `INVALID_ACCOUNT_STATE_VALUE` | P1 | validation.engine | `src/katarina/validation/engine.py:638` | — |
| `INVALID_CLOCK_EVIDENCE_IN_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:897`<br>`src/katarina/intelligence/operations/data_health.py:897` | — |
| `INVALID_DECISION_INPUTS_CONFIG` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/decision_inputs.py:69`<br>`src/katarina/intelligence/cognition/decision_inputs.py:78` | — |
| `INVALID_DECISION_INPUTS_MODE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/decision_inputs.py:26` | — |
| `INVALID_DECISION_SHADOW` | P1 | intelligence.operations | `src/katarina/intelligence/operations/observation_ledger.py:253` | — |
| `INVALID_DEMO_BARS` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_strategy.py:55`<br>`src/katarina/intelligence/demo/demo_strategy.py:63` | — |
| `INVALID_DEMO_COST_CHECKS` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_strategy.py:19` | — |
| `INVALID_DEMO_SPREAD` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_strategy.py:70` | — |
| `INVALID_DEMO_STRATEGY` | P1 | intelligence.demo | `src/katarina/intelligence/demo/demo_strategy.py:32` | — |
| `INVALID_DEMO_WORKER_OPTIONS` | P1 | intelligence.demo | `src/katarina/intelligence/demo/independent_demo_worker.py:40` | — |
| `INVALID_EXPECTED_ACCOUNT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:36` | — |
| `INVALID_HF_CREDENTIAL` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:54` | — |
| `INVALID_LOGICAL_SOURCE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:324` | — |
| `INVALID_MARGIN_VALUE` | P1 | validation.engine | `src/katarina/validation/engine.py:650` | — |
| `INVALID_NEWS_DIAGNOSTICS` | P1 | intelligence.operations | `src/katarina/intelligence/operations/observation_ledger.py:184`<br>`src/katarina/intelligence/operations/observation_ledger.py:189`<br>`src/katarina/intelligence/operations/observation_ledger.py:200` | — |
| `INVALID_OHLC_ORDER` | P1 | validation.engine | `src/katarina/validation/engine.py:581` | `tests/unit/validation/test_stage08_validation.py` |
| `INVALID_ORDER_IDENTITY` | P1 | validation.engine | `src/katarina/validation/engine.py:862` | — |
| `INVALID_ORDER_TIME` | P1 | validation.engine | `src/katarina/validation/engine.py:890` | — |
| `INVALID_ORDER_VOLUME` | P1 | validation.engine | `src/katarina/validation/engine.py:903` | `tests/unit/validation/test_stage08_state_semantics.py` |
| `INVALID_PINNED_ARCHIVE_PATH` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:61` | `tests/unit/test_hf_portable_deployment.py` |
| `INVALID_POSITION_IDENTITY` | P1 | validation.engine | `src/katarina/validation/engine.py:727` | — |
| `INVALID_POSITION_SIDE` | P1 | validation.engine | `src/katarina/validation/engine.py:749` | — |
| `INVALID_POSITION_TIME` | P1 | validation.engine | `src/katarina/validation/engine.py:762` | — |
| `INVALID_POSITION_VOLUME` | P1 | validation.engine | `src/katarina/validation/engine.py:774` | — |
| `INVALID_REPOSITORY` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:34` | `tests/unit/test_hf_portable_deployment.py` |
| `INVALID_RESTORE_CHECKSUM` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:415` | — |
| `INVALID_RESTORE_SIZE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:412` | — |
| `INVALID_SOURCE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:315` | — |
| `INVALID_SYMBOL_IDENTITY` | P1 | validation.engine | `src/katarina/validation/engine.py:443` | — |
| `INVALID_SYMBOL_SPEC_SCALE` | P1 | validation.engine | `src/katarina/validation/engine.py:429` | — |
| `INVALID_SYMBOL_SPEC_VALUE` | P1 | validation.engine | `src/katarina/validation/engine.py:415` | — |
| `INVALID_TIMEFRAME` | P1 | validation.engine | `src/katarina/validation/engine.py:555` | — |
| `INVALID_VOLUME_RANGE` | P1 | validation.engine | `src/katarina/validation/engine.py:457` | — |
| `JSON_CAPTURE_LIMIT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:478` | — |
| `MANIFEST_CHECKSUM_MISMATCH` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:294`<br>`scripts/ai/hf_archive_sync.py:388` | — |
| `MANIFEST_FILE_NOT_FOUND` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:815` | — |
| `MANIFEST_HASH_MISMATCH_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:831`<br>`src/katarina/intelligence/operations/data_health.py:831` | — |
| `MANIFEST_READ_ERROR_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:911`<br>`src/katarina/intelligence/operations/data_health.py:911` | — |
| `MEMORY_ARCHIVE_LIMIT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:191`<br>`scripts/ai/hf_archive_sync.py:274`<br>`scripts/ai/hf_archive_sync.py:277` | — |
| `MISSING_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/network_doctor.py:104` | `tests/integration/test_dialog_readiness_kit.py`<br>`tests/integration/test_unified_katarina_stack.py`<br>`tests/static/test_code_change_gate.py` (+17) |
| `MISSING_QUOTE_PATH_BIAS` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_cognitive_cycle.py:183` | — |
| `MISSING_REQUIRED_FIELD` | P1 | validation.engine | `src/katarina/validation/engine.py:1043` | — |
| `MISSING_SERVER_SHIFT_HOURS` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:640` | — |
| `MISSING_SHADOW_MODES_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:788`<br>`src/katarina/intelligence/operations/data_health.py:788` | — |
| `MISSING_SOURCE_TIME` | P1 | validation.engine | `src/katarina/validation/engine.py:321` | `tests/unit/validation/test_stage08_validation.py` |
| `MIXED_DAILY_CLOCK_SHIFTS_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:518`<br>`src/katarina/intelligence/operations/data_health.py:518` | `tests/unit/operations/test_data_audit_wp14.py` |
| `MODEL_NOT_CONFIGURED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:287` | `tests/integration/test_unified_owner_surface.py` |
| `MOVE_NOT_RESTORABLE` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:127` | — |
| `NEGATIVE_OR_UNSTABLE_QUOTE_EVIDENCE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_review.py:57` | — |
| `NEGATIVE_SPREAD_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:580`<br>`src/katarina/intelligence/operations/data_health.py:580` | `tests/unit/operations/test_data_audit_wp14.py` |
| `NEGATIVE_VIRTUAL_OUTCOMES_CONSERVATIVE_QUARANTINE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:344` | — |
| `NON_FINITE_NUMBER` | P1 | validation.engine | `src/katarina/validation/engine.py:364` | `tests/unit/validation/test_stage08_validation.py` |
| `NON_POSITIVE_PRICE` | P1 | validation.engine | `src/katarina/validation/engine.py:499`<br>`src/katarina/validation/engine.py:571`<br>`src/katarina/validation/engine.py:791` | — |
| `NOT_SUPPORTED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:204` | `tests/unit/operations/test_stage0_cutoff_triage.py` |
| `NO_CLOSED_BAR_VALID_HYPOTHESIS` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:233` | — |
| `NO_CYCLES_IN_WINDOW` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:462` | — |
| `NO_DATA` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:430`<br>`src/katarina/intelligence/operations/data_health.py:461`<br>`src/katarina/intelligence/operations/data_health.py:544`<br>`src/katarina/intelligence/operations/data_health.py:687` (+4) | `tests/unit/intelligence/test_data_health.py`<br>`tests/unit/intelligence/test_stage0_since_wp13.py`<br>`tests/unit/operations/test_data_audit_wp14.py` (+3) |
| `NO_ELIGIBLE_BROKER_SYMBOLS` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:319` | — |
| `NO_QUOTES_IN_WINDOW` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:545` | — |
| `NO_SIGNAL` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/contextual_observation_journal.py:57` | `tests/unit/body/test_end_to_end_body.py`<br>`tests/unit/body/test_functional_body.py`<br>`tests/unit/intelligence/test_contextual_observer_news.py` (+1) |
| `NO_SNAPSHOTS_CHECKED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:713` | — |
| `OBSERVATION_LEDGER_MISSING` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:139`<br>`src/katarina/intelligence/operations/data_health.py:431` | — |
| `OBSERVATION_SAFETY_VIOLATION` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/continuous_observation.py:201` | — |
| `ONE_VIRTUAL_PORTFOLIO_POSITION_AT_A_TIME` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:242` | `tests/unit/intelligence/test_prospective_shadow_book.py` |
| `OWNER_APPROVED_RESEARCH_ONLY_ROLLBACK` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_cognitive_cycle.py:377` | — |
| `PARALLEL_STORAGE_UNAVAILABLE` | P1 | intelligence.cognition, intelligence.operations | `src/katarina/intelligence/cognition/continuous_observation.py:150`<br>`src/katarina/intelligence/operations/parallel_storage.py:17` | — |
| `PASS_SYNTHETIC_SOFTWARE_SAFETY_ONLY` | P1 | scripts/ai | `scripts/ai/audit_autonomous_shadow.py:85` | — |
| `PAUSED_CLOUD_QUOTA` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:502` | — |
| `PAYLOAD_NOT_MAPPING` | P1 | validation.engine | `src/katarina/validation/engine.py:1059` | — |
| `POSITIVE_CYCLE_LIMIT_REQUIRED` | P1 | intelligence.demo | `src/katarina/intelligence/demo/independent_demo_worker.py:42` | — |
| `POSITIVE_VIRTUAL_QUOTE_DIAGNOSTIC_ONLY` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_review.py:59` | — |
| `PRICE_OFF_TICK_GRID` | P1 | validation.engine | `src/katarina/validation/engine.py:1024` | `tests/unit/validation/test_stage08_validation.py` |
| `PRIVATE_REPOSITORY_REQUIRED` | P1 | scripts/ai, scripts/deployment | `scripts/ai/hf_archive_sync.py:149`<br>`scripts/deployment/recover_hf_catalog.py:15` | `tests/unit/test_hf_portable_deployment.py` |
| `PROTECTED_SOURCE_EVICTION_FORBIDDEN` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:70` | — |
| `QUARANTINED_UNAUTHENTICATED_RESEARCH_MEMORY` | P1 | memory.quarantined_research_memory | `src/katarina/memory/quarantined_research_memory.py:157` | `tests/unit/memory/test_quarantined_research_memory.py` |
| `RECONCILIATION_MISMATCH_MATCHED_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:705`<br>`src/katarina/intelligence/operations/data_health.py:705` | — |
| `REPOSITORY_NOT_PRIVATE` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:32` | — |
| `RESEARCH_CANDIDATE_REVIEW_REQUIRED` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:192` | `tests/unit/governance/test_external_model_bridge.py`<br>`tests/unit/intelligence/test_self_evolution_lab.py`<br>`tests/unit/intelligence/test_unified_adaptive_research_cycle.py` |
| `RESTARTED_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/network_doctor.py:88` | `tests/integration/test_network_doctor.py` |
| `RESTORED_CACHE_PROTECTED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:332` | `tests/unit/test_hf_archive_sync.py` |
| `RESTORE_CHECKSUM_MISMATCH` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:228`<br>`scripts/ai/hf_archive_sync.py:252`<br>`scripts/ai/hf_archive_sync.py:265` | — |
| `RESTORE_CONFLICT_OR_CONTENT_CHANGED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/file_housekeeping.py:132` | — |
| `RESTORE_DESTINATION_EXISTS` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:420` | — |
| `RESTORE_DESTINATION_REQUIRED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:606` | — |
| `RESTORE_RACE_CONFLICT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:439` | — |
| `RESTORE_SIZE_EXCEEDED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:226`<br>`scripts/ai/hf_archive_sync.py:245`<br>`scripts/ai/hf_archive_sync.py:263` | — |
| `RESTORE_WAITING_DISK_RESERVE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:423` | — |
| `RETRY_PENDING` | P1 | intelligence.demo, intelligence.lab, intelligence.operations, scripts/ai | `scripts/ai/hf_archive_sync.py:515`<br>`scripts/ai/hf_archive_sync.py:531`<br>`scripts/ai/hf_archive_sync.py:570`<br>`src/katarina/intelligence/demo/independent_demo_worker.py:67` (+4) | — |
| `SENSOR_DEPENDENCY_UNAVAILABLE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/continuous_observation.py:187` | — |
| `SHADOW_EVALUATION_FAILED_*` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/observer.py:467` | `tests/static/test_reason_code_index.py` |
| `SHADOW_LEARNING_INVALID_FAIL_CLOSED` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:199` | `tests/unit/intelligence/test_self_evolution_lab.py` |
| `SIMULATED_STOP_QUOTE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:144` | `tests/unit/intelligence/test_prospective_shadow_book.py` |
| `SIMULATED_TARGET_QUOTE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:148` | `tests/unit/intelligence/test_prospective_shadow_book.py` |
| `SIMULATED_TIMED_EXIT_QUOTE` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:152` | `tests/unit/intelligence/test_prospective_shadow_book.py`<br>`tests/unit/intelligence/test_unified_cognitive_cycle.py` |
| `SOURCE_CHANGED` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:279`<br>`scripts/ai/hf_archive_sync.py:356` | — |
| `SOURCE_CHANGED_AFTER_UPLOAD` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:289`<br>`scripts/ai/hf_archive_sync.py:376` | — |
| `SOURCE_CHANGED_BEFORE_EVICTION` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:300`<br>`scripts/ai/hf_archive_sync.py:398` | — |
| `SOURCE_TIME_IN_FUTURE` | P1 | validation.engine | `src/katarina/validation/engine.py:332` | `tests/unit/validation/test_stage08_validation.py` |
| `SQLITE_*` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:93` | `tests/integration/test_unified_katarina_stack.py` |
| `STALE_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/network_doctor.py:105` | `tests/unit/engines/test_demo_execution.py`<br>`tests/unit/intelligence/test_data_health.py`<br>`tests/unit/intelligence/test_data_recovery.py` (+8) |
| `STALE_DATA` | P1 | validation.engine | `src/katarina/validation/engine.py:346` | `tests/unit/validation/test_stage08_validation.py` |
| `STALE_QUOTE_AGE_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:590`<br>`src/katarina/intelligence/operations/data_health.py:590` | — |
| `STALE_SYMBOL_SPEC` | P1 | validation.engine | `src/katarina/validation/engine.py:1005` | `tests/unit/validation/test_stage08_state_semantics.py`<br>`tests/unit/validation/test_stage08_validation.py` |
| `STATE_AND_CREDENTIAL_DIRECTORIES_MUST_DIFFER` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:38` | — |
| `SYMBOL_SPEC_REVISION_ROLLBACK` | P1 | validation.engine | `src/katarina/validation/engine.py:470` | `tests/unit/validation/test_stage08_validation.py` |
| `SYMLINK_SOURCE_FORBIDDEN` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:312` | — |
| `TEST_*` | P1 | intelligence.operations, monitoring.activity_trace, monitoring.pair_activity, monitoring.public_research, monitoring.worker_runtime, scripts/governance | `scripts/governance/code_change_gate.py:252`<br>`src/katarina/intelligence/operations/runtime_evidence.py:43`<br>`src/katarina/monitoring/activity_trace.py:10`<br>`src/katarina/monitoring/pair_activity.py:8` (+2) | `tests/integration/test_assistant_pretrial.py`<br>`tests/integration/test_continuous_observation.py`<br>`tests/integration/test_demo_forward_runtime.py` (+52) |
| `TICK_DAY_STATUS_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:623`<br>`src/katarina/intelligence/operations/data_health.py:623` | — |
| `TICK_FILE_HASH_MISMATCH_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:673`<br>`src/katarina/intelligence/operations/data_health.py:673` | `tests/unit/operations/test_data_audit_wp14.py`<br>`tests/unit/research/test_context_export.py`<br>`tests/unit/research/test_spread_profile.py` |
| `TICK_FILE_HASH_NOT_RECORDED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:662` | `tests/unit/operations/test_data_audit_wp14.py` |
| `TICK_FILE_NOT_FOUND_ON_DISK_*` | P1 | intelligence.operations | `src/katarina/intelligence/operations/data_health.py:688`<br>`src/katarina/intelligence/operations/data_health.py:688` | — |
| `TRAIN_TO_HOLDOUT_SIGN_REVERSAL` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_cognitive_cycle.py:180` | — |
| `UNEXPECTED_ACCOUNT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:140` | `tests/unit/test_hf_portable_deployment.py` |
| `UNEXPECTED_HF_ACCOUNT` | P1 | scripts/ai | `scripts/ai/hf_storage_smoke.py:26` | — |
| `UNKNOWN_ENUM_VALUE` | P1 | validation.engine | `src/katarina/validation/engine.py:935` | `tests/unit/validation/test_stage08_state_semantics.py` |
| `UNKNOWN_SYMBOL_SPEC` | P1 | validation.engine | `src/katarina/validation/engine.py:995` | `tests/unit/validation/test_stage08_validation.py` |
| `UNSTABLE_OR_NEGATIVE_QUOTE_EDGE` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/self_evolution_lab.py:190` | `tests/integration/test_unified_katarina_stack.py`<br>`tests/unit/intelligence/test_self_evolution_lab.py`<br>`tests/unit/intelligence/test_unified_adaptive_research_cycle.py` (+1) |
| `UTC_AWARE_TIME_REQUIRED` | P1 | scripts/ai | `scripts/ai/diagnose_stage0_cutoff.py:33` | `tests/unit/operations/test_stage0_cutoff_triage.py` |
| `VALIDATION_RULE_EXCEPTION` | P1 | validation.engine | `src/katarina/validation/engine.py:183` | `tests/unit/validation/test_stage08_validation.py` |
| `VERIFY_WAITING_DISK_RESERVE` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:371` | — |
| `VIRTUAL_QUOTE_MARKOUT_NOT_BROKER_EXECUTION` | P1 | intelligence.cognition | `src/katarina/intelligence/cognition/unified_brain.py:401` | — |
| `VIRTUAL_UNCLEARED_RESEARCH_ONLY` | P1 | intelligence.shadow | `src/katarina/intelligence/shadow/prospective_shadow_book.py:261` | — |
| `VOLUME_OFF_STEP_GRID` | P1 | validation.engine | `src/katarina/validation/engine.py:962` | — |
| `VOLUME_OUT_OF_RANGE` | P1 | validation.engine | `src/katarina/validation/engine.py:953` | `tests/unit/validation/test_stage08_state_semantics.py` |
| `VPS_PUBLIC_KEY_MISMATCH` | P1 | scripts/ai | `scripts/ai/seal_hf_secret.py:11` | — |
| `WAITING_CLOUD_RATE_LIMIT` | P1 | scripts/ai | `scripts/ai/hf_archive_sync.py:83` | `tests/unit/test_hf_archive_sync.py` |
| `WP6_ACTION_NOT_CANONICAL_LAUNCHER` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:69` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_AUTOLOGON_STATE_UNKNOWN` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:103` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_AUTOLOGON_USER_MISMATCH` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:107` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_BATTERY_POLICY_CAN_STOP` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:83` | — |
| `WP6_EXECUTION_TIME_LIMIT` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:75` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_LAUNCHER_ABANDONED_MUTEX_NOT_HANDLED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:91` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_LAUNCHER_NO_SINGLE_INSTANCE_MUTEX` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:87` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_LAUNCHER_NO_STOP_MARKER` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:85` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_MULTIPLE_INSTANCES_ALLOWED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:71` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_NO_AUTOLOGON` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:105` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_NO_REBOOT_TRIGGER` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:109` | — |
| `WP6_NO_RESTART_ON_FAILURE` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:80` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_SESSION0_MT5_UNVERIFIED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:97` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_TASK_DISABLED` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:65` | `tests/unit/operations/test_wp6_startup.py` |
| `WP6_TASK_XML_INVALID` | P1 | intelligence.operations | `src/katarina/intelligence/operations/startup_task.py:53` | `tests/unit/operations/test_wp6_startup.py` |
| `WRONG_REPOSITORY` | P1 | scripts/ai, scripts/deployment | `scripts/ai/hf_archive_sync.py:408`<br>`scripts/deployment/recover_hf_catalog.py:22` | — |
| `ABSTAIN_DATA_WITHIN_HISTORICAL_TRAINING` | P2 | scripts/research | `scripts/research/probe_current_market_analogs.py:49` | — |
| `ABSTAIN_INVALID_OR_MISSING_REGIME` | P2 | scripts/research | `scripts/research/probe_current_market_analogs.py:42` | `tests/unit/intelligence/test_historical_analog_memory.py` |
| `ABSTAIN_NO_RESOLVED_ANALOGS` | P2 | intelligence.perception | `src/katarina/intelligence/perception/historical_analog_memory.py:86` | `tests/unit/intelligence/test_historical_analog_memory.py` |
| `ABSTAIN_STALE_REGIME` | P2 | scripts/research | `scripts/research/probe_current_market_analogs.py:46` | — |
| `ABSTAIN_UNKNOWN` | P2 | intelligence.perception | `src/katarina/intelligence/perception/historical_analog_memory.py:81` | `tests/unit/intelligence/test_historical_analog_memory.py` |
| `ALLOWLISTED_UNTRACKED_GENERATED_ARTIFACT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:195` | — |
| `ARCHIVE_CLOCK_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:25` | — |
| `AWARE_UTC_REQUIRED` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:17` | `tests/unit/operations/test_session_hypothesis.py` |
| `BAR_FIELD_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:428` | — |
| `BAR_OHLC_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:432` | — |
| `BAR_OHLC_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:410` | — |
| `BAR_OHLC_NONFINITE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:430` | — |
| `BAR_TIME_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:61`<br>`src/katarina/research/bar_clock_evidence.py:415` | — |
| `BAR_VOLUME_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:76`<br>`src/katarina/research/bar_clock_evidence.py:434` | — |
| `BAR_VOLUME_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:412` | — |
| `BATCH_CROSSES_SEGMENTS_OR_UNVERIFIED` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:299` | — |
| `BLOCKED_*` | P2 | research.alpha_survival, scripts/research | `scripts/research/audit_private_alpha_holdout.py:36`<br>`src/katarina/research/alpha_survival.py:67`<br>`src/katarina/research/alpha_survival.py:67` | `tests/integration/test_assistant_pretrial.py`<br>`tests/integration/test_brain_owned_workflow.py`<br>`tests/integration/test_continuous_observation.py` (+23) |
| `BLOCKED_TIMEOUT_OR_RUNTIME` | P2 | scripts/pc | `scripts/pc/run_system_acceptance.py:83` | — |
| `BROKER_BARS_UNAVAILABLE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:532` | `tests/unit/research/test_bar_clock_evidence.py` |
| `BROKER_BAR_CLOCK_NOT_VERIFIED` | P2 | research.dev_dataset | `src/katarina/research/dev_dataset.py:103`<br>`src/katarina/research/dev_dataset.py:106`<br>`src/katarina/research/dev_dataset.py:114`<br>`src/katarina/research/dev_dataset.py:251` | `tests/integration/test_legacy_clock_wp12.py`<br>`tests/static/test_reason_code_index.py`<br>`tests/unit/research/test_dev_dataset_wp8a.py` (+1) |
| `BROKER_BAR_CLOCK_NOT_VERIFIED_WP12` | P2 | intelligence.perception | `src/katarina/intelligence/perception/screening.py:203` | `tests/integration/test_legacy_clock_wp12.py`<br>`tests/static/test_reason_code_index.py` |
| `BROKER_SENSOR_DATA_DEGRADED` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:89` | — |
| `BROKER_TICK_ARCHIVE_INVALID` | P2 | scripts/research | `scripts/research/export_candidates.py:89`<br>`scripts/research/export_candidates.py:116` | — |
| `BROKER_TICK_ARCHIVE_TOO_LARGE` | P2 | scripts/research | `scripts/research/export_candidates.py:112` | — |
| `BROKER_TICK_CLOCK_OR_RECONCILIATION_UNVERIFIED` | P2 | scripts/research | `scripts/research/export_candidates.py:74` | — |
| `BROKER_TICK_COUNT_MISMATCH` | P2 | scripts/research | `scripts/research/export_candidates.py:118` | — |
| `BROKER_TICK_FILE_UNSAFE` | P2 | scripts/research | `scripts/research/export_candidates.py:77`<br>`scripts/research/export_candidates.py:81` | — |
| `BROKER_TICK_GAP_IN_WINDOW` | P2 | research.context_export | `src/katarina/research/context_export.py:130` | `tests/unit/research/test_context_export.py` |
| `BROKER_TICK_HASH_MISMATCH` | P2 | scripts/research | `scripts/research/export_candidates.py:91` | — |
| `BROKER_TICK_HEADER_INVALID` | P2 | scripts/research | `scripts/research/export_candidates.py:97` | — |
| `BROKER_TICK_ROW_INVALID` | P2 | scripts/research | `scripts/research/export_candidates.py:100`<br>`scripts/research/export_candidates.py:105` | — |
| `BROKER_UNAVAILABLE_OFFLINE_ONLY` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:83` | `tests/integration/test_pc_acceptance.py` |
| `CALENDAR_EVIDENCE_EMPTY` | P2 | research.bar_clock_evidence, scripts/research | `scripts/research/build_bar_clock_evidence.py:50`<br>`scripts/research/build_bar_clock_evidence.py:54`<br>`src/katarina/research/bar_clock_evidence.py:313` | `tests/unit/research/test_bar_clock_evidence.py` |
| `CALENDAR_EVIDENCE_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:310` | — |
| `CALENDAR_FILE_NOT_FOUND` | P2 | research.bar_clock_evidence, scripts/research | `scripts/research/build_bar_clock_evidence.py:46`<br>`src/katarina/research/bar_clock_evidence.py:568` | — |
| `CALENDAR_HASH_MISMATCH` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:573` | `tests/unit/research/test_bar_clock_evidence.py` |
| `CALENDAR_ROW_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:319` | — |
| `CALENDAR_SOURCE_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:321` | — |
| `CANDIDATE_DB_MISSING` | P2 | scripts/research | `scripts/research/export_candidates.py:238` | — |
| `CANDIDATE_EXPORT_LIMIT_REACHED` | P2 | scripts/research | `scripts/research/export_candidates.py:144` | — |
| `CANDIDATE_OR_TICK_LEDGER_MISSING` | P2 | scripts/research | `scripts/research/export_candidates.py:136` | — |
| `CANDIDATE_OUTPUT_UNSAFE` | P2 | scripts/research | `scripts/research/export_candidates.py:234` | — |
| `CANDIDATE_PRICE_INVALID` | P2 | scripts/research | `scripts/research/export_candidates.py:164`<br>`scripts/research/export_candidates.py:166` | — |
| `CANDIDATE_RECORDED` | P2 | intelligence.news | `src/katarina/intelligence/news/public_language_research.py:119` | `tests/unit/test_public_language_research.py` |
| `CANONICAL_RUNNER_MISSING` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:81` | — |
| `CATALOG_FAILED` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:61` | — |
| `CATALOG_SAVED` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:55` | — |
| `CLOCK_EVIDENCE_NOT_FOUND` | P2 | scripts/research | `scripts/research/export_dev_bars.py:47` | — |
| `CONNECTION_CONFIG_REQUIRED` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:70` | `tests/integration/test_pc_acceptance.py` |
| `CONTINUATION_*` | P2 | intelligence.perception | `src/katarina/intelligence/perception/market_regime_intelligence.py:168` | `tests/unit/intelligence/test_historical_analog_memory.py`<br>`tests/unit/intelligence/test_market_regime_intelligence.py` |
| `COST_STRESS_*` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:228` | `tests/unit/intelligence/test_prospective_shadow_book.py` |
| `CROSSES_PERIOD_END` | P2 | research.validation | `src/katarina/research/validation.py:309` | `tests/unit/research/test_validation.py`<br>`tests/unit/research/test_validation_guard_codes.py` |
| `DATASET_CHANGED_REVIEW_UNAVAILABLE` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:235` | `tests/unit/intelligence/test_autonomous_research.py`<br>`tests/unit/intelligence/test_research_reports.py` |
| `DATASET_INTEGRITY_FAILED` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:29`<br>`src/katarina/intelligence/lab/autonomous_research.py:39` | `tests/unit/test_research_failure_diagnostics.py` |
| `DATASET_OUTPUT_MUST_BE_OUTSIDE_REPO` | P2 | scripts/research | `scripts/research/export_dev_bars.py:45` | — |
| `DATASET_SHAPE_FAILED` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:41` | — |
| `DEPENDENCY_*` | P2 | scripts/governance | `scripts/governance/code_change_gate.py:197` | `tests/integration/test_environment_recovery.py`<br>`tests/static/test_code_change_gate.py`<br>`tests/unit/operations/test_dependency_links.py` |
| `DESCRIPTIVE_PROFILE_GENERATED` | P2 | scripts/research | `scripts/research/spread_profile.py:47` | — |
| `DEVELOPMENT_BARS_NOT_MONOTONIC` | P2 | research.dev_dataset | `src/katarina/research/dev_dataset.py:152`<br>`src/katarina/research/dev_dataset.py:273` | — |
| `DEVELOPMENT_CHUNK_OVER_LIMIT` | P2 | research.dev_dataset | `src/katarina/research/dev_dataset.py:133` | — |
| `DEVELOPMENT_CONFLICTING_BAR` | P2 | research.dev_dataset | `src/katarina/research/dev_dataset.py:141` | — |
| `DEVELOPMENT_RESEARCH_ONLY` | P2 | scripts/research | `scripts/research/export_candidates.py:247`<br>`scripts/research/simulate_setups.py:51` | — |
| `DIAGNOSTIC_ONLY` | P2 | scripts/research | `scripts/research/blocker_ladder.py:41` | `tests/unit/operations/test_stage0_cutoff_triage.py` |
| `DISCOVERY_COMPLETED_RESEARCH_ONLY` | P2 | scripts/research | `scripts/research/run_autonomous_strategy_discovery.py:117` | — |
| `DUPLICATE_OR_EMPTY_ID` | P2 | research.validation | `src/katarina/research/validation.py:293` | `tests/unit/research/test_validation_guard_codes.py` |
| `ENTRY_IN_GAP` | P2 | research.validation | `src/katarina/research/validation.py:305` | `tests/unit/research/test_validation.py` |
| `ENVIRONMENT_POINTER_INVALID` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:92` | — |
| `ENVIRONMENT_REPAIR_REQUIRED` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:155` | — |
| `EVIDENCE_REPORT_HASH_MISMATCH` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:354` | — |
| `EVIDENCE_REPORT_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:348`<br>`src/katarina/research/bar_clock_evidence.py:356`<br>`src/katarina/research/bar_clock_evidence.py:564` | — |
| `EVIDENCE_REPORT_INVALID_HASH` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:351` | — |
| `EVIDENCE_REPORT_INVALID_JSON` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:561` | — |
| `EVIDENCE_REPORT_NOT_FOUND` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:557` | — |
| `EVIDENCE_REPORT_TIMELINE_NOT_REPRODUCIBLE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:358` | `tests/unit/research/test_bar_clock_evidence.py` |
| `EVIDENCE_SAMPLES_INSUFFICIENT` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:327`<br>`src/katarina/research/bar_clock_evidence.py:360`<br>`src/katarina/research/bar_clock_evidence.py:377` | — |
| `EVIDENCE_SAMPLE_DUPLICATE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:341` | — |
| `EVIDENCE_SAMPLE_INVALID` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:331`<br>`src/katarina/research/bar_clock_evidence.py:334` | — |
| `EVIDENCE_SAMPLE_LINEAGE_MISSING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:336` | `tests/unit/research/test_bar_clock_evidence.py` |
| `EVIDENCE_SAMPLE_OFF_CALENDAR` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:339` | `tests/unit/research/test_bar_clock_evidence.py` |
| `EXISTING_CONFIG_STATE_MISMATCH` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:51` | `tests/unit/test_hf_portable_deployment.py` |
| `EXISTING_CREDENTIAL_DIFFERS_ROTATE_SEPARATELY` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:72` | — |
| `EXISTING_REPOSITORY_DIFFERS_MIGRATE_SEPARATELY` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:47` | — |
| `EXPERIMENT_COMPLETED` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:156` | — |
| `EXPLORATORY_ASSOCIATION_ONLY` | P2 | intelligence.perception | `src/katarina/intelligence/perception/observational_associations.py:17` | — |
| `FAIL_STRATEGY_RESEARCH_EVIDENCE_INTEGRITY` | P2 | scripts/governance | `scripts/governance/audit_stage14_15_research.py:46` | — |
| `FROZEN_DEVELOPMENT_ONLY` | P2 | scripts/research | `scripts/research/export_dev_bars.py:59` | — |
| `FULL_BODY_STORED` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:157` | `tests/unit/intelligence/test_research_news_collection.py` |
| `FUTURE_CACHE_RECEIPT` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:36` | `tests/unit/intelligence/test_official_cache_provenance.py` |
| `GITHUB_API_ACCESS_DENIED_OR_UNAVAILABLE` | P2 | scripts/github | `scripts/github/check_access.py:44` | — |
| `H1_M15_*` | P2 | intelligence.perception | `src/katarina/intelligence/perception/market_regime_intelligence.py:168`<br>`src/katarina/intelligence/perception/market_regime_intelligence.py:170` | `tests/unit/intelligence/test_contextual_decision_intelligence.py`<br>`tests/unit/intelligence/test_directional_consensus.py` |
| `HF_TOKEN_ENVIRONMENT_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:68` | — |
| `HISTORICAL_RESEARCH_ONLY` | P2 | intelligence.lab | `src/katarina/intelligence/lab/adaptive_walkforward.py:311` | `tests/unit/intelligence/test_adaptive_walkforward.py` |
| `HOST_PREFLIGHT_BLOCKED` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:52` | — |
| `HTTP_*` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:160`<br>`src/katarina/intelligence/news/research_news_collection.py:160` | `tests/integration/test_assistant_pretrial.py`<br>`tests/integration/test_automatic_connection.py`<br>`tests/integration/test_unified_owner_surface.py` (+3) |
| `HYPOTHESES_ONLY` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:294` | — |
| `HYPOTHESES_SAVED` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:297` | — |
| `IDENTICAL_CONTENT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:153` | `tests/static/test_safe_cleanup.py` |
| `INSUFFICIENT_COMPLETE_BARS` | P2 | research.context_export | `src/katarina/research/context_export.py:161` | — |
| `INSUFFICIENT_SAMPLES` | P2 | intelligence.perception | `src/katarina/intelligence/perception/observational_associations.py:9` | `tests/unit/intelligence/test_continuous_research_lab.py`<br>`tests/unit/intelligence/test_observational_associations.py`<br>`tests/unit/test_research_memory_export.py` (+1) |
| `INVALID_BROKER_SYMBOL_MAPPING` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:473` | `tests/unit/research/test_bar_clock_evidence.py` |
| `INVALID_DATETIME_FORMAT` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:42` | — |
| `INVALID_DATE_FORMAT` | P2 | research.spread_profile | `src/katarina/research/spread_profile.py:58` | — |
| `INVALID_DATE_RANGE` | P2 | research.spread_profile | `src/katarina/research/spread_profile.py:60` | — |
| `INVALID_INTERVAL` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:50` | — |
| `INVALID_MAX_RELEASES` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:57` | — |
| `INVALID_POLICY` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:28` | — |
| `INVALID_PRICES` | P2 | research.validation | `src/katarina/research/validation.py:297` | `tests/unit/research/test_validation_guard_codes.py` |
| `INVALID_RELEASE_DATETIME` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:491` | — |
| `INVALID_RESEARCH_METHOD` | P2 | intelligence.lab | `src/katarina/intelligence/lab/research_reports.py:27` | — |
| `INVALID_SYMBOL_WINDOWS` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:45` | — |
| `INVALID_TASK_NAME` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:90` | — |
| `INVALID_UTC_TIMESTAMP` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:15` | — |
| `ISOLATED_TERMINAL_ABSOLUTE_PATH_REQUIRED` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:90` | — |
| `ISOLATED_TERMINAL_AUTOTRADING_MUST_BE_OFF` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:125` | — |
| `ISOLATED_TERMINAL_EXE_REQUIRED` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:96` | — |
| `ISOLATED_TERMINAL_IDENTITY_UNAVAILABLE` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:119` | — |
| `ISOLATED_TERMINAL_INITIALIZE_FAILED` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:115` | — |
| `ISOLATED_TERMINAL_MARKER_INVALID` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:107` | — |
| `ISOLATED_TERMINAL_MARKER_REQUIRED` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:101` | — |
| `ISOLATED_TERMINAL_MUST_BE_OUTSIDE_REPO` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:98` | — |
| `ISOLATED_TERMINAL_NOT_FOUND` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:94` | — |
| `ISOLATED_TERMINAL_PATH_MISMATCH` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:123` | — |
| `LATEST_FETCH_NOT_OK` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:40` | `tests/unit/intelligence/test_official_cache_provenance.py` |
| `LOCAL_CONTINUATION_*` | P2 | intelligence.perception | `src/katarina/intelligence/perception/market_regime_intelligence.py:178` | `tests/unit/intelligence/test_market_regime_intelligence.py` |
| `LOGICAL_SOURCE_NOT_FOUND` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:53` | — |
| `LOOKAHEAD_DATA_AFTER_ENTRY` | P2 | research.validation | `src/katarina/research/validation.py:299` | `tests/unit/research/test_validation.py` |
| `MAIN_BRANCH` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:214` | `tests/static/test_safe_cleanup.py` |
| `MALFORMED_BROKER_BARS` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:529` | `tests/unit/research/test_bar_clock_evidence.py` |
| `MALFORMED_CACHE_PAYLOAD` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:47` | — |
| `MANIFEST_*` | P2 | scripts/governance | `scripts/governance/code_change_gate.py:289` | `tests/integration/test_master_design_traceability.py`<br>`tests/static/test_code_change_gate.py`<br>`tests/unit/engines/test_daily_drawdown_sync.py` (+1) |
| `MANIFEST_OUTPUT_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:51` | — |
| `MISSING_INVALID_OR_STALE_OBSERVER_SNAPSHOT` | P2 | scripts/pc | `scripts/pc/run_system_acceptance.py:51` | — |
| `MISSING_RELEASE_UTC` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:485` | — |
| `MISSING_SYMBOL_WINDOWS` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:41` | — |
| `MODEL_REVIEW_UNAVAILABLE` | P2 | intelligence.news | `src/katarina/intelligence/news/public_language_research.py:110` | `tests/unit/test_public_language_research.py` |
| `NATIVE_MT5_REQUIRES_WINDOWS_64BIT` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:150` | — |
| `NOT_A_GIT_WORKTREE_ROOT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:183` | `tests/static/test_safe_cleanup.py` |
| `NOT_TESTED` | P2 | scripts/pc | `scripts/pc/run_system_acceptance.py:85` | — |
| `NO_ARCHIVED_EVENTS` | P2 | intelligence.lab | `src/katarina/intelligence/lab/adaptive_walkforward.py:226` | `tests/unit/intelligence/test_adaptive_walkforward.py` |
| `NO_AUTHORIZED_SESSION_POLICY` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:31` | `tests/unit/operations/test_session_hypothesis.py` |
| `NO_CONSENSUS_OR_WEAK_EVIDENCE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:546` | `tests/unit/research/test_bar_clock_evidence.py` |
| `NO_ELIGIBLE_PUBLIC_DOCUMENT` | P2 | intelligence.news | `src/katarina/intelligence/news/public_language_research.py:58` | `tests/unit/test_public_language_research.py` |
| `NO_EVIDENCE` | P2 | research.bar_clock_evidence | `src/katarina/research/bar_clock_evidence.py:171`<br>`src/katarina/research/bar_clock_evidence.py:184`<br>`src/katarina/research/bar_clock_evidence.py:197`<br>`src/katarina/research/bar_clock_evidence.py:221` (+1) | `tests/unit/research/test_bar_clock_evidence.py` |
| `NO_NEW_ARTICLE` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:140` | `tests/unit/intelligence/test_research_news_collection.py` |
| `NO_SAMPLES_COLLECTED_FAIL_CLOSED` | P2 | scripts/research | `scripts/research/build_bar_clock_evidence.py:64` | — |
| `NO_VARIATION` | P2 | intelligence.perception | `src/katarina/intelligence/perception/observational_associations.py:14` | — |
| `NO_WRITABLE_PRIVATE_ENVIRONMENT_LOCATION` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:74` | — |
| `OBSERVATIONAL_EVENT_STUDY` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:229` | — |
| `OBSERVER_DATABASE_NOT_FOUND` | P2 | research.spread_profile | `src/katarina/research/spread_profile.py:65` | — |
| `OFFLINE_RESTART_CHECK_FAILED` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:65` | — |
| `OUTCOME_KNOWN_BEFORE_EXIT` | P2 | research.validation | `src/katarina/research/validation.py:301` | `tests/unit/research/test_validation.py` |
| `OUTCOME_NOT_YET_KNOWN` | P2 | research.validation | `src/katarina/research/validation.py:303` | `tests/unit/research/test_validation.py` |
| `OUTSIDE_PERIOD` | P2 | research.validation | `src/katarina/research/validation.py:307` | `tests/unit/research/test_market_intelligence.py` |
| `OUTSIDE_WORKTREE` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:101` | — |
| `OVERLAPPING_OR_UNSORTED_WINDOWS` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:56` | `tests/unit/operations/test_session_hypothesis.py` |
| `OVERLAPPING_POSITION` | P2 | research.validation | `src/katarina/research/validation.py:313` | `tests/unit/research/test_validation_guard_codes.py` |
| `PASS_READONLY_OBSERVATION_ONLY` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:90` | `tests/integration/test_pc_acceptance.py` |
| `PASS_SHADOW_RESEARCH_ONLY` | P2 | research.alpha_survival | `src/katarina/research/alpha_survival.py:188` | `tests/unit/research/test_alpha_survival.py` |
| `PASS_STRATEGY_EVIDENCE_FAIL_CLOSED` | P2 | scripts/governance | `scripts/governance/audit_stage14_15_research.py:48` | `tests/unit/research/test_stage14_15_evidence.py` |
| `PASS_SYNTHETIC_PC_ONLY` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:67` | `tests/integration/test_pc_acceptance.py` |
| `PASS_SYNTHETIC_PRETRIAL_ONLY` | P2 | scripts/pc | `scripts/pc/run_pretrial_acceptance.py:116` | — |
| `PATH_ESCAPE` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:86` | `tests/static/test_safe_cleanup.py` |
| `PERSISTED_RESEARCH_COUNTS` | P2 | monitoring.research_growth | `src/katarina/monitoring/research_growth.py:28` | `tests/unit/test_terminal_network_client.py` |
| `PINNED_CATALOG_REVISION_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/recover_hf_catalog.py:16` | — |
| `PINNED_SOURCE_COMMIT_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:33` | — |
| `POSITION_CROSSES_GAP` | P2 | research.validation | `src/katarina/research/validation.py:311` | `tests/unit/research/test_validation.py` |
| `PRIVATE_BASE_SYMLINK_FORBIDDEN` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:27`<br>`scripts/deployment/install_hf_storage.py:37` | — |
| `PRIVATE_RUNTIME_MUST_BE_OUTSIDE_CHECKOUT` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:31` | — |
| `PRODUCTION_CHECKOUT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:211` | `tests/static/test_safe_cleanup.py` |
| `PROTECTED_CONTENT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:111`<br>`scripts/governance/safe_cleanup.py:113` | `tests/static/test_safe_cleanup.py` |
| `PROTECTED_LOCATION` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:89`<br>`scripts/governance/safe_cleanup.py:92` | `tests/static/test_safe_cleanup.py` |
| `PUBLIC_HYPOTHESIS_RECORDED_NOT_IMPLEMENTED` | P2 | scripts/memory | `scripts/memory/export_research_memory.py:64` | — |
| `PUBLIC_MODEL_DAILY_BUDGET_REACHED` | P2 | intelligence.news | `src/katarina/intelligence/news/public_language_research.py:67` | `tests/unit/test_public_language_research.py` |
| `PUBLISH_FAILED` | P2 | monitoring.monitor_publisher | `src/katarina/monitoring/monitor_publisher.py:92` | — |
| `PULLBACK_*` | P2 | intelligence.perception | `src/katarina/intelligence/perception/market_regime_intelligence.py:170` | `tests/integration/test_unified_owner_surface.py`<br>`tests/unit/engines/test_multi_symbol_execution.py`<br>`tests/unit/engines/test_opportunity.py` (+28) |
| `RECORDED_CURRENT_SPREAD_PLUS_*` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:83` | — |
| `RECOVERY_ALREADY_RUNNING` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:45` | — |
| `RECOVERY_COOLDOWN_USE_EXPLICIT_REPAIR` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:167` | — |
| `RECOVERY_FAILURE_RECORD_INVALID` | P2 | scripts/pc | `scripts/pc/environment_recovery.py:169` | — |
| `REGISTERED_DEVELOPMENT_ONLY` | P2 | scripts/research | `scripts/research/register_setup_hypothesis.py:44` | — |
| `RELEASE_MANIFEST_REQUIRED` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:21` | — |
| `RELEASE_SOURCE_DRIFT` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:25` | — |
| `REPLAY_LOOKAHEAD_FORBIDDEN` | P2 | scripts/research | `scripts/research/replay_technical_signals.py:66` | — |
| `REPLAY_SIGNAL_INVALID` | P2 | scripts/research | `scripts/research/replay_technical_signals.py:74` | — |
| `RESEARCH_HISTORY_COMPARISON_ONLY` | P2 | scripts/research | `scripts/research/probe_current_market_analogs.py:57` | — |
| `RESEARCH_POOL_STOP_TIMEOUT` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:204` | — |
| `RESEARCH_REPORTS` | P2 | intelligence.lab | `src/katarina/intelligence/lab/research_reports.py:114`<br>`src/katarina/intelligence/lab/research_reports.py:144` | `tests/unit/intelligence/test_research_reports.py`<br>`tests/unit/test_persisted_report_snapshot.py` |
| `RESEARCH_WORKER_STOP_TIMEOUT` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:102` | — |
| `RETROACTIVE_EFFECTIVE_TIME` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:36` | `tests/unit/operations/test_session_hypothesis.py` |
| `RETRY_AFTER_COOLDOWN` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:300`<br>`src/katarina/intelligence/lab/autonomous_research.py:301`<br>`src/katarina/intelligence/lab/autonomous_research.py:308` | `tests/unit/intelligence/test_autonomous_research.py` |
| `REVERSAL_*` | P2 | intelligence.perception | `src/katarina/intelligence/perception/market_regime_intelligence.py:151` | `tests/unit/intelligence/test_adaptive_regime_v2.py`<br>`tests/unit/intelligence/test_directional_consensus.py`<br>`tests/unit/intelligence/test_market_regime_intelligence.py` (+2) |
| `REVIEW_COMPLETED` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:240` | — |
| `ROOT_CAUSE_AND_REPRODUCTION_TEST_REQUIRED` | P2 | scripts/governance | `scripts/governance/code_change_gate.py:418` | — |
| `ROOT_CAUSE_IDENTIFIED` | P2 | scripts/governance | `scripts/governance/code_change_gate.py:407`<br>`scripts/governance/code_change_gate.py:419` | — |
| `SIDE_NOT_REGISTERED` | P2 | research.validation | `src/katarina/research/validation.py:295` | `tests/unit/research/test_validation.py` |
| `SOURCE_UNAVAILABLE` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:21` | `tests/unit/intelligence/test_official_cache_provenance.py` |
| `STAGE_*` | P2 | scripts/governance | `scripts/governance/audit_constitution_guard.py:46` | `tests/static/test_stage06_mt5_bridge.py`<br>`tests/static/test_stage35_runner_behavior.py`<br>`tests/unit/body/test_end_to_end_body.py` (+7) |
| `STALE_CACHE_RECEIPT` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:38` | `tests/unit/intelligence/test_official_cache_provenance.py` |
| `SYMLINK_OR_JUNCTION` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:98`<br>`scripts/governance/safe_cleanup.py:109` | `tests/static/test_safe_cleanup.py` |
| `SYNC_INTERVAL_MUST_BE_10_TO_1440_MINUTES` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:35` | — |
| `SYNTHETIC_OBSERVER_CHECK_FAILED` | P2 | scripts/pc | `scripts/pc/run_pc_acceptance.py:61` | — |
| `TAMPERED_OR_MISSING_RAW_DIGEST` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:42` | `tests/unit/intelligence/test_official_cache_provenance.py` |
| `TICK_CLOCK_BASIS_UNKNOWN` | P2 | research.context_export, research.spread_profile | `src/katarina/research/context_export.py:114`<br>`src/katarina/research/context_export.py:137`<br>`src/katarina/research/spread_profile.py:85`<br>`src/katarina/research/spread_profile.py:90` | `tests/unit/research/test_context_export.py`<br>`tests/unit/research/test_spread_profile.py` |
| `TICK_DAY_NOT_STORED` | P2 | research.context_export | `src/katarina/research/context_export.py:140` | `tests/unit/research/test_context_export.py` |
| `TICK_FILE_HASH_MISMATCH` | P2 | research.context_export | `src/katarina/research/context_export.py:50` | `tests/unit/operations/test_data_audit_wp14.py`<br>`tests/unit/research/test_context_export.py`<br>`tests/unit/research/test_spread_profile.py` |
| `TICK_FILE_MALFORMED` | P2 | research.context_export | `src/katarina/research/context_export.py:60` | — |
| `TIMEFRAME_*` | P2 | research.bar_clock_evidence, research.dev_dataset | `src/katarina/research/bar_clock_evidence.py:467`<br>`src/katarina/research/dev_dataset.py:92` | `tests/integration/test_auto_calibration.py`<br>`tests/integration/test_brain_owned_workflow.py`<br>`tests/integration/test_demo_forward_runtime.py` (+7) |
| `TOO_FEW_TICKS` | P2 | research.context_export | `src/katarina/research/context_export.py:159` | — |
| `TRACKED_BY_GIT` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:103` | `tests/static/test_safe_cleanup.py` |
| `UNAVAILABLE_*` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:162`<br>`src/katarina/intelligence/news/research_news_collection.py:162` | `tests/integration/test_automatic_connection.py`<br>`tests/integration/test_pc_acceptance.py`<br>`tests/integration/test_wp1_observer_universe.py` (+12) |
| `UNREACHABLE_MODULE` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:165` | — |
| `UNSAFE_CLOSED_WINDOW` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:53` | `tests/unit/operations/test_session_hypothesis.py` |
| `UNSAFE_MANIFEST_PATH` | P2 | scripts/deployment | `scripts/deployment/release_manifest.py:36` | — |
| `UNSAFE_VALIDITY_INTERVAL` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:38` | — |
| `UNVERIFIABLE_SOURCE_RECEIPT` | P2 | intelligence.news | `src/katarina/intelligence/news/official_cache_provenance.py:67` | — |
| `UPSTREAM_*` | P2 | scripts/governance | `scripts/governance/code_change_gate.py:361` | `tests/static/test_code_change_gate.py` |
| `USE_DOCUMENTED_SYSTEMD_TIMER_ON_LINUX` | P2 | scripts/deployment | `scripts/deployment/install_hf_storage.py:89` | — |
| `UTC_ISO_STRING_REQUIRED` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:11` | — |
| `UTC_OFFSET_REQUIRED` | P2 | scripts/governance | `scripts/governance/session_hypothesis.py:21` | `tests/unit/operations/test_session_hypothesis.py` |
| `WAITING_DATA_OR_DATABASE` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:166` | — |
| `WAITING_ELIGIBLE_CANDIDATE` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:226` | `tests/unit/test_research_scheduler.py`<br>`tests/unit/test_runtime_site_worker.py` |
| `WAITING_FOR_DATA` | P2 | intelligence.news | `src/katarina/intelligence/news/research_news_collection.py:182` | `tests/unit/intelligence/test_research_news_collection.py` |
| `WAITING_NEW_DATA` | P2 | intelligence.lab | `src/katarina/intelligence/lab/autonomous_research.py:158` | `tests/unit/intelligence/test_autonomous_research.py` |
| `WAITING_PUBLIC_MODEL_INTERVAL` | P2 | intelligence.news | `src/katarina/intelligence/news/public_language_research.py:64` | `tests/unit/test_public_language_research.py` |
| `WAIT_UNVERIFIED_HYPOTHESIS` | P2 | scripts/governance | `scripts/governance/audit_alpha_regime_program.py:54` | — |
| `WINDOW_OUTSIDE_DEVELOPMENT_OR_IN_GAP` | P2 | research.context_export | `src/katarina/research/context_export.py:128` | `tests/unit/research/test_context_export.py` |
| `WORKTREE_CHANGED_DURING_CLEANUP` | P2 | scripts/governance | `scripts/governance/safe_cleanup.py:220` | `tests/static/test_safe_cleanup.py` |
| `ZERO_RANGE` | P2 | research.context_export | `src/katarina/research/context_export.py:163` | — |

## Kode protokol (beku)

Codes are stable. New meanings get new codes; existing codes are never redefined.

| Nomor | Kode |
|---|---|
| 0 | `NONE` |
| 1 | `MALFORMED_FRAME` |
| 2 | `CRC_MISMATCH` |
| 3 | `UNSUPPORTED_WIRE_VERSION` |
| 4 | `UNSUPPORTED_SCHEMA_VERSION` |
| 5 | `BINDING_MISMATCH` |
| 6 | `CAPABILITY_MISMATCH` |
| 7 | `SEQUENCE_GAP` |
| 8 | `SNAPSHOT_UNAVAILABLE` |
| 9 | `SNAPSHOT_INCOMPLETE` |
| 10 | `STALE_SYMBOL_SPEC` |
| 11 | `STALE_ACCOUNT_REVISION` |
| 12 | `STALE_POSITION_REVISION` |
| 13 | `INTENT_EXPIRED` |
| 14 | `PENDING_SETUP_EXPIRED` |
| 15 | `NATIVE_SL_REQUIRED` |
| 16 | `NATIVE_SL_INVALID` |
| 17 | `UNSUPPORTED_ORDER_TYPE` |
| 18 | `UNSUPPORTED_FILLING_POLICY` |
| 19 | `UNSUPPORTED_EXPIRATION_POLICY` |
| 20 | `MARKET_OR_SESSION_CLOSED` |
| 21 | `VOLUME_RULE_VIOLATION` |
| 22 | `MARGIN_OR_RISK_PREFLIGHT_FAILED` |
| 23 | `ORDER_CHECK_FAILED` |
| 24 | `IDEMPOTENCY_CONFLICT` |
| 25 | `DUPLICATE_KNOWN_REQUEST` |
| 26 | `ORDER_SEND_REJECTED` |
| 27 | `EXECUTION_OUTCOME_UNKNOWN` |
| 28 | `RECONCILIATION_REQUIRED` |
| 29 | `EXTERNAL_ACCOUNT_MUTATION` |
| 30 | `PENDING_INVALIDATED_BY_POSITION_CHANGE` |
| 31 | `ACCOUNT_UNIT_PROFILE_CHANGED` |
| 32 | `BROKER_CALC_FAILED` |
| 33 | `JOURNAL_UNAVAILABLE` |
| 34 | `CRITICAL_QUEUE_OVERFLOW` |
| 35 | `DATA_STALE` |
| 36 | `CLOCK_INVALID` |
| 37 | `EXECUTION_NOT_ARMED` |
