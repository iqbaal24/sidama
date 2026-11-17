"""Authentication, profile and user management views."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import LoginForm, ProfileForm, UserCreateForm, UserUpdateForm
from apps.accounts.models import Role, User
from apps.core.mixins import RoleRequiredMixin
from apps.core.views import ColumnListView, FormPageMixin

MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    next_url = request.GET.get("next") or request.POST.get("next") or ""
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip().lower()
        cache_key = f"login-attempts:{_client_ip(request)}:{identifier}"
        attempts = cache.get(cache_key, 0)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            form.add_error(
                None,
                "Terlalu banyak percobaan masuk. Coba lagi dalam 5 menit.",
            )
        elif form.is_valid():
            cache.delete(cache_key)
            login(request, form.get_user())
            messages.success(
                request,
                "Berhasil masuk. Selamat bekerja.",
            )
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("core:dashboard")
        else:
            cache.set(cache_key, attempts + 1, LOGIN_WINDOW_SECONDS)
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "Anda telah keluar.")
    return redirect("public:home")


@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil diperbarui.")
        return redirect("accounts:profile")
    return render(request, "app/form.html", {
        "form": form,
        "title": "Profil saya",
        "subtitle": "Perbarui data diri dan kontak Anda.",
        "submit_label": "Simpan profil",
        "cancel_url": reverse("core:dashboard"),
        "nav": "",
    })


class UserListView(ColumnListView):
    model = User
    allowed_roles = (Role.ADMIN,)
    nav = "users"
    title = "Pengguna"
    subtitle = "Kelola akun dan peran pengurus."
    headers = ["Nama", "Email", "Peran", "Status", "Terakhir masuk"]
    search_fields = ["first_name", "last_name", "username", "email"]
    create_url = reverse_lazy("accounts:user_create")
    create_label = "Tambah pengguna"
    row_url_name = "accounts:user_update"
    empty_text = "Belum ada pengguna."

    def get_queryset(self):
        return User.objects.all().order_by("role", "first_name")

    def get_cells(self, obj):
        return [
            {"text": obj.display_name, "strong": True, "sub": f"@{obj.username}"},
            {"text": obj.email, "muted": True},
            {"text": obj.role_label,
             "badge": "success" if obj.role in (Role.ADMIN, Role.CHAIR) else "muted"},
            {"text": "Aktif" if obj.is_active else "Nonaktif",
             "badge": "success" if obj.is_active else "danger"},
            {"text": obj.last_login.strftime("%d/%m/%Y %H:%M") if obj.last_login else "—",
             "muted": True},
        ]


class UserCreateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = (Role.ADMIN,)
    nav = "users"
    title = "Tambah pengguna"
    subtitle = "Akun baru dapat langsung masuk dengan kata sandi yang Anda tentukan."
    cancel_url = reverse_lazy("accounts:user_list")

    def get(self, request):
        return render(request, "app/form.html", self.context(UserCreateForm()))

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Pengguna {user.display_name} ditambahkan.")
            return redirect("accounts:user_list")
        return render(request, "app/form.html", self.context(form))


class UserUpdateView(RoleRequiredMixin, FormPageMixin, View):
    allowed_roles = (Role.ADMIN,)
    nav = "users"
    title = "Ubah pengguna"
    cancel_url = reverse_lazy("accounts:user_list")

    def get(self, request, pk):
        user = User.objects.get(pk=pk)
        return render(request, "app/form.html",
                      self.context(UserUpdateForm(instance=user)))

    def post(self, request, pk):
        user = User.objects.get(pk=pk)
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Data pengguna diperbarui.")
            return redirect("accounts:user_list")
        return render(request, "app/form.html", self.context(form))
