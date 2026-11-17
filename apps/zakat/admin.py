from django.contrib import admin

from apps.zakat.models import Mustahik, Muzakki, ZakatDistribution, ZakatReceipt


@admin.register(Muzakki)
class MuzakkiAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "address")
    search_fields = ("name", "phone")


@admin.register(ZakatReceipt)
class ZakatReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "payer_name", "zakat_type", "amount")
    list_filter = ("zakat_type", "date")
    search_fields = ("number", "muzakki_name", "muzakki__name")


@admin.register(Mustahik)
class MustahikAdmin(admin.ModelAdmin):
    list_display = ("name", "asnaf", "is_verified", "address")
    list_filter = ("asnaf", "is_verified")
    search_fields = ("name", "address")


@admin.register(ZakatDistribution)
class ZakatDistributionAdmin(admin.ModelAdmin):
    list_display = ("date", "mustahik", "amount", "item_description")
    list_filter = ("date", "mustahik__asnaf")
    search_fields = ("mustahik__name", "note")
