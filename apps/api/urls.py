"""API routes."""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.api import views

router = DefaultRouter()
router.register("transactions", views.TransactionViewSet, basename="transaction")
router.register("funds", views.FundViewSet, basename="fund")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("programs", views.ProgramViewSet, basename="program")
router.register("donations", views.DonationViewSet, basename="donation")
router.register("zakat/receipts", views.ZakatReceiptViewSet, basename="zakat-receipt")
router.register("zakat/muzakki", views.MuzakkiViewSet, basename="zakat-muzakki")
router.register("zakat/mustahik", views.MustahikViewSet, basename="zakat-mustahik")
router.register("zakat/distributions", views.ZakatDistributionViewSet,
                basename="zakat-distribution")
router.register("qurban/registrations", views.QurbanRegistrationViewSet,
                basename="qurban-registration")
router.register("qurban/distributions", views.MeatDistributionViewSet,
                basename="qurban-distribution")
router.register("assets", views.AssetViewSet, basename="asset")
router.register("reports", views.ReportViewSet, basename="report")
router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="api-login"),
    path("auth/me/", views.MeView.as_view(), name="api-me"),
    path("zakat/calculate/", views.ZakatCalculateView.as_view(),
         name="api-zakat-calculate"),
    path("public/summary/", views.PublicSummaryView.as_view(), name="api-public-summary"),
    path("forecast/cashflow/", views.ForecastView.as_view(), name="api-forecast"),
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"),
         name="api-docs"),
    path("", include(router.urls)),
]
