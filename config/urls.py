"""Root URL configuration.

When ``SIDAMA_PUBLIC_ONLY=1`` only the jamaah-facing transparency site is mounted:
the internal dashboard, Django admin and authenticated API routes are not
registered at all, so they return 404 instead of a login wall.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import healthcheck

public_patterns = [
    path("healthz/", healthcheck, name="healthcheck"),
    path("api/", include("apps.api.urls")),
    path("", include("apps.public.urls")),
]

internal_patterns = [
    path("healthz/", healthcheck, name="healthcheck"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.finance.urls")),
    path("", include("apps.programs.urls")),
    path("", include("apps.zakat.urls")),
    path("", include("apps.qurban.urls")),
    path("", include("apps.assets.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.forecasting.urls")),
    path("", include("apps.public.urls")),
]

urlpatterns = public_patterns if settings.PUBLIC_ONLY else internal_patterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
