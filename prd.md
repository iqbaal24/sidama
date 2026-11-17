# PRD: Sistem Informasi Dana Masjid (SIDAMA)

| Item | Keterangan |
|---|---|
| Nama produk | SIDAMA – Sistem Informasi Dana Masjid |
| Jenis | Aplikasi web (portofolio, siap dipakai nyata) |
| Framework utama | Django + Django REST Framework |
| Versi dokumen | 1.0 |
| Status | Draft |

---

## 1. Ringkasan

SIDAMA adalah aplikasi web untuk mengelola dan mentransparansikan keuangan masjid. Aplikasi ini mencatat kas masuk dan keluar, mengelola zakat, infak, wakaf, dan kurban, serta menyediakan halaman publik agar jamaah dapat melihat penggunaan dana tanpa login. Tujuan utamanya adalah meningkatkan kepercayaan jamaah dan memudahkan kerja pengurus (DKM), terutama bendahara.

## 2. Latar Belakang dan Masalah

Banyak masjid masih mencatat keuangan secara manual di buku atau Excel yang tidak terstruktur. Akibatnya:

- Laporan keuangan lambat dibuat dan rawan salah hitung.
- Jamaah sulit mengetahui ke mana dana digunakan, sehingga transparansi rendah.
- Bukti transaksi (nota, bukti transfer) mudah hilang.
- Pengelolaan zakat, kurban, dan donasi program tidak terdokumentasi dengan baik.
- Tidak ada jejak siapa mengubah data apa, sehingga rawan sengketa.

## 3. Tujuan dan Metrik Keberhasilan

### 3.1 Tujuan produk
1. Menyediakan pencatatan keuangan masjid yang rapi, cepat, dan bisa diaudit.
2. Menyediakan halaman transparansi publik yang mudah dipahami jamaah.
3. Mengotomatiskan pembuatan laporan keuangan (PDF/Excel).
4. Mendukung pengelolaan zakat, donasi program, dan kurban dalam satu sistem.

### 3.2 Tujuan portofolio
1. Menunjukkan kemampuan Django, REST API, database relasional, dan deployment.
2. Menunjukkan pemahaman proses bisnis nyata (akuntansi sederhana, hak akses, audit).
3. Dapat didemokan secara online dengan data dummy yang realistis.

### 3.3 Metrik keberhasilan

| Metrik | Target |
|---|---|
| Waktu input satu transaksi | < 30 detik |
| Waktu pembuatan laporan bulanan | < 10 detik (otomatis) |
| Skor Lighthouse halaman publik (performance & accessibility) | ≥ 85 |
| Cakupan unit test pada modul inti (keuangan, zakat) | ≥ 70% |
| Waktu muat halaman publik | < 2 detik |
| Seluruh transaksi memiliki audit log | 100% |

## 4. Di Luar Lingkup (Non-Goals)

- Bukan aplikasi akuntansi penuh (tidak ada jurnal debit-kredit lengkap atau neraca formal).
- Tidak memproses uang secara langsung; pembayaran memakai QRIS/transfer yang dikonfirmasi manual atau lewat simulasi.
- Tidak menangani penggajian rinci seperti HRIS.
- Aplikasi mobile native (cukup web responsif).

## 5. Pengguna dan Peran

| Peran | Deskripsi | Hak akses utama |
|---|---|---|
| Admin Sistem | Pengelola teknis aplikasi | Kelola pengguna, peran, pengaturan, seluruh data |
| Ketua DKM | Pimpinan pengurus | Melihat semua data, menyetujui pengeluaran besar, menerbitkan laporan |
| Bendahara | Pengelola keuangan harian | Input transaksi, unggah bukti, kelola zakat, buat laporan |
| Sekretaris / Petugas | Pengurus pendukung | Kelola data jamaah, mustahik, kurban, inventaris aset |
| Jamaah (publik) | Masyarakat umum | Lihat halaman transparansi, hitung zakat, donasi |
| Donatur terdaftar (opsional) | Jamaah yang login | Riwayat donasi pribadi, unduh bukti donasi |

### Persona singkat

- **Pak Hasan (Bendahara, 52 tahun)**: tidak terlalu mahir teknologi, butuh form sederhana dan laporan otomatis.
- **Ibu Rina (Jamaah, 35 tahun)**: ingin tahu dana donasi renovasi dipakai untuk apa, biasanya membuka lewat HP.
- **Pak Ahmad (Ketua DKM, 60 tahun)**: ingin ringkasan saldo dan persetujuan pengeluaran dengan cepat.

## 6. User Stories

| ID | Sebagai | Saya ingin | Agar | Prioritas |
|---|---|---|---|---|
| US-01 | Bendahara | mencatat pemasukan dan pengeluaran per kategori | keuangan tercatat rapi | Must |
| US-02 | Bendahara | mengunggah foto nota/bukti transfer | transaksi punya bukti | Must |
| US-03 | Bendahara | membuat laporan bulanan PDF/Excel otomatis | tidak perlu rekap manual | Must |
| US-04 | Ketua DKM | menyetujui pengeluaran di atas batas tertentu | pengeluaran besar terkontrol | Should |
| US-05 | Jamaah | melihat saldo dan rincian penggunaan dana tanpa login | percaya pada pengelolaan | Must |
| US-06 | Jamaah | melihat progres donasi program (misal renovasi) | tahu target dan capaiannya | Must |
| US-07 | Jamaah | menghitung zakat mal, penghasilan, dan fitrah | mudah menentukan kewajiban zakat | Should |
| US-08 | Jamaah | berdonasi lewat QRIS dan menerima konfirmasi | donasi mudah | Should |
| US-09 | Petugas | mencatat data mustahik dan penyaluran zakat | distribusi terdokumentasi | Should |
| US-10 | Petugas | mengelola pendaftar kurban dan pembagian daging | kurban tertib | Could |
| US-11 | Admin | melihat audit log perubahan data | ada jejak perubahan | Must |
| US-12 | Bendahara | menerima peringatan jika saldo diprediksi tidak cukup | bisa merencanakan kas | Could |
| US-13 | Petugas | mencatat aset masjid (sajadah, pengeras suara) | aset terdata | Could |
| US-14 | Pengurus | menerima notifikasi Telegram saat ada pemasukan besar | cepat tahu perkembangan | Could |

Keterangan prioritas (MoSCoW): **Must** wajib untuk MVP, **Should** sebaiknya ada, **Could** bila waktu cukup.

## 7. Kebutuhan Fungsional

### 7.1 Modul Autentikasi dan Hak Akses
- FR-AUTH-01: Login/logout dengan email atau username dan password.
- FR-AUTH-02: Role-based access control (RBAC) untuk peran pada bagian 5.
- FR-AUTH-03: Ganti password dan reset password via email.
- FR-AUTH-04: Pembatasan percobaan login (rate limiting) untuk mencegah brute force.

### 7.2 Modul Keuangan (Kas Masuk/Keluar)
- FR-KEU-01: CRUD transaksi dengan atribut tanggal, jenis (masuk/keluar), kategori, nominal, deskripsi, penanggung jawab, dan bukti.
- FR-KEU-02: Kategori pemasukan: infak Jumat, infak umum, zakat, wakaf, sedekah, donasi program. Kategori pengeluaran: operasional (listrik, air, kebersihan), honor petugas, kegiatan, pembangunan, penyaluran zakat, lain-lain.
- FR-KEU-03: Unggah bukti (JPG/PNG/PDF, maksimum 5 MB) dengan validasi tipe file.
- FR-KEU-04: Transaksi yang sudah dikunci (periode ditutup) tidak dapat diubah, hanya dikoreksi lewat transaksi pembalik.
- FR-KEU-05: Saldo kas dihitung otomatis dan dipisah per dana (dana umum, dana zakat, dana program/terikat).
- FR-KEU-06: Alur persetujuan: pengeluaran di atas ambang batas (diatur admin) berstatus "Menunggu Persetujuan" sampai disetujui Ketua DKM.
- FR-KEU-07: Pencarian, filter (tanggal, kategori, jenis), dan pengurutan transaksi.

### 7.3 Modul Dana Terikat dan Donasi Program
- FR-PRG-01: CRUD program donasi (judul, deskripsi, target dana, tanggal mulai/selesai, gambar).
- FR-PRG-02: Progres donasi dihitung otomatis dari donasi yang terkonfirmasi.
- FR-PRG-03: Donasi publik oleh jamaah (nama atau anonim, nominal, pesan/doa).
- FR-PRG-04: Pembayaran lewat QRIS statis/transfer; konfirmasi manual oleh bendahara atau simulasi webhook untuk demo.
- FR-PRG-05: Penggunaan dana program dicatat sebagai pengeluaran yang tertaut ke program tersebut.

### 7.4 Modul Zakat
- FR-ZKT-01: Kalkulator zakat mal, zakat penghasilan, dan zakat fitrah (nisab dan harga beras diatur admin).
- FR-ZKT-02: Pencatatan muzakki (pembayar zakat) dan penerimaan zakat, lengkap dengan bukti penerimaan.
- FR-ZKT-03: Data mustahik (penerima) dengan kategori asnaf, alamat, dan catatan verifikasi.
- FR-ZKT-04: Pencatatan penyaluran zakat ke mustahik, terhubung ke transaksi keluar.
- FR-ZKT-05: Laporan zakat: total penerimaan, penyaluran, dan sisa per periode.

### 7.5 Modul Kurban
- FR-KUR-01: Pendaftaran shohibul kurban (jenis hewan, jumlah, pembayaran).
- FR-KUR-02: Pencatatan hewan kurban dan status penyembelihan.
- FR-KUR-03: Pembagian daging ke penerima, dengan kuota dan penandaan sudah menerima (opsional kode QR/kupon).
- FR-KUR-04: Laporan distribusi kurban.

### 7.6 Modul Inventaris Aset
- FR-AST-01: CRUD aset (nama, kategori, jumlah, kondisi, lokasi, tanggal perolehan, nilai).
- FR-AST-02: Riwayat perubahan kondisi dan perawatan aset.
- FR-AST-03: Peminjaman aset (opsional) dengan status dipinjam/dikembalikan.

### 7.7 Modul Laporan
- FR-LAP-01: Laporan keuangan bulanan dan tahunan (PDF dan Excel).
- FR-LAP-02: Laporan per kategori, per dana, dan per program.
- FR-LAP-03: Penerbitan laporan oleh Ketua DKM; laporan terbit otomatis tampil di halaman publik.
- FR-LAP-04: Laporan terjadwal otomatis setiap akhir bulan (Celery beat).

### 7.8 Halaman Publik Transparansi
- FR-PUB-01: Ringkasan saldo kas dan total pemasukan/pengeluaran bulan berjalan.
- FR-PUB-02: Grafik tren pemasukan dan pengeluaran (Chart.js).
- FR-PUB-03: Rincian penggunaan dana per kategori (tanpa data pribadi sensitif).
- FR-PUB-04: Daftar program donasi beserta bar progres.
- FR-PUB-05: Unduh laporan yang sudah terbit.
- FR-PUB-06: Kalkulator zakat dan formulir donasi.
- FR-PUB-07: Tampilan responsif, ringan, dan ramah ponsel.

### 7.9 Modul Notifikasi
- FR-NTF-01: Notifikasi Telegram/WhatsApp (via bot atau API) saat ada pemasukan di atas ambang batas atau laporan terbit.
- FR-NTF-02: Notifikasi dalam aplikasi untuk pengeluaran yang menunggu persetujuan.
- FR-NTF-03: Pengiriman dilakukan asinkron lewat Celery agar tidak memperlambat permintaan.

### 7.10 Modul Prediksi Kas (Fitur Unggulan)
- FR-PRD-01: Memperkirakan pengeluaran bulan depan dari pola 6–12 bulan terakhir (moving average atau regresi sederhana).
- FR-PRD-02: Menampilkan peringatan jika proyeksi saldo kurang dari kebutuhan operasional.
- FR-PRD-03: Visualisasi proyeksi pada dasbor internal.

### 7.11 Audit Log
- FR-AUD-01: Mencatat siapa, kapan, apa yang diubah (nilai lama dan baru) untuk transaksi, zakat, program, dan pengguna.
- FR-AUD-02: Audit log hanya bisa dibaca (tidak bisa diubah/dihapus lewat UI).
- FR-AUD-03: Filter audit log berdasarkan pengguna, tanggal, dan jenis aksi.

## 8. Kebutuhan Non-Fungsional

| Aspek | Kebutuhan |
|---|---|
| Keamanan | Hash password (Argon2/PBKDF2), proteksi CSRF, XSS, SQL injection (ORM), HTTPS, validasi upload, pembatasan akses berdasar peran |
| Privasi | Data mustahik dan donatur tidak ditampilkan lengkap ke publik; opsi donasi anonim |
| Kinerja | Halaman publik < 2 detik, query dioptimalkan (select_related, indeks database), cache untuk data publik |
| Ketersediaan | Dapat berjalan di Docker; backup database berkala |
| Skalabilitas | Pemisahan tugas berat ke Celery worker |
| Aksesibilitas | Kontras warna cukup, ukuran font nyaman, mendukung layar kecil |
| Lokalisasi | Bahasa Indonesia, format Rupiah dan tanggal Indonesia, zona waktu Asia/Jakarta |
| Keterpeliharaan | Kode terstruktur per app Django, linting (ruff/flake8), dokumentasi API otomatis |
| Pengujian | Unit test dan integration test pada modul inti, dijalankan di CI |

## 9. Arsitektur dan Teknologi

### 9.1 Tumpukan teknologi

| Lapisan | Pilihan |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Antrean tugas | Celery + Redis |
| Frontend | Django Templates + Tailwind CSS / Bootstrap, Chart.js, HTMX atau Alpine.js (opsional) |
| Dokumentasi API | drf-spectacular (Swagger/OpenAPI) |
| Laporan | WeasyPrint/ReportLab (PDF), openpyxl (Excel) |
| Notifikasi | Telegram Bot API (utama), WhatsApp gateway (opsional) |
| Deployment | Docker, Docker Compose, Gunicorn, Nginx; hosting seperti Railway/Render/VPS |
| CI/CD | GitHub Actions (lint, test, build image) |
| Penyimpanan berkas | Media lokal atau S3-compatible storage |

### 9.2 Struktur proyek (app Django)

```
sidama/
├── config/            # settings, urls, celery
├── apps/
│   ├── accounts/      # pengguna, peran, autentikasi
│   ├── finance/       # transaksi, kategori, dana, persetujuan
│   ├── programs/      # program donasi & donasi
│   ├── zakat/         # muzakki, mustahik, penyaluran, kalkulator
│   ├── qurban/        # kurban & distribusi daging
│   ├── assets/        # inventaris aset
│   ├── reports/       # generator laporan PDF/Excel
│   ├── notifications/ # Telegram/WA, notifikasi internal
│   ├── forecasting/   # prediksi kas
│   ├── audit/         # audit log
│   └── public/        # halaman transparansi publik
├── templates/
├── static/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### 9.3 Arsitektur tingkat tinggi

Pengguna mengakses Nginx, yang meneruskan ke Gunicorn (Django). Django membaca dan menulis ke PostgreSQL, menyimpan bukti di media storage, dan mengirim tugas berat (laporan, notifikasi, prediksi) ke Redis untuk diproses Celery worker. Celery beat menjalankan tugas terjadwal seperti laporan bulanan.

## 10. Model Data (ERD Tingkat Tinggi)

| Entitas | Atribut utama | Relasi |
|---|---|---|
| User | id, nama, email, password, role, is_active | 1–N Transaction (dibuat oleh) |
| Fund (Dana) | id, nama, tipe (umum/zakat/terikat) | 1–N Transaction |
| Category | id, nama, tipe (masuk/keluar) | 1–N Transaction |
| Transaction | id, tanggal, tipe, nominal, deskripsi, status (draft/menunggu/disetujui/ditolak), bukti, locked | N–1 Fund, Category, User; N–1 Program (opsional) |
| Program | id, judul, deskripsi, target, mulai, selesai, status | 1–N Donation, Transaction |
| Donation | id, program, nama_donatur, anonim, nominal, metode, status (pending/terkonfirmasi), pesan | N–1 Program |
| Muzakki | id, nama, kontak, alamat | 1–N ZakatReceipt |
| ZakatReceipt | id, muzakki, jenis (mal/penghasilan/fitrah), nominal, tanggal | N–1 Muzakki |
| Mustahik | id, nama, asnaf, alamat, status verifikasi | 1–N ZakatDistribution |
| ZakatDistribution | id, mustahik, nominal/barang, tanggal, transaksi | N–1 Mustahik, Transaction |
| QurbanRegistration | id, nama, jenis hewan, jumlah, status bayar | 1–N MeatDistribution |
| MeatDistribution | id, penerima, berat, status diterima | N–1 QurbanRegistration (opsional) |
| Asset | id, nama, kategori, jumlah, kondisi, lokasi, nilai, tanggal_perolehan | 1–N AssetLog |
| AssetLog | id, asset, jenis (perawatan/kondisi/pinjam), catatan, tanggal | N–1 Asset |
| Report | id, periode, jenis, file, status terbit, diterbitkan_oleh | N–1 User |
| AuditLog | id, user, aksi, model, object_id, nilai_lama, nilai_baru, waktu, IP | N–1 User |
| Setting | key, value (nisab, harga beras, ambang persetujuan, dll.) | – |

## 11. Rancangan API (Ringkas)

| Metode | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| POST | /api/auth/login/ | Login (token/JWT) | Publik |
| GET/POST | /api/transactions/ | Daftar & buat transaksi | Bendahara, Ketua, Admin |
| GET/PUT/DELETE | /api/transactions/{id}/ | Detail, ubah, hapus (jika belum terkunci) | Bendahara, Admin |
| POST | /api/transactions/{id}/approve/ | Setujui pengeluaran | Ketua DKM |
| GET | /api/funds/balance/ | Saldo per dana | Pengurus |
| GET/POST | /api/programs/ | Daftar & buat program | Publik (GET), Pengurus (POST) |
| POST | /api/programs/{id}/donate/ | Buat donasi | Publik |
| POST | /api/donations/{id}/confirm/ | Konfirmasi donasi | Bendahara |
| GET/POST | /api/zakat/receipts/ | Penerimaan zakat | Bendahara, Petugas |
| GET/POST | /api/zakat/mustahik/ | Data mustahik | Petugas |
| POST | /api/zakat/distributions/ | Penyaluran zakat | Bendahara |
| GET | /api/zakat/calculate/ | Hitung zakat | Publik |
| GET/POST | /api/qurban/registrations/ | Pendaftaran kurban | Petugas |
| GET/POST | /api/assets/ | Inventaris aset | Petugas |
| POST | /api/reports/generate/ | Buat laporan (async) | Bendahara |
| GET | /api/reports/{id}/download/ | Unduh laporan | Sesuai status terbit |
| GET | /api/public/summary/ | Ringkasan transparansi | Publik |
| GET | /api/forecast/cashflow/ | Proyeksi kas | Pengurus |
| GET | /api/audit-logs/ | Audit log | Admin, Ketua |

Dokumentasi interaktif tersedia di `/api/docs/` (Swagger).

## 12. Alur Utama

### 12.1 Pencatatan pengeluaran dengan persetujuan
1. Bendahara membuat transaksi keluar dan mengunggah nota.
2. Jika nominal di bawah ambang batas, status langsung "Disetujui" dan saldo berkurang.
3. Jika di atas ambang batas, status "Menunggu Persetujuan" dan Ketua DKM menerima notifikasi.
4. Ketua DKM menyetujui atau menolak dengan catatan.
5. Sistem memperbarui saldo, mencatat audit log, dan mengirim notifikasi hasil.

### 12.2 Donasi program oleh jamaah
1. Jamaah membuka halaman program dan memilih nominal.
2. Sistem menampilkan QRIS/rekening beserta kode unik.
3. Jamaah membayar, lalu bendahara mengonfirmasi (atau webhook simulasi).
4. Donasi masuk sebagai pemasukan dana terikat, progres bar bertambah, dan jamaah menerima bukti donasi.

### 12.3 Penutupan periode dan penerbitan laporan
1. Bendahara memeriksa semua transaksi bulan berjalan.
2. Bendahara menutup periode (transaksi terkunci).
3. Sistem membuat laporan PDF/Excel secara asinkron.
4. Ketua DKM meninjau dan menerbitkan; laporan otomatis muncul di halaman publik.

## 13. Rancangan Antarmuka (Daftar Halaman)

**Publik:** beranda transparansi, daftar & detail program, kalkulator zakat, formulir donasi, arsip laporan, tentang masjid.

**Internal:** dasbor (saldo, grafik, transaksi terbaru, persetujuan tertunda), manajemen transaksi, manajemen dana & kategori, program & donasi, zakat (muzakki, mustahik, penyaluran), kurban, aset, laporan, prediksi kas, audit log, pengaturan, manajemen pengguna.

**Prinsip desain:** sederhana, tombol besar, font mudah dibaca (pengguna pengurus bisa berusia lanjut), warna tenang (hijau/putih), mobile-first untuk halaman publik, dan seluruh teks berbahasa Indonesia.

## 14. Keamanan dan Kepatuhan

- Semua halaman internal wajib login dan pengecekan izin berdasarkan peran di setiap view/endpoint.
- Validasi dan sanitasi seluruh input; batasi ukuran dan tipe file unggahan; simpan file dengan nama acak.
- Variabel rahasia (SECRET_KEY, kredensial DB, token bot) disimpan di environment variable, bukan di repositori.
- Aktifkan HTTPS, secure cookies, HSTS, dan `DEBUG=False` di produksi.
- Data pribadi (mustahik, donatur) hanya terlihat oleh peran yang berwenang; halaman publik hanya menampilkan data agregat atau nama yang sudah dianonimkan.
- Backup database terjadwal dan uji pemulihan.
- Audit log tidak dapat dihapus oleh pengguna biasa.

## 15. Strategi Pengujian

| Jenis | Cakupan |
|---|---|
| Unit test | Perhitungan saldo, kalkulator zakat, validasi nominal, aturan penguncian periode |
| Integration test | Alur persetujuan, donasi sampai progres program, pembuatan laporan |
| Permission test | Setiap peran hanya dapat mengakses fitur yang diizinkan |
| API test | Kontrak endpoint dan kode respons |
| Manual/UAT | Uji coba oleh 2–3 orang di luar pengembang (misal teman atau pengurus masjid) |
| Keamanan dasar | Pengecekan OWASP Top 10 sederhana, uji upload file berbahaya |

## 16. Deployment dan Operasional

- Semua layanan (web, db, redis, worker, beat, nginx) dijalankan via `docker-compose`.
- Pipeline GitHub Actions: lint, test, build image, deploy otomatis ke hosting.
- Migrasi database dijalankan otomatis saat rilis.
- Perintah `python manage.py seed_demo` membuat data dummy realistis (transaksi 12 bulan, program renovasi, mustahik, aset).
- Akun demo untuk tiap peran disediakan di README agar rekruter dapat mencoba.

## 17. Roadmap dan Milestone

| Fase | Durasi (perkiraan) | Isi | Hasil |
|---|---|---|---|
| Fase 0 – Persiapan | 3–4 hari | Riset, ERD, setup repo, Docker, CI dasar | Kerangka proyek berjalan |
| Fase 1 – MVP Inti | 2 minggu | Autentikasi, RBAC, keuangan, bukti, saldo, audit log | Pencatatan kas lengkap |
| Fase 2 – Transparansi | 1 minggu | Halaman publik, grafik, laporan PDF/Excel | Jamaah dapat melihat dana |
| Fase 3 – Donasi dan Zakat | 2 minggu | Program donasi, kalkulator, muzakki/mustahik, penyaluran | Modul sosial lengkap |
| Fase 4 – Otomatisasi | 1 minggu | Celery, notifikasi Telegram, laporan terjadwal | Sistem terasa "hidup" |
| Fase 5 – Fitur Unggulan | 1–2 minggu | Prediksi kas, kurban, inventaris aset | Pembeda portofolio |
| Fase 6 – Penyempurnaan | 1 minggu | Pengujian, optimasi, deploy, README, demo | Siap dipamerkan |

Total perkiraan: 8–10 minggu untuk satu pengembang paruh waktu. MVP (Fase 1–2) sudah cukup layak ditampilkan.

## 18. Dokumentasi Portofolio (Deliverables)

- Repositori GitHub dengan commit rapi dan pesan commit bermakna.
- README berisi deskripsi masalah, fitur, tangkapan layar/GIF, cara instalasi, akun demo, dan tautan demo live.
- Diagram arsitektur dan ERD (misal dibuat dengan dbdiagram.io atau draw.io).
- Dokumentasi API (Swagger) dan koleksi Postman.
- Video demo singkat (1–2 menit) sebagai pelengkap.
- Tulisan studi kasus singkat: masalah, keputusan teknis, tantangan, dan pembelajaran.

## 19. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Lingkup terlalu besar | Proyek tidak selesai | Kerjakan bertahap per fase, prioritaskan MVP |
| Integrasi pembayaran rumit | Fitur donasi tertunda | Mulai dengan QRIS statis + konfirmasi manual, webhook disimulasikan |
| Data keuangan salah hitung | Hilangnya kepercayaan | Test otomatis perhitungan saldo, periode terkunci |
| Kebocoran data pribadi | Risiko privasi | RBAC ketat, anonimisasi di halaman publik |
| Kurang pemahaman fikih zakat | Perhitungan keliru | Gunakan nisab dan aturan dari sumber resmi (BAZNAS), bisa diubah admin, beri catatan bahwa hasil bersifat estimasi |
| Biaya hosting | Demo tidak online | Pakai tier gratis dan data dummy, sediakan video demo cadangan |

## 20. Asumsi dan Pertanyaan Terbuka

**Asumsi:** satu instalasi melayani satu masjid; pembayaran donasi dikonfirmasi manual atau disimulasikan; data pada demo adalah data dummy.

**Pertanyaan terbuka:**
1. Apakah akan dibuat multi-masjid (multi-tenant) di masa depan?
2. Apakah laporan perlu mengikuti format standar tertentu (misal pedoman DMI atau BAZNAS)?
3. Gateway WhatsApp apa yang akan dipakai, atau cukup Telegram?
4. Apakah donatur terdaftar (login) dibutuhkan di versi awal?

## 21. Glosarium

| Istilah | Arti |
|---|---|
| DKM | Dewan Kemakmuran Masjid, pengurus masjid |
| Muzakki | Orang yang membayar zakat |
| Mustahik | Orang yang berhak menerima zakat |
| Asnaf | Golongan penerima zakat |
| Nisab | Batas minimal harta wajib zakat |
| Infak/Sedekah | Pemberian sukarela |
| Wakaf | Penyerahan harta untuk kepentingan umum |
| Dana terikat | Dana yang hanya boleh dipakai untuk tujuan tertentu |
| RBAC | Role-Based Access Control, hak akses berdasarkan peran |
| QRIS | Standar kode QR pembayaran Indonesia |
