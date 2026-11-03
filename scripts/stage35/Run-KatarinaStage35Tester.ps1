param(
    [Parameter(Mandatory=$true)][string]$TerminalPath,
    [Parameter(Mandatory=$true)][string]$Expert,
    [Parameter(Mandatory=$true)][string]$Symbol,
    [string]$Period = "M1",
    [Parameter(Mandatory=$true)][string]$FromDate,
    [Parameter(Mandatory=$true)][string]$ToDate,
    [string]$ReportName = "KatarinaStage35",
    [int]$Model = 4,
    [int]$Deposit = 10000,
    [int]$Leverage = 100,
    [int]$TimeoutSeconds = 3600,
    [string]$OutputRoot = "C:\Katarina\state\stage35",
    [switch]$Portable,
    [string]$ExistingTerminalDataPath = "",
    [string]$ParametersPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

if (-not (Test-Path -LiteralPath $TerminalPath -PathType Leaf)) {
    throw "terminal64.exe not found: $TerminalPath"
}
if ([IO.Path]::GetFileName($TerminalPath).ToLowerInvariant() -ne "terminal64.exe") {
    throw "TerminalPath must point to terminal64.exe"
}
if ($Model -notin @(0,1,2,3,4)) { throw "Unsupported MT5 tester Model=$Model" }
if ($Model -ne 4) {
    Write-Warning "Stage35 governed evidence should use Model=4 (Every tick based on real ticks)."
}
if ($TimeoutSeconds -lt 60) { throw "TimeoutSeconds must be >= 60" }

# Existing installations require their explicit, origin-bound data directory.
if ($Portable -and $ExistingTerminalDataPath) { throw 'Choose one terminal mode.' }
if (-not $Portable -and -not $ExistingTerminalDataPath) { throw "Use -Portable or an explicit ExistingTerminalDataPath." }
foreach ($Value in @($Expert, $Symbol, $Period, $FromDate, $ToDate, $ReportName)) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match '[\r\n\x00]') {
        throw "Tester fields must be nonempty single-line values."
    }
}
if ($Expert -notmatch '^[A-Za-z0-9_\\/-]+(?:\.ex5)?$' -or $Expert.Contains('..') -or $Expert.StartsWith('\') -or $Expert.StartsWith('/')) {
    throw "Expert must be a relative MQL5 Experts path."
}
if ($ReportName -notmatch '^[A-Za-z0-9_-]+$') { throw "ReportName must be a filename stem." }
if ($Symbol -notmatch '^[A-Za-z0-9_.#-]+$') { throw "Invalid Symbol." }
if ($Period -notmatch '^(M(1|2|3|4|5|6|10|12|15|20|30)|H(1|2|3|4|6|8|12)|D1|W1|MN1)$') { throw "Invalid Period." }
$StartDate = [DateTime]::ParseExact($FromDate, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
$EndDate = [DateTime]::ParseExact($ToDate, 'yyyy.MM.dd', [Globalization.CultureInfo]::InvariantCulture)
if ($EndDate -le $StartDate) { throw "ToDate must follow FromDate." }
if ($Deposit -le 0 -or $Leverage -le 0) { throw "Deposit and Leverage must be positive." }
$TerminalPath = (Resolve-Path -LiteralPath $TerminalPath).Path
$TerminalDir = Split-Path -Parent $TerminalPath
$DataDir = $TerminalDir
if ($ExistingTerminalDataPath) {
    $DataDir = (Resolve-Path -LiteralPath $ExistingTerminalDataPath).Path
    $Origin = Join-Path $DataDir 'origin.txt'
    if (-not (Test-Path -LiteralPath $Origin -PathType Leaf)) { throw 'Missing terminal origin binding.' }
    $BoundHome = (Get-Content -LiteralPath $Origin -Raw).Trim()
    if (-not [string]::Equals($BoundHome.TrimEnd('\','/'), $TerminalDir.TrimEnd('\','/'), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Data directory belongs to a different terminal installation.'
    }
}
$ExpertFile = $Expert
if (-not $ExpertFile.EndsWith('.ex5')) { $ExpertFile += '.ex5' }
$ExpertPath = Join-Path (Join-Path $DataDir 'MQL5\Experts') $ExpertFile
if (-not (Test-Path -LiteralPath $ExpertPath -PathType Leaf)) { throw "Compiled Expert missing: $ExpertPath" }
# Refuse reuse of a running terminal; never terminate a pre-existing session.
foreach ($Existing in @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)) {
    if (-not $Existing.Path -or $Existing.Path -eq $TerminalPath) {
        throw "Tester terminal is running or its identity cannot be verified."
    }
}
$Root = $OutputRoot
$RunId = [Guid]::NewGuid().ToString('N')
$ReportName = $ReportName + '-' + $RunId
$RunRoot = Join-Path $Root $RunId
$EvidenceRoot = Join-Path $RunRoot "evidence"
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$ParametersName = $null
$ParametersHash = $null
if ($ParametersPath) {
    $ParametersPath = (Resolve-Path -LiteralPath $ParametersPath).Path
    $ParametersName = 'Katarina-' + $RunId + '.set'
    $PresetDir = Join-Path $DataDir 'MQL5\Profiles\Tester'
    New-Item -ItemType Directory -Force -Path $PresetDir | Out-Null
    Copy-Item -LiteralPath $ParametersPath -Destination (Join-Path $PresetDir $ParametersName)
    Copy-Item -LiteralPath $ParametersPath -Destination (Join-Path $EvidenceRoot 'parameters.set')
    $ParametersHash = (Get-FileHash -LiteralPath $ParametersPath -Algorithm SHA256).Hash
}

$IniPath = Join-Path $RunRoot "tester.ini"
$Ini = @(
    "[Experts]",
    "AllowLiveTrading=0",
    "AllowDllImport=0",
    "[Tester]",
    "Expert=$ExpertFile",
    "Symbol=$Symbol",
    "Period=$Period",
    "Model=$Model",
    "FromDate=$FromDate",
    "ToDate=$ToDate",
    "ForwardMode=0",
    "Deposit=$Deposit",
    "Currency=USD",
    "Leverage=$Leverage",
    "Optimization=0",
    "Report=$ReportName",
    "ReplaceReport=1",
    "ShutdownTerminal=1",
    "Visual=0"
)
if ($ParametersName) { $Ini += "ExpertParameters=$ParametersName" }
$Ini | Set-Content -LiteralPath $IniPath -Encoding UTF8

$Before = [DateTime]::UtcNow
$ExpertSha256 = (Get-FileHash -LiteralPath $ExpertPath -Algorithm SHA256).Hash
$RunnerSha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
$IniSha256 = (Get-FileHash -LiteralPath $IniPath -Algorithm SHA256).Hash
$LaunchArgs = @("/skipupdate", "/config:`"$IniPath`"")
if ($Portable) { $LaunchArgs += "/portable" }

$Process = Start-Process -FilePath $TerminalPath -ArgumentList $LaunchArgs -PassThru
$TimedOut = $false
try {
    Wait-Process -Id $Process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    $TimedOut = $true
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
}

if (-not $TimedOut) { $Process.Refresh() }
$ExitCode = if ($TimedOut) { $null } else { $Process.ExitCode }
$Report = $null
$ExpectedReport = Join-Path $DataDir ($ReportName + ".htm")
if (Test-Path -LiteralPath $ExpectedReport -PathType Leaf) {
    $Candidate = Get-Item -LiteralPath $ExpectedReport
    if ($Candidate.LastWriteTimeUtc -ge $Before -and $Candidate.Length -gt 0) { $Report = $Candidate }
}
$ReportPath = $null
$ReportSha256 = $null
if ($Report) {
    $ReportPath = Join-Path $EvidenceRoot 'tester-report.htm'
    Copy-Item -LiteralPath $Report.FullName -Destination $ReportPath
    foreach ($Asset in @(Get-ChildItem -LiteralPath $DataDir -Filter ($ReportName + '*.png') -File)) {
        Copy-Item -LiteralPath $Asset.FullName -Destination (Join-Path $EvidenceRoot $Asset.Name)
    }
    $ReportSha256 = (Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash
}

$Evidence = [ordered]@{
    schema_version = 2
    run_id = $RunId
    expert_sha256 = $ExpertSha256
    runner_sha256 = $RunnerSha256
    config_sha256 = $IniSha256
    parameters_sha256 = $ParametersHash
    strategy_validated = $false
    proof_type = "KATARINA_STAGE35_MT5_TESTER"
    generated_utc = [DateTime]::UtcNow.ToString("o")
    terminal_path = $TerminalPath
    terminal_data_path = $DataDir
    portable = [bool]$Portable
    expert = $Expert
    symbol = $Symbol
    period = $Period
    from_date = $FromDate
    to_date = $ToDate
    model = $Model
    model_real_ticks = ($Model -eq 4)
    optimization = 0
    shutdown_terminal = 1
    timed_out = $TimedOut
    process_exit_code = $ExitCode
    report_path = $ReportPath
    report_sha256 = $ReportSha256
    report_present = ($null -ne $Report)
    live_risk_ready = $false
    live_execution_enabled = $false
    result = if ((-not $TimedOut) -and ($null -ne $ExitCode) -and ($ExitCode -eq 0) -and $Report -and ($Model -eq 4)) {
        "PASS_STAGE35_TESTER_INFRASTRUCTURE"
    } else {
        "FAIL_STAGE35_TESTER_INFRASTRUCTURE"
    }
}

$EvidencePath = Join-Path $EvidenceRoot "stage35-tester-evidence.json"
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8

Write-Host $Evidence.result
Write-Host "Evidence: $EvidencePath"
if ($ParametersName) { Remove-Item -LiteralPath (Join-Path $PresetDir $ParametersName) -ErrorAction SilentlyContinue }
if ($Evidence.result -ne "PASS_STAGE35_TESTER_INFRASTRUCTURE") { exit 2 }
