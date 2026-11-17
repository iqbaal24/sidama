"""API routes.

In public-only mode only the anonymous endpoints are exposed: transparency
summary, program listing/donation and the zakat calculator.
"""
from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.api import views

public_router = DefaultRouter()
public_router.register("programs", views.ProgramViewSet, basename="program")

internal_router = DefaultRouter()
internal_router.register("transactions", views.TransactionViewSet, basename="transaction")
internal_router.register("funds", views.FundViewSet, basename="fund")
internal_router.register("categories", views.CategoryViewSet, basename="category")
internal_router.register("programs", views.ProgramViewSet, basename="program")
internal_router.register("donations", views.DonationViewSet, basename="donation")
internal_router.register("zakat/receipts", views.ZakatReceiptViewSet, basename="zakat-receipt")
internal_router.register("zakat/muzakki", views.MuzakkiViewSet, basename="zakat-muzakki")
internal_router.register("zakat/mustahik", views.MustahikViewSet, basename="zakat-mustahik")
internal_router.register("zakat/distributions", views.ZakatDistributionViewSet,
                         basename="zakat-distribution")
internal_router.register("qurban/registrations", views.QurbanRegistrationViewSet,
                         basename="qurban-registration")
internal_router.register("qurban/distributions", views.MeatDistributionViewSet,
                         basename="qurban-distribution")
internal_router.register("assets", views.AssetViewSet, basename="asset")
internal_router.register("reports", views.ReportViewSet, basename="report")
internal_router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")

public_urlpatterns = [
    path("zakat/calculate/", views.ZakatCalculateView.as_view(),
         name="api-zakat-calculate"),
    path("public/summary/", views.PublicSummaryView.as_view(), name="api-public-summary"),
    path("", include(public_router.urls)),
]

internal_urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="api-login"),
    path("auth/me/", views.MeView.as_view(), name="api-me"),
    path("zakat/calculate/", views.ZakatCalculateView.as_view(),
         name="api-zakat-calculate"),
    path("public/summary/", views.PublicSummaryView.as_view(), name="api-public-summary"),
    path("forecast/cashflow/", views.ForecastView.as_view(), name="api-forecast"),
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"),
         name="api-docs"),
    path("", include(internal_router.urls)),
]

urlpatterns = public_urlpatterns if settings.PUBLIC_ONLY else internal_urlpatterns
