"""Zakat: muzakki, receipts, mustahik and distributions."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.utils import month_label


class Muzakki(TimeStampedModel):
    name = models.CharField("nama", max_length=120)
    phone = models.CharField("telepon", max_length=30, blank=True)
    address = models.CharField("alamat", max_length=255, blank=True)
    note = models.CharField("catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "muzakki"
        verbose_name_plural = "muzakki"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ZakatReceipt(TimeStampedModel):
    class Type(models.TextChoices):
        MAL = "mal", "Zakat Mal"
        PENGHASILAN = "penghasilan", "Zakat Penghasilan"
        FITRAH = "fitrah", "Zakat Fitrah"

    number = models.CharField("nomor bukti", max_length=30, unique=True, blank=True)
    muzakki = models.ForeignKey(Muzakki, verbose_name="muzakki", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="receipts")
    muzakki_name = models.CharField("nama pembayar", max_length=120, blank=True)
    zakat_type = models.CharField("jenis zakat", max_length=20, choices=Type.choices)
    amount = models.DecimalField("nominal", max_digits=14, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("1"))])
    date = models.DateField("tanggal", default=timezone.localdate)
    note = models.CharField("catatan", max_length=255, blank=True)
    transaction = models.OneToOneField("finance.Transaction", null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name="zakat_receipt")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="zakat_receipts")

    class Meta:
        verbose_name = "penerimaan zakat"
        verbose_name_plural = "penerimaan zakat"
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        return f"{self.number} — {self.payer_name}"

    def save(self, *args, **kwargs):
        if not self.number:
            prefix = f"ZK-{self.date:%y%m}" if self.date else f"ZK-{timezone.localdate():%y%m}"
            sequence = ZakatReceipt.objects.filter(number__startswith=prefix).count() + 1
            number = f"{prefix}-{sequence:03d}"
            while ZakatReceipt.objects.filter(number=number).exists():
                sequence += 1
                number = f"{prefix}-{sequence:03d}"
            self.number = number
        super().save(*args, **kwargs)

    @property
    def payer_name(self) -> str:
        return self.muzakki_name or (self.muzakki.name if self.muzakki else "Hamba Allah")

    @property
    def period_label(self) -> str:
        return month_label(self.date.year, self.date.month)


class Mustahik(TimeStampedModel):
    class Asnaf(models.TextChoices):
        FAKIR = "fakir", "Fakir"
        MISKIN = "miskin", "Miskin"
        AMIL = "amil", "Amil"
        MUALLAF = "muallaf", "Muallaf"
        RIQAB = "riqab", "Riqab"
        GHARIM = "gharim", "Gharim"
        FISABILILLAH = "fisabilillah", "Fisabilillah"
        IBNU_SABIL = "ibnu_sabil", "Ibnu Sabil"

    name = models.CharField("nama", max_length=120)
    asnaf = models.CharField("asnaf", max_length=30, choices=Asnaf.choices,
                             default=Asnaf.FAKIR)
    address = models.CharField("alamat", max_length=255, blank=True)
    phone = models.CharField("telepon", max_length=30, blank=True)
    is_verified = models.BooleanField("terverifikasi", default=False)
    note = models.CharField("catatan verifikasi", max_length=255, blank=True)

    class Meta:
        verbose_name = "mustahik"
        verbose_name_plural = "mustahik"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def total_received(self) -> Decimal:
        total = self.distributions.aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0")


class ZakatDistribution(TimeStampedModel):
    mustahik = models.ForeignKey(Mustahik, verbose_name="mustahik",
                                 on_delete=models.PROTECT, related_name="distributions")
    amount = models.DecimalField("nominal", max_digits=14, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("1"))])
    item_description = models.CharField("bentuk penyaluran", max_length=255, blank=True,
                                        help_text="Kosongkan jika berupa uang tunai.")
    date = models.DateField("tanggal", default=timezone.localdate)
    note = models.CharField("catatan", max_length=255, blank=True)
    transaction = models.OneToOneField("finance.Transaction", null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name="zakat_distribution")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="zakat_distributions")

    class Meta:
        verbose_name = "penyaluran zakat"
        verbose_name_plural = "penyaluran zakat"
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        return f"{self.mustahik.name} — {self.amount}"
