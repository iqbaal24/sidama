"""Zakat calculator and bookkeeping."""
from __future__ import annotations

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.core.models import Setting
from apps.finance.services import fund_balance
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt
from apps.zakat.services import (
    calculate_zakat,
    record_distribution,
    record_receipt,
    zakat_fund,
    zakat_summary,
)
from tests.base import BaseTestCase


class ZakatCalculatorTests(BaseTestCase):
    def test_mal_below_nisab_is_not_obligated(self):
        result = calculate_zakat(zakat_type="mal", assets=10_000_000, debts=0)
        self.assertFalse(result["obligated"])
        self.assertEqual(result["amount"], Decimal("0"))

    def test_mal_above_nisab_uses_2_5_percent(self):
        Setting.set("nisab_gold_grams", "85")
        Setting.set("gold_price_per_gram", "1000000")
        result = calculate_zakat(zakat_type="mal", assets=100_000_000, debts=15_000_000)
        self.assertTrue(result["obligated"])
        self.assertEqual(result["base"], Decimal("85000000"))
        self.assertEqual(result["amount"], Decimal("2125000"))

    def test_income_uses_monthly_nisab(self):
        Setting.set("nisab_gold_grams", "85")
        Setting.set("gold_price_per_gram", "1200000")
        result = calculate_zakat(zakat_type="penghasilan", monthly_income=10_000_000)
        self.assertTrue(result["obligated"])
        self.assertEqual(result["amount"], Decimal("250000"))

    def test_fitrah_multiplies_rice_price_by_household(self):
        Setting.set("rice_price_per_kg", "15000")
        result = calculate_zakat(zakat_type="fitrah", dependents=4)
        self.assertEqual(result["amount"], Decimal("150000"))

    def test_public_calculator_renders_result(self):
        response = self.client.post(reverse("public:zakat"), {
            "zakat_type": "mal", "assets": "100000000", "debts": "0",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2.500.000")


class ZakatBookkeepingTests(BaseTestCase):
    def setUp(self):
        self.muzakki = Muzakki.objects.create(name="H. Sulaiman")
        self.mustahik = Mustahik.objects.create(
            name="Ibu Siti", asnaf=Mustahik.Asnaf.FAKIR, is_verified=True,
        )

    def test_receipt_creates_income_in_zakat_fund(self):
        receipt = ZakatReceipt.objects.create(
            muzakki=self.muzakki, zakat_type=ZakatReceipt.Type.MAL,
            amount=Decimal("2500000"), date=timezone.localdate(),
        )
        record_receipt(receipt, self.treasurer)
        receipt.refresh_from_db()
        self.assertIsNotNone(receipt.transaction_id)
        self.assertEqual(receipt.transaction.fund, zakat_fund())
        self.assertEqual(fund_balance(zakat_fund()), Decimal("2500000"))
        self.assertTrue(receipt.number.startswith("ZK-"))

    def test_distribution_reduces_zakat_balance(self):
        receipt = ZakatReceipt.objects.create(
            muzakki=self.muzakki, zakat_type=ZakatReceipt.Type.MAL,
            amount=Decimal("3000000"),
        )
        record_receipt(receipt, self.treasurer)
        distribution = ZakatDistribution.objects.create(
            mustahik=self.mustahik, amount=Decimal("1000000"),
        )
        record_distribution(distribution, self.treasurer)
        self.assertEqual(fund_balance(zakat_fund()), Decimal("2000000"))

    def test_summary_matches_receipts_and_distributions(self):
        receipt = ZakatReceipt.objects.create(
            muzakki=self.muzakki, zakat_type=ZakatReceipt.Type.FITRAH,
            amount=Decimal("500000"),
        )
        record_receipt(receipt, self.treasurer)
        summary = zakat_summary()
        self.assertEqual(summary["received"], Decimal("500000"))
        self.assertEqual(summary["remaining"], Decimal("500000"))

    def test_unverified_mustahik_cannot_receive(self):
        self.client.force_login(self.treasurer)
        self.mustahik.is_verified = False
        self.mustahik.save()
        response = self.client.post(reverse("zakat:distribution_create"), {
            "date": timezone.localdate().isoformat(),
            "mustahik": self.mustahik.pk,
            "amount": "500000",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ZakatDistribution.objects.exists())
