# Private HF storage migration — Windows test VPS

Repository: `alfaaulia/katarina-research-archive` (private dataset).

## Verified before this continuation

- 26 inactive legacy outputs / QA snapshots, 665,767,277 source bytes, uploaded and remotely downloaded with compressed and restored SHA-256 verification before local eviction.
- A real 2,287,799-byte archived research file restored to a temporary destination; full original SHA-256 matched. Temporary restore was removed afterwards.
- Context and cognitive-memory SQLite backups uploaded and stream verified. Original live databases retained.
- Owner credential stored using Windows DPAPI with SYSTEM / Administrators ACL. Neither credentials nor MT5 account configuration are archive sources.

## Continuation changes

- Backups track daily success per database, so a failed experiment backup no longer repeats successful memory/context backups.
- Recover abandoned staging directories only under the exclusive archive service lock.
- Allow 1,800 seconds for a large consistent SQLite copy, subject to the disk reserve throughout. Prefer uncompressed staging when it fits above the reserve; compress the completed copy once to avoid recompressing changing SQLite pages.
- Extend the inactive legacy result allowlist by 40 files / 22,676,353 bytes after checking running-process and scheduled-task references. This selection itself does not delete files. Existing synchronizer still verifies every remote object and manifest before eviction.
- Increase active experiment database + WAL budget from 512 to 768 MiB. Maintain the independent 2 GiB free-disk guard and 8 MiB write reserve.
- Restart only the continuous read-only observation task to load the capacity change. New worker PID 5576 reported the 805,306,368-byte budget and READY capacity. No LIVE permission changes.

## Validation

- Archive integrity, mutation, eviction allowlist, bounded stream verification, exact restore, Windows path handling, SQLite copy, independent retry clocks and provider cooldown: 16 tests passed on Linux and Windows.
- Capacity tests: 2 passed with PYTHONPATH=src, including a 600 MiB database and WAL accounting / low disk guard.
- Relevant GitHub archive checks and HF smoke checks passed. The broader Body CI was queued; no claim of a complete repository CI pass.

## Operation and restore

Scheduled task `KatarinaHFResearchArchiveSync` runs every 10 minutes, with an exclusive lock. Small JSON snapshots follow that schedule; each full database backup is due after 24 hours since its own last success. The configured cloud archive limit is 80 GB.

Local receipts are in `C:\\KatarinaDev\\config\\hf-storage\\manifests`. Evicted files retain an adjacent `.hf-cloud.json` marker. Invoke the committed `scripts/ai/hf_archive_sync.py --restore-manifest RECEIPT --destination PATH` with the configured Python runtime. Restoration verifies checksums and refuses to overwrite a different existing file. A restored original is protected against automatic re-eviction.

Restore database backups to a separate location for validation; the synchronizer never deletes or replaces a live database. Current tick inputs, active SQLite files, runtime/dependencies and private connection files stay on the VPS.

## Final operational outcome

At 2026-10-20 21:16 UTC:

- 59 inactive files, 682,954,784 source bytes, remotely verified and locally evicted. The seven remaining originals total 5,488,846 bytes and remain intact locally.
- Free disk after staging cleanup: 2,686,300,160 bytes (about 2.69 GB).
- All nine experiment worker files have fresh updates, READY capacity, and the 805,306,368-byte database budget. Their experiment counters increased. The observation process received 17 market symbols and completed a successful cycle.
- Provider upload probe returned HTTP 429 with Retry-After 3,474 seconds. This is an upload action limit; the response's general API counter still showed 910 remaining requests. Do not treat this as storage exhaustion or a credential failure.
- Persisted cooldown prevents cloud requests and expensive SQLite snapshots while waiting. Next allowed retry is 2026-10-20 22:14:52 UTC; the existing ten-minute task is expected to attempt again at 22:19 UTC. No success is promised before observing that run.
- Scheduled task enabled, Ready, last result 0 after a real cooldown-mode run. Current storage status is WAITING_CLOUD_RATE_LIMIT, not SYNCED.
- Context/memory backups remain verified. The large experiment database backup and the seven remaining files are still pending. It must not be called complete until a verified success appears in the per-database clock and sync report.

No LIVE permission changes or credential uploads. Active datasets, live databases and tick inputs remain on the VPS. The storage migration improves archive headroom and the active research budget; it does not prove model accuracy gains.
