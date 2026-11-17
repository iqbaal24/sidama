"""Internal program & donation management."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView, FormPageMixin
from apps.programs.forms import ProgramForm
from apps.programs.models import Donation, Program
from apps.programs.services import confirm_donation, reject_donation

PROGRAM_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)


class ProgramListView(ColumnListView):
    model = Program
    allowed_roles = PROGRAM_ROLES
    nav = "programs"
    title = "Program Donasi"
    subtitle = "Program penggalangan dana dan dana terikat."
    headers = ["Program", "Periode", "Target", "Terkumpul", "Status"]
    search_fields = ["title", "description"]
    create_url = reverse_lazy("programs:program_create")
    create_roles = PROGRAM_ROLES
    create_label = "Buat program"
    row_url_name = "programs:program_update"
    empty_text = "Belum ada program donasi."
    filters = [
        {"name": "status", "label": "Status", "field": "status", "type": "select",
         "options": list(Program.Status.choices)},
    ]

    def get_queryset(self):
        return Program.objects.select_related("fund")

    def get_cells(self, obj):
        period = obj.start_date.strftime("%d/%m/%Y")
        if obj.end_date:
            period += f" – {obj.end_date.strftime('%d/%m/%Y')}"
        tone = {"active": "success", "completed": "info",
                "draft": "muted", "cancelled": "danger"}.get(obj.status, "muted")
        return [
            {"text": obj.title, "strong": True,
             "sub": "Tampil publik" if obj.is_published else "Belum tampil publik"},
            {"text": period, "muted": True},
            {"text": obj.target_amount, "money": True},
            {"text": obj.collected, "money": True,
             "sub": f"{obj.progress}% dari target"},
            {"text": obj.get_status_display(), "badge": tone},
        ]


class ProgramCreateView(RoleRequiredMixin, FormPageMixin, CreateView):
    model = Program
    form_class = ProgramForm
    allowed_roles = PROGRAM_ROLES
    nav = "programs"
    template_name = "app/form.html"
    title = "Buat program donasi"
    subtitle = "Program yang dipublikasikan akan tampil di halaman transparansi."
    cancel_url = reverse_lazy("programs:program_list")
    success_url = reverse_lazy("programs:program_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_action(self.request.user, "create", self.object, note="Program dibuat")
        messages.success(self.request, f"Program “{self.object.title}” dibuat.")
        return response


class ProgramUpdateView(RoleRequiredMixin, FormPageMixin, UpdateView):
    model = Program
    form_class = ProgramForm
    allowed_roles = PROGRAM_ROLES
    nav = "programs"
    template_name = "app/form.html"
    title = "Ubah program"
    cancel_url = reverse_lazy("programs:program_list")
    success_url = reverse_lazy("programs:program_list")

    def form_valid(self, form):
        messages.success(self.request, "Program diperbarui.")
        return super().form_valid(form)


class ProgramPublishView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN, Role.CHAIR)

    def post(self, request, pk):
        program = get_object_or_404(Program, pk=pk)
        program.is_published = not program.is_published
        if program.is_published and program.status == Program.Status.DRAFT:
            program.status = Program.Status.ACTIVE
        program.save()
        log_action(request.user, "publish" if program.is_published else "update",
                   program,
                   note="Program dipublikasikan" if program.is_published
                   else "Program disembunyikan dari publik")
        messages.success(
            request,
            "Program dipublikasikan." if program.is_published
            else "Program disembunyikan dari halaman publik.",
        )
        return redirect("programs:program_list")


class DonationListView(ColumnListView):
    model = Donation
    allowed_roles = PROGRAM_ROLES
    nav = "donations"
    title = "Donasi"
    subtitle = "Konfirmasi donasi yang masuk melalui QRIS, transfer, atau tunai."
    headers = ["Kode", "Donatur", "Program", "Nominal", "Metode", "Status"]
    search_fields = ["code", "donor_name", "program__title"]
    empty_text = "Belum ada donasi."
    filters = [
        {"name": "status", "label": "Status", "field": "status", "type": "select",
         "options": list(Donation.Status.choices)},
        {"name": "method", "label": "Metode", "field": "method", "type": "select",
         "options": list(Donation.Method.choices)},
        {"name": "program", "label": "Program", "field": "program_id",
         "type": "select", "options": []},
    ]

    def get_queryset(self):
        return Donation.objects.select_related("program", "confirmed_by")

    def get_filter_specs(self):
        specs = super().get_filter_specs()
        for spec in specs:
            if spec["name"] == "program":
                spec["options"] = [(str(p.pk), p.title) for p in Program.objects.all()]
        return specs

    def get_row_url(self, obj):
        return reverse("public:donation_status", args=[obj.code])

    def get_cells(self, obj):
        return [
            {"text": obj.code, "strong": True, "sub": obj.created_at.strftime("%d/%m/%Y")},
            {"text": obj.display_name,
             "sub": "Anonim" if obj.is_anonymous else (obj.contact or "")},
            {"text": obj.program.title, "muted": True},
            {"text": obj.amount, "money": True},
            {"text": obj.get_method_display()},
            {"text": obj.get_status_display(), "badge": obj.status_tone},
        ]


class DonationDecisionView(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN, Role.CHAIR, Role.TREASURER)
    confirm: bool = True

    def post(self, request, pk):
        donation = get_object_or_404(Donation, pk=pk)
        if self.confirm:
            if donation.status == Donation.Status.CONFIRMED:
                messages.info(request, "Donasi ini sudah dikonfirmasi.")
                return redirect("programs:donation_list")
            confirm_donation(donation, request.user)
            messages.success(
                request,
                f"Donasi {donation.code} dikonfirmasi dan masuk ke kas dana program.",
            )
        else:
            reject_donation(donation, request.user,
                            request.POST.get("note", "").strip())
            messages.warning(request, f"Donasi {donation.code} ditolak.")
        return redirect("programs:donation_list")


class DonationConfirmView(DonationDecisionView):
    confirm = True


class DonationRejectView(DonationDecisionView):
    confirm = False
