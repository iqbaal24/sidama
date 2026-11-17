# ERD SIDAMA

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
        string role
        string phone
        bool is_active
    }
    FUND {
        int id PK
        string name
        string code
        string fund_type
        bool is_active
    }
    CATEGORY {
        int id PK
        string name
        string category_type
        bool is_active
    }
    PERIOD {
        int id PK
        int year
        int month
        bool is_closed
        datetime closed_at
    }
    TRANSACTION {
        int id PK
        date date
        string transaction_type
        decimal amount
        string description
        string pic
        file receipt
        string status
        bool locked
        int fund_id FK
        int category_id FK
        int program_id FK
        int reversal_of_id FK
        int created_by_id FK
        int approved_by_id FK
    }
    PROGRAM {
        int id PK
        string title
        string slug
        text description
        decimal target_amount
        date start_date
        date end_date
        string status
        bool is_published
        int fund_id FK
    }
    DONATION {
        int id PK
        string code
        int program_id FK
        string donor_name
        bool is_anonymous
        decimal amount
        string method
        string status
        string message
        int transaction_id FK
    }
    MUZAKKI {
        int id PK
        string name
        string phone
        string address
    }
    ZAKAT_RECEIPT {
        int id PK
        string number
        int muzakki_id FK
        string zakat_type
        decimal amount
        date date
        int transaction_id FK
    }
    MUSTAHIK {
        int id PK
        string name
        string asnaf
        string address
        bool is_verified
    }
    ZAKAT_DISTRIBUTION {
        int id PK
        int mustahik_id FK
        decimal amount
        string item_description
        date date
        int transaction_id FK
    }
    QURBAN_REGISTRATION {
        int id PK
        int year
        string name
        string animal_type
        int share_count
        decimal amount
        string payment_status
    }
    MEAT_DISTRIBUTION {
        int id PK
        int registration_id FK
        string recipient_name
        decimal weight_kg
        string coupon_code
        bool is_received
    }
    ASSET {
        int id PK
        string name
        string category
        int quantity
        string condition
        string location
        decimal value
        date acquired_date
    }
    ASSET_LOG {
        int id PK
        int asset_id FK
        string log_type
        text note
        date date
    }
    REPORT {
        int id PK
        string report_type
        int period_year
        int period_month
        string status
        file pdf_file
        file xlsx_file
        datetime published_at
    }
    AUDIT_LOG {
        int id PK
        int user_id FK
        string action
        string model_name
        string object_id
        json old_values
        json new_values
        string ip_address
        datetime created_at
    }
    NOTIFICATION {
        int id PK
        int user_id FK
        string title
        string message
        string level
        bool is_read
    }
    SETTING {
        int id PK
        string key
        string value
        string group
    }

    USER ||--o{ TRANSACTION : creates
    FUND ||--o{ TRANSACTION : holds
    CATEGORY ||--o{ TRANSACTION : classifies
    PROGRAM ||--o{ TRANSACTION : spends
    PROGRAM ||--o{ DONATION : receives
    PROGRAM ||--o| FUND : "dana terikat"
    DONATION ||--o| TRANSACTION : "kas masuk"
    MUZAKKI ||--o{ ZAKAT_RECEIPT : pays
    ZAKAT_RECEIPT ||--o| TRANSACTION : "kas masuk"
    MUSTAHIK ||--o{ ZAKAT_DISTRIBUTION : receives
    ZAKAT_DISTRIBUTION ||--o| TRANSACTION : "kas keluar"
    QURBAN_REGISTRATION ||--o{ MEAT_DISTRIBUTION : distributes
    ASSET ||--o{ ASSET_LOG : history
    USER ||--o{ AUDIT_LOG : performs
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ REPORT : publishes
```

## Catatan

- `Transaction.program` opsional; hanya dipakai untuk pengeluaran yang menggunakan dana program.
- `Transaction.reversal_of` menunjuk transaksi asal saat koreksi periode tertutup.
- `Donation.transaction`, `ZakatReceipt.transaction`, dan `ZakatDistribution.transaction`
  adalah relasi satu-ke-satu agar tidak ada pembukuan ganda.
- `Period` unik per `(year, month)`; penutupan mengunci transaksi pada rentang tanggal tersebut.
