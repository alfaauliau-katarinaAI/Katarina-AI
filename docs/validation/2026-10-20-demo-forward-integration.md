# Katarina demo integration audit — 20 October 2026

Status: INTEGRATED_ON_VPS; DEMO ORDER EXECUTION REMAINS GATED.

## Connected path

Historical research candidates -> immutable protected H1 variant -> persistent demo-account risk ledger -> existing Risk Governor -> durable native demo outbox -> broker position/deal reconciliation -> horizon exit / broker SL and TP -> persisted forward lessons and variant cooldown.

The owner process retains the existing 13 research threads. A cooperative service runs between bound sensor reads on the same foreground thread and reuses its MT5 connection. It does not initialize/shutdown MT5 underneath an active sensor read. Idle passes use a bounded cadence. This is coordinated multitasking, not simultaneous independent order senders or a claim that Python removes native API latency.

## Verified on the VPS

- Connected ALFA account independently identified as DEMO through SDK account mode and exact private account/server binding.
- Account risk reconciled from a new explicit demo enrolment epoch. This does not certify lifetime equity peaks, historical drawdown, future fees or real-account risk.
- Protected variant was tested against its exact frozen dataset: 58 development and 32 chronological review observations. These reused historical splits are NOT independent prospective proof.
- Native audit sent no orders. New owner process 3156 reported 13 research workers and an integrated demo status with the same process identity at 2026-10-20T03:17 UTC.
- Algo Trading remains OFF. One non-Katarina expert, ReverseTrail_SAR_EntryProtect_30Pip_v1_20, was found in saved chart profiles; its active-profile status has not been established. Enabling terminal-wide Algo Trading could enable other experts and was not attempted.

| Cost multiplier | Development mean (range units) | Review mean (range units) | Result |
| --- | ---: | ---: | --- |
| 1x | 0.445207 | 0.374815 | Pass |
| 2x | 0.206499 | 0.135486 | Pass |
| 3x | -0.032208 | -0.103842 | Fail |

Current decision: PROTECTED_VARIANT_NOT_QUALIFIED. Entry decisions, real broker forward outcomes and submitted demo orders remain zero. A rejected variant is an actual research result, not a reason to fabricate an entry to animate the dashboard.

## Risk and recovery behavior

Every submission rechecks demo account type, binding, permissions, owner stop, protection, freshness and approved account-native loss. The minimum broker lot must fit the budget, including an explicit stress reserve. The experiment requests at most 0.1% risk before the existing governor applies its tighter limits. There is one account position at a time in this bounded trial.

Unknown submissions never trigger blind retry. Reconciliation proves owned fills and exact closed volume before recording P/L with commission, swap and fee. Mixed ownership and missing protection require review. At least three closed outcomes with negative aggregate P/L place the variant in a research cooldown; this is a predefined rule, not neural-weight training or a profitability guarantee.

Broker-side SL/TP remain effective independently of the Python loop. Owner stop files remain respected. No strategy is promoted to real trading and no real-account permission is enabled.

## Validation and remaining limits

Local integration/regression tests cover the lifecycle, actual persisted candidate schema, protective variant re-test, risk-budget rejection, concurrent reservations, timeout recovery, mixed ownership, deposits, restart, horizon exit, cooldown, account switching and connection reuse. The Windows regression run completed 107 tests successfully with one pre-existing TLS certificate test skipped because OpenSSL is unavailable; the later cooperative scheduling subset is recorded separately in the audit evidence.

An initial candidate-schema mismatch (digest stored in the trials column, not result JSON) was found by the native audit and corrected with a schema-level integration test. A Windows test fixture SQLite handle leak was corrected. The main observer was stopped and restarted through its retained stop-file protocol; no forced termination of the owner occurred. One explicitly read-only audit child was cancelled while testing access ordering.

There is no actual MT5 open/close-cycle proof yet. General sensor coverage remains a separate diagnostic. A several-minute foreground interval between history collection and risk audit was observed; its exact SQLite/CPU cause has not been profiled. Cooperative sensor service improves scheduling points but does not prove a strict latency bound during every computation or native SDK call. This remaining latency must be measured during a qualified demo trial before making readiness claims.

Private ticks, datasets, account identifiers, broker books and cognitive memory remain on the VPS. Only code and this redacted audit are committed.

Final validation update: 111 local tests passed. The Windows 107-test regression and subsequent 48-test cooperative scheduling subset passed with the same OpenSSL-dependent TLS test skipped. A final focused boundary suite covers missing exit history, active-owner audit refusal and connection reuse. Native audit CLI now refuses to connect unless the owner has gracefully stopped with its retained stop file. An unresolved OPEN outbox entry also blocks the next entry until broker close evidence arrives.


## Final operational evidence
At 2026-10-20T03:24:30 UTC the final validated owner (5056) was WAITING with 13 background research threads, model configured, and live execution false. Its demo status had the same process identity, reconciled enrolment risk, PROTECTED_VARIANT_NOT_QUALIFIED, DEMO_TRADING_PERMISSION_OFF and zero closed broker outcomes. No owner stop file remained. Both the Sites public-status and Cloudflare api/runtime endpoints returned HTTP 200 with telemetry_verified=true, current-process identity matching the owner and fresh activity. This confirms telemetry/coordination, not market completeness or executed forward trades. The final 32-test Windows boundary suite passed without skips; earlier broader suites retained the one OpenSSL-dependent TLS skip. The final source commit was 460ba526984787192c1ea21f3cdfff588613dd08.
