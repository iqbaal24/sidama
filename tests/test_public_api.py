"""Public pages and the REST API."""
from __future__ import annotations

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.finance.models import Transaction
from apps.programs.models import Program
from tests.base import BaseTestCase


class PublicPageTests(BaseTestCase):
    def setUp(self):
        self.program = Program.objects.create(
            title="Beasiswa Santri", description="Dukungan pendidikan santri.",
            target_amount=Decimal("5000000"), start_date=timezone.localdate(),
            status=Program.Status.ACTIVE, is_published=True,
        )

    def test_home_shows_mosque_and_balance(self):
        self.make_transaction(amount="1200000")
        response = self.client.get(reverse("public:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masjid Al-Ikhlas")
        self.assertContains(response, "1.200.000")

    def test_program_list_and_detail_are_public(self):
        self.assertEqual(self.client.get(reverse("public:program_list")).status_code, 200)
        response = self.client.get(self.program.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beasiswa Santri")

    def test_private_program_is_not_public(self):
        self.program.is_published = False
        self.program.save()
        response = self.client.get(self.program.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_public_summary_api(self):
        self.make_transaction(amount="500000")
        response = self.client.get(reverse("api-public-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_balance", response.json())
        self.assertIn("programs", response.json())

    def test_healthcheck(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class ApiTests(BaseTestCase):
    def login_token(self, username="bendahara", password="testpass123"):
        response = self.client.post("/api/auth/login/", {
            "username": username, "password": password,
        })
        self.assertEqual(response.status_code, 200)
        return response.json()["token"]

    def test_login_returns_token(self):
        token = self.login_token()
        self.assertTrue(token)

    def test_api_requires_authentication(self):
        response = self.client.get("/api/transactions/")
        self.assertEqual(response.status_code, 401)

    def test_transaction_list_with_token(self):
        self.make_transaction(amount="300000")
        token = self.login_token()
        response = self.client.get("/api/transactions/", HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_large_expense_created_as_pending(self):
        token = self.login_token()
        response = self.client.post(
            "/api/transactions/",
            data={
                "date": timezone.localdate().isoformat(),
                "transaction_type": "expense",
                "fund": self.fund.pk,
                "category": self.expense_category.pk,
                "amount": "5000000",
                "description": "Pengeluaran besar via API",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["status"], "pending")

    def test_chair_can_approve_via_api(self):
        transaction = self.make_transaction(
            amount="2000000", transaction_type="expense",
            status=Transaction.Status.PENDING,
        )
        token = self.login_token("ketua")
        response = self.client.post(
            f"/api/transactions/{transaction.pk}/approve/",
            data={}, content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.Status.APPROVED)

    def test_zakat_calculator_api_is_public(self):
        response = self.client.get("/api/zakat/calculate/",
                                   {"type": "fitrah", "dependents": 3})
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.json())

    def test_donor_cannot_access_transactions_api(self):
        token = self.login_token("donatur")
        response = self.client.get("/api/transactions/", HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)
