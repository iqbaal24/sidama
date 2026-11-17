"""Generated financial reports (PDF + Excel)."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.utils import month_label


class Report(models.Model):
    class Type(models.TextChoices):
        MONTHLY = "monthly", "Laporan Bulanan"
        ANNUAL = "annual", "Laporan Tahunan"
        PROGRAMS = "programs", "Laporan Program"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draf"
        PUBLISHED = "published", "Terbit"

    report_type = models.CharField("jenis laporan", max_length=20, choices=Type.choices,
                                   default=Type.MONTHLY)
    period_year = models.PositiveIntegerField("tahun")
    period_month = models.PositiveSmallIntegerField("bulan", null=True, blank=True)
    status = models.CharField("status", max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    pdf_file = models.FileField("berkas PDF", upload_to="reports/", blank=True)
    xlsx_file = models.FileField("berkas Excel", upload_to="reports/", blank=True)
    generated_at = models.DateTimeField("dibuat pada", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="reports")
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name="published_reports")
    published_at = models.DateTimeField("terbit pada", null=True, blank=True)
    note = models.CharField("catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "laporan"
        verbose_name_plural = "laporan"
        ordering = ["-period_year", "-period_month", "-id"]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} — {self.period_label}"

    @property
    def period_label(self) -> str:
        if self.report_type == self.Type.ANNUAL:
            return f"Tahun {self.period_year}"
        if self.report_type == self.Type.PROGRAMS:
            return f"Program {self.period_year}"
        if self.period_month:
            return month_label(self.period_year, self.period_month)
        return f"Tahun {self.period_year}"

    @property
    def filename_stem(self) -> str:
        if self.report_type == self.Type.ANNUAL:
            return f"laporan-tahunan-{self.period_year}"
        if self.report_type == self.Type.PROGRAMS:
            return f"laporan-program-{self.period_year}"
        return f"laporan-keuangan-{self.period_year}-{self.period_month:02d}"

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def has_files(self) -> bool:
        return bool(self.pdf_file and self.xlsx_file)
