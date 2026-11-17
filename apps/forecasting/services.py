"""Simple cash-flow forecasting from historical monthly patterns."""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.core.utils import month_label
from apps.finance.models import Transaction
from apps.finance.services import approved_transactions, cash_position, monthly_series

DEFAULT_WINDOW = 6


def _average(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def completed_months(window: int = DEFAULT_WINDOW) -> list[dict]:
    """Monthly totals excluding the month in progress."""
    series = monthly_series(window + 1)
    return series[:-1] if len(series) > 1 else series


def category_forecast(window: int = DEFAULT_WINDOW) -> list[dict]:
    """Average monthly expense per category over the last completed months."""
    months = completed_months(window)
    if not months:
        return []
    first, last = months[0], months[-1]
    from apps.core.utils import month_bounds

    start, _ = month_bounds(first["year"], first["month"])
    _, end = month_bounds(last["year"], last["month"])
    rows = (
        approved_transactions()
        .filter(transaction_type=Transaction.Type.EXPENSE,
                date__gte=start, date__lte=end)
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    results = []
    for row in rows:
        total = row["total"] or Decimal("0")
        results.append({
            "name": row["category__name"],
            "total": total,
            "average": total / Decimal(len(months)),
        })
    results.sort(key=lambda item: item["average"], reverse=True)
    return results


def cashflow_forecast(window: int = DEFAULT_WINDOW) -> dict:
    months = completed_months(window)
    balance = cash_position()
    incomes = [Decimal(str(row["income"])) for row in months]
    expenses = [Decimal(str(row["expense"])) for row in months]
    avg_income = _average(incomes)
    avg_expense = _average(expenses)
    projected_balance = balance + avg_income - avg_expense
    runway = (balance / avg_expense) if avg_expense > 0 else None

    if avg_expense == 0 and balance <= 0:
        status, tone = "Belum ada data pengeluaran", "muted"
    elif projected_balance < 0:
        status, tone = "Saldo diprediksi tidak cukup", "danger"
    elif runway is not None and runway < Decimal("1"):
        status, tone = "Kas hanya cukup < 1 bulan", "warning"
    elif runway is not None and runway < Decimal("2"):
        status, tone = "Kas cukup untuk sekitar 1–2 bulan", "warning"
    else:
        status, tone = "Kas dalam kondisi sehat", "success"

    next_month = months[-1] if months else None
    if next_month:
        year, month = next_month["year"], next_month["month"]
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        next_label = month_label(year, month)
    else:
        today = timezone.localdate()
        next_label = month_label(today.year, today.month)

    return {
        "window": window,
        "months": months,
        "balance": balance,
        "avg_income": avg_income,
        "avg_expense": avg_expense,
        "projected_balance": projected_balance,
        "runway_months": round(float(runway), 1) if runway is not None else None,
        "status": status,
        "tone": tone,
        "next_label": next_label,
        "series": monthly_series(window),
    }
