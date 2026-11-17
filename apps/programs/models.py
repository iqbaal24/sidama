"""Donation programs and their donations."""
from __future__ import annotations

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.utils import percent
from apps.core.validators import validate_upload_size, validate_upload_type
from apps.finance.models import Fund


def program_image_upload_to(instance, filename: str) -> str:
    return f"programs/{instance.slug or 'program'}-{filename}"


class Program(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draf"
        ACTIVE = "active", "Berjalan"
        COMPLETED = "completed", "Selesai"
        CANCELLED = "cancelled", "Dibatalkan"

    title = models.CharField("judul", max_length=160)
    slug = models.SlugField("slug", max_length=180, unique=True, blank=True)
    description = models.TextField("deskripsi")
    target_amount = models.DecimalField("target dana", max_digits=14, decimal_places=2,
                                        validators=[MinValueValidator(Decimal("1"))])
    start_date = models.DateField("mulai", default=timezone.localdate)
    end_date = models.DateField("selesai", null=True, blank=True)
    image = models.ImageField("gambar", upload_to=program_image_upload_to, blank=True,
                              validators=[validate_upload_size, validate_upload_type])
    status = models.CharField("status", max_length=20, choices=Status.choices,
                              default=Status.DRAFT)
    is_published = models.BooleanField("tampil di publik", default=False)
    fund = models.ForeignKey(Fund, verbose_name="dana terikat", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="programs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="programs")

    class Meta:
        verbose_name = "program donasi"
        verbose_name_plural = "program donasi"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:160] or "program"
            slug = base
            counter = 2
            while Program.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("public:program_detail", args=[self.slug])

    @property
    def collected(self) -> Decimal:
        total = self.donations.filter(
            status=Donation.Status.CONFIRMED
        ).aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0")

    @property
    def progress(self) -> float:
        return percent(self.collected, self.target_amount)

    @property
    def donor_count(self) -> int:
        return self.donations.filter(status=Donation.Status.CONFIRMED).count()

    @property
    def remaining(self) -> Decimal:
        remaining = self.target_amount - self.collected
        return remaining if remaining > 0 else Decimal("0")

    @property
    def is_open(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.end_date and self.end_date < timezone.localdate():
            return False
        return True


class Donation(TimeStampedModel):
    class Method(models.TextChoices):
        QRIS = "qris", "QRIS"
        TRANSFER = "transfer", "Transfer Bank"
        CASH = "cash", "Tunai"

    class Status(models.TextChoices):
        PENDING = "pending", "Menunggu Konfirmasi"
        CONFIRMED = "confirmed", "Terkonfirmasi"
        REJECTED = "rejected", "Ditolak"

    program = models.ForeignKey(Program, verbose_name="program", on_delete=models.CASCADE,
                                related_name="donations")
    donor_name = models.CharField("nama donatur", max_length=120)
    donor_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="akun donatur",
                                   null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="donations")
    contact = models.CharField("kontak", max_length=120, blank=True,
                               help_text="Nomor WhatsApp atau email (tidak ditampilkan publik).")
    is_anonymous = models.BooleanField("anonim", default=False)
    amount = models.DecimalField("nominal", max_digits=14, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("10000"))])
    method = models.CharField("metode", max_length=20, choices=Method.choices,
                              default=Method.QRIS)
    message = models.CharField("pesan / doa", max_length=255, blank=True)
    status = models.CharField("status", max_length=20, choices=Status.choices,
                              default=Status.PENDING)
    code = models.CharField("kode donasi", max_length=20, unique=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name="confirmed_donations")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    transaction = models.OneToOneField("finance.Transaction", null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name="donation")

    class Meta:
        verbose_name = "donasi"
        verbose_name_plural = "donasi"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["code"])]

    def __str__(self) -> str:
        return f"{self.code} — {self.display_name} ({self.amount})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_code() -> str:
        while True:
            code = f"DN-{secrets.token_hex(3).upper()}"
            if not Donation.objects.filter(code=code).exists():
                return code

    @property
    def display_name(self) -> str:
        return "Hamba Allah" if self.is_anonymous else self.donor_name

    @property
    def status_tone(self) -> str:
        return {"pending": "warning", "confirmed": "success",
                "rejected": "danger"}.get(self.status, "muted")
