from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    path("app/audit/", views.AuditLogListView.as_view(), name="list"),
    path("app/audit/<int:pk>/", views.AuditLogDetailView.as_view(), name="detail"),
]
