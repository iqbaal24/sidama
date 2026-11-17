from django.urls import path

from apps.programs import views

app_name = "programs"

urlpatterns = [
    path("app/program/", views.ProgramListView.as_view(), name="program_list"),
    path("app/program/baru/", views.ProgramCreateView.as_view(), name="program_create"),
    path("app/program/<int:pk>/ubah/", views.ProgramUpdateView.as_view(), name="program_update"),
    path("app/program/<int:pk>/publikasi/", views.ProgramPublishView.as_view(),
         name="program_publish"),
    path("app/donasi/", views.DonationListView.as_view(), name="donation_list"),
    path("app/donasi/<int:pk>/konfirmasi/", views.DonationConfirmView.as_view(),
         name="donation_confirm"),
    path("app/donasi/<int:pk>/tolak/", views.DonationRejectView.as_view(),
         name="donation_reject"),
]
