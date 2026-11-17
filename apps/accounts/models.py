"""Users, roles and access helpers."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin Sistem"
    CHAIR = "chair", "Ketua DKM"
    TREASURER = "treasurer", "Bendahara"
    STAFF = "staff", "Sekretaris / Petugas"
    DONOR = "donor", "Donatur"


class User(AbstractUser):
    email = models.EmailField("email", unique=True)
    role = models.CharField("peran", max_length=20, choices=Role.choices,
                            default=Role.DONOR)
    phone = models.CharField("nomor telepon", max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "pengguna"
        verbose_name_plural = "pengguna"
        ordering = ["first_name", "username"]

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        full_name = self.get_full_name().strip()
        return full_name or self.username

    @property
    def role_label(self) -> str:
        return self.get_role_display()

    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def can_manage_finance(self) -> bool:
        return self.is_superuser or self.role in (Role.ADMIN, Role.CHAIR, Role.TREASURER)

    @property
    def can_approve(self) -> bool:
        return self.is_superuser or self.role in (Role.ADMIN, Role.CHAIR)

    @property
    def can_manage_master_data(self) -> bool:
        return self.is_superuser or self.role in (
            Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF
        )
