"""Authentication and user-management forms."""
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.accounts.models import Role, User
from apps.core.forms import StyledForm, StyledModelForm


class LoginForm(StyledForm, AuthenticationForm):
    username = forms.CharField(
        label="Email atau username",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username",
                                      "placeholder": "nama@email.com"}),
    )
    password = forms.CharField(
        label="Kata sandi",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Email/username atau kata sandi salah.",
    }


class UserCreateForm(StyledModelForm):
    password1 = forms.CharField(label="Kata sandi", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Ulangi kata sandi", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "role",
                  "is_active"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Kata sandi tidak sama.")
        password = cleaned.get("password1")
        if password and len(password) < 8:
            self.add_error("password1", "Kata sandi minimal 8 karakter.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserUpdateForm(StyledModelForm):
    new_password = forms.CharField(
        label="Kata sandi baru", required=False,
        help_text="Biarkan kosong jika tidak ingin mengganti kata sandi.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "role",
                  "is_active"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password and len(password) < 8:
            raise forms.ValidationError("Kata sandi minimal 8 karakter.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("new_password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class ProfileForm(StyledModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email


class DonorSignupForm(UserCreationForm):
    """Optional donor account, used by the public donation flow."""

    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Nama", max_length=80, required=True)

    class Meta:
        model = User
        fields = ["first_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "checkbox" if isinstance(field.widget, forms.CheckboxInput) else "input"
            field.widget.attrs["class"] = css

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.role = Role.DONOR
        if commit:
            user.save()
        return user
