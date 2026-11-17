# Arsitektur SIDAMA

## Ringkasan

SIDAMA adalah aplikasi monolit Django dengan pemisahan tugas per app. Halaman publik dan
internal memakai Django Templates; integrasi eksternal (Telegram) dan tugas berat
(laporan, notifikasi) dijalankan melalui Celery.

```mermaid
flowchart TB
    subgraph Client
        B[Browser pengurus]
        J[Browser jamaah]
    end

    subgraph Edge
        N[Nginx :80/:8080]
    end

    subgraph App
        G[Gunicorn]
        D[Django + DRF]
        T[Django Templates]
        S[Static files]
    end

    subgraph Data
        P[(PostgreSQL)]
        M[(Media storage)]
        R[(Redis)]
    end

    subgraph Async
        W[Celery worker]
        C[Celery beat]
    end

    TG[Telegram Bot API]

    B --> N
    J --> N
    N --> G
    G --> D
    D --> T
    N --> S
    D --> P
    D --> M
    D --> R
    R --> W
    R --> C
    C --> W
    W --> P
    W --> TG
```

## Alur utama

### 1. Pencatatan pengeluaran dengan persetujuan

```mermaid
sequenceDiagram
    participant B as Bendahara
    participant S as SIDAMA
    participant K as Ketua DKM

    B->>S: Catat pengeluaran + bukti
    alt nominal ≤ ambang batas
        S->>S: status Disetujui, saldo berkurang
    else nominal > ambang batas
        S->>S: status Menunggu Persetujuan
        S-->>K: Notifikasi persetujuan
        K->>S: Setujui / tolak + catatan
        S->>S: Perbarui saldo + audit log
        S-->>B: Notifikasi hasil
    end
```

### 2. Donasi program

```mermaid
sequenceDiagram
    participant J as Jamaah
    participant S as SIDAMA
    participant B as Bendahara

    J->>S: Isi form donasi (QRIS/transfer)
    S->>S: Donasi status pending + kode unik
    S-->>J: Instruksi pembayaran
    B->>S: Konfirmasi donasi
    S->>S: Buat pemasukan dana terikat program
    S->>S: Progres program bertambah
    S-->>J: Status donasi terkonfirmasi
```

### 3. Tutup buku dan laporan

```mermaid
sequenceDiagram
    participant B as Bendahara
    participant S as SIDAMA
    participant C as Celery
    participant K as Ketua DKM

    B->>S: Tutup periode
    S->>S: Kunci seluruh transaksi bulan itu
    B->>S: Buat laporan
    S->>C: Tugas generate PDF/Excel
    C-->>S: Berkas tersimpan
    K->>S: Terbitkan laporan
    S->>S: Laporan tampil di halaman publik
```

## Modul dan tanggung jawab

| App | Tanggung jawab |
|---|---|
| `core` | Pengaturan berbasis database, dashboard, komponen list/form bersama, `seed_demo` |
| `accounts` | User kustom, peran (admin/ketua/bendahara/petugas/donatur), login email/username |
| `audit` | Model audit, middleware konteks request, signal perubahan data |
| `finance` | Dana, kategori, transaksi, persetujuan, periode/tutup buku |
| `programs` | Program donasi, donasi, konfirmasi → dana terikat |
| `zakat` | Muzakki, mustahik, penerimaan, penyaluran, kalkulator |
| `qurban` | Pendaftaran kurban, distribusi daging, laporan |
| `assets` | Inventaris dan riwayat aset |
| `reports` | Generator PDF/Excel, penerbitan, jadwal Celery |
| `notifications` | Notifikasi internal, transport Telegram |
| `forecasting` | Proyeksi kas dari rata-rata historis |
| `public` | Halaman transparansi, program, zakat, laporan |
| `api` | Serializer, viewset, permission, skema OpenAPI |

## Keputusan desain

- **Saldo dihitung, bukan disimpan.** `fund_balance()` mengagregasi transaksi berstatus
  `approved`; tidak ada risiko saldo ganda saat approval/pembalik.
- **Dana terikat per program.** `Program.fund` dibuat otomatis saat donasi pertama
  dikonfirmasi, sehingga laporan per program bersih.
- **Audit tidak dapat dihapus.** Model hanya dibaca lewat UI; admin Django dibuat read-only.
- **Pemisahan tugas.** Semua query lintas modul berada di `services.py` agar view dan API
  memakai aturan yang sama.
- **Idempoten.** Konfirmasi donasi dan pembukuan zakat tidak membuat transaksi ganda.
