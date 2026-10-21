# LAPORAN KATARINA AI — Pengujian Independen dan Strategi Per-Simbol
**Tanggal:** 11 Oktober 2026 (WIB)
**Lingkungan:** Windows VPS, MetaTrader 5 ALFA, broker Valetax demo (.vx).
**Keputusan risiko:** \`NO_TRADE\` — tidak ada pembukaan posisi otomatis.

## Ringkasan eksekutif
Riset memperbaiki dua kendala besar: (1) strategi tidak lagi disamaratakan
untuk semua pair; (2) penyaringan harus mengikuti riwayat dan jam quote
yang benar-benar disediakan broker. NAS100 masih kandidat paling menarik,
tetapi efek terhadap random timestamp cocok waktu/ATR/spread belum
signifikan. Gold mempunyai banyak sampel setelah perbaikan entry khusus
emas, tetapi menghasilkan expectancy negatif. US30 dan JPN225 tidak
stabil antarbualan. Jangan mengaktifkan satu pun strategi berdasarkan
laporan riset ini.

## A. Uji NAS100: pembanding yang lebih kuat
Hipotesis **nas_trend_pullback_continuation_v1**:
- Strategi yang telah dibekukan di commit lokal 0c75dcb, bukan
  diubah untuk mendapatkan hasil lebih tinggi.
- M1 pullback/reclaim terhadap EMA20 dengan konteks M5 tren + ADX,
  sesi New York, stop di swing 6-candle, TP 1,65 x risiko;
  durasi maksimal 45 menit.
- Semua simulasi memakai historis real bid/ask quote broker dengan
  1 tick slippage adverse saat entry dan 1 tick saat exit.
- Juli (32 entry): **+0,292 R**; Agustus (7): **+0,544 R**;
  September (15): **+0,0118 R**; Oktober 1–9 (7): **+0,0473 R**.
- 61 entry total rata-rata **+0,2240 R**, PF **1,465**; 36
  hari sinyal UTC. 95% CI mean R dengan resampling per hari:
  **−0,0571 hingga +0,4759 R**. Masih melintasi nol.
- Kontrol lama berupa entry terbalik di tick persis sama:
  +0,5797 R selisih rata-rata arah, namun TIDAK sama dengan
  entry acak dalam kondisi pasar serupa.

### Kontrol waktu acak dicocokkan (BARU)
- 61 sinyal asli; 57 mendapat matched control memadai,
  4 tidak terpasangkan (3 tidak ada pool waktu/ATR, 1 tidak
  mendapat matched spread).
- **226 entry kontrol aktual** memakai tanggal UTC yang sama,
  jam New York yang sama, maksimal ±120 menit dari sinyal,
  minimum 45 menit terpisah, ATR ±30%, spread/ATR ±0,12,
  arah yang sama, rasio risiko/target ke ATR yang sama,
  hingga 4 kontrol per sinyal, random seed tetap.
- NAS100 pada 57 signal = **+0,2240 R**.
- Kontrol timestamp sebanding = **+0,1043 R**.
- Selisih = **+0,1197 R**, 95% bootstrap per hari
  **−0,2660 sampai +0,4997 R**.
- Interval positif NEGATIF melintasi nol, artinya belum
  dapat dinyatakan NAS100 mengungguli kontrol secara statistik.
- Data Juli–Oktober telah pernah digunakan KATARINA dalam riset
  sebelumnya. Ini bukan pengujian *untouched prospective holdout*,
  apalagi hasil transaksi riil. Komisi/slippage riil belum diukur.
- Audit independen memverifikasi kedua laporan sumber SHA256,
  tanggal dan jarak matched-time, ATR/spread toleransi, bobot
  rata-rata dan resampling reproduksibel. Status: riset saja.

Bukti:
\`C:\KatarinaDev\artifacts\historical-brain\nas100-matched-control-20261011-v1.json\`
\`C:\KatarinaDev\artifacts\historical-brain\nas100-matched-control-20261011-v1-audit.json\`

## B. XAUUSD — strategi khusus baru
\`gold_sweep_rejection_30m_structural_v2\` menggunakan M1 20-bar
liquidity sweep dan candle penolakan yang kembali ke rentang,
stop di luar wick + 0,15 ATR, target ke 75% rentang lawan.
Tidak mengambil model NAS100. Dibanding versi v1 yang hanya
mendapat 1 entry, pendekatan v2 memiliki **346** kandidat
spread/stop-eligible:
- Agustus: 129 selesai, **−0,290 R**, PF 0,645.
- September: 142 selesai dan satu exit tak tersedia,
  **−0,272 R**, PF 0,664.
- Oktober: 74 selesai, **−0,201 R**, PF 0,744.
- **345 berhasil diukur**, 1 tidak lengkap. Semuanya negatif.
- Peningkatan jumlah sinyal TIDAK menyelesaikan masalah
  prediksi arah yang tepat. Metode v2 tetap dalam arsip
  eksperimen dan tidak diaktifkan.

## C. US30 — strategi khusus alternatif
\`dow_newyork_failed_break_mean_revert_v2\`: penolakan breakout
range pembukaan New York, stop di luar wick dan target
kembali ke midpoint range. Berbeda dari metode v1 breakout.
- Agustus: 9 entry, **+0,762 R**, PF 3,169.
- September: 11 entry, **−0,413 R**, PF 0,468.
- Oktober: 8 entry, **−0,294 R**, PF 0,678.
- **28 entry** valid. Gagal konsistensi. Jangan memilih
  bulan Agustus saja.

## D. JPN225 — menemukan dan memperbaiki masalah data
Investigasi source quote MT5 September 21–25 menemukan JPN225
mempunyai **nol candle M1 pukul 00.00–00.59 UTC**; yang pertama
tampak sekitar 01.01 UTC. Penelitian pertama secara keliru
mengasumsikan 09.00 JST / 00.00 UTC adalah awal harga CFD broker.
Selain itu fungsi \`intact(...)\` terdahulu mensyaratkan panjang
persis 120 bar, sehingga penggunaan 35 bar untuk opening session
ditolak salah. Laboratorium JPN khusus v2 sekarang menghitung
opening range dari **30 menit setelah kutipan pertama tersedia**,
dan meminta 35 candle M1 + 6 candle M5 terbaru valid,
tanpa menciptakan candle di jam pasar broker tutup.
- Agustus: 8 valid, **+0,459 R**, PF 2,188.
- September: 8 valid, **−0,0066 R**, PF 0,987.
- Oktober: 5 valid, **−1,056 R**, PF 0.
- Total 21, semuanya diaudit, 0 transaksi broker riil.
- Sinyal sudah bisa diamati, tetapi strategi belum layak.

Catatan penting: pembukaan 01.01 UTC adalah **observasi
ketersediaan quote broker**, bukan klaim jam buka bursa
saham Jepang. CFD dapat mempunyai sesi broker yang berbeda.

## E. Forex tidak memakai strategi indeks
EURUSD, GBPUSD dan USDJPY tetap mempunyai playbook
khusus mereka sendiri. Pada akun demo saat ini, seluruh
setup dalam tiga periode sampel tertolak biaya spread
relatif ATR menurut anggaran riset yang ditetapkan.
Tidak ada backfill dari model NAS100 atau indeks lainnya.

## F. Audit eksekusi dan batas hasil
- Alternatif emas, US30, JPN awal:
  **374** jalur entry, **1.122** skenario slippage
  (0/1/3 ticks masing-masing sisi), **1.119** selesai,
  tiga record dari 1 entry emas tanpa exit quote valid.
- JPN225 setelah perbaikan sesi:
  **21** jalur, 63 skenario, semuanya berhasil diukur.
- Semua statistik adalah **simulasi harga historis**
  pada bid/ask MT5, bukan deal executed.
- Dalam kode yang baru, penelitian alternatif tidak
  didaftarkan sebagai sinyal live/pemantau produksi karena
  tidak lolos hasil; observer tetap memakai registry khusus
  per simbol versi v1 dengan \`NO_TRADE\`.
- Besaran spread riil historis sudah masuk ke perhitungan
  harga masuk/keluar; tambahan slippage 1 broker tick
  saat entry dan exit bersifat **skenario**, belum bukti
  fill/commission riil. Perubahan syarat broker di
  masa lampau tidak dapat dibuktikan dari metadata sekarang.
- Ketidakpastian NAS di atas belum mengoreksi semua
  multiple testing / pemilihan strategi sebelumnya.

Bukti:
\`C:\KatarinaDev\artifacts\historical-brain\alt-gold-dow-nikkei-playbooks-v2.json\`
\`C:\KatarinaDev\artifacts\historical-brain\alt-gold-dow-nikkei-playbooks-v2-audit.json\`
\`C:\KatarinaDev\artifacts\historical-brain\alt-nikkei-broker-session-v4.json\`
\`C:\KatarinaDev\artifacts\historical-brain\alt-nikkei-broker-session-v4-audit.json\`

## G. Keputusan teknis dan riset berikutnya
1. Pertahankan NAS100 v1 sebagai **prioritas shadow-forward**,
   bukan strategi otomatis live: expectancy absolut bootstrap
   melewati nol dan matched-control lift juga belum signifikan.
2. XAUUSD v2, US30 v2, JPN225 v2 tetap di folder
   alternatif eksperimen, bukan rekomendasi entry.
3. Untuk JPN225, pisahkan kalender sesi CFD broker dari
   jam pasar tunai Tokyo; lakukan validasi sesi pada
   lebih banyak hari dan periode DST broker.
4. Untuk Forex, evaluasi kondisi spread/kontrak akun secara
   independen; jangan menaikkan batas biaya semata-mata
   demi memperbanyak sinyal.
5. Dapatkan data sampel validasi prospektif yang benar-benar
   belum dilihat, variasi spread dan komisi nyata,
   risiko posisi simultan lintas pair, serta waktu berita
   dari arsip vintage yang dapat dipercaya.
6. Hindari klaim win rate tinggi atau payout dari simulasinya.

**Status final:** \`NO_TRADE\`, \`live_execution_enabled=false\`.
