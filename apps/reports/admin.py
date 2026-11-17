from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "generated_at", "published_at")
    list_filter = ("report_type", "status", "period_year")
    readonly_fields = ("generated_at", "published_at")
