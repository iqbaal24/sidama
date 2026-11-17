"""Zakat forms."""
from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.core.forms import StyledModelForm
from apps.core.validators import validate_upload_size, validate_upload_type
from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt


class MuzakkiForm(StyledModelForm):
    class Meta:
        model = Muzakki
        fields = ["name", "phone", "address", "note"]


class MustahikForm(StyledModelForm):
    class Meta:
        model = Mustahik
        fields = ["name", "asnaf", "address", "phone", "is_verified", "note"]


class ZakatReceiptForm(StyledModelForm):
    new_muzakki_name = forms.CharField(
        label="Nama pembayar baru", required=False,
        help_text="Isi jika pembayar belum terdaftar sebagai muzakki.",
    )
    proof = forms.FileField(
        label="Bukti penerimaan", required=False,
        validators=[validate_upload_size, validate_upload_type],
        help_text="JPG, PNG, atau PDF. Maksimal 5 MB.",
    )

    class Meta:
        model = ZakatReceipt
        fields = ["date", "muzakki", "zakat_type", "amount", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "1000", "min": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["muzakki"].required = False
        self.fields["muzakki"].queryset = Muzakki.objects.all()
        self.fields["muzakki"].empty_label = "— Pilih muzakki —"
        if not self.instance.pk:
            self.initial.setdefault("date", timezone.localdate())

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("muzakki") and not (cleaned.get("new_muzakki_name") or "").strip():
            self.add_error("new_muzakki_name", "Pilih muzakki atau isi nama pembayar baru.")
        return cleaned

    def save(self, commit=True):
        receipt = super().save(commit=False)
        new_name = (self.cleaned_data.get("new_muzakki_name") or "").strip()
        if new_name and not receipt.muzakki_id:
            receipt.muzakki, _ = Muzakki.objects.get_or_create(name=new_name)
        if receipt.muzakki_id:
            receipt.muzakki_name = receipt.muzakki.name
        if commit:
            receipt.save()
        return receipt


class ZakatDistributionForm(StyledModelForm):
    class Meta:
        model = ZakatDistribution
        fields = ["date", "mustahik", "amount", "item_description", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "1000", "min": "1"}),
            "item_description": forms.TextInput(
                attrs={"placeholder": "Misal: paket sembako 10 kg"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mustahik"].queryset = Mustahik.objects.filter(is_verified=True)
        if not self.instance.pk:
            self.initial.setdefault("date", timezone.localdate())
        if not Mustahik.objects.filter(is_verified=True).exists():
            self.fields["mustahik"].help_text = (
                "Belum ada mustahik terverifikasi. Tambahkan dan verifikasi mustahik dahulu."
            )
