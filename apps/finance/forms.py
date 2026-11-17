"""Finance forms."""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import StyledModelForm
from apps.core.models import Setting
from apps.finance.models import Category, Fund, Transaction


class TransactionForm(StyledModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "transaction_type", "fund", "category", "amount",
                  "description", "pic", "program", "receipt"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "1000", "min": "1",
                                               "inputmode": "numeric"}),
            "description": forms.TextInput(attrs={"placeholder": "Misal: honor marbot bulan November"}),
            "pic": forms.TextInput(attrs={"placeholder": "Nama penanggung jawab"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["fund"].queryset = Fund.objects.filter(is_active=True)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["program"].required = False
        self.fields["program"].empty_label = "— Tidak terkait program —"
        self.fields["receipt"].help_text = "JPG, PNG, atau PDF. Maksimal 5 MB."
        if self.instance.pk and self.instance.locked:
            for field in self.fields.values():
                field.disabled = True

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.locked:
            raise ValidationError(
                "Transaksi ini berada pada periode yang sudah ditutup. "
                "Gunakan transaksi pembalik untuk mengoreksi."
            )
        category = cleaned.get("category")
        transaction_type = cleaned.get("transaction_type")
        if category and transaction_type and category.category_type != transaction_type:
            self.add_error("category", "Kategori tidak sesuai dengan jenis transaksi.")
        program = cleaned.get("program")
        if program and cleaned.get("transaction_type") == Transaction.Type.INCOME:
            self.add_error("program", "Pemasukan program dicatat otomatis dari donasi.")
        return cleaned

    def save(self, commit: bool = True):
        transaction = super().save(commit=False)
        if not transaction.pk:
            transaction.created_by = self.user
            threshold = Setting.get_decimal("approval_threshold", "1000000")
            if transaction.is_expense and transaction.amount > threshold:
                transaction.status = Transaction.Status.PENDING
            else:
                transaction.status = Transaction.Status.APPROVED
        if commit:
            transaction.save()
            self.save_m2m()
        return transaction


class FundForm(StyledModelForm):
    class Meta:
        model = Fund
        fields = ["name", "fund_type", "description", "is_active"]


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "category_type", "description", "is_active"]


class ApprovalForm(forms.Form):
    note = forms.CharField(
        label="Catatan", required=False, max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "class": "textarea",
                                     "placeholder": "Alasan atau catatan persetujuan"}),
    )


class PeriodCloseForm(forms.Form):
    note = forms.CharField(
        label="Catatan penutupan", required=False, max_length=255,
        widget=forms.TextInput(attrs={"class": "input"}),
    )

    def clean(self):
        cleaned = super().clean()
        return cleaned
