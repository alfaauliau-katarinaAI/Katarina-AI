<#
WP6: register the reboot-safe observer task definition, with backup and rollback.
DRY-RUN BY DEFAULT. Nothing changes unless -Apply is given, and -Apply is only for the Owner (or with
the Owner's explicit approval). Never touches autologon, passwords, MT5, broker data or the running
observer process: re-registering the task does not stop the current instance (IgnoreNew).

  .\wp6_apply_observer_startup.ps1                       # dry run: show current vs proposed, write nothing
  .\wp6_apply_observer_startup.ps1 -Apply                # backup current XML + hash, then register proposed
  .\wp6_apply_observer_startup.ps1 -Rollback <backup.xml> # re-register the backed-up definition

Prerequisite for mode AUTOLOGON_INTERACTIVE: the Owner enables Windows autologon for the task user
(Sysinternals Autologon, run by the Owner). Verify afterwards with scripts/ai/wp6_startup_preflight.py.
#>
param(
    [switch]$Apply,
    [string]$Rollback,
    [string]$TaskName = 'Katarina-Readonly-Observer',
    [string]$Proposed = (Join-Path $PSScriptRoot 'observer-task.autologon.xml'),
    [string]$BackupRoot = 'C:\Katarina\backups'
)
$ErrorActionPreference = 'Stop'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$current = (schtasks /query /tn $TaskName /xml | Out-String)
if ($LASTEXITCODE -ne 0 -or -not $current.Trim()) { throw "WP6_TASK_NOT_FOUND $TaskName" }

if ($Rollback) {
    if (-not (Test-Path $Rollback)) { throw "WP6_ROLLBACK_FILE_MISSING $Rollback" }
    if (-not $Apply) { Write-Output "DRY_RUN rollback would re-register $TaskName from $Rollback"; exit 0 }
    Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content $Rollback -Raw) -Force | Out-Null
    Write-Output "WP6_ROLLED_BACK $TaskName from $Rollback"
    exit 0
}

if (-not (Test-Path $Proposed)) { throw "WP6_PROPOSED_DEFINITION_MISSING $Proposed" }
$proposedXml = Get-Content $Proposed -Raw
Write-Output "CURRENT_SHA256 $((Get-FileHash -InputStream ([IO.MemoryStream]::new([Text.Encoding]::Unicode.GetBytes($current))) -Algorithm SHA256).Hash)"
Write-Output "PROPOSED $Proposed"
if (-not $Apply) {
    Write-Output 'DRY_RUN no change made. Re-run with -Apply after Owner approval and autologon setup.'
    exit 0
}

# 1. Backup before any change (definition + hash), outside the checkout.
$backupDir = Join-Path $BackupRoot "wp6-task-$stamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backup = Join-Path $backupDir "$TaskName.xml"
[IO.File]::WriteAllText($backup, $current, [Text.Encoding]::Unicode)
$hash = (Get-FileHash $backup -Algorithm SHA256).Hash
Set-Content -Path (Join-Path $backupDir 'SHA256.txt') -Value "$hash  $TaskName.xml"
Write-Output "WP6_BACKUP $backup $hash"

# 2. Register the proposed definition; on any error restore the backup immediately.
try {
    Register-ScheduledTask -TaskName $TaskName -Xml $proposedXml -Force | Out-Null
    $after = (schtasks /query /tn $TaskName /xml | Out-String)
    if ($after -notmatch 'run-observer\.ps1' -or $after -notmatch '<MultipleInstancesPolicy>IgnoreNew') {
        throw 'WP6_VERIFY_FAILED'
    }
    Write-Output "WP6_APPLIED $TaskName (rollback: -Apply -Rollback `"$backup`")"
} catch {
    Register-ScheduledTask -TaskName $TaskName -Xml $current -Force | Out-Null
    Write-Output "WP6_APPLY_FAILED_RESTORED $($_.Exception.Message)"
    exit 1
}
