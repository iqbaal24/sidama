"""Zakat views: overview, muzakki, mustahik, receipts, distributions, report."""
from __future__ import annotations

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView, FormPageMixin
from apps.zakat.forms import MustahikForm, MuzakkiForm, ZakatDistributionForm, ZakatReceiptForm
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt
from apps.zakat.services import (
    monthly_zakat_report,
    record_distribution,
    record_receipt,
    zakat_summary,
)

ZAKAT_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)
TREASURER_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER)


class ZakatOverviewView(RoleRequiredMixin, TemplateView):
    template_name = "app/zakat_overview.html"
    allowed_roles = ZAKAT_ROLES
    nav = "zakat"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = int(self.request.GET.get("year") or today.year)
        context.update({
            "nav": self.nav,
            "title": "Zakat",
            "subtitle": "Penerimaan, penyaluran, dan mustahik dalam satu tempat.",
            "summary": zakat_summary(year=year),
            "year": year,
            "years": range(today.year, today.year - 4, -1),
            "monthly": monthly_zakat_report(year),
            "recent_receipts": ZakatReceipt.objects.select_related("muzakki")[:5],
            "recent_distributions": (
                ZakatDistribution.objects.select_related("mustahik")[:5]
            ),
            "mustahik_pending": Mustahik.objects.filter(is_verified=False).count(),
        })
        return context


class MuzakkiListView(ColumnListView):
    model = Muzakki
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_muzakki"
    title = "Muzakki"
    subtitle = "Data pembayar zakat."
    headers = ["Nama", "Telepon", "Alamat", "Jumlah penerimaan"]
    search_fields = ["name", "phone", "address"]
    create_url = reverse_lazy("zakat:muzakki_create")
    create_label = "Tambah muzakki"
    row_url_name = "zakat:muzakki_update"

    def get_queryset(self):
        return Muzakki.objects.annotate(receipt_count=Count("receipts")).order_by("name")

    def get_cells(self, obj):
        return [
            {"text": obj.name, "strong": True},
            {"text": obj.phone or "—", "muted": True},
            {"text": obj.address or "—", "muted": True},
            {"text": f"{obj.receipt_count} penerimaan"},
        ]


class MuzakkiCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_muzakki"
    title = "Tambah muzakki"
    cancel_url = reverse_lazy("zakat:muzakki_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(MuzakkiForm()))

    def post(self, request):
        form = MuzakkiForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Muzakki {obj.name} ditambahkan.")
            return redirect("zakat:muzakki_list")
        return render(request, "app/form.html", self.context(form))


class MuzakkiUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Muzakki
    form_class = MuzakkiForm
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_muzakki"
    template_name = "app/form.html"
    title = "Ubah muzakki"
    success_url = reverse_lazy("zakat:muzakki_list")
    cancel_url = reverse_lazy("zakat:muzakki_list")


class MustahikListView(ColumnListView):
    model = Mustahik
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_mustahik"
    title = "Mustahik"
    subtitle = "Penerima zakat beserta status verifikasi."
    headers = ["Nama", "Asnaf", "Alamat", "Diterima", "Verifikasi"]
    search_fields = ["name", "address", "note"]
    create_url = reverse_lazy("zakat:mustahik_create")
    create_label = "Tambah mustahik"
    row_url_name = "zakat:mustahik_update"
    filters = [
        {"name": "asnaf", "label": "Asnaf", "field": "asnaf", "type": "select",
         "options": list(Mustahik.Asnaf.choices)},
        {"name": "verified", "label": "Verifikasi", "field": "is_verified",
         "type": "select", "options": [("1", "Terverifikasi"), ("0", "Belum")]},
    ]

    def get_queryset(self):
        return Mustahik.objects.prefetch_related("distributions")

    def get_cells(self, obj):
        return [
            {"text": obj.name, "strong": True},
            {"text": obj.get_asnaf_display()},
            {"text": obj.address or "—", "muted": True},
            {"text": obj.total_received, "money": True},
            {"text": "Terverifikasi" if obj.is_verified else "Belum",
             "badge": "success" if obj.is_verified else "warning"},
        ]


class MustahikCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_mustahik"
    title = "Tambah mustahik"
    cancel_url = reverse_lazy("zakat:mustahik_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(MustahikForm()))

    def post(self, request):
        form = MustahikForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Mustahik {obj.name} ditambahkan.")
            return redirect("zakat:mustahik_list")
        return render(request, "app/form.html", self.context(form))


class MustahikUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Mustahik
    form_class = MustahikForm
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_mustahik"
    template_name = "app/form.html"
    title = "Ubah mustahik"
    success_url = reverse_lazy("zakat:mustahik_list")
    cancel_url = reverse_lazy("zakat:mustahik_list")


class MustahikVerifyView(RoleRequiredMixin, View):
    allowed_roles = ZAKAT_ROLES

    def post(self, request, pk):
        mustahik = get_object_or_404(Mustahik, pk=pk)
        mustahik.is_verified = not mustahik.is_verified
        mustahik.save(update_fields=["is_verified", "updated_at"])
        log_action(request.user, "update", mustahik,
                   note="Verifikasi mustahik diubah")
        messages.success(
            request,
            f"{mustahik.name} {'diverifikasi' if mustahik.is_verified else 'dibatalkan verifikasinya'}.",
        )
        return redirect("zakat:mustahik_list")


class ReceiptListView(ColumnListView):
    model = ZakatReceipt
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_receipts"
    title = "Penerimaan Zakat"
    subtitle = "Setiap penerimaan otomatis masuk ke Dana Zakat."
    headers = ["Bukti", "Tanggal", "Pembayar", "Jenis", "Nominal"]
    search_fields = ["number", "muzakki_name", "muzakki__name"]
    create_url = reverse_lazy("zakat:receipt_create")
    create_roles = TREASURER_ROLES
    create_label = "Catat penerimaan"
    empty_text = "Belum ada penerimaan zakat."
    filters = [
        {"name": "type", "label": "Jenis", "field": "zakat_type", "type": "select",
         "options": list(ZakatReceipt.Type.choices)},
        {"name": "date_from", "label": "Dari", "field": "date__gte", "type": "date"},
        {"name": "date_to", "label": "Sampai", "field": "date__lte", "type": "date"},
    ]

    def get_queryset(self):
        return ZakatReceipt.objects.select_related("muzakki", "transaction")

    def get_cells(self, obj):
        return [
            {"text": obj.number, "strong": True,
             "sub": "Masuk kas" if obj.transaction_id else "Belum dibukukan"},
            {"text": obj.date.strftime("%d/%m/%Y"), "muted": True},
            {"text": obj.payer_name},
            {"text": obj.get_zakat_type_display()},
            {"text": obj.amount, "money": True},
        ]


class ReceiptCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = TREASURER_ROLES
    nav = "zakat_receipts"
    title = "Catat penerimaan zakat"
    subtitle = "Penerimaan akan otomatis dibukukan sebagai kas masuk Dana Zakat."
    cancel_url = reverse_lazy("zakat:receipt_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(ZakatReceiptForm()))

    def post(self, request):
        form = ZakatReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save()
            record_receipt(receipt, request.user)
            messages.success(
                request,
                f"Penerimaan {receipt.number} dicatat dan masuk ke Dana Zakat.",
            )
            return redirect("zakat:receipt_list")
        return render(request, "app/form.html", self.context(form))


class DistributionListView(ColumnListView):
    model = ZakatDistribution
    allowed_roles = ZAKAT_ROLES
    nav = "zakat_distributions"
    title = "Penyaluran Zakat"
    subtitle = "Penyaluran ke mustahik tercatat sebagai kas keluar Dana Zakat."
    headers = ["Tanggal", "Mustahik", "Bentuk", "Nominal", "Status"]
    search_fields = ["mustahik__name", "item_description", "note"]
    create_url = reverse_lazy("zakat:distribution_create")
    create_roles = TREASURER_ROLES
    create_label = "Catat penyaluran"
    empty_text = "Belum ada penyaluran zakat."
    filters = [
        {"name": "asnaf", "label": "Asnaf", "field": "mustahik__asnaf",
         "type": "select", "options": list(Mustahik.Asnaf.choices)},
        {"name": "date_from", "label": "Dari", "field": "date__gte", "type": "date"},
        {"name": "date_to", "label": "Sampai", "field": "date__lte", "type": "date"},
    ]

    def get_queryset(self):
        return ZakatDistribution.objects.select_related("mustahik", "transaction")

    def get_cells(self, obj):
        return [
            {"text": obj.date.strftime("%d/%m/%Y"), "muted": True},
            {"text": obj.mustahik.name, "strong": True,
             "sub": obj.mustahik.get_asnaf_display()},
            {"text": obj.item_description or "Uang tunai", "muted": True},
            {"text": obj.amount, "money": True},
            {"text": "Dibukukan" if obj.transaction_id else "Belum",
             "badge": "success" if obj.transaction_id else "warning"},
        ]


class DistributionCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = TREASURER_ROLES
    nav = "zakat_distributions"
    title = "Catat penyaluran zakat"
    subtitle = "Pastikan mustahik sudah terverifikasi sebelum menyalurkan dana."
    cancel_url = reverse_lazy("zakat:distribution_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(ZakatDistributionForm()))

    def post(self, request):
        form = ZakatDistributionForm(request.POST)
        if form.is_valid():
            distribution = form.save()
            record_distribution(distribution, request.user)
            messages.success(request, "Penyaluran zakat dicatat dan dibukukan.")
            return redirect("zakat:distribution_list")
        return render(request, "app/form.html", self.context(form))
