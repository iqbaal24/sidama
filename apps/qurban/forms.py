"""Qurban forms."""
from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.core.forms import StyledModelForm
from apps.qurban.models import MeatDistribution, QurbanRegistration


class QurbanRegistrationForm(StyledModelForm):
    class Meta:
        model = QurbanRegistration
        fields = ["year", "name", "phone", "animal_type", "share_count", "amount",
                  "payment_status", "note"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "50000", "min": "0"}),
            "year": forms.NumberInput(attrs={"min": "2020", "max": "2100"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault("year", timezone.localdate().year)


class MeatDistributionForm(StyledModelForm):
    class Meta:
        model = MeatDistribution
        fields = ["registration", "recipient_name", "weight_kg", "is_received", "note"]
        widgets = {
            "weight_kg": forms.NumberInput(attrs={"step": "0.1", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["registration"].required = False
        self.fields["registration"].empty_label = "— Tidak terkait pendaftaran —"
        self.fields["registration"].queryset = QurbanRegistration.objects.order_by("-year", "name")
