# VPS, private archive and redeployment audit

Audit date: 21 October 2026 WIB (20 October UTC). This records the test deployment, not production acceptance.

## Source and deployment identity

The Windows test VPS's 373 inventoried source/configuration/template files match GitHub source commit `b6d900572acf0b762616d98388f568fd2f61d8a1`, allowing only reported CRLF/BOM normalization. The release manifest rejects missing, changed and extra source files. The VPS checkout's original Git HEAD remains older; the installed content is attested by the manifest and private deployment receipt, rather than by that old checkout metadata.

Recovered runtime modules, tests, memory export and the read-only MT5 dashboard are now versioned. Dependency pins, destination configuration templates, installer, remote recovery catalog and archive service templates are included. Follow [the deployment guide](../deployment/KATARINA_REDEPLOY.md); credentials and local authorization are provisioned separately. Native MT5 and destination service startup still require destination acceptance.

## Private transport and credentials

- The Hugging Face dataset is private; an anonymous request returned HTTP 401.
- A real archived 106,909-byte file was restored exactly. The tested large-object route used HTTPS through `huggingface.co` and `us.aws.cdn.hf.co`; the Authorization header was not forwarded across origins.
- HF credential storage uses Windows DPAPI and restricted ACLs. The portable POSIX path requires an owner-only secret and private directory. Tokens are not committed or supplied as CLI arguments.
- The broker connection private JSON had an inherited Windows Users read grant. This was removed; its verified ACL now grants only SYSTEM and Administrators. HF, model, owner and relay configuration permissions were also inspected without printing secret contents.
- A credential-pattern scan of tracked source found no matching HF tokens, Google API keys or private PEM headers. This is a scoped scan, not a guarantee about every possible credential format.
- Archive eviction excludes active databases, credentials, tick input and SQLite files with WALs. Reviewed cold outputs can be removed only after remote verification. Preserve a 2 GiB local free-space reserve.

## Recovery evidence

A catalog was rebuilt from the remote repository at revision `a9ce9fca69f912855c4662ace0861c6d8e33fc5e`: 74 manifest versions, without using local archive receipts. A 131,727,360-byte context database restored from that catalog matched the remote SHA-256 and passed SQLite `quick_check=ok` at `2026-10-20T22:09:17Z`. The temporary restored copy was removed after closing the database. A separate fresh-root test exercised destination configuration and restore mapping. Legacy manifests require explicit destination mapping; future snapshots use stable `state/...` identities.

## Coverage and remaining gates

| Area | Observed state |
| --- | --- |
| Cold migration | 59 files / 682,954,784 bytes completed; 7 remaining originals / 5,488,846 bytes retained locally |
| Database coverage | Eight configured: experiment jobs, context, cognitive memory, calibration, network doctor, soak, demo experiments and demo orders |
| Verified full snapshots | Context and cognitive memory verified; six other configured databases still pending |
| Cloud status | `WAITING_CLOUD_RATE_LIMIT`; respect persisted provider HTTP 429 cooldown, not `SYNCED` |
| Next attempt | Cooldown expires 21 October 05:14:52 WIB; scheduled attempt approximately 05:16 WIB, success not guaranteed |
| Observer | Fresh process evidence, 17 market symbols received, successful cycles and worker counters increasing after reload |
| Publisher | `PUBLISHED` after reload |
| DEMO executor | Stale heartbeat at 20:21:32 UTC, task last result 1; not restarted in this storage/security audit |
| Trading authorization | LIVE remains OFF; archive installation does not enable execution |

Only the configured source allowlist is archived. This is not a whole-disk backup: protected authentication and original tick inputs need their own verified transfer. All required database snapshots, destination MT5 telemetry and executor health must pass before moving execution. Stop the old executing host and reconcile broker orders/positions before activating an executor elsewhere.

## Validation

- Linux core unit suite: 1,455 passed.
- Integration: 215 run, OK, 3 skipped; static: 113 run, OK, 4 skipped.
- Dependency-link audit, unified-brain verifier, compile checks and whitespace checks passed.
- Windows HF suite: 27 run, OK, 2 POSIX tests skipped; release manifest tests: 2 passed.
- Windows installer and actual 373-file manifest verification passed.
- MT5 dashboard compiled with 0 errors and 0 warnings.
- GitHub Body CI for the pinned source was queued when checked; it is not reported as passed. PR 129 remains open.

Counts and storage status are observations at audit time. Research record growth is evidence of activity, not proof of better prediction accuracy or model weight updates.
