"""Small helpers shared across apps."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
               "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return the first and last day of a month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def month_label(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def month_short(year: int, month: int) -> str:
    return f"{MONTH_SHORT[month - 1]} {str(year)[2:]}"


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def last_n_months(n: int, *, today: date | None = None) -> list[tuple[int, int]]:
    today = today or timezone.localdate()
    return [shift_month(today.year, today.month, -offset) for offset in range(n - 1, -1, -1)]


def rupiah(value, *, prefix: str = "Rp", space: str = "\u00a0") -> str:
    try:
        amount = Decimal(str(value or 0))
    except Exception:  # noqa: BLE001 - display helper must never raise
        return f"{prefix}{space}0"
    rounded = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    formatted = f"{int(rounded):,}".replace(",", ".")
    sign = "-" if rounded < 0 else ""
    return f"{sign}{prefix}{space}{formatted.lstrip('-')}"


def short_rupiah(value) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return "Rp 0"
    for limit, suffix in ((1_000_000_000, "M"), (1_000_000, "jt"), (1_000, "rb")):
        if abs(amount) >= limit:
            compact = amount / limit
            text = f"{compact:.1f}".rstrip("0").rstrip(".")
            return f"Rp {text.replace('.', ',')} {suffix}"
    return rupiah(amount)


def percent(part, whole) -> float:
    try:
        whole = float(whole or 0)
        if whole <= 0:
            return 0.0
        return round(min(float(part or 0) / whole * 100, 100), 1)
    except (TypeError, ValueError):
        return 0.0


def indo_date(value, *, with_year: bool = True) -> str:
    if not value:
        return "-"
    if hasattr(value, "date") and not isinstance(value, date):
        value = timezone.localtime(value).date()
    pattern = "%d %b %Y" if with_year else "%d %b"
    months = MONTH_SHORT
    text = pattern.replace("%b", months[value.month - 1]).replace("%d", f"{value.day:02d}")
    return text.replace("%Y", str(value.year)) if with_year else text
