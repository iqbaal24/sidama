"""Finance queries shared by dashboards, reports and the public pages."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce, TruncMonth

from apps.core.utils import last_n_months, month_short
from apps.finance.models import Fund, Transaction

ZERO = Decimal("0")
APPROVED = Transaction.Status.APPROVED
INCOME = Transaction.Type.INCOME
EXPENSE = Transaction.Type.EXPENSE


def approved_transactions(*, until: date | None = None):
    qs = Transaction.objects.filter(status=APPROVED)
    if until:
        qs = qs.filter(date__lte=until)
    return qs


def _sum(queryset, **filters) -> Decimal:
    value = queryset.aggregate(
        total=Coalesce(Sum("amount", filter=Q(**filters)), ZERO,
                       output_field=Transaction._meta.get_field("amount"))
    )["total"]
    return value or ZERO


def fund_balance(fund: Fund, *, until: date | None = None) -> Decimal:
    qs = approved_transactions(until=until).filter(fund=fund)
    income = _sum(qs, transaction_type=INCOME)
    expense = _sum(qs, transaction_type=EXPENSE)
    return income - expense


def fund_balances(*, until: date | None = None) -> list[dict]:
    rows = (
        Fund.objects.filter(is_active=True)
        .annotate(
            income=Coalesce(
                Sum("transactions__amount",
                    filter=Q(transactions__status=APPROVED,
                             transactions__transaction_type=INCOME)),
                ZERO,
            ),
            expense=Coalesce(
                Sum("transactions__amount",
                    filter=Q(transactions__status=APPROVED,
                             transactions__transaction_type=EXPENSE)),
                ZERO,
            ),
        )
        .order_by("fund_type", "name")
    )
    return [
        {"fund": fund, "income": fund.income, "expense": fund.expense,
         "balance": fund.income - fund.expense}
        for fund in rows
    ]


def totals(*, start: date | None = None, end: date | None = None) -> dict:
    qs = approved_transactions()
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    income = _sum(qs, transaction_type=INCOME)
    expense = _sum(qs, transaction_type=EXPENSE)
    return {"income": income, "expense": expense, "net": income - expense}


def month_totals(year: int, month: int) -> dict:
    from apps.core.utils import month_bounds

    start, end = month_bounds(year, month)
    return totals(start=start, end=end)


def monthly_series(months: int = 12) -> list[dict]:
    """Income/expense per month for the last ``months`` months."""
    keys = last_n_months(months)
    first_year, first_month = keys[0]
    from apps.core.utils import month_bounds

    start, _ = month_bounds(first_year, first_month)
    rows = (
        approved_transactions()
        .filter(date__gte=start)
        .annotate(bucket=TruncMonth("date"))
        .values("bucket", "transaction_type")
        .annotate(total=Sum("amount"))
    )
    bucket_map: dict[tuple[int, int], dict] = {}
    for row in rows:
        bucket = row["bucket"]
        key = (bucket.year, bucket.month)
        entry = bucket_map.setdefault(key, {"income": ZERO, "expense": ZERO})
        entry[row["transaction_type"]] = row["total"] or ZERO
    series = []
    for year, month in keys:
        entry = bucket_map.get((year, month), {"income": ZERO, "expense": ZERO})
        series.append({
            "year": year,
            "month": month,
            "label": month_short(year, month),
            "income": float(entry["income"]),
            "expense": float(entry["expense"]),
            "net": float(entry["income"] - entry["expense"]),
        })
    return series


def expense_by_category(start: date, end: date) -> list[dict]:
    rows = (
        approved_transactions()
        .filter(transaction_type=EXPENSE, date__gte=start, date__lte=end)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [{"name": row["category__name"], "total": row["total"]} for row in rows]


def income_by_category(start: date, end: date) -> list[dict]:
    rows = (
        approved_transactions()
        .filter(transaction_type=INCOME, date__gte=start, date__lte=end)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [{"name": row["category__name"], "total": row["total"]} for row in rows]


def cash_position(*, until: date | None = None) -> Decimal:
    qs = approved_transactions(until=until)
    return _sum(qs, transaction_type=INCOME) - _sum(qs, transaction_type=EXPENSE)


def pending_count() -> int:
    return Transaction.objects.filter(status=Transaction.Status.PENDING).count()


def default_status(transaction_type: str, amount) -> str:
    """Expenses above the configured threshold need chair approval."""
    from apps.core.models import Setting

    threshold = Setting.get_decimal("approval_threshold", "1000000")
    if transaction_type == Transaction.Type.EXPENSE and amount > threshold:
        return Transaction.Status.PENDING
    return Transaction.Status.APPROVED
