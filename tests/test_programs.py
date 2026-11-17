"""Programs, donations, and the confirmation workflow."""
from __future__ import annotations

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.finance.models import Transaction
from apps.programs.models import Donation, Program
from apps.programs.services import confirm_donation, ensure_program_fund, reject_donation
from tests.base import BaseTestCase


class ProgramTests(BaseTestCase):
    def setUp(self):
        self.program = Program.objects.create(
            title="Renovasi Ruang Wudhu",
            description="Renovasi ruang wudhu jamaah.",
            target_amount=Decimal("10000000"),
            start_date=timezone.localdate(),
            status=Program.Status.ACTIVE,
            is_published=True,
            created_by=self.chair,
        )

    def test_confirmed_donation_creates_restricted_income(self):
        donation = Donation.objects.create(
            program=self.program, donor_name="Bapak Rizal",
            amount=Decimal("2500000"), method=Donation.Method.QRIS,
        )
        self.assertTrue(donation.code.startswith("DN-"))
        confirm_donation(donation, self.treasurer)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.CONFIRMED)
        self.assertIsNotNone(donation.transaction_id)
        self.assertEqual(donation.transaction.transaction_type, Transaction.Type.INCOME)
        self.assertEqual(donation.transaction.fund, ensure_program_fund(self.program))
        self.assertEqual(self.program.collected, Decimal("2500000"))
        self.assertEqual(self.program.progress, 25.0)

    def test_program_completes_when_target_reached(self):
        donation = Donation.objects.create(
            program=self.program, donor_name="Hamba Allah",
            amount=Decimal("10000000"),
        )
        confirm_donation(donation, self.treasurer)
        self.program.refresh_from_db()
        self.assertEqual(self.program.status, Program.Status.COMPLETED)

    def test_rejected_donation_has_no_transaction(self):
        donation = Donation.objects.create(
            program=self.program, donor_name="Bapak Joko",
            amount=Decimal("500000"),
        )
        reject_donation(donation, self.treasurer, "Bukti tidak valid")
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.REJECTED)
        self.assertIsNone(donation.transaction_id)

    def test_public_donation_flow_creates_pending_donation(self):
        response = self.client.post(
            reverse("public:donate", args=[self.program.slug]),
            {
                "donor_name": "Ibu Rina", "amount": "150000",
                "method": Donation.Method.QRIS, "message": "Semoga berkah",
                "is_anonymous": "",
            },
        )
        donation = Donation.objects.get(donor_name="Ibu Rina")
        self.assertRedirects(response, reverse("public:donation_status",
                                               args=[donation.code]))
        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertEqual(donation.amount, Decimal("150000"))

    def test_public_program_page_hides_anonymous_donor_names(self):
        donation = Donation.objects.create(
            program=self.program, donor_name="Rahasia", amount=Decimal("1000000"),
            is_anonymous=True,
        )
        confirm_donation(donation, self.treasurer)
        response = self.client.get(self.program.get_absolute_url())
        self.assertContains(response, "Hamba Allah")
        self.assertNotContains(response, "Rahasia")

    def test_treasurer_confirms_donation_from_internal_list(self):
        donation = Donation.objects.create(
            program=self.program, donor_name="Ibu Fitri",
            amount=Decimal("300000"),
        )
        self.client.force_login(self.treasurer)
        response = self.client.post(reverse("programs:donation_confirm",
                                            args=[donation.pk]))
        self.assertRedirects(response, reverse("programs:donation_list"))
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.CONFIRMED)
