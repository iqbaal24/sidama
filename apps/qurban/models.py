"""Qurban registration and meat distribution."""
from __future__ import annotations

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


def current_year() -> int:
    return timezone.localdate().year


class QurbanRegistration(TimeStampedModel):
    class Animal(models.TextChoices):
        COW = "cow", "Sapi"
        GOAT = "goat", "Kambing"
        SHEEP = "sheep", "Domba"

    class Payment(models.TextChoices):
        UNPAID = "unpaid", "Belum Bayar"
        DP = "dp", "Uang Muka"
        PAID = "paid", "Lunas"

    year = models.PositiveIntegerField("tahun", default=current_year)
    name = models.CharField("nama shohibul", max_length=120)
    phone = models.CharField("telepon", max_length=30, blank=True)
    animal_type = models.CharField("jenis hewan", max_length=20, choices=Animal.choices)
    share_count = models.PositiveSmallIntegerField("jumlah jiwa", default=1)
    amount = models.DecimalField("nominal", max_digits=14, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0"))])
    payment_status = models.CharField("status bayar", max_length=20,
                                      choices=Payment.choices, default=Payment.UNPAID)
    note = models.CharField("catatan", max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="qurban_registrations")

    class Meta:
        verbose_name = "pendaftaran kurban"
        verbose_name_plural = "pendaftaran kurban"
        ordering = ["-year", "name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.get_animal_type_display()} {self.year}"

    def save(self, *args, **kwargs):
        if not self.year:
            self.year = timezone.localdate().year
        super().save(*args, **kwargs)


class MeatDistribution(TimeStampedModel):
    registration = models.ForeignKey(QurbanRegistration, verbose_name="pendaftaran",
                                     null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="meat_distributions")
    recipient_name = models.CharField("nama penerima", max_length=120)
    weight_kg = models.DecimalField("berat (kg)", max_digits=6, decimal_places=2,
                                    default=Decimal("0"))
    coupon_code = models.CharField("kode kupon", max_length=20, unique=True, blank=True)
    is_received = models.BooleanField("sudah menerima", default=False)
    received_at = models.DateTimeField("waktu diterima", null=True, blank=True)
    note = models.CharField("catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "distribusi daging"
        verbose_name_plural = "distribusi daging"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.recipient_name} — {self.weight_kg} kg"

    def save(self, *args, **kwargs):
        if not self.coupon_code:
            while True:
                code = f"QR-{secrets.token_hex(2).upper()}"
                if not MeatDistribution.objects.filter(coupon_code=code).exists():
                    self.coupon_code = code
                    break
        if self.is_received and not self.received_at:
            self.received_at = timezone.now()
        super().save(*args, **kwargs)
