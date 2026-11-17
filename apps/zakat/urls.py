from django.urls import path

from apps.zakat import views

app_name = "zakat"

urlpatterns = [
    path("app/zakat/", views.ZakatOverviewView.as_view(), name="overview"),
    path("app/zakat/muzakki/", views.MuzakkiListView.as_view(), name="muzakki_list"),
    path("app/zakat/muzakki/baru/", views.MuzakkiCreateView.as_view(), name="muzakki_create"),
    path("app/zakat/muzakki/<int:pk>/ubah/", views.MuzakkiUpdateView.as_view(),
         name="muzakki_update"),
    path("app/zakat/mustahik/", views.MustahikListView.as_view(), name="mustahik_list"),
    path("app/zakat/mustahik/baru/", views.MustahikCreateView.as_view(), name="mustahik_create"),
    path("app/zakat/mustahik/<int:pk>/ubah/", views.MustahikUpdateView.as_view(),
         name="mustahik_update"),
    path("app/zakat/mustahik/<int:pk>/verifikasi/", views.MustahikVerifyView.as_view(),
         name="mustahik_verify"),
    path("app/zakat/penerimaan/", views.ReceiptListView.as_view(), name="receipt_list"),
    path("app/zakat/penerimaan/baru/", views.ReceiptCreateView.as_view(),
         name="receipt_create"),
    path("app/zakat/penyaluran/", views.DistributionListView.as_view(),
         name="distribution_list"),
    path("app/zakat/penyaluran/baru/", views.DistributionCreateView.as_view(),
         name="distribution_create"),
]
