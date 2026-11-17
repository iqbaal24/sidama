"""Asset views."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, UpdateView

from apps.accounts.models import Role
from apps.assets.forms import AssetForm, AssetLogForm
from apps.assets.models import Asset
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView, FormPageMixin

ASSET_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)


class AssetListView(ColumnListView):
    model = Asset
    allowed_roles = ASSET_ROLES
    nav = "assets"
    title = "Inventaris Aset"
    subtitle = "Sajadah, pengeras suara, dan aset masjid lainnya."
    headers = ["Nama aset", "Kategori", "Jumlah", "Kondisi", "Lokasi", "Nilai"]
    search_fields = ["name", "category", "location"]
    create_url = reverse_lazy("assets:asset_create")
    create_label = "Tambah aset"
    row_url_name = "assets:asset_detail"
    filters = [
        {"name": "condition", "label": "Kondisi", "field": "condition",
         "type": "select", "options": list(Asset.Condition.choices)},
    ]

    def get_queryset(self):
        return Asset.objects.prefetch_related("logs")

    def get_cells(self, obj):
        return [
            {"text": obj.name, "strong": True, "sub": obj.note or ""},
            {"text": obj.category},
            {"text": obj.quantity},
            {"text": obj.get_condition_display(), "badge": obj.condition_tone},
            {"text": obj.location or "—", "muted": True},
            {"text": obj.value, "money": True},
        ]


class AssetCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = ASSET_ROLES
    nav = "assets"
    title = "Tambah aset"
    cancel_url = reverse_lazy("assets:asset_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(AssetForm()))

    def post(self, request):
        form = AssetForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Aset {obj.name} ditambahkan.")
            return redirect("assets:asset_detail", pk=obj.pk)
        return render(request, "app/form.html", self.context(form))


class AssetUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    allowed_roles = ASSET_ROLES
    nav = "assets"
    template_name = "app/form.html"
    title = "Ubah aset"
    cancel_url = reverse_lazy("assets:asset_list")

    def get_success_url(self):
        return reverse_lazy("assets:asset_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Aset diperbarui.")
        return super().form_valid(form)


class AssetDetailView(RoleRequiredMixin, DetailView):
    model = Asset
    template_name = "app/asset_detail.html"
    allowed_roles = ASSET_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav"] = "assets"
        context["logs"] = self.object.logs.select_related("created_by")
        context["log_form"] = AssetLogForm()
        return context


class AssetLogCreateView(RoleRequiredMixin, View):
    allowed_roles = ASSET_ROLES

    def post(self, request, pk):
        asset = Asset.objects.get(pk=pk)
        form = AssetLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.asset = asset
            log.created_by = request.user
            log.save()
            messages.success(request, "Riwayat aset dicatat.")
        else:
            messages.error(request, "Riwayat aset gagal dicatat. Periksa kembali isian.")
        return redirect("assets:asset_detail", pk=asset.pk)
