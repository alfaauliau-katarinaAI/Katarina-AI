# WP6 — observer kembali sendiri setelah reboot VPS

Status 10 Nov 2026: **PREPARED, `NOT_READY`**.

- Task dan launcher sudah diterapkan pada 4 Nov (RH-014).
- Satu-satunya blocker konfigurasi adalah `WP6_NO_AUTOLOGON`, yang menunggu aksi Owner.
- Uji reboot belum dijalankan.
- `READY_AFTER_REBOOT` hanya boleh diberikan oleh `wp6_reboot_check.py check` sesudah reboot sungguhan.

## Kondisi produksi (audit baca-saja K3, 10 Nov 2026)

| Aspek | Nilai |
|---|---|
| Task `Katarina-Readonly-Observer` | `LogonTrigger` Administrator + delay PT1M, `InteractiveToken`, `IgnoreNew`, `ExecutionTimeLimit PT0S`, `RestartOnFailure` 5 menit × 999, baterai tidak menghentikan. Status Running |
| Launcher | `C:\Katarina\run-observer.ps1` = `ops/windows/run-observer.ps1`, berisi mutex `Global\KatarinaReadonlyObserver` dengan penanganan abandoned mutex dan marker `STOP_OBSERVER` |
| Instance | Satu rantai observer: redirector venv `Scripts\python.exe` → interpreter `python312` (2 proses, 1 instance). Satu `terminal64.exe`. Keduanya berjalan di sesi interaktif 2 |
| Autologon | `AutoAdminLogon=0`, `DefaultUserName` kosong, tidak ada `DefaultPassword`. Sysinternals Autologon tersedia di `C:\AutoLogon` |
| Task lain | `Katarina-Stage0-Daily-Health` (SYSTEM, harian, baca-saja). `Katarina-DC-Connection-Watchdog` (SYSTEM, 3 menit) memulihkan Desktop Commander setelah reboot. Sisa task uji lama: `ChatGPTUserTest`, `DNSTT-Test-AutoCleanup` (perlu keputusan Owner) |
| Windows Update | Tidak ada kebijakan AU; `PendingReboot` false. Reboot otomatis Windows Update tetap mungkin terjadi, dan karena itulah autologon diperlukan |
| Boot terakhir | 4 Okt 2026 22:45 UTC |

Preflight konfigurasi: `python scripts/ai/wp6_startup_preflight.py --live` (baca-saja). Hasil 10 Nov: `NOT_READY`, `WP6_NO_AUTOLOGON`.

Verdict preflight paling tinggi adalah **`READY_FOR_REBOOT_TEST`**. Preflight hanya menilai konfigurasi, jadi tidak boleh lagi disebut `READY_AFTER_REBOOT`.

## Evaluasi mekanisme start setelah reboot

| Opsi | Penilaian |
|---|---|
| **Sysinternals Autologon** (password disimpan sebagai LSA secret) + task `LogonTrigger` yang ada | **Direkomendasikan.** Kompatibel dengan MT5 yang butuh desktop interaktif. Perubahan paling kecil. Dijalankan oleh **Owner** di konsol VPS; Claude tidak pernah melihat password |
| Registry `DefaultPassword` plaintext | **Ditolak.** Password terbaca oleh siapa pun yang punya akses registry |
| `BootTrigger` + S4U/Password (sesi 0) | **`BLOCKED_EVIDENCE`.** MT5 di sesi 0 belum terbukti. Wajib diuji di host riset terpisah dulu |
| Tanpa autologon (login RDP manual setelah reboot) | Aman, tetapi observer mati sampai ada login. Outage tercatat jujur dan tidak di-backfill |

Risiko autologon: siapa pun yang punya akses fisik/konsol mendapat desktop Administrator. Mitigasi:

- batasi akses konsol hypervisor;
- akses RDP tetap memakai password kuat.

## Prosedur uji reboot (butuh izin Owner terpisah; Sabtu, pasar tutup)

1. **Owner**: aktifkan autologon dengan `C:\AutoLogon\Autologon.exe` untuk user task (Administrator).
2. Jalankan preflight `wp6_startup_preflight.py --live`. Hasil yang diharapkan: `READY_FOR_REBOOT_TEST`.
3. Rekam baseline dan backup. DB disalin dengan backup online SQLite ke folder baru, lalu `integrity_check` dijalankan pada salinan, bukan DB live:
   `python scripts/ai/wp6_reboot_check.py baseline --output C:\Katarina\state\wp6\baseline-<UTC>.json --backup-dir C:\Katarina\backups\wp6-reboot-<UTC>`
4. Tunggu backup selesai. Catat hash dan RAM bebas.
5. **Owner** me-reboot VPS.
6. Setelah ±15 menit, jalankan:
   `python scripts/ai/wp6_reboot_check.py check --baseline <baseline.json> --output C:\Katarina\state\wp6\post-reboot-<UTC>.json`
   - `READY_AFTER_REBOOT` hanya jika semua syarat ini terpenuhi:
     - boot lebih baru dari baseline;
     - tepat satu rantai observer dan satu MT5, di sesi interaktif yang sama;
     - siklus OK pertama dengan offset jam ≤ 20 menit setelah boot;
     - jeda reboot terlihat (≥ 180 s, tanpa backfill) dan tidak ada siklus duplikat;
     - `quick_check=ok`;
     - total order 0;
     - task XML dan launcher sama dengan baseline.
   - Selain itu `NOT_READY` (dengan alasan) atau `NOT_TESTED`.
7. Jalankan `check_stage0_health.py --since official`. Outage reboot tercatat sebagai outage biasa; definisi keberhasilan tidak diubah.

## Rollback

| Masalah | Langkah |
|---|---|
| Autologon tidak diinginkan | Owner menjalankan `Autologon.exe` lalu memilih *Disable* |
| Task | `ops/windows/wp6_apply_observer_startup.ps1 -Apply -Rollback C:\Katarina\backups\wp6-task-20261104T131438Z\Katarina-Readonly-Observer.xml` |
| Observer tidak start | Login RDP sebagai Administrator. Task `LogonTrigger` menjalankan launcher. Jika tidak, `schtasks /run /tn Katarina-Readonly-Observer` (izin Owner) |
| DB rusak | Hentikan observer (`continuous.stop`), pulihkan salinan dari `wp6-reboot-<UTC>` yang hash dan `integrity_check`-nya tercatat di baseline |

## Tes regresi

- `tests/unit/operations/test_wp6_startup.py` mencakup:
  - definisi task dan launcher;
  - verdict konfigurasi `READY_FOR_REBOOT_TEST`;
  - mode sesi 0 berstatus `BLOCKED_EVIDENCE`;
  - kompatibilitas PowerShell 4;
  - skrip apply dry-run default dengan backup dan restore.
- `tests/unit/operations/test_wp6_post_reboot.py` mencakup:
  - rantai redirector venv dihitung satu instance;
  - parsing waktu WMI;
  - `READY_AFTER_REBOOT` hanya setelah boot baru;
  - `NOT_TESTED` tanpa baseline atau reboot;
  - observer ganda atau MT5 di sesi 0 gagal;
  - order, siklus terlambat, backfill dan siklus tanpa jam gagal;
  - DB dibuka baca-saja;
  - backup tidak menimpa salinan yang sudah ada;
  - CLI tanpa perintah reboot, kill, task, autologon atau order.
