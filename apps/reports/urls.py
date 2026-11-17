from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("app/laporan/", views.ReportListView.as_view(), name="list"),
    path("app/laporan/buat/", views.ReportGenerateView.as_view(), name="generate"),
    path("app/laporan/<int:pk>/terbitkan/", views.ReportPublishView.as_view(),
         name="publish"),
    path("app/laporan/<int:pk>/tarik/", views.ReportUnpublishView.as_view(),
         name="unpublish"),
    path("app/laporan/<int:pk>/unduh/<str:fmt>/", views.ReportDownloadView.as_view(),
         name="download"),
]
