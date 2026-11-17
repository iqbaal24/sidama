"""Program forms."""
from __future__ import annotations

from django import forms

from apps.core.forms import StyledModelForm
from apps.programs.models import Donation, Program


class ProgramForm(StyledModelForm):
    class Meta:
        model = Program
        fields = ["title", "description", "target_amount", "start_date", "end_date",
                  "image", "status", "is_published"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5,
                                                 "placeholder": "Jelaskan tujuan dan rencana penggunaan dana."}),
            "target_amount": forms.NumberInput(attrs={"step": "10000", "min": "1"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return cleaned


class PublicDonationForm(forms.Form):
    donor_name = forms.CharField(
        label="Nama", max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "Nama Anda atau Hamba Allah"}),
    )
    contact = forms.CharField(
        label="WhatsApp / email", max_length=120, required=False,
        widget=forms.TextInput(attrs={"placeholder": "0812xxxxxxx (opsional)"}),
    )
    amount = forms.DecimalField(
        label="Nominal", min_value=10000, max_digits=14, decimal_places=0,
        widget=forms.NumberInput(attrs={"placeholder": "100000", "step": "10000"}),
    )
    method = forms.ChoiceField(label="Metode", choices=Donation.Method.choices,
                               initial=Donation.Method.QRIS)
    message = forms.CharField(
        label="Pesan / doa", max_length=255, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Semoga menjadi amal jariyah"}),
    )
    is_anonymous = forms.BooleanField(label="Sembunyikan nama saya (anonim)",
                                      required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "checkbox"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "select"
            else:
                field.widget.attrs["class"] = "input"
