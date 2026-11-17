from django.contrib import admin

from apps.finance.models import Category, Fund, Period, Transaction


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("name", "fund_type", "is_active")
    list_filter = ("fund_type", "is_active")
    search_fields = ("name", "code")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type", "is_active")
    list_filter = ("category_type", "is_active")
    search_fields = ("name",)


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "is_closed", "closed_at", "closed_by")
    list_filter = ("is_closed", "year")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "transaction_type", "description", "amount", "fund",
                    "status", "locked")
    list_filter = ("transaction_type", "status", "locked", "fund")
    search_fields = ("description", "pic")
    date_hierarchy = "date"
    autocomplete_fields = ("fund", "category")
