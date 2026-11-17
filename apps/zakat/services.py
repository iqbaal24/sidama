"""Zakat calculation and bookkeeping services."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

from apps.audit.services import log_action
from apps.core.models import Setting
from apps.core.utils import month_bounds, month_label
from apps.finance.models import Category, Fund, Transaction
from apps.zakat.models import ZakatDistribution, ZakatReceipt

ZAKAT_RATE = Decimal("0.025")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def zakat_settings() -> dict:
    return {
        "nisab_gold_grams": Setting.get_decimal("nisab_gold_grams", "85"),
        "gold_price_per_gram": Setting.get_decimal("gold_price_per_gram", "1450000"),
        "rice_price_per_kg": Setting.get_decimal("rice_price_per_kg", "15000"),
    }


def calculate_zakat(*, zakat_type: str, assets=0, debts=0, monthly_income=0,
                    dependents=1, rice_price=None) -> dict:
    """Return a transparent breakdown of the zakat obligation.

    The result is an estimate, following BAZNAS' commonly used nisab of 85 g gold.
    """
    config = zakat_settings()
    gold_price = config["gold_price_per_gram"]
    nisab_annual = _money(config["nisab_gold_grams"] * gold_price)
    nisab_monthly = _money(nisab_annual / 12)

    result = {
        "zakat_type": zakat_type,
        "nisab_annual": nisab_annual,
        "nisab_monthly": nisab_monthly,
        "gold_price_per_gram": gold_price,
        "rice_price_per_kg": config["rice_price_per_kg"],
        "obligated": False,
        "base": Decimal("0"),
        "amount": Decimal("0"),
        "notes": [],
    }

    if zakat_type == ZakatReceipt.Type.MAL:
        base = _money(Decimal(str(assets or 0)) - Decimal(str(debts or 0)))
        result["base"] = max(base, Decimal("0"))
        result["obligated"] = base >= nisab_annual
        if result["obligated"]:
            result["amount"] = _money(base * ZAKAT_RATE)
            result["notes"].append("Harta bersih mencapai nisab setara 85 gram emas.")
        else:
            result["notes"].append("Harta bersih belum mencapai nisab, belum wajib zakat.")

    elif zakat_type == ZakatReceipt.Type.PENGHASILAN:
        income = _money(monthly_income)
        result["base"] = income
        result["obligated"] = income >= nisab_monthly
        if result["obligated"]:
            result["amount"] = _money(income * ZAKAT_RATE)
            result["notes"].append("Penghasilan bulanan mencapai nisab bulanan (nisab tahunan ÷ 12).")
        else:
            result["notes"].append("Penghasilan bulanan belum mencapai nisab.")

    elif zakat_type == ZakatReceipt.Type.FITRAH:
        rice = _money(rice_price if rice_price is not None else config["rice_price_per_kg"])
        people = max(int(dependents or 1), 1)
        base = _money(rice * Decimal("2.5") * people)
        result["base"] = base
        result["amount"] = base
        result["obligated"] = True
        result["notes"].append(
            f"Setara 2,5 kg beras per jiwa untuk {people} jiwa "
            f"(@ Rp {rice:,.0f}/kg).".replace(",", ".")
        )
    else:
        result["notes"].append("Jenis zakat tidak dikenali.")

    result["amount"] = max(result["amount"], Decimal("0"))
    return result


def zakat_fund() -> Fund:
    fund = Fund.objects.filter(fund_type=Fund.Type.ZAKAT).first()
    if fund:
        return fund
    fund, _ = Fund.objects.get_or_create(
        name="Dana Zakat",
        defaults={
            "fund_type": Fund.Type.ZAKAT,
            "code": "zakat",
            "description": "Dana khusus penerimaan dan penyaluran zakat.",
        },
    )
    return fund


def _category(name: str, category_type: str) -> Category:
    category, _ = Category.objects.get_or_create(
        name=name, category_type=category_type,
        defaults={"description": "Dibuat otomatis oleh modul zakat."},
    )
    return category


@db_transaction.atomic
def record_receipt(receipt: ZakatReceipt, user) -> ZakatReceipt:
    """Book a zakat receipt as income into the zakat fund."""
    if receipt.transaction_id:
        return receipt
    transaction = Transaction.objects.create(
        date=receipt.date,
        transaction_type=Transaction.Type.INCOME,
        fund=zakat_fund(),
        category=_category("Zakat", Category.Type.INCOME),
        amount=receipt.amount,
        description=f"Penerimaan {receipt.get_zakat_type_display()} — {receipt.payer_name}"[:255],
        pic=user.get_full_name() or user.username,
        status=Transaction.Status.APPROVED,
        created_by=user,
    )
    receipt.transaction = transaction
    receipt.created_by = user
    receipt.save(update_fields=["transaction", "created_by", "updated_at"])
    log_action(user, "create", receipt, note="Penerimaan zakat dibukukan")
    return receipt


@db_transaction.atomic
def record_distribution(distribution: ZakatDistribution, user) -> ZakatDistribution:
    """Book a distribution as an expense from the zakat fund."""
    if distribution.transaction_id:
        return distribution
    transaction = Transaction.objects.create(
        date=distribution.date,
        transaction_type=Transaction.Type.EXPENSE,
        fund=zakat_fund(),
        category=_category("Penyaluran Zakat", Category.Type.EXPENSE),
        amount=distribution.amount,
        description=f"Penyaluran zakat — {distribution.mustahik.name}"[:255],
        pic=user.get_full_name() or user.username,
        status=Transaction.Status.APPROVED,
        created_by=user,
    )
    distribution.transaction = transaction
    distribution.created_by = user
    distribution.save(update_fields=["transaction", "created_by", "updated_at"])
    log_action(user, "create", distribution, note="Penyaluran zakat dibukukan")
    return distribution


def zakat_summary(*, year: int | None = None, month: int | None = None) -> dict:
    receipts = ZakatReceipt.objects.all()
    distributions = ZakatDistribution.objects.all()
    if year and month:
        start, end = month_bounds(year, month)
        receipts = receipts.filter(date__gte=start, date__lte=end)
        distributions = distributions.filter(date__gte=start, date__lte=end)
        label = month_label(year, month)
    elif year:
        receipts = receipts.filter(date__year=year)
        distributions = distributions.filter(date__year=year)
        label = f"Tahun {year}"
    else:
        label = "Semua periode"
    received = receipts.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    distributed = distributions.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return {
        "label": label,
        "received": received,
        "distributed": distributed,
        "remaining": received - distributed,
        "receipt_count": receipts.count(),
        "distribution_count": distributions.count(),
    }


def monthly_zakat_report(year: int) -> list[dict]:
    rows = []
    for month in range(1, 13):
        summary = zakat_summary(year=year, month=month)
        if summary["receipt_count"] or summary["distribution_count"]:
            rows.append({"month": month, "label": month_label(year, month), **summary})
    return rows


def current_period() -> tuple[int, int]:
    today = timezone.localdate()
    return today.year, today.month
