# Reproducible Katarina test deployment

Code is owned by GitHub. The Windows VPS is a test runtime. Pin the containing GitHub commit before deployment; this branch is not production clearance and is not merged automatically.

## Layout and data ownership

| Layer | Canonical location | New-host requirement |
|---|---|---|
| Observer, research workers, doctor and dashboard publisher | `src/katarina`, `scripts/ai` | Checkout the pinned commit; verify the release manifest |
| Private HF archive service | `scripts/ai/hf_archive_sync.py`, `run_hf_archive_sync.py` | Explicit private config, token, separate environment and scheduler |
| Cloud recovery inventory | `scripts/deployment/recover_hf_catalog.py` | Rebuild from a pinned HF revision; original VPS receipts are not required |
| Active market/research databases and tick inputs | External runtime directory | Restore consistent database copies; transfer/retain tick inputs separately |
| HF, Gemini, broker and relay credentials | Destination secret store / protected configuration | Provision again on the destination; never commit or put authentication secrets in the dataset |
| Public website | `sites/runtime-monitor` and deployment guide | Rebind its telemetry endpoint/secrets on the destination |
| MT5 native executor/dashboard | `mt5` | Windows MT5 installation, compile/load and broker validation on destination |

The HF service itself is portable to Linux. Native MT5 execution remains Windows-specific. Core tests on Linux do not verify a real MT5 installation elsewhere.

## Clean source and environments

1. Clone the repository, disable Git line-ending conversion for the release checkout, and check out the exact reviewed commit. Do not deploy a moving branch name.
2. Verify code: `python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json`. Missing, modified or extra source must be reviewed before installation. CRLF/BOM differences are reported separately.
3. Create separate environments. The Windows brain uses `requirements-stage07.txt` plus `requirements-brain-observer.txt`. The archive environment uses `requirements-hf-storage.txt`. This separation preserves their independently pinned CA/dependency versions.
4. Keep code, private configuration and runtime state in separate directories. The installer refuses runtime storage inside the checkout.

## Provision HF on another Windows machine

The following is a path example. Run the installer with the archive environment's Python. Inject `HF_TOKEN` from a secret manager or a protected GitHub deployment step; do not place its value in command arguments, source, logs or the example config.

```powershell
python scripts/deployment/install_hf_storage.py --code-root D:\Katarina\code --base-dir D:\Katarina\private\hf --state-dir D:\Katarina\state --repo-id OWNER/katarina-research-archive --expected-account OWNER --source-commit PINNED_40_CHARACTER_COMMIT --provision-credential --include-operational-ledgers --verify --schedule
```

Credentials are newly protected using destination Windows DPAPI and a SYSTEM/Administrators directory ACL. The existing VPS DPAPI blob cannot be reused as the destination credential. A fresh destination RSA public key must be pinned/reviewed if reusing the GitHub encrypted-transfer workflow; the old VPS transfer key is not a universal deployment key.

The scheduled action points directly to the canonical checkout runner with `--config`; it no longer needs a copied Python runner under the credential directory. Existing cold-file allowlists are preserved on in-place upgrades. Fresh installations begin with an empty eviction list. Changing the existing state directory or repository in place is rejected.

The installer configures only the archive task. It does not start an observer/executor or enable LIVE trading.

Apply the destination service account's private ACL to broker, relay and model configuration as well. For the current SYSTEM/Administrators Windows test profile, use `icacls BROKER_PRIVATE_CONFIG /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F"` on the broker private JSON and verify that no other explicit read grants remain. This removes the inherited Users read grant found during the test-VPS audit. A different service identity needs its own explicitly reviewed ACL.

## Linux archive host

Use Python 3.11+ and the archive requirements in a dedicated environment. Run the same installer as the intended service user, with Linux paths, omitting `--schedule`. Use `--provision-credential` with an injected environment token, or mount an owner-readable `HF_TOKEN_FILE`. The private base must be mode 0700 and a token file mode 0600; symlink/world-readable credentials are refused.

Templates are in `ops/deployment/katarina-hf-storage.service` and `.timer`. Adjust user and paths before installation. The template grants write access only to the private archive directory and runtime state. Add an explicitly reviewed cold archive root if eviction is needed elsewhere. Linux service startup is a destination acceptance step, not a claim from the Windows test.

## Recover data after VPS loss

1. Provision a destination token and config without starting trading processes.
2. Run `python scripts/deployment/recover_hf_catalog.py --config PRIVATE_CONFIG`. It reads existing remote manifests and writes a private recovery catalog pinned to one repository revision, without uploading.
3. Export a chosen current manifest, for example with `--logical-source state/context.sqlite3 --manifest-output PRIVATE_OUTPUT_MANIFEST`. New backups use stable `state/...` identities. Legacy snapshots retain their old source labels and are explicitly marked as requiring destination mapping; choose the correct source and date rather than treating an old Windows path as a destination.
4. Restore to a separate destination: `python scripts/ai/hf_archive_sync.py --config PRIVATE_CONFIG --restore-manifest PRIVATE_OUTPUT_MANIFEST --destination NEW_OFFLINE_COPY`. Restore is allowed during an upload cooldown, verifies compressed and restored hashes, refuses overwrite, and maintains the disk reserve.
5. Validate SQLite `quick_check`, schema, record counts and checkpoint consistency before selecting that state directory for startup. Start the observer and verify fresh process/market evidence before separately validating any executor.

Authentication configuration and original tick inputs are intentionally not in this archive. Restore them through their protected source/transfer procedure. Current service config is an explicit source allowlist, not a whole-disk backup.

## State coverage and handoff

Full Windows test-state coverage with `--include-operational-ledgers` comprises the experiment jobs, context, cognitive memory, calibration, network doctor, soak evidence, demo experiment book and demo order book. Active databases remain on the VPS; consistent snapshots are archived privately. Authorization files such as `independent.enabled`, stop markers, broker/model credentials and private connection configuration are revalidated separately on the destination.

Complete these acceptance conditions before the eventual move: all required database clocks show verified backups; a fresh remote catalog can recover the required state; tick transfer is verified; destination native MT5/telemetry works; the old executing host is stopped and broker orders/positions are reconciled before another executor is activated. These checks do not authorize LIVE execution.

## Ongoing operation

- Small JSON snapshots: ten-minute schedule; unchanged captured content is not uploaded again.
- Full databases: success tracked independently per source, due every 24 hours.
- HF 429: honor provider `Retry-After` and pause network uploads/expensive copies until the persisted cooldown expires.
- Eviction: only reviewed old outputs, after remote download/hash and durable manifest verification. Active state, credential files, open SQLite WALs and tick inputs are excluded.
- Archive budget: 80 GB configured cap; local reserve: 2 GiB. The cap is not a provider billing guarantee.
- `hf-storage-status.json`, `backup-clock.json`, the release manifest and private `deployment.json` provide status/source evidence. A scheduler exit code 0 while waiting does not mean `SYNCED`.
- HF smoke/credential-transfer workflows are manual. Main CI covers automatic source tests without consuming HF commits or resealing credentials on every PR update.
