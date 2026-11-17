from django.urls import path

from apps.public import views
from apps.reports.views import public_download

app_name = "public"

urlpatterns = [
    path("", views.PublicHomeView.as_view(), name="home"),
    path("program/", views.ProgramListView.as_view(), name="program_list"),
    path("program/<slug:slug>/", views.ProgramDetailView.as_view(), name="program_detail"),
    path("program/<slug:slug>/donasi/", views.donate, name="donate"),
    path("donasi/<str:code>/", views.DonationStatusView.as_view(), name="donation_status"),
    path("zakat/", views.ZakatCalculatorView.as_view(), name="zakat"),
    path("zakat/kalkulator/", views.ZakatCalculatorView.as_view(), name="zakat_calculator"),
    path("laporan/", views.PublicReportListView.as_view(), name="reports"),
    path("laporan/<int:pk>/unduh/<str:fmt>/", public_download, name="report_download"),
    path("tentang/", views.AboutView.as_view(), name="about"),
]
