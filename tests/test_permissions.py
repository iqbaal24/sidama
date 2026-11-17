"""Role-based access control across pages and endpoints."""
from __future__ import annotations

from django.urls import reverse

from apps.finance.models import Transaction
from tests.base import BaseTestCase


class PagePermissionTests(BaseTestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_donor_cannot_open_dashboard(self):
        self.client.force_login(self.donor)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_transactions_but_not_settings(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("finance:transaction_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("core:settings")).status_code, 403)

    def test_only_admin_can_open_user_management(self):
        self.client.force_login(self.chair)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 200)

    def test_treasurer_cannot_publish_reports(self):
        self.client.force_login(self.treasurer)
        response = self.client.get(reverse("reports:list"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_publish"])

    def test_chair_can_see_audit_log(self):
        self.client.force_login(self.chair)
        self.assertEqual(self.client.get(reverse("audit:list")).status_code, 200)
        self.client.force_login(self.treasurer)
        self.assertEqual(self.client.get(reverse("audit:list")).status_code, 403)

    def test_login_accepts_email_or_username(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "bendahara@example.com", "password": "testpass123",
        })
        self.assertRedirects(response, reverse("core:dashboard"))
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {
            "username": "bendahara", "password": "testpass123",
        })
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_login_rate_limit_blocks_after_five_failures(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {
                "username": "bendahara", "password": "salah",
            })
        response = self.client.post(reverse("accounts:login"), {
            "username": "bendahara", "password": "testpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terlalu banyak percobaan")


class TransactionPermissionTests(BaseTestCase):
    def test_staff_cannot_create_transactions(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("finance:transaction_create"))
        self.assertEqual(response.status_code, 403)

    def test_treasurer_can_create_transaction(self):
        self.client.force_login(self.treasurer)
        response = self.client.post(reverse("finance:transaction_create"), {
            "date": "2026-01-10",
            "transaction_type": "income",
            "fund": self.fund.pk,
            "category": self.income_category.pk,
            "amount": "250000",
            "description": "Infak uji",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Transaction.objects.filter(description="Infak uji").exists())
