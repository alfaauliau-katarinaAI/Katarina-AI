# WP6 — observer kembali sendiri setelah reboot VPS

Status 4 Nov 2026: **CODE READY, BELUM DITERAPKAN**. Task aktif dan VPS tidak diubah. Penerapan memerlukan izin Owner.

## Kondisi produksi (bukti baca-saja, 4 Nov 2026)

| Aspek | Nilai | Akibat |
|---|---|---|
| Trigger | `LogonTrigger` user Administrator, `InteractiveToken` | Hanya berjalan setelah ada login |
| Autologon Windows | `AutoAdminLogon=0` (Sysinternals Autologon ada di `C:\AutoLogon` tetapi tidak aktif) | Setelah reboot tanpa login, observer **tidak** start |
| Sesi | MT5 dan observer berjalan di sesi RDP 2 yang terputus (boot terakhir 5 Okt) | MT5 butuh desktop interaktif |
| Sudah benar | `IgnoreNew`, `ExecutionTimeLimit PT0S`, `RestartOnFailure` 5 menit × 999, aksi `run-observer.ps1`, mutex `Global\KatarinaReadonlyObserver` + file lock `worker.lock` | Tidak ada instance ganda |
| Launcher | Tidak pernah ada di Git sebelumnya. Kini salinan byte-identik ada di `ops/windows/run-observer.ps1` (commit baseline, SHA-256 `95bf61a9…976e`) | Drift VPS ↔ repo bisa diperiksa |

Preflight: `python scripts/ai/wp6_startup_preflight.py --live` di VPS (baca-saja), atau offline dengan `--task-xml/--launcher/--autologon`. Hasil hari ini **`NOT_READY`**:
- `WP6_NO_AUTOLOGON` (P0);
- `WP6_LAUNCHER_ABANDONED_MUTEX_NOT_HANDLED` (P1): launcher yang mati saat reboot/crash meninggalkan mutex abandoned. `WaitOne` lalu melempar exception sehingga start pertama gagal sampai retry 5 menit;
- `WP6_BATTERY_POLICY_CAN_STOP` (P2).

## Usulan (mode `AUTOLOGON_INTERACTIVE`, perubahan paling kecil)

1. **Owner** mengaktifkan autologon Windows untuk user task dengan Sysinternals Autologon (password disimpan sebagai LSA secret). Claude/Katarina tidak pernah menangani password.
2. Daftarkan `ops/windows/observer-task.autologon.xml` lewat `ops/windows/wp6_apply_observer_startup.ps1`. Isinya sama dengan task sekarang, hanya ditambah delay logon 1 menit dan kebijakan baterai dimatikan.
   - Tanpa `-Apply` = dry-run.
   - Dengan `-Apply`: XML lama di-backup ke `C:\Katarina\backups\wp6-task-<UTC>\` beserta SHA-256, lalu didaftarkan, lalu diverifikasi. Bila gagal, XML lama langsung dipulihkan.
   - Rollback: `-Apply -Rollback <backup.xml>`.
3. Deploy launcher `ops/windows/run-observer.ps1` (perbaikan mutex abandoned) bersama rilis berikutnya. Perlu izin deploy Owner dan gate `KAT-CG-05`.
4. Verifikasi: `wp6_startup_preflight.py --live` → `READY_AFTER_REBOOT`. Lalu uji reboot terjadwal di luar jam pasar (Sabtu) dengan izin Owner. Hasil yang diharapkan:
   - gap dicatat sebagai `observer_outages` dan tidak di-backfill;
   - tidak ada siklus ganda;
   - 0 order.

Alternatif `BOOT_NON_INTERACTIVE` (BootTrigger + S4U/Password, sesi 0) tetap **`BLOCKED_EVIDENCE`** sampai MT5 di sesi 0 terbukti berjalan di host riset terpisah.

## Tes regresi

`tests/unit/operations/test_wp6_startup.py`:
- Task produksi dinilai NOT_READY.
- Definisi usulan + autologon dinilai READY.
- Autologon tidak diketahui, atau user-nya berbeda, ditolak.
- Mode sesi 0 berstatus BLOCKED_EVIDENCE.
- Instance paralel, batas waktu, restart kurang, task nonaktif, dan aksi non-canonical ditolak.
- Launcher tanpa mutex/STOP ditolak.
- Launcher repo hanya berbeda pada perbaikan mutex.
- Skrip apply bersifat dry-run default, backup sebelum perubahan, restore saat gagal, dan tanpa start/stop task, restart komputer, autologon, password, atau MT5.
- Observer kedua ditolak, dan lock pulih setelah crash.
- Gap reboot 15 menit tercatat sebagai outage tanpa duplikat, tanpa backfill, dan 0 order.
