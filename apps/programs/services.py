"""Program donation services (confirmation creates a restricted-fund income)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.finance.models import Category, Fund, Transaction
from apps.programs.models import Donation, Program


def ensure_program_fund(program: Program) -> Fund:
    if program.fund_id:
        return program.fund
    fund, _ = Fund.objects.get_or_create(
        name=f"Dana Program: {program.title}"[:120],
        defaults={
            "fund_type": Fund.Type.RESTRICTED,
            "description": f"Dana terikat untuk program {program.title}.",
        },
    )
    program.fund = fund
    program.save(update_fields=["fund"])
    return fund


@db_transaction.atomic
def confirm_donation(donation: Donation, user) -> Donation:
    if donation.status == Donation.Status.CONFIRMED:
        return donation
    program = donation.program
    fund = ensure_program_fund(program)
    category, _ = Category.objects.get_or_create(
        name="Donasi Program",
        category_type=Category.Type.INCOME,
        defaults={"description": "Donasi yang masuk melalui program donasi."},
    )
    transaction_date = (
        donation.created_at.date() if donation.created_at else timezone.localdate()
    )
    transaction = Transaction.objects.create(
        date=transaction_date,
        transaction_type=Transaction.Type.INCOME,
        fund=fund,
        category=category,
        amount=donation.amount,
        description=f"Donasi {donation.code} — {program.title}"[:255],
        pic=user.get_full_name() or user.username,
        status=Transaction.Status.APPROVED,
        program=program,
        created_by=user,
    )
    donation.status = Donation.Status.CONFIRMED
    donation.confirmed_by = user
    donation.confirmed_at = timezone.now()
    donation.transaction = transaction
    donation.save(update_fields=["status", "confirmed_by", "confirmed_at",
                                 "transaction", "updated_at"])
    log_action(user, "confirm", donation,
               note=f"Donasi dikonfirmasi menjadi transaksi #{transaction.pk}")
    if (program.status == Program.Status.ACTIVE
            and program.collected >= program.target_amount):
        program.status = Program.Status.COMPLETED
        program.save(update_fields=["status", "updated_at"])
        log_action(user, "update", program,
                   note="Target program tercapai; status menjadi selesai")
    return donation


def reject_donation(donation: Donation, user, note: str = "") -> Donation:
    if donation.status == Donation.Status.CONFIRMED:
        raise ValueError("Donasi yang sudah dikonfirmasi tidak dapat ditolak.")
    donation.status = Donation.Status.REJECTED
    donation.confirmed_by = user
    donation.confirmed_at = timezone.now()
    donation.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
    log_action(user, "reject", donation, note=note or "Donasi ditolak")
    return donation


def create_donation(*, program: Program, donor_name: str, amount: Decimal,
                    method: str = Donation.Method.QRIS, message: str = "",
                    is_anonymous: bool = False, contact: str = "",
                    donor_user=None) -> Donation:
    return Donation.objects.create(
        program=program,
        donor_name=donor_name.strip() or "Hamba Allah",
        amount=amount,
        method=method,
        message=message,
        is_anonymous=is_anonymous,
        contact=contact,
        donor_user=donor_user if getattr(donor_user, "is_authenticated", False) else None,
    )
