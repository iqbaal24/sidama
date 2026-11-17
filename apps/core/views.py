"""Generic list/form pages plus the internal dashboard and settings screen."""
from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from apps.accounts.models import Role
from apps.core.forms import StyledForm
from apps.core.mixins import RoleRequiredMixin
from apps.core.models import Setting
from apps.core.settings_schema import SETTING_GROUPS
from apps.core.utils import month_label


def _normalise_cell(cell):
    if isinstance(cell, dict):
        return cell
    if isinstance(cell, tuple):
        return {"text": cell[0], "tone": cell[1] if len(cell) > 1 else None}
    return {"text": cell}


class ColumnListView(RoleRequiredMixin, ListView):
    """List page rendered by the shared ``app/list.html`` table template.

    Subclasses declare ``headers`` and implement ``get_cells(obj)``.
    """

    template_name = "app/list.html"
    paginate_by = 20
    headers: list[str] = []
    filters: list[dict] = []
    search_fields: list[str] = []
    search_placeholder = "Cari…"
    title = ""
    subtitle = ""
    create_url = None
    create_label = "Tambah"
    create_roles: tuple[str, ...] = ()
    row_url_name = None
    empty_text = "Belum ada data."
    nav = ""
    align_right: tuple[int, ...] = ()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(condition)
        for spec in self.filters:
            value = self.request.GET.get(spec["name"], "").strip()
            if not value:
                continue
            field = spec.get("field", spec["name"])
            try:
                queryset = queryset.filter(**{field: value})
            except (ValueError, TypeError):
                continue
        return queryset

    def get_cells(self, obj) -> list:
        return [str(obj)]

    def get_row_url(self, obj) -> str | None:
        if not self.row_url_name:
            return None
        try:
            return reverse(self.row_url_name, args=[obj.pk])
        except Exception:  # noqa: BLE001 - optional row link
            return None

    def get_rows(self, objects=None) -> list[dict]:
        objects = self.object_list if objects is None else objects
        return [
            {
                "obj": obj,
                "cells": [_normalise_cell(cell) for cell in self.get_cells(obj)],
                "url": self.get_row_url(obj),
            }
            for obj in objects
        ]

    def get_filter_specs(self) -> list[dict]:
        specs = []
        for spec in self.filters:
            item = dict(spec)
            item["value"] = self.request.GET.get(spec["name"], "")
            specs.append(item)
        return specs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "subtitle": self.subtitle,
                "headers": self.headers,
                "align_right": self.align_right,
                "rows": self.get_rows(context.get("object_list")),
                "filters": self.get_filter_specs(),
                "search_fields": self.search_fields,
                "search_placeholder": self.search_placeholder,
                "query": self.request.GET.get("q", ""),
                "create_url": self.create_url,
                "create_label": self.create_label,
                "can_create": bool(self.create_url)
                and (
                    not self.create_roles
                    or self.request.user.role in self.create_roles
                    or self.request.user.is_superuser
                ),
                "empty_text": self.empty_text,
                "total_count": context["paginator"].count if context.get("paginator") else len(self.object_list),
                "nav": self.nav,
                "has_filters": bool(self.filters) or bool(self.search_fields),
            }
        )
        params = self.request.GET.copy()
        params.pop("page", None)
        context["querystring"] = params.urlencode()
        return context


class FormPageMixin:
    """Context helpers for pages rendered with ``app/form.html``."""

    title = ""
    subtitle = ""
    cancel_url = None
    submit_label = "Simpan"
    form_intro = ""
    nav = ""

    def context(self, form) -> dict:
        return {
            "form": form,
            "title": self.title,
            "subtitle": self.subtitle,
            "cancel_url": self.cancel_url,
            "submit_label": self.submit_label,
            "form_intro": self.form_intro,
            "nav": self.nav,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("title", self.title)
        context.setdefault("subtitle", self.subtitle)
        context.setdefault("cancel_url", self.cancel_url)
        context.setdefault("submit_label", self.submit_label)
        context.setdefault("form_intro", self.form_intro)
        context.setdefault("nav", self.nav)
        return context


class DashboardView(RoleRequiredMixin, TemplateView):
    template_name = "app/dashboard.html"
    allowed_roles = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)
    nav = "dashboard"

    def get_context_data(self, **kwargs):
        from django.db.models import Sum

        from apps.finance.models import Transaction
        from apps.finance.services import fund_balances, month_totals, monthly_series
        from apps.forecasting.services import cashflow_forecast
        from apps.programs.models import Program
        from apps.zakat.models import ZakatDistribution, ZakatReceipt

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        balances = fund_balances()
        current = month_totals(today.year, today.month)
        previous_year, previous_month = (
            (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        )
        previous = month_totals(previous_year, previous_month)

        def delta(current_value, previous_value):
            if not previous_value:
                return None
            change = (float(current_value) - float(previous_value)) / float(previous_value) * 100
            return round(change, 1)

        context.update(
            {
                "nav": self.nav,
                "today": today,
                "month_label": month_label(today.year, today.month),
                "total_balance": sum(row["balance"] for row in balances),
                "balances": balances,
                "month": current,
                "income_delta": delta(current["income"], previous["income"]),
                "expense_delta": delta(current["expense"], previous["expense"]),
                "series": monthly_series(12),
                "recent": (
                    Transaction.objects.filter(status=Transaction.Status.APPROVED)
                    .select_related("category", "fund")
                    .order_by("-date", "-id")[:8]
                ),
                "pending": (
                    Transaction.objects.filter(status=Transaction.Status.PENDING)
                    .select_related("fund", "created_by")
                    .order_by("date")[:5]
                ),
                "pending_total": Transaction.objects.filter(
                    status=Transaction.Status.PENDING
                ).count(),
                "programs": (
                    Program.objects.filter(is_published=True)
                    .exclude(status=Program.Status.CANCELLED)
                    .order_by("status", "-created_at")[:3]
                ),
                "forecast": cashflow_forecast(),
            }
        )
        zakat_received = ZakatReceipt.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        zakat_distributed = (
            ZakatDistribution.objects.aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        context["zakat"] = {
            "received": zakat_received,
            "distributed": zakat_distributed,
            "remaining": zakat_received - zakat_distributed,
        }
        return context


class SettingsForm(StyledForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groups = []
        for group in SETTING_GROUPS:
            fields = []
            for spec in group["fields"]:
                self.fields[spec["key"]] = forms.CharField(
                    label=spec["label"],
                    required=False,
                    initial=Setting.get(spec["key"]),
                    help_text=spec.get("help", ""),
                    widget=forms.TextInput(
                        attrs={"class": "input", "placeholder": spec.get("placeholder", "")}
                    ),
                )
                fields.append((spec, self[spec["key"]]))
            self.groups.append({"key": group["key"], "label": group["label"],
                                "description": group.get("description", ""),
                                "fields": fields})


class SettingsView(RoleRequiredMixin, TemplateView):
    template_name = "app/settings.html"
    allowed_roles = (Role.ADMIN,)
    nav = "settings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or SettingsForm()
        context["title"] = "Pengaturan"
        context["nav"] = self.nav
        return context

    def post(self, request):
        form = SettingsForm(request.POST)
        if form.is_valid():
            for group in SETTING_GROUPS:
                for spec in group["fields"]:
                    Setting.set(spec["key"], form.cleaned_data.get(spec["key"], ""),
                                label=spec["label"], group=group["key"])
            messages.success(request, "Pengaturan tersimpan.")
            return redirect("core:settings")
        return render(request, "app/settings.html", self.get_context_data(form=form))


def healthcheck(request):
    return JsonResponse({"status": "ok", "service": "sidama"})
