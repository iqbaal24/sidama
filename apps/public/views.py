"""Public transparency pages — no login required."""
from __future__ import annotations

from django import forms
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from apps.core.models import Setting
from apps.core.utils import month_bounds, month_label
from apps.finance.models import Transaction
from apps.finance.services import expense_by_category, fund_balances, month_totals, monthly_series
from apps.programs.forms import PublicDonationForm
from apps.programs.models import Donation, Program
from apps.programs.services import create_donation
from apps.reports.models import Report
from apps.zakat.services import calculate_zakat, zakat_summary


class PublicHomeView(TemplateView):
    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        start, end = month_bounds(today.year, today.month)
        cache_key = f"public-home:{today:%Y-%m-%d}:{Transaction.objects.count()}"
        cached = cache.get(cache_key)
        if cached:
            context.update(cached)
            return context

        balances = fund_balances()
        fund_groups = []
        for fund_type, label in [
            ("general", "Dana umum"),
            ("zakat", "Dana zakat"),
            ("restricted", "Dana terikat program"),
        ]:
            total = sum(
                row["balance"] for row in balances
                if row["fund"].fund_type == fund_type
            )
            if total or fund_type != "restricted":
                fund_groups.append({"label": label, "balance": total})
        current = month_totals(today.year, today.month)
        previous_year, previous_month = (
            (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        )
        previous = month_totals(previous_year, previous_month)
        data = {
            "total_balance": sum(row["balance"] for row in balances),
            "funds": balances,
            "fund_groups": fund_groups,
            "month": current,
            "previous": previous,
            "month_label": month_label(today.year, today.month),
            "series": monthly_series(12),
            "expense_categories": [
                {"name": row["name"], "total": float(row["total"])}
                for row in expense_by_category(start, end)
            ],
            "programs": (
                Program.objects.filter(is_published=True,
                                       status=Program.Status.ACTIVE)
                .order_by("-created_at")[:3]
            ),
            "active_program_count": Program.objects.filter(
                is_published=True, status=Program.Status.ACTIVE
            ).count(),
            "reports": Report.objects.filter(status=Report.Status.PUBLISHED)[:4],
            "donations": (
                Donation.objects.filter(status=Donation.Status.CONFIRMED)
                .select_related("program").order_by("-created_at")[:5]
            ),
            "zakat": zakat_summary(),
            "today": today,
        }
        cache.set(cache_key, data, 60)
        context.update(data)
        return context


class ProgramListView(TemplateView):
    template_name = "public/programs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        programs = Program.objects.filter(is_published=True).exclude(
            status=Program.Status.CANCELLED
        )
        status = self.request.GET.get("status", "active")
        if status in {Program.Status.ACTIVE, Program.Status.COMPLETED}:
            programs = programs.filter(status=status)
        else:
            status = "all"
        context.update({
            "programs": programs.order_by("-status", "-created_at"),
            "active_status": status,
            "total_target": programs.aggregate(total=Sum("target_amount"))["total"] or 0,
        })
        return context


class ProgramDetailView(TemplateView):
    template_name = "public/program_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = get_object_or_404(
            Program.objects.filter(is_published=True), slug=kwargs["slug"]
        )
        donations = program.donations.filter(status=Donation.Status.CONFIRMED)
        context.update({
            "program": program,
            "donation_form": PublicDonationForm(initial={"amount": 100000}),
            "donation_count": donations.count(),
            "donations": donations.order_by("-confirmed_at")[:10],
            "expenses": program.transactions.filter(
                transaction_type=Transaction.Type.EXPENSE,
                status=Transaction.Status.APPROVED,
            ).select_related("category")[:10],
        })
        return context


def donate(request, slug):
    program = get_object_or_404(
        Program.objects.filter(is_published=True), slug=slug
    )
    if request.method != "POST":
        return redirect("public:program_detail", slug=slug)
    form = PublicDonationForm(request.POST)
    if not program.is_open:
        messages.error(request, "Program ini sudah tidak menerima donasi baru.")
        return redirect("public:program_detail", slug=slug)
    if not form.is_valid():
        donations = program.donations.filter(status=Donation.Status.CONFIRMED)
        return render(request, "public/program_detail.html", {
            "program": program,
            "donation_form": form,
            "donation_count": donations.count(),
            "donations": donations.order_by("-confirmed_at")[:10],
        }, status=400)
    donation = create_donation(
        program=program,
        donor_name=form.cleaned_data["donor_name"],
        amount=form.cleaned_data["amount"],
        method=form.cleaned_data["method"],
        message=form.cleaned_data["message"],
        is_anonymous=form.cleaned_data["is_anonymous"],
        contact=form.cleaned_data["contact"],
        donor_user=request.user,
    )
    messages.success(
        request,
        f"Donasi {donation.code} dicatat. Silakan selesaikan pembayaran sesuai instruksi.",
    )
    return redirect("public:donation_status", code=donation.code)


class DonationStatusView(TemplateView):
    template_name = "public/donation_status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        donation = get_object_or_404(
            Donation.objects.select_related("program", "transaction"),
            code=kwargs["code"].upper(),
        )
        context.update({
            "donation": donation,
            "bank_account": Setting.get("bank_account"),
            "qris_note": Setting.get("qris_note"),
            "mosque_phone": Setting.get("mosque_phone"),
        })
        return context


class ZakatCalculatorForm(forms.Form):
    zakat_type = forms.ChoiceField(
        label="Jenis zakat",
        choices=[("mal", "Zakat Mal (harta)"),
                 ("penghasilan", "Zakat Penghasilan"),
                 ("fitrah", "Zakat Fitrah")],
        widget=forms.RadioSelect(attrs={"class": "radio"}),
    )
    assets = forms.DecimalField(
        label="Total harta (tabungan, emas, investasi)", required=False,
        min_value=0, max_digits=16, decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "0",
                                        "step": "100000"}),
    )
    debts = forms.DecimalField(
        label="Utang / kewajiban", required=False, min_value=0,
        max_digits=16, decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "0",
                                        "step": "100000"}),
    )
    monthly_income = forms.DecimalField(
        label="Penghasilan per bulan", required=False, min_value=0,
        max_digits=16, decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "0",
                                        "step": "100000"}),
    )
    dependents = forms.IntegerField(
        label="Jumlah jiwa", required=False, min_value=1, max_value=50, initial=1,
        widget=forms.NumberInput(attrs={"class": "input", "min": "1"}),
    )

    def clean(self):
        cleaned = super().clean()
        zakat_type = cleaned.get("zakat_type")
        if zakat_type == "mal" and not cleaned.get("assets"):
            self.add_error("assets", "Isi total harta untuk menghitung zakat mal.")
        if zakat_type == "penghasilan" and not cleaned.get("monthly_income"):
            self.add_error("monthly_income", "Isi penghasilan bulanan.")
        return cleaned


class ZakatCalculatorView(TemplateView):
    template_name = "public/zakat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or ZakatCalculatorForm(
            initial={"zakat_type": "mal"}
        )
        context["result"] = kwargs.get("result")
        context["mosque_name"] = Setting.get("mosque_name")
        return context

    def post(self, request):
        form = ZakatCalculatorForm(request.POST)
        if not form.is_valid():
            return render(request, "public/zakat.html",
                          self.get_context_data(form=form), status=400)
        data = form.cleaned_data
        result = calculate_zakat(
            zakat_type=data["zakat_type"],
            assets=data.get("assets") or 0,
            debts=data.get("debts") or 0,
            monthly_income=data.get("monthly_income") or 0,
            dependents=data.get("dependents") or 1,
        )
        return render(request, "public/zakat.html",
                      self.get_context_data(form=form, result=result))


class PublicReportListView(TemplateView):
    template_name = "public/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = Report.objects.filter(
            status=Report.Status.PUBLISHED
        ).select_related("published_by")
        return context


class AboutView(TemplateView):
    template_name = "public/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today"] = timezone.localdate()
        return context
