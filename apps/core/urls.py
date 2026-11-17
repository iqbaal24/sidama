from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("app/", views.DashboardView.as_view(), name="dashboard"),
    path("app/pengaturan/", views.SettingsView.as_view(), name="settings"),
]
