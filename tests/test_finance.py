"""Finance rules: balances, approval threshold, locking, reversal."""
from __future__ import annotations

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.utils import month_bounds, shift_month
from apps.finance.forms import TransactionForm
from apps.finance.models import Period, Transaction
from apps.finance.services import cash_position, default_status, fund_balance, month_totals
from tests.base import BaseTestCase


class BalanceTests(BaseTestCase):
    def test_balance_only_counts_approved_transactions(self):
        self.make_transaction(amount="500000")
        self.make_transaction(amount="200000", transaction_type="expense")
        self.make_transaction(amount="900000", transaction_type="expense",
                              status=Transaction.Status.PENDING)
        self.assertEqual(fund_balance(self.fund), Decimal("300000"))

    def test_month_totals_separate_income_and_expense(self):
        today = timezone.localdate()
        self.make_transaction(amount="1000000")
        self.make_transaction(amount="400000", transaction_type="expense")
        totals = month_totals(today.year, today.month)
        self.assertEqual(totals["income"], Decimal("1000000"))
        self.assertEqual(totals["expense"], Decimal("400000"))
        self.assertEqual(totals["net"], Decimal("600000"))

    def test_cash_position_matches_balance(self):
        self.make_transaction(amount="750000")
        self.assertEqual(cash_position(), fund_balance(self.fund))


class ApprovalTests(BaseTestCase):
    def test_large_expense_requires_approval(self):
        self.assertEqual(
            default_status(Transaction.Type.EXPENSE, Decimal("1500000")),
            Transaction.Status.PENDING,
        )
        self.assertEqual(
            default_status(Transaction.Type.EXPENSE, Decimal("500000")),
            Transaction.Status.APPROVED,
        )

    def test_form_sets_pending_status_for_large_expense(self):
        form = TransactionForm(data={
            "date": timezone.localdate().isoformat(),
            "transaction_type": Transaction.Type.EXPENSE,
            "fund": self.fund.pk,
            "category": self.expense_category.pk,
            "amount": "2500000",
            "description": "Renovasi karpet",
            "pic": "Bendahara",
        }, user=self.treasurer)
        self.assertTrue(form.is_valid(), form.errors)
        transaction = form.save()
        self.assertEqual(transaction.status, Transaction.Status.PENDING)
        self.assertIsNone(transaction.approved_by)

    def test_form_rejects_category_type_mismatch(self):
        form = TransactionForm(data={
            "date": timezone.localdate().isoformat(),
            "transaction_type": Transaction.Type.INCOME,
            "fund": self.fund.pk,
            "category": self.expense_category.pk,
            "amount": "100000",
            "description": "Salah kategori",
        }, user=self.treasurer)
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_chair_can_approve_pending_expense(self):
        transaction = self.make_transaction(
            amount="3000000", transaction_type="expense",
            status=Transaction.Status.PENDING,
        )
        self.client.force_login(self.chair)
        response = self.client.post(
            reverse("finance:transaction_approve", args=[transaction.pk]),
            {"note": "Sesuai RAB"},
        )
        self.assertRedirects(response, reverse("finance:approval_queue"))
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.Status.APPROVED)
        self.assertEqual(transaction.approved_by, self.chair)
        self.assertEqual(fund_balance(self.fund), Decimal("-3000000"))

    def test_treasurer_cannot_approve(self):
        transaction = self.make_transaction(
            amount="3000000", transaction_type="expense",
            status=Transaction.Status.PENDING,
        )
        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("finance:transaction_approve", args=[transaction.pk])
        )
        self.assertEqual(response.status_code, 403)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.Status.PENDING)


class PeriodLockTests(BaseTestCase):
    def test_closing_period_locks_transactions_and_blocks_edits(self):
        year, month = shift_month(timezone.localdate().year,
                                  timezone.localdate().month, -1)
        start, end = month_bounds(year, month)
        transaction = self.make_transaction(amount="500000", date=start)
        self.client.force_login(self.treasurer)
        response = self.client.post(reverse("finance:period_close"), {
            "year": year, "month": month, "note": "Tutup buku",
        })
        self.assertRedirects(response, reverse("finance:period_list"))
        transaction.refresh_from_db()
        self.assertTrue(transaction.locked)
        self.assertTrue(Period.objects.get(year=year, month=month).is_closed)

        edit = self.client.get(reverse("finance:transaction_update",
                                       args=[transaction.pk]))
        self.assertRedirects(edit, reverse("finance:transaction_detail",
                                           args=[transaction.pk]))

    def test_new_transaction_in_closed_period_is_locked(self):
        year, month = shift_month(timezone.localdate().year,
                                  timezone.localdate().month, -2)
        start, _ = month_bounds(year, month)
        Period.objects.create(year=year, month=month, is_closed=True)
        transaction = self.make_transaction(date=start)
        self.assertTrue(transaction.locked)

    def test_reversal_creates_opposite_entry(self):
        transaction = self.make_transaction(amount="800000", locked=True)
        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("finance:transaction_reverse", args=[transaction.pk])
        )
        reversal = Transaction.objects.get(reversal_of=transaction)
        self.assertRedirects(response, reverse("finance:transaction_detail",
                                               args=[reversal.pk]))
        self.assertEqual(reversal.transaction_type, Transaction.Type.EXPENSE)
        self.assertEqual(reversal.amount, transaction.amount)
        self.assertEqual(fund_balance(self.fund), Decimal("0"))


class AuditSignalTests(BaseTestCase):
    def test_update_creates_audit_log_with_old_and_new_values(self):
        transaction = self.make_transaction(amount="100000")
        self.client.force_login(self.treasurer)
        response = self.client.post(
            reverse("finance:transaction_update", args=[transaction.pk]),
            {
                "date": timezone.localdate().isoformat(),
                "transaction_type": Transaction.Type.INCOME,
                "fund": self.fund.pk,
                "category": self.income_category.pk,
                "amount": "250000",
                "description": "Transaksi diubah",
                "pic": "Bendahara",
            },
        )
        self.assertEqual(response.status_code, 302)
        log = AuditLog.objects.filter(
            model_name="finance.Transaction", object_id=str(transaction.pk),
            action=AuditLog.Action.UPDATE,
        ).latest("id")
        self.assertEqual(log.old_values["amount"], "100000.00")
        self.assertEqual(log.new_values["amount"], "250000.00")
        self.assertEqual(log.user, self.treasurer)
