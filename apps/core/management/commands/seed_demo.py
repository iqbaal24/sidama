"""Populate SIDAMA with realistic demo data.

Usage:
    python manage.py seed_demo           # abort if data already exists
    python manage.py seed_demo --reset   # wipe SIDAMA data and re-seed
"""
from __future__ import annotations

import calendar
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.assets.models import Asset, AssetLog
from apps.audit.models import AuditLog
from apps.core.models import Setting
from apps.core.utils import month_bounds, shift_month
from apps.finance.models import Category, Fund, Period, Transaction
from apps.notifications.models import Notification
from apps.notifications.services import notify_roles
from apps.programs.models import Donation, Program
from apps.programs.services import confirm_donation, ensure_program_fund
from apps.qurban.models import MeatDistribution, QurbanRegistration
from apps.reports.generator import generate_report
from apps.reports.models import Report
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt
from apps.zakat.services import record_distribution, record_receipt

PASSWORD = "sidama123"
MONEY = Decimal


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("1"))


def fridays(year: int, month: int) -> list[date]:
    days = calendar.monthrange(year, month)[1]
    return [
        date(year, month, day)
        for day in range(1, days + 1)
        if date(year, month, day).weekday() == 4
    ]


class Command(BaseCommand):
    help = "Membuat data demo SIDAMA: 12 bulan transaksi, program, zakat, kurban, aset, laporan."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Hapus seluruh data SIDAMA sebelum membuat data demo.")

    @db_transaction.atomic
    def handle(self, *args, **options):
        if User.objects.exists():
            if not options["reset"]:
                self.stdout.write(self.style.WARNING(
                    "Database sudah berisi data. Jalankan dengan --reset untuk membuat ulang."
                ))
                return
            self._wipe()

        random.seed(2026)
        today = timezone.localdate()
        self.today = today
        self.users = self._users()
        self._settings()
        self.funds = self._funds()
        self.categories = self._categories()
        self._transactions(today)
        self._programs(today)
        self._zakat(today)
        self._qurban(today)
        self._assets(today)
        self._reports(today)
        self._notifications()
        self._periodic_task()

        self.stdout.write(self.style.SUCCESS("\nData demo SIDAMA siap."))
        self.stdout.write(
            "Akun demo (password: sidama123):\n"
            "  admin      — Admin Sistem\n"
            "  ketua      — Ketua DKM\n"
            "  bendahara  — Bendahara\n"
            "  sekretaris — Sekretaris / Petugas\n"
        )
        self.stdout.write(f"Transaksi: {Transaction.objects.count()} · "
                          f"Program: {Program.objects.count()} · "
                          f"Donasi: {Donation.objects.count()} · "
                          f"Laporan: {Report.objects.count()}")

    # ------------------------------------------------------------------ users
    def _users(self) -> dict[str, User]:
        people = [
            ("admin", "Admin", "Sistem", "admin@sidama.local", Role.ADMIN, True),
            ("ketua", "Ahmad", "Fauzi", "ketua@sidama.local", Role.CHAIR, False),
            ("bendahara", "Hasan", "Basri", "bendahara@sidama.local", Role.TREASURER, False),
            ("sekretaris", "Rina", "Kartika", "sekretaris@sidama.local", Role.STAFF, False),
            ("donatur", "Dina", "Maulida", "donatur@sidama.local", Role.DONOR, False),
        ]
        users = {}
        for username, first, last, email, role, is_admin in people:
            user = User.objects.create_user(
                username=username, email=email, password=PASSWORD,
                first_name=first, last_name=last, role=role,
                is_staff=is_admin, is_superuser=is_admin,
            )
            users[username] = user
        return users

    def _settings(self):
        values = {
            "mosque_name": "Masjid Al-Ikhlas",
            "mosque_city": "Malang",
            "mosque_address": "Jl. Soekarno-Hatta No. 45, Lowokwaru, Malang",
            "mosque_phone": "(0341) 555-0123",
            "approval_threshold": "1000000",
            "nisab_gold_grams": "85",
            "gold_price_per_gram": "1450000",
            "rice_price_per_kg": "15000",
            "qris_note": "QRIS Masjid Al-Ikhlas — a.n. DKM Al-Ikhlas",
            "bank_account": "BSI 7112 3456 78 a.n. DKM Masjid Al-Ikhlas",
            "telegram_chat_id": "",
        }
        for key, value in values.items():
            Setting.set(key, value)


    def _date(self, year: int, month: int, day: int) -> date:
        """Clamp a day to the current date so demo data never sits in the future."""
        last_day = calendar.monthrange(year, month)[1]
        day = min(day, last_day)
        if (year, month) == (self.today.year, self.today.month):
            day = min(day, self.today.day)
        return date(year, month, max(day, 1))

    def _funds(self) -> dict[str, Fund]:
        return {
            "general": Fund.objects.create(
                name="Dana Umum", fund_type=Fund.Type.GENERAL,
                description="Infak Jumat, infak umum, dan sedekah untuk operasional masjid.",
            ),
            "zakat": Fund.objects.create(
                name="Dana Zakat", fund_type=Fund.Type.ZAKAT,
                description="Penerimaan dan penyaluran zakat sesuai asnaf.",
            ),
        }

    def _categories(self) -> dict[str, Category]:
        income = [
            ("Infak Jumat", "Infak kotak amal salat Jumat."),
            ("Infak Umum", "Infak harian dan transfer jamaah."),
            ("Zakat", "Penerimaan zakat mal, penghasilan, dan fitrah."),
            ("Wakaf", "Wakaf tunai untuk pembangunan dan operasional."),
            ("Sedekah", "Sedekah tidak terikat."),
            ("Donasi Program", "Donasi melalui program penggalangan dana."),
        ]
        expense = [
            ("Operasional Listrik & Air", "Tagihan listrik, air, dan internet."),
            ("Kebersihan", "Honor petugas kebersihan dan perlengkapan."),
            ("Honor Petugas", "Honor marbot, muadzin, dan imam."),
            ("Kegiatan", "Kajian, peringatan hari besar, dan kegiatan sosial."),
            ("Pembangunan", "Renovasi dan pemeliharaan bangunan."),
            ("Penyaluran Zakat", "Penyaluran zakat kepada mustahik."),
            ("Lain-lain", "Pengeluaran tak terduga."),
        ]
        categories = {}
        for name, description in income:
            categories[name] = Category.objects.create(
                name=name, category_type=Category.Type.INCOME, description=description,
            )
        for name, description in expense:
            categories[name] = Category.objects.create(
                name=name, category_type=Category.Type.EXPENSE, description=description,
            )
        return categories

    # ------------------------------------------------------------- transactions
    def _tx(self, *, date_, type_, category, amount, description, fund=None,
            pic="Hasan Basri", status=Transaction.Status.APPROVED, program=None):
        tx = Transaction.objects.create(
            date=date_,
            transaction_type=type_,
            fund=fund or self.funds["general"],
            category=self.categories[category],
            amount=money(amount),
            description=description,
            pic=pic,
            status=status,
            program=program,
            created_by=self.users["bendahara"],
            approved_by=self.users["ketua"] if status == Transaction.Status.APPROVED else None,
            approved_at=(timezone.make_aware(datetime.combine(date_, time(20, 0)))
                         if status == Transaction.Status.APPROVED else None),
        )
        return tx

    def _transactions(self, today: date):
        for offset in range(11, -1, -1):
            year, month = shift_month(today.year, today.month, -offset)
            last_day = calendar.monthrange(year, month)[1]
            month_end = date(year, month, last_day)
            if (year, month) == (today.year, today.month):
                month_end = today

            # Infak Jumat (weekly)
            for index, friday in enumerate(fridays(year, month), start=1):
                if friday > month_end:
                    continue
                base = random.randint(9, 22) * 100_000
                self._tx(
                    date_=friday, type_=Transaction.Type.INCOME,
                    category="Infak Jumat", amount=base + random.randint(0, 9) * 25_000,
                    description=f"Infak Jumat pekan ke-{index}",
                )

            # Infak umum / sedekah / wakaf
            self._tx(
                date_=self._date(year, month, 5),
                type_=Transaction.Type.INCOME, category="Infak Umum",
                amount=random.randint(15, 45) * 100_000,
                description="Infak umum melalui transfer bank",
            )
            if random.random() > 0.35:
                self._tx(
                    date_=self._date(year, month, 17),
                    type_=Transaction.Type.INCOME, category="Sedekah",
                    amount=random.randint(5, 20) * 100_000,
                    description="Sedekah jamaah untuk kegiatan sosial",
                )
            if random.random() > 0.6:
                self._tx(
                    date_=self._date(year, month, 21),
                    type_=Transaction.Type.INCOME, category="Wakaf",
                    amount=random.randint(10, 30) * 100_000,
                    description="Wakaf tunai pembangunan",
                )

            # Fixed monthly expenses
            self._tx(
                date_=self._date(year, month, 3),
                type_=Transaction.Type.EXPENSE, category="Honor Petugas",
                amount=1_500_000, description="Honor marbot dan muadzin",
            )
            self._tx(
                date_=self._date(year, month, 8),
                type_=Transaction.Type.EXPENSE, category="Operasional Listrik & Air",
                amount=random.randint(65, 95) * 10_000,
                description="Tagihan listrik dan air bulanan",
            )
            self._tx(
                date_=self._date(year, month, 12),
                type_=Transaction.Type.EXPENSE, category="Kebersihan",
                amount=450_000, description="Honor petugas kebersihan",
            )
            if random.random() > 0.4:
                self._tx(
                    date_=self._date(year, month, 19),
                    type_=Transaction.Type.EXPENSE, category="Kegiatan",
                    amount=random.randint(8, 28) * 100_000,
                    description=random.choice([
                        "Kajian rutin bulanan dan konsumsi",
                        "Santunan anak yatim",
                        "Peringatan hari besar Islam",
                        "Buka puasa bersama jamaah",
                    ]),
                )
            if random.random() > 0.55:
                self._tx(
                    date_=self._date(year, month, 24),
                    type_=Transaction.Type.EXPENSE, category="Pembangunan",
                    amount=random.randint(15, 40) * 100_000,
                    description=random.choice([
                        "Perbaikan sound system ruang utama",
                        "Penggantian lampu dan kipas",
                        "Pengecatan pagar masjid",
                        "Perbaikan atap teras",
                    ]),
                )

        # Two expenses waiting for approval in the current month.
        for index, (description, amount) in enumerate([
            ("Renovasi karpet ruang salat utama", 12_500_000),
            ("Pembelian 2 unit AC untuk ruang wudhu", 7_800_000),
        ], start=1):
            self._tx(
                date_=today - timedelta(days=index),
                type_=Transaction.Type.EXPENSE, category="Pembangunan",
                amount=amount, description=description,
                status=Transaction.Status.PENDING,
            )

        # Lock an older period to demonstrate closed books.
        year, month = shift_month(today.year, today.month, -4)
        start, end = month_bounds(year, month)
        period, _ = Period.objects.get_or_create(year=year, month=month)
        period.is_closed = True
        period.closed_at = timezone.make_aware(
            datetime.combine(end, time(21, 0))
        )
        period.closed_by = self.users["bendahara"]
        period.note = "Tutup buku rutin"
        period.save()
        Transaction.objects.filter(date__gte=start, date__lte=end).update(locked=True)

    # ---------------------------------------------------------------- programs
    def _programs(self, today: date) -> list[Program]:
        ketua = self.users["ketua"]
        bendahara = self.users["bendahara"]

        wudhu = Program.objects.create(
            title="Renovasi Ruang Wudhu & Tempat Parkir",
            description=(
                "Renovasi ruang wudhu jamaah putra dan putri, penambahan tempat parkir "
                "sepeda motor, serta perbaikan saluran air agar masjid lebih nyaman "
                "dipakai untuk salat berjamaah dan kegiatan kajian."
            ),
            target_amount=money(150_000_000),
            start_date=today - timedelta(days=90),
            end_date=today + timedelta(days=120),
            status=Program.Status.ACTIVE,
            is_published=True,
            created_by=ketua,
        )
        tahfidz = Program.objects.create(
            title="Beasiswa Santri Tahfidz",
            description=(
                "Dukungan biaya pendidikan dan hafalan Al-Qur'an untuk 12 santri "
                "dari keluarga prasejahtera di lingkungan masjid selama satu tahun ajaran."
            ),
            target_amount=money(60_000_000),
            start_date=today - timedelta(days=45),
            end_date=today + timedelta(days=200),
            status=Program.Status.ACTIVE,
            is_published=True,
            created_by=ketua,
        )
        ramadan = Program.objects.create(
            title="Sembako Ramadan 1447 H",
            description=(
                "Paket sembako untuk 200 keluarga penerima manfaat di sekitar masjid "
                "menjelang Ramadan. Program telah selesai dan laporannya tersedia."
            ),
            target_amount=money(40_000_000),
            start_date=today - timedelta(days=320),
            end_date=today - timedelta(days=250),
            status=Program.Status.COMPLETED,
            is_published=True,
            created_by=ketua,
        )

        donor_pool = [
            "Hamba Allah", "Bapak Sulaiman", "Ibu Nur Aisyah", "Keluarga Hendra",
            "Bapak Rizal", "Ibu Fitriani", "Komunitas Sepeda Malang", "H. Abdurrahman",
            "Ibu Wulandari", "Bapak Joko", "Alumni SMA 3 Malang", "Hamba Allah",
        ]
        for program, count, low, high in [
            (wudhu, 34, 2, 15),
            (tahfidz, 21, 1, 8),
            (ramadan, 26, 1, 6),
        ]:
            for index in range(count):
                amount = random.randint(low, high) * 500_000
                donation = Donation.objects.create(
                    program=program,
                    donor_name=random.choice(donor_pool),
                    amount=money(amount),
                    method=random.choice([Donation.Method.QRIS,
                                          Donation.Method.TRANSFER,
                                          Donation.Method.CASH]),
                    message=random.choice([
                        "Semoga menjadi amal jariyah.",
                        "Semoga masjid semakin makmur.",
                        "Barakallahu fiikum.",
                        "Untuk keberkahan keluarga kami.",
                        "",
                    ]),
                    is_anonymous=random.random() < 0.18,
                    contact="",
                )
                created = timezone.make_aware(datetime.combine(
                    program.start_date + timedelta(days=random.randint(0, 40)),
                    time(random.randint(8, 20), random.randint(0, 59)),
                ))
                Donation.objects.filter(pk=donation.pk).update(created_at=created)
                donation.refresh_from_db()
                if index % 9 == 3:
                    donation.status = Donation.Status.PENDING
                    donation.save(update_fields=["status"])
                    continue
                confirm_donation(donation, bendahara)

        # A few donations still waiting for confirmation.
        for program, name, amount in [
            (wudhu, "Bapak Syamsul", 3_000_000),
            (tahfidz, "Ibu Halimah", 1_500_000),
            (wudhu, "Hamba Allah", 5_000_000),
        ]:
            Donation.objects.create(
                program=program, donor_name=name, amount=money(amount),
                method=Donation.Method.QRIS, message="Semoga bermanfaat.",
                is_anonymous=(name == "Hamba Allah"),
            )
        # A completed program must show a fully funded bar.
        ramadan.target_amount = ramadan.collected or money(40_000_000)
        ramadan.save(update_fields=["target_amount"])

        # Record real spending from each program's restricted fund.
        spending = [
            (wudhu, "Pembangunan", [
                ("Pembayaran tukang dan material ruang wudhu", 40_000_000),
                ("Keramik, kran, dan sanitasi ruang wudhu", 14_000_000),
                ("Paving dan kanopi tempat parkir", 8_000_000),
            ]),
            (tahfidz, "Kegiatan", [
                ("Beasiswa santri tahfidz tahap 1", 7_500_000),
                ("Biaya pembinaan dan sertifikasi hafalan", 7_500_000),
            ]),
            (ramadan, "Kegiatan", [
                ("Distribusi 200 paket sembako Ramadan", 47_000_000),
            ]),
        ]
        for program, category, items in spending:
            fund = ensure_program_fund(program)
            for index, (description, amount) in enumerate(items):
                spend_date = program.start_date + timedelta(days=25 + index * 7)
                self._tx(
                    date_=min(spend_date, today),
                    type_=Transaction.Type.EXPENSE,
                    category=category,
                    amount=amount,
                    description=description,
                    fund=fund,
                    program=program,
                    status=Transaction.Status.APPROVED,
                )
        return [wudhu, tahfidz, ramadan]

    # ------------------------------------------------------------------- zakat
    def _zakat(self, today: date):
        bendahara = self.users["bendahara"]
        muzakki_names = [
            "H. Sulaiman", "Ibu Nur Aisyah", "Bapak Hendra Wijaya", "Ibu Fitriani",
            "Bapak Rizal Hakim", "H. Abdurrahman", "Ibu Wulandari", "Bapak Joko Santoso",
        ]
        muzakki = [Muzakki.objects.create(name=name, phone="08" + str(random.randint(1000000000, 9999999999)),
                                          address="Lowokwaru, Malang") for name in muzakki_names]

        for offset in range(11, -1, -1):
            year, month = shift_month(today.year, today.month, -offset)
            if random.random() < 0.55:
                receipt = ZakatReceipt.objects.create(
                    muzakki=random.choice(muzakki),
                    zakat_type=random.choice(list(ZakatReceipt.Type.values)),
                    amount=money(random.randint(10, 40) * 250_000),
                    date=self._date(year, month, random.randint(5, 25)),
                    note="Pembayaran zakat melalui transfer",
                )
                record_receipt(receipt, bendahara)

        mustahik_data = [
            ("Ibu Siti Aminah", Mustahik.Asnaf.FAKIR, "Jl. Mawar 12"),
            ("Bapak Slamet", Mustahik.Asnaf.MISKIN, "Jl. Melati 5"),
            ("Ibu Rukmini", Mustahik.Asnaf.FAKIR, "Gang Kenanga 3"),
            ("Bapak Sutrisno", Mustahik.Asnaf.MISKIN, "Jl. Anggrek 8"),
            ("Ibu Yuliana", Mustahik.Asnaf.GHARIM, "Jl. Dahlia 21"),
            ("Muhammad Fajar", Mustahik.Asnaf.FISABILILLAH, "Santri tahfidz"),
            ("Ibu Kartini", Mustahik.Asnaf.FAKIR, "Jl. Cempaka 7"),
            ("Bapak Suparman", Mustahik.Asnaf.MISKIN, "Jl. Kamboja 2"),
            ("Ibu Lestari", Mustahik.Asnaf.MUALLAF, "Jl. Flamboyan 9"),
            ("Bapak Iskandar", Mustahik.Asnaf.IBNU_SABIL, "Musafir"),
        ]
        mustahik = []
        for name, asnaf, address in mustahik_data:
            mustahik.append(Mustahik.objects.create(
                name=name, asnaf=asnaf, address=address,
                is_verified=random.random() > 0.2,
                note="Terverifikasi oleh petugas" if random.random() > 0.2 else "Menunggu verifikasi",
            ))

        verified = [m for m in mustahik if m.is_verified]
        for offset in range(0, 10):
            year, month = shift_month(today.year, today.month, -offset)
            for _ in range(random.randint(1, 3)):
                distribution = ZakatDistribution.objects.create(
                    mustahik=random.choice(verified),
                    amount=money(random.randint(4, 12) * 100_000),
                    item_description=random.choice([
                        "", "Paket sembako", "Biaya pendidikan", "Bantuan kesehatan",
                    ]),
                    date=self._date(year, month, random.randint(2, 26)),
                    note="Penyaluran zakat rutin",
                )
                record_distribution(distribution, bendahara)

    # ------------------------------------------------------------------ qurban
    def _qurban(self, today: date):
        names = [
            "H. Ahmad Fauzi", "H. Sulaiman", "Ibu Nur Aisyah", "Bapak Hendra Wijaya",
            "Keluarga Rizal Hakim", "Ibu Fitriani", "H. Abdurrahman", "Bapak Joko Santoso",
        ]
        registrations = []
        for index, name in enumerate(names):
            registrations.append(QurbanRegistration.objects.create(
                year=today.year, name=name,
                phone="08" + str(random.randint(1000000000, 9999999999)),
                animal_type=QurbanRegistration.Animal.COW if index < 5
                else QurbanRegistration.Animal.GOAT,
                share_count=1,
                amount=money(3_500_000 if index < 5 else 2_500_000),
                payment_status=QurbanRegistration.Payment.PAID if index < 6
                else QurbanRegistration.Payment.DP,
                created_by=self.users["sekretaris"],
            ))
        recipients = [
            "Ibu Siti Aminah", "Bapak Slamet", "Ibu Rukmini", "Bapak Sutrisno",
            "Ibu Yuliana", "Muhammad Fajar", "Ibu Kartini", "Bapak Suparman",
            "Ibu Lestari", "Bapak Iskandar", "Ibu Maryam", "Bapak Darto",
            "Ibu Sri Wahyuni", "Bapak Bambang", "Ibu Endang", "Bapak Wawan",
        ]
        for index, name in enumerate(recipients):
            MeatDistribution.objects.create(
                registration=registrations[index % len(registrations)],
                recipient_name=name,
                weight_kg=Decimal(str(random.randint(5, 15) / 10 + 1)).quantize(Decimal("0.01")),
                is_received=index % 3 != 0,
                note="Penerima warga sekitar masjid",
            )

    # ------------------------------------------------------------------ assets
    def _assets(self, today: date):
        data = [
            ("Sajadah tebal 120x60", "Perlengkapan Ibadah", 120, Asset.Condition.GOOD,
             "Ruang salat utama", 18_000_000, today - timedelta(days=400)),
            ("Pengeras suara TOA 500W", "Elektronik", 2, Asset.Condition.GOOD,
             "Ruang kontrol", 7_500_000, today - timedelta(days=250)),
            ("AC split 2 PK", "Elektronik", 4, Asset.Condition.MINOR,
             "Ruang salat utama", 16_000_000, today - timedelta(days=600)),
            ("Karpet ruang wudhu", "Perlengkapan Ibadah", 8, Asset.Condition.GOOD,
             "Ruang wudhu", 4_800_000, today - timedelta(days=180)),
            ("Almari Al-Qur'an", "Perabot", 3, Asset.Condition.GOOD,
             "Ruang utama", 3_600_000, today - timedelta(days=320)),
            ("Genset 5000 watt", "Elektronik", 1, Asset.Condition.MINOR,
             "Gudang", 12_500_000, today - timedelta(days=900)),
            ("Mesin air jet pump", "Elektronik", 1, Asset.Condition.GOOD,
             "Area wudhu", 2_800_000, today - timedelta(days=500)),
            ("Tenda kegiatan 4x6", "Perlengkapan", 3, Asset.Condition.GOOD,
             "Gudang", 6_000_000, today - timedelta(days=220)),
            ("Kursi lipat", "Perabot", 80, Asset.Condition.MINOR,
             "Gudang", 8_000_000, today - timedelta(days=700)),
            ("CCTV 8 channel", "Keamanan", 1, Asset.Condition.GOOD,
             "Ruang kontrol", 5_500_000, today - timedelta(days=150)),
            ("Jam digital waktu salat", "Elektronik", 1, Asset.Condition.GOOD,
             "Ruang utama", 1_900_000, today - timedelta(days=300)),
            ("Rak sandal", "Perabot", 6, Asset.Condition.BROKEN,
             "Pintu masuk", 1_200_000, today - timedelta(days=800)),
        ]
        for name, category, quantity, condition, location, value, acquired in data:
            asset = Asset.objects.create(
                name=name, category=category, quantity=quantity, condition=condition,
                location=location, acquired_date=acquired, value=money(value),
            )
            AssetLog.objects.create(
                asset=asset, log_type=AssetLog.Type.MAINTENANCE,
                note="Pemeriksaan dan perawatan rutin bulanan.",
                date=today - timedelta(days=random.randint(10, 120)),
                created_by=self.users["sekretaris"],
            )
            if condition != Asset.Condition.GOOD:
                AssetLog.objects.create(
                    asset=asset, log_type=AssetLog.Type.CONDITION,
                    note="Kondisi menurun, perlu anggaran perbaikan.",
                    date=today - timedelta(days=random.randint(5, 60)),
                    created_by=self.users["sekretaris"],
                )

    # ----------------------------------------------------------------- reports
    def _reports(self, today: date):
        previous = today.replace(day=1) - timedelta(days=1)
        months = []
        for offset in range(0, 4):
            year, month = shift_month(previous.year, previous.month, -offset)
            months.append((year, month))
        for index, (year, month) in enumerate(months):
            report, _ = Report.objects.get_or_create(
                report_type=Report.Type.MONTHLY,
                period_year=year, period_month=month,
                defaults={"created_by": self.users["bendahara"]},
            )
            generate_report(report)
            if index < 3:
                report.status = Report.Status.PUBLISHED
                report.published_by = self.users["ketua"]
                report.published_at = timezone.now() - timedelta(days=index * 30 + 2)
                report.save(update_fields=["status", "published_by", "published_at"])

    def _notifications(self):
        notify_roles(
            [Role.CHAIR, Role.ADMIN],
            title="2 pengeluaran menunggu persetujuan",
            message="Renovasi karpet dan pembelian AC menunggu persetujuan Ketua DKM.",
            url="/app/persetujuan/",
            level="warning",
        )
        notify_roles(
            [Role.TREASURER],
            title="Donasi baru menunggu konfirmasi",
            message="3 donasi program belum dikonfirmasi.",
            url="/app/donasi/",
            level="info",
        )
        notify_roles(
            [Role.TREASURER, Role.STAFF],
            title="2 mustahik belum terverifikasi",
            message="Lengkapi verifikasi data mustahik sebelum penyaluran berikutnya.",
            url="/app/zakat/mustahik/",
            level="warning",
        )

    def _periodic_task(self):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0", hour="2", day_of_month="1", month_of_year="*",
            day_of_week="*", timezone="Asia/Jakarta",
        )
        PeriodicTask.objects.update_or_create(
            name="SIDAMA — laporan bulanan otomatis",
            defaults={
                "task": "reports.monthly",
                "crontab": schedule,
                "enabled": True,
                "description": "Membuat laporan keuangan bulan sebelumnya setiap tanggal 1.",
            },
        )

    # ------------------------------------------------------------------- reset
    def _wipe(self):
        self.stdout.write("Menghapus data SIDAMA lama…")
        Notification.objects.all().delete()
        AuditLog.objects.all().delete()
        for report in Report.objects.all():
            if report.pdf_file:
                report.pdf_file.delete(save=False)
            if report.xlsx_file:
                report.xlsx_file.delete(save=False)
        Report.objects.all().delete()
        Donation.objects.all().delete()
        Program.objects.all().delete()
        ZakatDistribution.objects.all().delete()
        ZakatReceipt.objects.all().delete()
        Mustahik.objects.all().delete()
        Muzakki.objects.all().delete()
        MeatDistribution.objects.all().delete()
        QurbanRegistration.objects.all().delete()
        AssetLog.objects.all().delete()
        Asset.objects.all().delete()
        Transaction.objects.all().delete()
        Period.objects.all().delete()
        Category.objects.all().delete()
        Fund.objects.all().delete()
        User.objects.all().delete()
        Setting.objects.all().delete()
