# VPS read-only audit and safe maintenance — 2026-10-19

**Policy:** all software/source changes in GitHub. VPS is test/maintenance-only;
no source checkout, edit, deployment, memory database change or strategy
promotion was performed in this intervention.

## Host and capacity

- Host: `WIN-4TTT19K3CL8` (Windows VPS, existing Desktop Commander connection).
- System disk C: 42,091,581,440 bytes total.
- C: free **before** 3,235,360,768 bytes; **after** 4,343,226,368 bytes.
- **1,107,865,600 bytes (~1.11 GB decimal) recovered**.
- Physical RAM 2,096,604 KiB (~2 GiB). Available RAM sampled before:
  875,896 KiB; after: 823,792 KiB. This fluctuates; **do not claim a RAM
  improvement** as a result of disk cache cleanup.
- Processes protected and verified after cleanup: MetaTrader 5 `terminal64`;
  Node PIDs 772 and 3400. Desktop Commander access maintained.

## Cleanup actually executed

Deleted only expendable artifacts:
- Three non-running `npm-cache/_npx` installs dated 11 October:
  `0eedb5afd4158ff3`, `16d477e2c74d3d5a`, `2744c97c82079ec6`.
- `npm-cache/_cacache`, `pip/Cache`.
- Unneeded root `C:\GitInstaller.exe` after confirming Git is installed.
- Eligible old files in Windows Temp and Administrator Temp (older than 3 days,
  best effort; locks/error protection preserved).
- Four **disabled** legacy scheduled tasks:
  `Katarina-AnalogMemory-Observer`,
  `Katarina-DecisionObserver-ReadOnly`,
  `Katarina-MarketBrain-Observer`,
  `Katarina-OneTime-RepairRiskTestAcl`.

Explicitly **preserved** the active NPM npx install `4b4c857f6efdfb61`
(used by Node PID 772), the Owner read-only observer task and DC watchdog
(both `Ready`), other task definitions pending later ownership review,
all MT5 installs, market/tick research, journal/checkpoints, database
files, code directories and private account access configuration.

## Remaining blockers

- Owner task `KatarinaOwnerContinuousReadonly` last run 16 October:
  Task Scheduler exit result 2, state Ready (not independently active).
  No observer Python process found during this session.
- VPS has low physical memory; do not forcibly trim Windows/system/MT5/Node
  process working sets or kill the remote-control path merely to show free RAM.
  The OS manages reclaimable standby memory; closing approved workloads requires
  separate safety verification.
- The GitHub feature branch is **not installed** on the VPS. Test the new
  dashboard only after code review/CI and explicit, non-persistent testing
  authorization. LIVE OFF remains the only accepted trading posture.

No claim of production readiness or strategy profitability is implied.
