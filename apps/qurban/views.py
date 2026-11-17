"""Qurban views."""
from __future__ import annotations

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView, FormPageMixin
from apps.qurban.forms import MeatDistributionForm, QurbanRegistrationForm
from apps.qurban.models import MeatDistribution, QurbanRegistration

QURBAN_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)


class RegistrationListView(ColumnListView):
    model = QurbanRegistration
    allowed_roles = QURBAN_ROLES
    nav = "qurban"
    title = "Pendaftaran Kurban"
    subtitle = "Shohibul kurban, jenis hewan, dan status pembayaran."
    headers = ["Shohibul", "Tahun", "Hewan", "Jiwa", "Nominal", "Pembayaran"]
    search_fields = ["name", "phone"]
    create_url = reverse_lazy("qurban:registration_create")
    create_label = "Tambah pendaftaran"
    row_url_name = "qurban:registration_update"
    filters = [
        {"name": "year", "label": "Tahun", "field": "year", "type": "select",
         "options": []},
        {"name": "payment", "label": "Pembayaran", "field": "payment_status",
         "type": "select", "options": list(QurbanRegistration.Payment.choices)},
        {"name": "animal", "label": "Hewan", "field": "animal_type",
         "type": "select", "options": list(QurbanRegistration.Animal.choices)},
    ]

    def get_queryset(self):
        return QurbanRegistration.objects.all()

    def get_filter_specs(self):
        specs = super().get_filter_specs()
        years = QurbanRegistration.objects.values_list("year", flat=True).distinct().order_by("-year")
        for spec in specs:
            if spec["name"] == "year":
                spec["options"] = [(str(y), str(y)) for y in years]
        return specs

    def get_cells(self, obj):
        return [
            {"text": obj.name, "strong": True, "sub": obj.phone or ""},
            {"text": obj.year, "muted": True},
            {"text": obj.get_animal_type_display()},
            {"text": f"{obj.share_count} jiwa"},
            {"text": obj.amount, "money": True},
            {"text": obj.get_payment_status_display(),
             "badge": {"paid": "success", "dp": "warning",
                       "unpaid": "danger"}.get(obj.payment_status, "muted")},
        ]


class RegistrationCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = QURBAN_ROLES
    nav = "qurban"
    title = "Tambah pendaftaran kurban"
    cancel_url = reverse_lazy("qurban:registration_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(QurbanRegistrationForm()))

    def post(self, request):
        form = QurbanRegistrationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, f"Pendaftaran {obj.name} ditambahkan.")
            return redirect("qurban:registration_list")
        return render(request, "app/form.html", self.context(form))


class RegistrationUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = QurbanRegistration
    form_class = QurbanRegistrationForm
    allowed_roles = QURBAN_ROLES
    nav = "qurban"
    template_name = "app/form.html"
    title = "Ubah pendaftaran kurban"
    success_url = reverse_lazy("qurban:registration_list")
    cancel_url = reverse_lazy("qurban:registration_list")


class DistributionListView(ColumnListView):
    model = MeatDistribution
    allowed_roles = QURBAN_ROLES
    nav = "qurban_distribution"
    title = "Distribusi Daging"
    subtitle = "Penerima daging kurban beserta kupon."
    headers = ["Penerima", "Berat", "Kupon", "Status", "Waktu"]
    search_fields = ["recipient_name", "coupon_code"]
    create_url = reverse_lazy("qurban:distribution_create")
    create_label = "Tambah penerima"
    row_url_name = "qurban:distribution_update"
    filters = [
        {"name": "received", "label": "Sudah menerima", "field": "is_received",
         "type": "select", "options": [("1", "Ya"), ("0", "Belum")]},
    ]

    def get_queryset(self):
        return MeatDistribution.objects.select_related("registration")

    def get_cells(self, obj):
        return [
            {"text": obj.recipient_name, "strong": True,
             "sub": obj.registration.name if obj.registration else ""},
            {"text": f"{obj.weight_kg} kg"},
            {"text": obj.coupon_code},
            {"text": "Sudah menerima" if obj.is_received else "Belum",
             "badge": "success" if obj.is_received else "warning"},
            {"text": obj.received_at.strftime("%d/%m/%Y %H:%M") if obj.received_at else "—",
             "muted": True},
        ]


class DistributionCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = QURBAN_ROLES
    nav = "qurban_distribution"
    title = "Tambah penerima daging"
    cancel_url = reverse_lazy("qurban:distribution_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(MeatDistributionForm()))

    def post(self, request):
        form = MeatDistributionForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Penerima {obj.recipient_name} ditambahkan.")
            return redirect("qurban:distribution_list")
        return render(request, "app/form.html", self.context(form))


class DistributionUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = MeatDistribution
    form_class = MeatDistributionForm
    allowed_roles = QURBAN_ROLES
    nav = "qurban_distribution"
    template_name = "app/form.html"
    title = "Ubah penerima daging"
    success_url = reverse_lazy("qurban:distribution_list")
    cancel_url = reverse_lazy("qurban:distribution_list")


class DistributionReceiveView(RoleRequiredMixin, View):
    allowed_roles = QURBAN_ROLES

    def post(self, request, pk):
        obj = get_object_or_404(MeatDistribution, pk=pk)
        obj.is_received = not obj.is_received
        if not obj.is_received:
            obj.received_at = None
        obj.save()
        log_action(request.user, "update", obj, note="Status penerimaan daging diubah")
        messages.success(
            request,
            f"{obj.recipient_name} ditandai {'sudah' if obj.is_received else 'belum'} menerima.",
        )
        return redirect("qurban:distribution_list")


class QurbanReportView(RoleRequiredMixin, TemplateView):
    template_name = "app/qurban_report.html"
    allowed_roles = QURBAN_ROLES
    nav = "qurban_report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = int(self.request.GET.get("year") or today.year)
        registrations = QurbanRegistration.objects.filter(year=year)
        distributions = MeatDistribution.objects.filter(
            registration__year=year
        ) | MeatDistribution.objects.filter(registration__isnull=True,
                                            created_at__year=year)
        context.update({
            "nav": self.nav,
            "title": "Laporan Kurban",
            "subtitle": f"Rekap pelaksanaan kurban tahun {year}.",
            "year": year,
            "years": range(today.year, today.year - 4, -1),
            "registrations": registrations,
            "total_people": registrations.aggregate(total=Sum("share_count"))["total"] or 0,
            "total_amount": registrations.aggregate(total=Sum("amount"))["total"] or 0,
            "paid_count": registrations.filter(payment_status="paid").count(),
            "distribution_count": distributions.count(),
            "distribution_weight": distributions.aggregate(total=Sum("weight_kg"))["total"] or 0,
            "received_count": distributions.filter(is_received=True).count(),
            "animal_summary": registrations.values("animal_type").annotate(
                count=Sum("share_count"), total=Sum("amount")
            ),
        })
        return context
