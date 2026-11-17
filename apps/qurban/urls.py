from django.urls import path

from apps.qurban import views

app_name = "qurban"

urlpatterns = [
    path("app/kurban/", views.RegistrationListView.as_view(), name="registration_list"),
    path("app/kurban/baru/", views.RegistrationCreateView.as_view(),
         name="registration_create"),
    path("app/kurban/<int:pk>/ubah/", views.RegistrationUpdateView.as_view(),
         name="registration_update"),
    path("app/kurban/distribusi/", views.DistributionListView.as_view(),
         name="distribution_list"),
    path("app/kurban/distribusi/baru/", views.DistributionCreateView.as_view(),
         name="distribution_create"),
    path("app/kurban/distribusi/<int:pk>/ubah/", views.DistributionUpdateView.as_view(),
         name="distribution_update"),
    path("app/kurban/distribusi/<int:pk>/terima/", views.DistributionReceiveView.as_view(),
         name="distribution_receive"),
    path("app/kurban/laporan/", views.QurbanReportView.as_view(), name="report"),
]
