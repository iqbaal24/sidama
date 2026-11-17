"""Shared test fixtures."""
from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.core.models import Setting
from apps.finance.models import Category, Fund, Transaction


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="testpass123",
            first_name="Admin", role=Role.ADMIN, is_staff=True, is_superuser=True,
        )
        cls.chair = User.objects.create_user(
            username="ketua", email="ketua@example.com", password="testpass123",
            first_name="Ketua", role=Role.CHAIR,
        )
        cls.treasurer = User.objects.create_user(
            username="bendahara", email="bendahara@example.com", password="testpass123",
            first_name="Bendahara", role=Role.TREASURER,
        )
        cls.staff = User.objects.create_user(
            username="petugas", email="petugas@example.com", password="testpass123",
            first_name="Petugas", role=Role.STAFF,
        )
        cls.donor = User.objects.create_user(
            username="donatur", email="donatur@example.com", password="testpass123",
            first_name="Donatur", role=Role.DONOR,
        )
        cls.fund = Fund.objects.create(name="Dana Umum", fund_type=Fund.Type.GENERAL)
        cls.zakat_fund = Fund.objects.create(name="Dana Zakat",
                                             fund_type=Fund.Type.ZAKAT)
        cls.income_category = Category.objects.create(
            name="Infak Jumat", category_type=Category.Type.INCOME,
        )
        cls.expense_category = Category.objects.create(
            name="Operasional", category_type=Category.Type.EXPENSE,
        )
        Setting.set("approval_threshold", "1000000")

    def make_transaction(self, *, amount="100000", transaction_type="income",
                         status=Transaction.Status.APPROVED, **kwargs):
        defaults = {
            "date": timezone.localdate(),
            "transaction_type": transaction_type,
            "fund": self.fund,
            "category": (self.income_category if transaction_type == "income"
                         else self.expense_category),
            "amount": Decimal(str(amount)),
            "description": "Transaksi uji",
            "status": status,
            "created_by": self.treasurer,
        }
        defaults.update(kwargs)
        return Transaction.objects.create(**defaults)
