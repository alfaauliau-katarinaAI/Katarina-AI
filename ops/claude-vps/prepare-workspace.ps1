# Prepare a separate, non-production checkout for owner-authorized Claude Code reviews.
# PowerShell 4+ compatible. Does not install Claude, change credentials or touch production.
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'C:\KatarinaDev\claude-workspace'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$expected = 'C:\KatarinaDev\claude-workspace'
if ($WorkspaceRoot.TrimEnd('\') -ine $expected) {
    throw "Refusing workspace outside approved path: $expected"
}

$source = 'https://github.com/alfaauliau-katarinaAI/Katarina-AI.git'
$checkout = Join-Path $WorkspaceRoot 'Katarina-AI'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not available'
}
if (Test-Path -LiteralPath $checkout) {
    Write-Host 'Existing Claude checkout detected; will not replace, reset, pull, or clean it.'
    if (Test-Path -LiteralPath (Join-Path $checkout '.git')) {
        & git -C $checkout remote -v
        & git -C $checkout status --short --branch
    }
    exit 0
}
if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    New-Item -ItemType Directory -Path $WorkspaceRoot | Out-Null
}
Write-Host 'Creating a new shallow source checkout (NO scripts or production deployment).'
& git clone --depth 1 --single-branch --branch main $source $checkout
if ($LASTEXITCODE -ne 0) {
    throw 'Clone failed. Existing files, if any, were left untouched.'
}
& git -C $checkout remote -v
if ($LASTEXITCODE -ne 0) { throw 'Could not verify origin' }
& git -C $checkout status --short --branch
if ($LASTEXITCODE -ne 0) { throw 'Could not verify workspace status' }
Write-Host 'READY_FOR_CLAUDE_SIGNIN_ON_COMPATIBLE_HOST (not VPS admin access).'
