from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("app/notifikasi/", views.NotificationListView.as_view(), name="list"),
    path("app/notifikasi/<int:pk>/baca/", views.NotificationReadView.as_view(), name="read"),
    path("app/notifikasi/baca-semua/", views.NotificationReadAllView.as_view(),
         name="read_all"),
]
