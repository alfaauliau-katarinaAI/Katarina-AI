# Demo experiment cost policy V2

Owner requested decision learning in demo without a hypothetical triple-cost veto. The 1x historical cost screen remains required; 2x/3x scenarios are advisory. Baseline costs are modeled estimates, not verified broker charges. Risk Governor, exact demo binding, SL/TP, owner stop, durable reconciliation and cooldown remain unchanged. No real account authority is granted.

Candidate selection rotates up to 32 baseline-positive, frozen-data trials, including parents rejected by stress reviews. Each protected variant still receives its own baseline screen. Policy reviews append to private storage and preserve variant identity and previous reports/outcomes.

Evidence before reload: 55 catalog instruments selected; 52 distinct instruments produced 103 contextual observations/decisions since 03:30 UTC, latest 03:39:38 UTC. Selection timestamps alone are not completed scans. Nine pattern/horizon workers plus reviews/coordinator/model roles were configured. No extra workers were added without throughput evidence.

Validation: local 21 integration tests and 12 execution-boundary tests passed. Covers stress-advisory eligibility, baseline failure, stable variant identity, cached frozen data, stress-rejected parent rotation, execution permissions and reconciliation. Native demo orders remain unproven while Algo Trading is OFF.

Deployment verified: Windows 21 integration tests passed in 71.991s; owner gracefully stopped then restarted as PID 6668. New policy review table contains two V2 reviews. Observations advanced to 118 across 52 instruments by 03:42:34 UTC. Demo execution permission remains OFF; one sampled rotated candidate remains baseline-unqualified. No forced qualification or native order claimed.

Readiness follow-up around 03:49 UTC: active owner snapshot confirms account_mode DEMO, demo_observation_enabled true and Algo Trading OFF. Private config explicitly enables demo experiments, local-only terminal exists and exact account/server binding is configured (values omitted). No owner/demo stop files. Five successful owner cycles since reload. Of 21 persisted V2 policy reviews, three pass baseline; one passes 2x and fails 3x, two fail both stress scenarios. Candidate qualification is therefore available without forcing failed variants. Automated entry path is installed but broker acceptance and prospective learning remain unverified until actual permitted demo fills/outcomes. Native calls remain on the owner thread. Risk/signal checks are evaluated per opportunity, not permanently marked passed.
