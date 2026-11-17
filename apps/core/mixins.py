"""Access-control mixins shared by every internal view."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict a view to a set of roles (superusers always pass)."""

    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.is_superuser or not self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("Peran Anda tidak memiliki akses ke halaman ini.")
        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """Function-view decorator counterpart of :class:`RoleRequiredMixin`."""

    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("Peran Anda tidak memiliki akses ke halaman ini.")

        _wrapped.__name__ = view_func.__name__
        _wrapped.__doc__ = view_func.__doc__
        return _wrapped

    return decorator
