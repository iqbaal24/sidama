"""Settings shown on the admin settings page."""

SETTING_GROUPS = [
    {
        "key": "masjid",
        "label": "Identitas Masjid",
        "description": "Tampil di halaman publik, laporan, dan struk donasi.",
        "fields": [
            {"key": "mosque_name", "label": "Nama masjid"},
            {"key": "mosque_city", "label": "Kota"},
            {"key": "mosque_address", "label": "Alamat"},
            {"key": "mosque_phone", "label": "Telepon"},
            {"key": "bank_account", "label": "Rekening donasi",
             "help": "Nomor rekening yang ditampilkan pada formulir donasi."},
            {"key": "qris_note", "label": "Keterangan QRIS",
             "help": "Teks pendamping untuk pembayaran QRIS."},
        ],
    },
    {
        "key": "keuangan",
        "label": "Keuangan",
        "description": "Ambang batas persetujuan pengeluaran oleh Ketua DKM.",
        "fields": [
            {"key": "approval_threshold", "label": "Ambang persetujuan (Rp)",
             "help": "Pengeluaran di atas nilai ini menunggu persetujuan Ketua DKM."},
        ],
    },
    {
        "key": "zakat",
        "label": "Zakat",
        "description": "Nisab dan harga acuan untuk kalkulator zakat. Sesuaikan dengan ketetapan BAZNAS setempat.",
        "fields": [
            {"key": "nisab_gold_grams", "label": "Nisab emas (gram)",
             "help": "Standar 85 gram emas."},
            {"key": "gold_price_per_gram", "label": "Harga emas per gram (Rp)"},
            {"key": "rice_price_per_kg", "label": "Harga beras per kg (Rp)",
             "help": "Dipakai untuk zakat fitrah (2,5 kg atau 3,5 liter beras)."},
        ],
    },
    {
        "key": "notifikasi",
        "label": "Notifikasi",
        "description": "Integrasi Telegram opsional. Kosongkan bila belum digunakan.",
        "fields": [
            {"key": "telegram_chat_id", "label": "Chat ID Telegram"},
        ],
    },
]
