"""DRF permissions based on SIDAMA roles."""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class RolePermission(BasePermission):
    roles: tuple[str, ...] = ()
    message = "Peran Anda tidak memiliki akses ke endpoint ini."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or user.role in self.roles


class IsFinance(RolePermission):
    roles = (Role.ADMIN, Role.CHAIR, Role.TREASURER)


class IsApprover(RolePermission):
    roles = (Role.ADMIN, Role.CHAIR)


class IsDataManager(RolePermission):
    roles = (Role.ADMIN, Role.CHAIR, Role.TREASURER, Role.STAFF)


class IsAdmin(RolePermission):
    roles = (Role.ADMIN,)
