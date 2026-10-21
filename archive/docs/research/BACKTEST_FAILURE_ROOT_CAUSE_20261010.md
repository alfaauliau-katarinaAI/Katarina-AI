# KATARINA — Penyebab Backtest Belum Lolos (10 Oktober 2026)

## Ringkasan
**Penolakan strategi tidak disebabkan oleh satu bug maupun spread saja.**
Pengujian tick historis mengindikasikan sinyal entry relatif lemah terhadap
target/stop yang dipilih; biaya spread memperburuk hasil. Walau slippage
tambahan disimulasikan nol, rata-rata 2 ATR TP / 1 ATR SL masih negatif.
KATARINA belum menjalankan training model prediktif: kandidat entry adalah
empat keluarga aturan indikator buatan, bukan model AI yang secara mandiri
mempelajari struktur market dari data hingga mendapatkan OOS edge.

## Bukti: data sebenarnya, bukan teori
Berkas input:
- artifacts/historical-brain/broker-aware-seven-symbol-study-v1.json
- artifacts/historical-brain/broker-aware-seven-symbol-study-v1-audit.json
- artifacts/historical-brain/broker-aware-seven-symbol-study-v1-selection.json

Hasil diagnosis tersimpan:
- artifacts/historical-brain/root-cause-broker-seven-symbols-20261010.json

Rentang sampel terpisah 16–31 Agu, 15–30 Sep, dan 1–9 Okt 2026 UTC.
Perhatikan tidak mencakup 1–14 Sep dan Oktober sudah pernah digunakan
untuk riset sebelumnya, bukan holdout tersembunyi.

Empat entry: EMA20 trend reclaim, liquidity-sweep/reclaim,
breakout/retest dan impulse-breakout control, dengan M1/M5 closed bars.
Skenario diagnosis di sini adalah TP2ATR/SL1ATR dan 30 menit.
Ada 2,036 sinyal hipotetis dan 2,035 jalur berakhir valid.
Karena beberapa keluarga/sisi pada simbol yang sama bisa berbarengan,
mereka **bukan 2,035 posisi mandiri dalam satu portofolio**.

Tipe exit: 483 TP (23.7%), 1,525 SL (74.9%),
27 TIME (1.3%). Keputusan TP/SL yang tepat bukan ditentukan
oleh OHLC saja, tapi urutan tick bid/ask broker.
Pada TP2/SL1, ambang impas teoritis paling sederhana adalah
>33.3% kemenangan jika TP tepat 2R dan SL tepat -1R.
Perdagangan yang gap melewati stop menuntut nilai lebih tinggi.
Faktanya proporsi TP hanya 23.7% dan semua kelompok keluarga
dengan sampel luas rata-rata -R pada data ini.

Recheck dampak slippage, XAUUSD saja (549 hasil valid):
- 0 tambahan slippage tick setiap sisi: mean **-0.2061 R**.
- 1 adverse broker tick masing-masing entry dan exit:
  mean **-0.2166 R**.
- 3 adverse broker ticks setiap sisi: mean **-0.2264 R**.
US30 544 valid: 0 tick mean **-0.3125 R**;
1 tick mean **-0.3281 R**; 3 tick mean **-0.3516 R**.

Artinya *slippage tambahan yang diasumsikan* bukan sumber
tunggal kerugian. Bahkan pada skenario 0 tambahan slippage,
spread bid/ask historis tetap dibayar, sehingga data ini
**tidak dapat membuktikan expectancy sebelum spread**.
Belum dilakukan eksperimen pasar midpoint/no-spread yang
menyimulasikan jalur TP/SL ulang.

Median spread/ATR di antara kandidat yang sudah LOLOS
filter penelitian <=0.5 ATR:
- XAUUSD 0.164 (median spread harga $0.30).
- US30 0.260 (3.3 indeks poin).
- NAS100 0.322 (3.4 indeks poin).
- JPN225 0.300 (9.5 indeks poin).
- EURUSD 0.436 (0.00014 = 1.4 pip).
- GBPUSD 0.423 (0.00019 = 1.9 pip).
- USDJPY 0.400 (0.029 = 2.9 pip).
**Selection bias**: median di atas HANYA pada entry ber-spread
<=0.50 ATR, bukan median semua menit broker.
Banyak lagi entry EURUSD/GBPUSD/USDJPY tertolak.
Komisi sebenarnya tidak terkalibrasi dari transaksi: koneksi
MT5 Valetax demo mempunyai nol posisi historis ber-simbol
yang memadai untuk mengukur commission, slippage dan fee.
Situs Valetax mencantumkan Standard komisi nol dan spread
'from 1.2 pip', bukan janji spread 1.2 pip setiap detik.

## Kekurangan hipotesis dan metodologi
- Sinyal berbasis konfirmasi candle, EMA, ADX, highs/lows dan
  tick-volume, bukan confirmation market structure shift,
  displacement setelah sweep, FVG valid, lokasi HTF segar,
  pengukuran likuiditas atau order flow nyata.
- KATARINA belum melatih dan menguji prediksi yang mengungguli
  random atau baseline waktu-matched. Banyak filter indikator
  hanya bisa mengurangi sampel dan menaikkan risiko overfit.
- M1 mempunyai market noise tinggi; ATR 1 menit sering
  tidak memadai jika menjadi jarak stop sekaligus penentu
  target 2 ATR tanpa pembuktian pergerakan follow-through.
- 99%-bound positif tiap dua periode pengembangan adalah
  gerbang penelitian ketat. Hal ini dapat menolak edge kecil
  positif, tetapi penolakan pada riset terakhir **bukan semata
  disebabkan ketatnya ambang**: rata-rata R dan PF sebagian
  besar memang negatif.
- Komisi, historical trade conditions, volatility around
  news/rollover, fill queue dan market-impact tidak bisa
  diketahui dari tick quote saja.
- Skenario 24,432 adalah 2,036 kandidat diulang 12 kali,
  bukan 24,432 sinyal independen; lebih banyak kombinasi
  indikator tidak berarti lebih besar bukti.
- Cross-family dan multi-pair correlation tidak dikonsolidasikan
  menjadi satu feasible hedging/netting portfolio.
- Titik awal backtest yang pernah digunakan untuk menemukan
  aturan sebelumnya tidak dapat diperlakukan sebagai OOS.
- Sebagian jarak stop historis dibandingkan current broker
  SYMBOL_TRADE_STOPS_LEVEL; nilai historisnya tidak direkam.
- Indikator Wilder ADX internal belum diverifikasi buffer-by-buffer
  dengan MT5 iADX dalam pengujian ini. EMA internal dibangkitkan
  dengan window warmup; alignment dengan indikator MT5 tetap
  memerlukan test parity.

## Perbaikan yang harus diprioritaskan
1. Lakukan studi baseline: sinyal random/blind entry yang cocok
   tanggal, jam, side, volatilitas, spread, dan SL/TP; uji
   apakah setup benar-benar lebih baik daripada baseline.
2. Ukur MFE/MAE per entry terhadap ATR dan distribusi first
   passage ke SL/TP, dengan bucket volatilitas, market session
   dan lokasi level. Jangan pilih TP/SL berdasarkan profit
   dari tanggal yang kemudian disebut holdout.
3. Audit indikator (MT5 iADX parity, close-bar timestamps, valid
   candle history), kontrak dan broker server tick completeness.
4. Perkenalkan hipotesis struktur yang terdaftar terlebih dahulu:
   sweep + market structure shift + displacement/FVG dan konfirmasi;
   dibandingkan dengan kontrol sederhana pada periodisasi yang
   bebas dari pemilihan parameter berulang.
5. Cari akun/instrumen dengan total biaya terhadap target yang
   masuk akal; jangan memaksa setup spread tinggi menjadi layak
   hanya dengan menaikkan batas spread/ATR.
6. Pisahkan kembali development dan *truly untouched future test*
   (atau prospective forward read-only), sertakan biaya slippage
   yang bisa dibuktikan dan uji sensitivitas.

**Keputusan:** NO_TRADE. Tidak ada jaminan bahwa salah satu metode
baru akan profitable; perbaikan bertujuan membedakan kendala data,
kelemahan alpha dan kesalahan simulasi sebelum menghabiskan banyak
siklus optimasi lagi.

Sumber eksternal:
https://www.mql5.com/en/docs/runtime/testing
https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
https://valetax.com/account-types/pro/
