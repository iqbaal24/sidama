from django.urls import path

from apps.assets import views

app_name = "assets"

urlpatterns = [
    path("app/aset/", views.AssetListView.as_view(), name="asset_list"),
    path("app/aset/baru/", views.AssetCreateView.as_view(), name="asset_create"),
    path("app/aset/<int:pk>/", views.AssetDetailView.as_view(), name="asset_detail"),
    path("app/aset/<int:pk>/ubah/", views.AssetUpdateView.as_view(), name="asset_update"),
    path("app/aset/<int:pk>/riwayat/", views.AssetLogCreateView.as_view(),
         name="asset_log_create"),
]
