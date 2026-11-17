"""Cash-flow forecast page."""
from __future__ import annotations

from django.views.generic import TemplateView

from apps.accounts.models import Role
from apps.core.mixins import RoleRequiredMixin
from apps.forecasting.services import cashflow_forecast, category_forecast


class ForecastView(RoleRequiredMixin, TemplateView):
    template_name = "app/forecast.html"
    allowed_roles = (Role.ADMIN, Role.CHAIR, Role.TREASURER)
    nav = "forecast"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "nav": self.nav,
            "title": "Prediksi Kas",
            "subtitle": "Proyeksi bulan depan dari rata-rata 6 bulan terakhir.",
            "forecast": cashflow_forecast(6),
            "categories": category_forecast(6),
        })
        return context
