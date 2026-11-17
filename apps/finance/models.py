"""Finance models: funds, categories, periods and transactions."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.utils import month_label
from apps.core.validators import validate_upload_size, validate_upload_type


def receipt_upload_to(instance, filename: str) -> str:
    today = timezone.localdate()
    return f"receipts/{today:%Y/%m}/{instance.pk or 'new'}-{filename}"


class Fund(TimeStampedModel):
    class Type(models.TextChoices):
        GENERAL = "general", "Dana Umum"
        ZAKAT = "zakat", "Dana Zakat"
        RESTRICTED = "restricted", "Dana Terikat"

    name = models.CharField("nama dana", max_length=120)
    code = models.SlugField("kode", max_length=60, unique=True, blank=True)
    fund_type = models.CharField("tipe", max_length=20, choices=Type.choices,
                                 default=Type.GENERAL)
    description = models.TextField("keterangan", blank=True)
    is_active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "dana"
        verbose_name_plural = "dana"
        ordering = ["fund_type", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            base = slugify(self.name) or "dana"
            code = base
            counter = 2
            while Fund.objects.filter(code=code).exclude(pk=self.pk).exists():
                code = f"{base}-{counter}"
                counter += 1
            self.code = code
        super().save(*args, **kwargs)

    @property
    def balance(self) -> Decimal:
        from apps.finance.services import fund_balance

        return fund_balance(self)


class Category(TimeStampedModel):
    class Type(models.TextChoices):
        INCOME = "income", "Pemasukan"
        EXPENSE = "expense", "Pengeluaran"

    name = models.CharField("nama kategori", max_length=120)
    category_type = models.CharField("tipe", max_length=20, choices=Type.choices)
    description = models.CharField("keterangan", max_length=255, blank=True)
    is_active = models.BooleanField("aktif", default=True)

    class Meta:
        verbose_name = "kategori"
        verbose_name_plural = "kategori"
        ordering = ["category_type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "category_type"],
                                    name="unique_category_per_type"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_type_display()})"


class Period(models.Model):
    """A closed period locks every transaction inside it."""

    year = models.PositiveIntegerField("tahun")
    month = models.PositiveSmallIntegerField("bulan")
    is_closed = models.BooleanField("ditutup", default=False)
    closed_at = models.DateTimeField("ditutup pada", null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="ditutup oleh",
                                  null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="closed_periods")
    note = models.CharField("catatan", max_length=255, blank=True)

    class Meta:
        verbose_name = "periode"
        verbose_name_plural = "periode"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="unique_period"),
        ]

    def __str__(self) -> str:
        return f"{month_label(self.year, self.month)}"

    @property
    def label(self) -> str:
        return month_label(self.year, self.month)


class Transaction(TimeStampedModel):
    class Type(models.TextChoices):
        INCOME = "income", "Pemasukan"
        EXPENSE = "expense", "Pengeluaran"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draf"
        PENDING = "pending", "Menunggu Persetujuan"
        APPROVED = "approved", "Disetujui"
        REJECTED = "rejected", "Ditolak"

    date = models.DateField("tanggal", default=timezone.localdate)
    transaction_type = models.CharField("jenis", max_length=10, choices=Type.choices)
    fund = models.ForeignKey(Fund, verbose_name="dana", on_delete=models.PROTECT,
                             related_name="transactions")
    category = models.ForeignKey(Category, verbose_name="kategori", on_delete=models.PROTECT,
                                 related_name="transactions")
    amount = models.DecimalField("nominal", max_digits=14, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.01"))])
    description = models.CharField("deskripsi", max_length=255)
    pic = models.CharField("penanggung jawab", max_length=120, blank=True)
    receipt = models.FileField("bukti", upload_to=receipt_upload_to, blank=True,
                               validators=[validate_upload_size, validate_upload_type])
    status = models.CharField("status", max_length=20, choices=Status.choices,
                              default=Status.APPROVED)
    locked = models.BooleanField("terkunci", default=False)
    program = models.ForeignKey("programs.Program", verbose_name="program", null=True,
                                blank=True, on_delete=models.SET_NULL,
                                related_name="transactions")
    reversal_of = models.ForeignKey("self", verbose_name="pembalik dari", null=True,
                                    blank=True, on_delete=models.SET_NULL,
                                    related_name="reversals")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="dibuat oleh",
                                   null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="transactions")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="disetujui oleh",
                                    null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="approved_transactions")
    approved_at = models.DateTimeField("disetujui pada", null=True, blank=True)
    approval_note = models.CharField("catatan persetujuan", max_length=255, blank=True)

    class Meta:
        verbose_name = "transaksi"
        verbose_name_plural = "transaksi"
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["transaction_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.amount} — {self.description}"

    def save(self, *args, **kwargs):
        if self.date and not self.locked:
            if Period.objects.filter(year=self.date.year, month=self.date.month,
                                     is_closed=True).exists():
                self.locked = True
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("finance:transaction_detail", args=[self.pk])

    @property
    def is_income(self) -> bool:
        return self.transaction_type == self.Type.INCOME

    @property
    def is_expense(self) -> bool:
        return self.transaction_type == self.Type.EXPENSE

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.is_income else -self.amount

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def can_be_edited(self) -> bool:
        return not self.locked
