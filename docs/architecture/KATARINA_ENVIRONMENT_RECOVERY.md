# Pemulihan environment PC yang terbatas

16 Oktober 2026 WIB. Pemulihan ini mengelola **environment dependensi privat**.
Tidak menulis ulang strategi/source, mengubah Risk Governor, mengaktifkan trading,
mengganti akun/kredensial, memperbaiki database Owner, atau mengunduh source baru.
Tidak ada klaim bisa memperbaiki semua ketidakcocokan OS/perangkat.

## Urutan saat setup/start

1. Python 3.12 harus tersedia lebih dahulu; interpreter bootstrap tidak dipasang
   atau diganti otomatis. Paket native MT5 tetap memerlukan Windows 64-bit.
2. Cari environment aktif yang terdaftar. Legacy `.venv-pc` sehat tetap dapat
   dipakai bila belum ada pointer; tidak dihapus atau dipindahkan.
3. Verifikasi import NumPy, versi Python/dependensi (`pyzmq`/`tornado` tidak lagi dibutuhkan sejak transport
   KAT1/ZMQ dipensiunkan 22 Okt 2026). MT5 diperiksa
   hanya bila diminta eksplisit ketika setup/repair atau tercatat wajib sebelumnya.
4. Bila sehat, langsung gunakan tanpa pip/download. Bila rusak dan environment
   sebelumnya sehat, jalankan acceptance sintetis pada state sementara sebelum
   memilih kembali environment tersebut.
5. Jika perlu pengganti, ambil lock dan bangun kandidat baru di lokasi finalnya,
   pasang dependensi repository, lalu uji import dan acceptance sintetis sungguhan.
   Acceptance menggunakan state buatan sementara, tidak menyentuh memori Owner.
6. Hanya kandidat yang lulus yang dipilih melalui penggantian pointer atomik.
   Virtualenv tidak di-rename agar path interpreter/entry point tetap valid.
7. Gagal memasang/menguji: pointer lama tetap, kandidat dan environment lama
   dipertahankan; catat alasan generik tanpa output pip/URL/token.

Lock mencegah dua proses memperbaiki lingkungan bersamaan. Satu kandidat per
pemanggilan, timeout pip maksimum 600 detik/request, batas probe 30 detik dan
acceptance 90 detik. Kegagalan memberi cooldown 5 menit pada percobaan otomatis;
perintah `repair` eksplisit boleh mencoba lagi. Tidak ada daemon/retry background.

## Lokasi dan audit

Default `.katarina-envs` di folder source. Jika folder source tidak dapat ditulis,
gunakan `~/.katarina/environments/<hash-lokasi-checkout>`. `KATARINA_ENV_HOME`
mengizinkan lokasi privat eksplisit; jika pilihan eksplisit tidak dapat ditulis,
blokir, tidak beralih diam-diam. Hash ini pemisah lokasi, bukan identitas keamanan.

`active.json` mencatat kandidat aktif, sebelumnya, serta kebutuhan MT5. Nama
kandidat dibatasi dan path traversal ditolak. Pointer rusak memblokir, tidak
mengizinkan pemilihan executable sembarang. `recovery-audit.jsonl` menyimpan fase
serta alasan tetap tanpa exception text/credential. Kandidat gagal tidak dihapus
otomatis; setelah semua proses berhenti, pemilik dapat meninjau dan membersihkan
folder environment yang tidak digunakan. Jangan menghapus direktori state.

**Lokasi memori/checkpoint tidak dipindahkan otomatis.** Folder state tidak dapat
ditulis tetap memblokir; pengalihan diam-diam bisa membuat pengetahuan tampak hilang.
Rollback di sini hanya pemilihan environment dependensi, bukan rollback source,
rollback database, transaksi broker, atau recovery posisi live.

## Perintah

```sh
python3.12 katarina_pc.py repair-status
python3.12 katarina_pc.py repair
python3.12 katarina_pc.py test --no-auto-repair
```

Windows memakai `py -3.12`. `setup --mt5` atau `repair --mt5` adalah permintaan
instalasi adapter native secara eksplisit; tidak login atau membuka MT5.
`doctor` dan `repair-status` tidak memasang environment baru.
`START_KATARINA.bat` sekarang memeriksa dan mencoba pemulihan dependensi bila perlu.
Internet dan ruang disk diperlukan untuk pemasangan baru. Persyaratan platform,
izin admin, credential, sertifikat, atau ketiadaan wheel kompatibel tetap dapat
memerlukan pemilik. Jika aplikasi gagal padahal import/versi sehat, jangan
menganggapnya kerusakan environment atau mengubah source/risk agar uji lulus.

## Pengujian

Fault injection memeriksa pemasangan/smoke gagal, pointer tetap, rollback tervalidasi,
lock, cooldown, redaksi, path pointer, lokasi source read-only, dan state/source yang
tidak berubah. CI Linux/Windows/macOS juga memasang paket ZIP bersih, membuat
interpreter kandidat aktif sementara tidak tersedia, lalu membuktikan startup
membangun pengganti yang lulus tanpa menghapus environment lama. Kerusakan hanya
disuntikkan ke paket sementara milik CI, tidak ke komputer pemilik.
