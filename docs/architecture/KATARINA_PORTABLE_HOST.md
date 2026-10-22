# Katarina portabel — adaptasi lingkungan

Patokan Owner, 16 Oktober 2026 WIB: satu otak tidak bergantung VPS. VPS, desktop,
laptop, container, atau cloud adalah host; Risk Governor tetap independen.
`katarina.host` menyediakan pemeriksaan lokal dan kebijakan anggaran observasi,
bukan strategi baru atau pemberi izin trading.

## Menjalankan dari tempat mana pun

Python 3.12 dan dependensi repository diperlukan. Setelah checkout dan instalasi
`requirements-stage07.txt` serta versi NumPy di `config/runtime_dependencies_v1.json`:

```sh
python /path/to/Katarina-AI/scripts/ai/run_contextual_market_observer.py --doctor
python /path/to/Katarina-AI/scripts/ai/run_contextual_market_observer.py --offline-research
```

Ganti `/path/to` dengan lokasi checkout sendiri. Tidak harus menjalankan perintah
dari direktori repository. `--doctor` hanya memeriksa host dan kemampuan menulis
state; tidak menginisialisasi MT5 atau menguji jaringan. `--offline-research`
menjalankan satu siklus otak atas bukti lokal, menyimpan checkpoint dan menutup
semua resource. Database kosong menghasilkan kekurangan bukti, bukan pengetahuan
atau keuntungan buatan. Tidak ada daemon, scheduler, atau order otomatis.

Untuk observasi broker, jalankan tanpa kedua flag tersebut pada host yang memiliki
adapter MetaTrader5. Adapter native tetap memiliki persyaratan platform vendor;
ketiadaan adapter tidak menghalangi siklus riset lokal. Transport Cloud Hands
lintas mesin masih integrasi terpisah dan belum diklaim selesai.

## Lokasi dan kontinuitas state

Urutan pemilihan: `--state-dir` → `KATARINA_STATE_DIR` → lokasi bawaan OS:

| OS | Bawaan |
|---|---|
| Windows | LOCALAPPDATA/Katarina/contextual-observer |
| macOS | ~/Library/Application Support/Katarina/contextual-observer |
| Linux | XDG_STATE_HOME/Katarina/contextual-observer atau ~/.local/state/Katarina/contextual-observer |

Tidak ada pemindahan otomatis dari layout lama (`C:\KatarinaDev`, sudah tidak dipakai) atau database legacy.
Di VPS sekarang state berada di `C:\Katarina\state` (diberikan lewat `--state-dir` / `KATARINA_STATE_DIR`).
Untuk mempertahankan pengetahuan saat pindah host: hentikan semua pemilik proses,
salin **seluruh direktori state setelah database ditutup**, arahkan state-dir
ke salinan baru, jalankan doctor, lalu siklus offline. Jangan menyalin SQLite
ketika masih ditulis. Lock berlaku pada direktori/host tersebut, bukan koordinasi
lintas host: jangan menjalankan dua host pada salinan divergen atau shared drive.
Digest checkpoint dan memori tetap divalidasi oleh komponen lama; health harus
menggunakan pengamatan baru. Cadangan dan kredensial tidak masuk git.

## Adaptasi sumber daya yang terbatas dan terlihat

CPU mengikuti affinity dan batas cgroup v2 ketika tersedia. RAM memakai sysconf
serta batas cgroup v2; OS yang tidak menyediakan angka tersebut dilaporkan unknown.
Tidak menebak RAM Windows/macOS. cgroup v1/nested custom mount belum terdeteksi.
RAM yang terdeteksi adalah kapasitas/batas, bukan jaminan memori bebas setiap saat.

| Profil | Kondisi | Batas simbol per pass |
|---|---|---|
| constrained | RAM unknown/<2 GiB atau CPU <2 | 3 |
| balanced | RAM <8 GiB atau CPU <4 | 8 |
| standard | Selain kondisi di atas | 17 |

Ini heuristik penjadwalan, bukan ambang finansial, kualitas strategi, atau SLO.
`--max-symbols 1..17` mengizinkan pilihan eksplisit, dilaporkan lewat hasil host.
Observasi lebih kecil berarti cakupan pasar lebih kecil; tidak dianggap semua
pasar siap. Mode recall offline default fast; tidak ada promosi strategi atau
perubahan risiko karena mesin lebih kuat. Ruang disk <64 MiB atau lokasi state
tidak dapat ditulis memblokir peluncuran. Pemeriksaan awal bukan reservasi disk.

## Bukti dan batas

CI menguji peluncuran dari direktori berbeda, lokasi OS, batas container, profil
kapasitas rendah/unknown, disk rendah, lock, cleanup gagal, siklus offline berulang,
dan pemulihan state yang dipindahkan setelah ditutup pada Linux, Windows, macOS.
Keberhasilan CI tidak membuktikan semua perangkat/arsitektur atau broker didukung.
Kemajuan pengetahuan memerlukan bukti baru yang valid; portabilitas tidak membuat
otak belajar tanpa input. Live OFF, Risk Governor independen, tidak ada koneksi
broker/jaringan yang dinyatakan sehat hanya karena doctor lulus.
