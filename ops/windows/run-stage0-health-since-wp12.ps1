# Read-only official Stage 0 health report (no broker connection, no SQLite writes, LIVE OFF).
# Called by C:\Katarina\run-stage0-health.ps1 (task Katarina-Stage0-Daily-Health). File and output names are
# kept for continuity; since Owner decision D8 (4 Nov 2026) it uses the deployed checker in C:\Katarina\code
# and the official count start (--since official = STAGE0_COUNT_SINCE_UTC, WP13 deploy 2026-11-03T15:18:14Z).
# The previous version ran a pinned pre-K-04 checkout (b3fd2e6) and reported clock_shift_stable PASS wrongly.
$ErrorActionPreference = 'Stop'
$code  = 'C:\Katarina\code'
$state = 'C:\Katarina\state\readonly-observer'
$env_ = Get-ChildItem (Join-Path $code '.katarina-envs') -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName 'Scripts\python.exe') } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $env_) { throw 'Official health report: private environment missing' }
$python = Join-Path $env_.FullName 'Scripts\python.exe'
$env:PYTHONPATH = Join-Path $code 'src'
Set-Location $code
$out = Join-Path $state 'stage0-health-since-wp12-daily.json'
$log = Join-Path $state 'stage0-health-since-wp12-daily.log'
$commit = (& 'C:\Program Files\Git\cmd\git.exe' -C $code rev-parse HEAD).Trim()
& $python 'scripts\ai\check_stage0_health.py' --state-dir $state --since official --output $out *> $log
if ($LASTEXITCODE -ne 0) { throw "Official health report: exit code $LASTEXITCODE" }
& $python 'scripts\ai\check_stage0_health.py' --state-dir $state --since official --breakdown `
    --output (Join-Path $state 'stage0-breakdown-daily.json') *>> $log
$report = Get-Content $out -Raw | ConvertFrom-Json
Add-Content -Path $log -Value ("REPORT_VERDICT=" + $report.verdict + "; as_of_utc=" + $report.as_of_utc +
    "; since_utc=" + $report.since_utc + "; checker_commit=" + $commit)
