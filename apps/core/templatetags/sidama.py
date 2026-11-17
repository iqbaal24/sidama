"""Template tags and filters used across SIDAMA templates."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

from apps.core.utils import indo_date, percent, rupiah, short_rupiah

register = template.Library()


@register.filter(name="rupiah")
def rupiah_filter(value) -> str:
    return rupiah(value)


@register.filter(name="short_rupiah")
def short_rupiah_filter(value) -> str:
    return short_rupiah(value)


@register.filter(name="indo_date")
def indo_date_filter(value) -> str:
    return indo_date(value)


@register.filter(name="percent")
def percent_filter(part, whole) -> float:
    return percent(part, whole)


@register.filter(name="status_tone")
def status_tone(value) -> str:
    mapping = {
        "approved": "success",
        "pending": "warning",
        "rejected": "danger",
        "draft": "muted",
        "active": "success",
        "completed": "info",
        "cancelled": "muted",
        "confirmed": "success",
        "paid": "success",
        "unpaid": "warning",
        "closed": "muted",
    }
    return mapping.get(str(value).lower(), "muted")


@register.filter(name="initial")
def initial_filter(value) -> str:
    text = str(value or "").strip()
    if not text:
        return "?"
    parts = [part for part in text.split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()


@register.filter(name="dict_get")
def dict_get(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None


@register.filter(name="mul")
def mul(value, factor):
    try:
        return Decimal(str(value)) * Decimal(str(factor))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name="div")
def div(value, divisor):
    try:
        divisor = Decimal(str(divisor))
        if divisor == 0:
            return 0
        return Decimal(str(value)) / divisor
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name="tone_class")
def tone_class(value) -> str:
    return f"tone-{value}" if value else ""


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs) -> str:
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.simple_tag
def progress_width(part, whole) -> str:
    return f"{percent(part, whole)}%"


@register.filter(name="add_class")
def add_class(field, css):
    existing = field.field.widget.attrs.get("class", "")
    field.field.widget.attrs["class"] = f"{existing} {css}".strip()
    return field
