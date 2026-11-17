"""Asset forms."""
from __future__ import annotations

from django import forms

from apps.assets.models import Asset, AssetLog
from apps.core.forms import StyledModelForm


class AssetForm(StyledModelForm):
    class Meta:
        model = Asset
        fields = ["name", "category", "quantity", "condition", "location",
                  "acquired_date", "value", "note"]
        widgets = {
            "acquired_date": forms.DateInput(attrs={"type": "date"}),
            "value": forms.NumberInput(attrs={"step": "1000", "min": "0"}),
            "category": forms.TextInput(attrs={"placeholder": "Elektronik, perlengkapan ibadah, …"}),
        }


class AssetLogForm(StyledModelForm):
    class Meta:
        model = AssetLog
        fields = ["date", "log_type", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }
