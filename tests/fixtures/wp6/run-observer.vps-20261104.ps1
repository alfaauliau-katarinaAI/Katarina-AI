# Katarina read-only market observer launcher (LIVE OFF, no orders).
# Runs the canonical observer from C:\Katarina\code with the private environment.
# Refuses to start until MT5 is installed/logged in and the private connection config exists.
# WP6: when C:\Katarina\private\observer_universe.json exists, the observer watches exactly its core symbols
# every cycle (--universe); delete or rename that file to return to the previous 3-symbol default.
$ErrorActionPreference = 'Stop'
$code     = 'C:\Katarina\code'
$state    = 'C:\Katarina\state\readonly-observer'
$logs     = 'C:\Katarina\logs'
$config   = 'C:\Katarina\private\katarina-connections.json'
$universe = 'C:\Katarina\private\observer_universe.json'
New-Item -ItemType Directory -Force -Path $state, $logs | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd')
$log = Join-Path $logs "observer-$stamp.log"

function Write-Log([string]$m) { Add-Content -Path $log -Value ((Get-Date).ToUniversalTime().ToString('o') + ' ' + $m) }

if (Test-Path 'C:\Katarina\STOP_OBSERVER') { Write-Log 'STOP_OBSERVER marker present; not starting'; exit 0 }
if (-not (Test-Path $config)) { Write-Log "BLOCKED: private connection config missing ($config)"; exit 3 }

$env_ = Get-ChildItem (Join-Path $code '.katarina-envs') -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'Scripts\python.exe') } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $env_) { Write-Log 'BLOCKED: private environment missing; run katarina_pc.py setup --mt5'; exit 4 }
$python = Join-Path $env_.FullName 'Scripts\python.exe'

$extra = @()
if (Test-Path $universe) { $extra = @('--universe', $universe) }

$mutex = New-Object System.Threading.Mutex($false, 'Global\KatarinaReadonlyObserver')
if (-not $mutex.WaitOne(0)) { Write-Log 'already running; exit'; exit 0 }
try {
    $env:PYTHONPATH = Join-Path $code 'src'
    $env:KATARINA_STATE_DIR = $state
    Set-Location $code
    Write-Log "START python=$python universe=$(if ($extra) { $universe } else { 'default' })"
    & $python 'scripts\ai\run_contextual_market_observer.py' --continuous `
        --connection-config $config --state-dir $state `
        --interval-seconds 60 --max-symbols 3 @extra *>> $log
    Write-Log "EXIT code=$LASTEXITCODE"
    exit $LASTEXITCODE
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
