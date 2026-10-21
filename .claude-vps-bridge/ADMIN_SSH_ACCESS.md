# Claude — Windows VPS administrator access

**Purpose:** deploy and test Katarina on the owner's Windows VPS using **direct SSH**, separate from the public GitHub inbox bridge.

## Configuration on VPS (2026-10-22)

- OpenSSH service is running on port 22.
- A dedicated Ed25519 public key was added to Windows OpenSSH's administrator authorized-keys file, restricted by ACL to SYSTEM and local Administrators.
- The associated **private key is NOT in GitHub**. It is stored only on the owner VPS at `C:\ClaudeGitHubBridge\credentials\claude-admin-ssh-ed25519`.
- Desktop Commander watchdog and existing inbound message polling remain enabled.
- No Katarina code or GitHub `main` branch was modified to configure this access.

## Required secure handoff

The owner must securely provision the private key to the environment actually running **Claude Code or another authorized SSH-capable Claude agent**, and supply the VPS endpoint through a private channel. Do not upload the private key into this public repo, issues, commits, chat transcripts, or public logs.

From an authenticated SSH-capable environment, use an SSH client with the securely installed private key and verify the Windows Administrator identity before deployments. Confirm the host SSH fingerprint out of band. External SSH reachability and the Claude-side login **have not yet been verified**.

The public GitHub bridge at `.claude-vps-bridge` is a separate, **limited** data/message transport. Posting `admin_exec` or shell commands to its public inbox **does not grant administrative execution**.

## Operational precautions

- Do not disable Desktop Commander networking, watchdog, Windows SSH/RDP services, or firewall controls supporting owner access.
- Keep GitHub repository credentials, broker account secrets and SSH private keys out of GitHub commits.
- Record deployments and test results. Trading LIVE remains disabled unless separately authorized and validated by the owner.
- Administrator access is intrinsically powerful and cannot technically guarantee immunity of Desktop Commander from intentional or accidental admin changes.
