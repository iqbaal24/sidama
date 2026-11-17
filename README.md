---
title: SIDAMA — Sistem Informasi Dana Masjid
emoji: 🕌
colorFrom: green
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Transparansi keuangan masjid (Django) — demo publik
---

# SIDAMA — Sistem Informasi Dana Masjid

Demo publik aplikasi pencatatan dan transparansi keuangan masjid, dibangun dengan
Django + Django REST Framework.

**Yang bisa dicoba di Space ini**

- Ringkasan saldo kas, grafik arus kas 12 bulan, rincian pengeluaran per kategori
- Daftar program donasi + formulir donasi (mode demo: donasi langsung terkonfirmasi)
- Kalkulator zakat mal, penghasilan, dan fitrah
- Arsip laporan bulanan yang bisa diunduh (PDF & Excel)

Mode ini berjalan dengan `SIDAMA_PUBLIC_ONLY=1`: dashboard pengurus, admin, dan API
terautentikasi sengaja tidak dimount (404) agar hanya tampilan jamaah yang tayang.

Kode lengkap, dokumentasi, dan cara menjalankan versi penuh (dengan dashboard pengurus,
persetujuan pengeluaran, audit log, dan prediksi kas):

**https://github.com/iqbaal24/sidama**

---

## Fitur lengkap (versi repo)

- Kas masuk/keluar berkategori, bukti nota, saldo per dana (umum/zakat/terikat)
- Alur persetujuan Ketua DKM untuk pengeluaran di atas ambang batas
- Tutup buku per periode + transaksi pembalik
- Program donasi dengan dana terikat sendiri
- Zakat: muzakki, mustahik, penerimaan, penyaluran, kalkulator
- Kurban, distribusi daging, inventaris aset
- Laporan PDF/Excel otomatis, notifikasi Telegram, prediksi kas
- Audit log read-only untuk setiap perubahan data
- 58 unit/integration test, CI GitHub Actions

Data pada demo adalah data dummy yang dibuat ulang otomatis setiap container hidup.
