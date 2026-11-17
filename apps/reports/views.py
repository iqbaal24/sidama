"""Report generation, publishing and download views."""
from __future__ import annotations

from django import forms
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View

from apps.accounts.models import Role
from apps.audit.services import log_action
from apps.core.forms import StyledForm
from apps.core.mixins import RoleRequiredMixin
from apps.core.utils import month_label
from apps.core.views import ColumnListView
from apps.notifications.services import send_telegram_async
from apps.reports.generator import generate_report
from apps.reports.models import Report

REPORT_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)
GENERATE_ROLES = (Role.ADMIN, Role.CHAIR, Role.TREASURER)
PUBLISH_ROLES = (Role.ADMIN, Role.CHAIR)


class ReportGenerateForm(StyledForm):
    report_type = forms.ChoiceField(label="Jenis laporan", choices=Report.Type.choices)
    period_year = forms.IntegerField(label="Tahun", min_value=2020, max_value=2100)
    period_month = forms.ChoiceField(
        label="Bulan", required=False,
        choices=[("", "— Untuk laporan tahunan —")]
        + [(str(month), month_label(2024, month)) for month in range(1, 13)],
    )
    note = forms.CharField(label="Catatan", required=False, max_length=255)


class ReportListView(ColumnListView):
    model = Report
    allowed_roles = REPORT_ROLES
    nav = "reports"
    title = "Laporan"
    subtitle = "Laporan bulanan dan tahunan dalam format PDF dan Excel."
    headers = ["Periode", "Jenis", "Dibuat", "Status", ""]
    create_url = reverse_lazy("reports:generate")
    create_roles = GENERATE_ROLES
    create_label = "Buat laporan"
    empty_text = "Belum ada laporan. Buat laporan bulanan pertama Anda."
    filters = [
        {"name": "type", "label": "Jenis", "field": "report_type", "type": "select",
         "options": list(Report.Type.choices)},
        {"name": "status", "label": "Status", "field": "status", "type": "select",
         "options": list(Report.Status.choices)},
        {"name": "year", "label": "Tahun", "field": "period_year", "type": "select",
         "options": []},
    ]

    def get_queryset(self):
        return Report.objects.select_related("published_by", "created_by")

    def get_filter_specs(self):
        specs = super().get_filter_specs()
        years = Report.objects.values_list("period_year", flat=True).distinct().order_by("-period_year")
        for spec in specs:
            if spec["name"] == "year":
                spec["options"] = [(str(y), str(y)) for y in years]
        return specs

    def get_row_url(self, obj):
        return None

    def get_rows(self, objects=None):
        rows = super().get_rows(objects)
        can_publish = (
            self.request.user.role in PUBLISH_ROLES or self.request.user.is_superuser
        )
        for row in rows:
            report = row["obj"]
            actions = []
            if report.pdf_file:
                actions.append({
                    "label": "PDF",
                    "url": reverse("reports:download", args=[report.pk, "pdf"]),
                    "class": "btn-outline",
                })
            if report.xlsx_file:
                actions.append({
                    "label": "Excel",
                    "url": reverse("reports:download", args=[report.pk, "xlsx"]),
                    "class": "btn-outline",
                })
            if can_publish:
                if report.is_published:
                    actions.append({
                        "label": "Tarik",
                        "url": reverse("reports:unpublish", args=[report.pk]),
                        "method": "post",
                        "class": "btn-ghost",
                        "confirm": "Tarik laporan ini dari halaman publik?",
                    })
                else:
                    actions.append({
                        "label": "Terbitkan",
                        "url": reverse("reports:publish", args=[report.pk]),
                        "method": "post",
                        "class": "btn-outline",
                    })
            row["extra_actions"] = actions
        return rows

    def get_cells(self, obj):
        return [
            {"text": obj.period_label, "strong": True,
             "sub": f"oleh {obj.created_by.display_name}" if obj.created_by else ""},
            {"text": obj.get_report_type_display()},
            {"text": obj.generated_at.strftime("%d/%m/%Y %H:%M")
             if obj.generated_at else "Belum dibuat",
             "muted": True},
            {"text": obj.get_status_display(),
             "badge": "success" if obj.is_published else "warning"},
            {"text": "", "actions": True},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_publish"] = self.request.user.role in PUBLISH_ROLES or self.request.user.is_superuser
        return context


class ReportGenerateView(RoleRequiredMixin, View):
    allowed_roles = GENERATE_ROLES
    nav = "reports"
    title = "Buat laporan"
    subtitle = "Laporan dibuat otomatis dari transaksi yang sudah disetujui."

    def get(self, request):
        today = timezone.localdate()
        form = ReportGenerateForm(initial={
            "report_type": Report.Type.MONTHLY,
            "period_year": today.year,
            "period_month": str(today.month),
        })
        return render(request, "app/report_form.html", {
            "form": form, "title": self.title, "subtitle": self.subtitle,
            "nav": self.nav, "cancel_url": reverse_lazy("reports:list"),
        })

    def post(self, request):
        form = ReportGenerateForm(request.POST)
        if not form.is_valid():
            return render(request, "app/report_form.html", {
                "form": form, "title": self.title, "subtitle": self.subtitle,
                "nav": self.nav, "cancel_url": reverse_lazy("reports:list"),
            })
        report_type = form.cleaned_data["report_type"]
        year = form.cleaned_data["period_year"]
        month = form.cleaned_data["period_month"] or None
        if report_type == Report.Type.MONTHLY and not month:
            form.add_error("period_month", "Laporan bulanan membutuhkan bulan.")
            return render(request, "app/report_form.html", {
                "form": form, "title": self.title, "subtitle": self.subtitle,
                "nav": self.nav, "cancel_url": reverse_lazy("reports:list"),
            })
        report, _ = Report.objects.get_or_create(
            report_type=report_type,
            period_year=year,
            period_month=None if report_type != Report.Type.MONTHLY else int(month),
            defaults={"created_by": request.user, "status": Report.Status.DRAFT},
        )
        report.created_by = report.created_by or request.user
        report.note = form.cleaned_data.get("note", "")
        report.save(update_fields=["created_by", "note"])
        generate_report(report)
        log_action(request.user, "generate", report, note="Laporan dibuat")
        messages.success(
            request,
            f"Laporan {report.period_label} berhasil dibuat. Unduh PDF atau Excel di daftar laporan.",
        )
        return redirect("reports:list")


class ReportPublishView(RoleRequiredMixin, View):
    allowed_roles = PUBLISH_ROLES

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        if not report.generated_at:
            generate_report(report)
        report.status = Report.Status.PUBLISHED
        report.published_at = timezone.now()
        report.published_by = request.user
        report.save(update_fields=["status", "published_at", "published_by"])
        log_action(request.user, "publish", report,
                   note="Laporan diterbitkan ke halaman publik")
        send_telegram_async(
            f"✅ Laporan {report.period_label} telah diterbitkan dan dapat diunduh jamaah."
        )
        messages.success(request, f"Laporan {report.period_label} diterbitkan.")
        return redirect("reports:list")


class ReportUnpublishView(RoleRequiredMixin, View):
    allowed_roles = PUBLISH_ROLES

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        report.status = Report.Status.DRAFT
        report.published_at = None
        report.published_by = None
        report.save(update_fields=["status", "published_at", "published_by"])
        log_action(request.user, "update", report,
                   note="Laporan ditarik dari halaman publik")
        messages.warning(request, f"Laporan {report.period_label} ditarik dari publik.")
        return redirect("reports:list")


class ReportDownloadView(RoleRequiredMixin, View):
    allowed_roles = REPORT_ROLES

    def get(self, request, pk, fmt):
        report = get_object_or_404(Report, pk=pk)
        return _serve(report, fmt)


def _serve(report: Report, fmt: str):
    if fmt not in {"pdf", "xlsx"}:
        raise Http404("Format tidak dikenal.")
    field = report.pdf_file if fmt == "pdf" else report.xlsx_file
    if not field:
        raise Http404("Berkas laporan belum dibuat.")
    content_type = ("application/pdf" if fmt == "pdf"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return FileResponse(field.open("rb"), as_attachment=True,
                        filename=f"{report.filename_stem}.{fmt}",
                        content_type=content_type)


def public_download(request, pk, fmt):
    report = get_object_or_404(Report, pk=pk, status=Report.Status.PUBLISHED)
    return _serve(report, fmt)
