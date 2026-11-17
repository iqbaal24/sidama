"""Values available to every template."""
from __future__ import annotations

from apps.core.models import Setting


def sidama_context(request):
    from django.conf import settings

    context = {
        "mosque_name": Setting.get("mosque_name"),
        "mosque_city": Setting.get("mosque_city"),
        "mosque_address": Setting.get("mosque_address"),
        "mosque_phone": Setting.get("mosque_phone"),
        "public_only": getattr(settings, "PUBLIC_ONLY", False),
    }
    if context["public_only"]:
        return context
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from apps.finance.services import pending_count
        from apps.notifications.models import Notification

        context["nav_pending_count"] = pending_count()
        context["nav_unread_count"] = Notification.objects.filter(
            user=user, is_read=False
        ).count()
    return context
