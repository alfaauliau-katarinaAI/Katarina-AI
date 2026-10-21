<#
.SYNOPSIS
  Probe-only GitHub HTTPS reachability and local checkout identity for Katarina AI.
.DESCRIPTION
  Read-only: no fetch, pull, checkout, reset, checkout modifications, firewall
  edits, credentials, services, files written, or orders sent.
  Compatible with Windows PowerShell 5.1.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$repository = 'alfaauliau-katarinaAI/Katarina-AI'
$githubUrl = 'https://github.com/alfaauliau-katarinaAI/Katarina-AI.git'
$state = [ordered]@{
    schema_version           = 1
    observed_utc             = [DateTime]::UtcNow.ToString('o')
    repository               = $repository
    git_available            = $false
    github_https_readable    = $false
    local_checkout_exists    = $false
    local_git_checkout_valid = $false
    origin_matches_canonical = $false
    github_main_sha          = $null
    local_head_sha           = $null
    checkout_matches_main    = $false
    result                   = 'BLOCKED'
}

# Disable interactive Git prompts just for this process; do not change host setup.
$previousGitPrompt = [Environment]::GetEnvironmentVariable('GIT_TERMINAL_PROMPT', 'Process')
[Environment]::SetEnvironmentVariable('GIT_TERMINAL_PROMPT', '0', 'Process')

try {
    $git = Get-Command 'git.exe' -ErrorAction SilentlyContinue
    if ($null -ne $git) {
        $state.git_available = $true
        try {
            $remoteText = @(& $git.Source ls-remote --heads $githubUrl main 2>$null) -join [Environment]::NewLine
            $remoteExit = $LASTEXITCODE
            $match = [regex]::Match($remoteText, '(?m)^([a-fA-F0-9]{40})\s+refs/heads/main\s*$')
            if ($remoteExit -eq 0 -and $match.Success) {
                $state.github_https_readable = $true
                $state.github_main_sha = $match.Groups[1].Value.ToLowerInvariant()
            }
        } catch {
            # Errors are intentionally not printed: Git may expose credential hints.
        }

        if (Test-Path -LiteralPath $RepoRoot -PathType Container) {
            $state.local_checkout_exists = $true
            try {
                $inside = @(& $git.Source -C $RepoRoot rev-parse --is-inside-work-tree 2>$null) -join ''
                if ($LASTEXITCODE -eq 0 -and $inside.Trim() -eq 'true') {
                    $state.local_git_checkout_valid = $true
                    $origin = @(& $git.Source -C $RepoRoot remote get-url origin 2>$null) -join ''
                    $expectedOrigin = '^(?:https://github\.com/alfaauliau-katarinaAI/Katarina-AI(?:\.git)?/?|git@github\.com:alfaauliau-katarinaAI/Katarina-AI(?:\.git)?|ssh://git@github\.com/alfaauliau-katarinaAI/Katarina-AI(?:\.git)?)$'
                    if ($LASTEXITCODE -eq 0 -and [regex]::IsMatch($origin.Trim(), $expectedOrigin, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
                        $state.origin_matches_canonical = $true
                    }
                    $localSha = @(& $git.Source -C $RepoRoot rev-parse --verify HEAD 2>$null) -join ''
                    if ($LASTEXITCODE -eq 0 -and $localSha.Trim() -match '^[a-fA-F0-9]{40}$') {
                        $state.local_head_sha = $localSha.Trim().ToLowerInvariant()
                    }
                }
            } catch {
                # No local changes or credential values are emitted.
            }
        }
    }
} finally {
    [Environment]::SetEnvironmentVariable('GIT_TERMINAL_PROMPT', $previousGitPrompt, 'Process')
}

$state.checkout_matches_main = [bool]($state.github_https_readable -and $state.local_head_sha -and ($state.local_head_sha -eq $state.github_main_sha))
if ($state.git_available -and $state.github_https_readable -and $state.local_git_checkout_valid -and $state.origin_matches_canonical) {
    $state.result = 'CONNECTED_READONLY'
}

$state | ConvertTo-Json -Depth 5
if ($state.result -eq 'CONNECTED_READONLY') {
    exit 0
}
exit 2
