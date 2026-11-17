from django.contrib import admin

from apps.qurban.models import MeatDistribution, QurbanRegistration


@admin.register(QurbanRegistration)
class QurbanRegistrationAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "animal_type", "share_count", "amount",
                    "payment_status")
    list_filter = ("year", "animal_type", "payment_status")
    search_fields = ("name", "phone")


@admin.register(MeatDistribution)
class MeatDistributionAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "weight_kg", "coupon_code", "is_received")
    list_filter = ("is_received",)
    search_fields = ("recipient_name", "coupon_code")
