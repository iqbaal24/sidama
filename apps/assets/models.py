"""Mosque asset inventory and its history."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Asset(TimeStampedModel):
    class Condition(models.TextChoices):
        GOOD = "good", "Baik"
        MINOR = "minor", "Rusak Ringan"
        BROKEN = "broken", "Rusak Berat"

    name = models.CharField("nama aset", max_length=120)
    category = models.CharField("kategori", max_length=80,
                                help_text="Misal: elektronik, perlengkapan ibadah, bangunan.")
    quantity = models.PositiveIntegerField("jumlah", default=1)
    condition = models.CharField("kondisi", max_length=20, choices=Condition.choices,
                                 default=Condition.GOOD)
    location = models.CharField("lokasi", max_length=120, blank=True)
    acquired_date = models.DateField("tanggal perolehan", null=True, blank=True)
    value = models.DecimalField("nilai", max_digits=14, decimal_places=2, default=0,
                                validators=[MinValueValidator(Decimal("0"))])
    note = models.CharField("catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "aset"
        verbose_name_plural = "aset"
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.quantity})"

    @property
    def condition_tone(self) -> str:
        return {"good": "success", "minor": "warning", "broken": "danger"}.get(
            self.condition, "muted"
        )


class AssetLog(TimeStampedModel):
    class Type(models.TextChoices):
        MAINTENANCE = "maintenance", "Perawatan"
        CONDITION = "condition", "Perubahan Kondisi"
        LOAN = "loan", "Dipinjamkan"
        RETURN = "return", "Dikembalikan"

    asset = models.ForeignKey(Asset, verbose_name="aset", on_delete=models.CASCADE,
                              related_name="logs")
    log_type = models.CharField("jenis", max_length=20, choices=Type.choices,
                                default=Type.MAINTENANCE)
    note = models.TextField("catatan", blank=True)
    date = models.DateField("tanggal", default=timezone.localdate)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="asset_logs")

    class Meta:
        verbose_name = "riwayat aset"
        verbose_name_plural = "riwayat aset"
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        return f"{self.asset.name} — {self.get_log_type_display()}"
