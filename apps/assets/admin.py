from django.contrib import admin

from apps.assets.models import Asset, AssetLog


class AssetLogInline(admin.TabularInline):
    model = AssetLog
    extra = 0


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity", "condition", "location", "value")
    list_filter = ("condition", "category")
    search_fields = ("name", "location")
    inlines = [AssetLogInline]
