from django.urls import path

from apps.forecasting import views

app_name = "forecasting"

urlpatterns = [
    path("app/prediksi/", views.ForecastView.as_view(), name="forecast"),
]
