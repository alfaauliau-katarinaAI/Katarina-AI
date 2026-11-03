# Stage0 health replacement template — NOT auto-deployed / NOT registered as a task.
# Requires explicit Owner permission and approved source checkout supporting --since.
# This job only reads the observer ledger; NEVER initializes MT5 or sends orders.
$ErrorActionPreference = 'Stop'
$code = 'C:\Katarina\code'
$state = 'C:\Katarina\state\readonly-observer'
$cutoff = '2026-10-28T16:57:00+00:00'
$cli = Join-Path $code 'scripts\ai\check_stage0_health.py'
$envs = Join-Path $code '.katarina-envs'

if (!(Test-Path -LiteralPath $cli -PathType Leaf)) {
    throw 'STAGE0_HEALTH_CLI_MISSING'
}
if (!(Test-Path -LiteralPath $envs -PathType Container)) {
    throw 'STAGE0_HEALTH_PYTHON_ENV_MISSING'
}
# Fail closed on old production SHA 64497b5: it lacks --since.
if (!(Select-String -LiteralPath $cli -Pattern 'parser.add_argument("--since"' -SimpleMatch -Quiet)) {
    throw 'STAGE0_HEALTH_CUTOFF_NOT_SUPPORTED_DO_NOT_REPLACE_SCHEDULER'
}
$selected = Get-ChildItem $envs -Directory |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -eq $selected) {
    throw 'STAGE0_HEALTH_PYTHON_ENV_MISSING'
}
$python = Join-Path $selected.FullName 'Scripts\python.exe'
if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'STAGE0_HEALTH_PYTHON_MISSING'
}
$env:PYTHONPATH = Join-Path $code 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $python -B $cli --state-dir $state --since $cutoff --output (Join-Path $state 'stage0-health-daily.json') *> (Join-Path $state 'stage0-health-daily.log')
if ($LASTEXITCODE -ne 0) {
    throw ('STAGE0_HEALTH_COMMAND_FAILED_' + $LASTEXITCODE)
}
# Leave the active observer and MT5 completely untouched.
