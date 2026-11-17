from django.contrib import admin

from apps.programs.models import Donation, Program


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 0
    fields = ("code", "donor_name", "amount", "method", "status")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "is_published", "target_amount", "start_date")
    list_filter = ("status", "is_published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DonationInline]


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("code", "donor_name", "program", "amount", "status", "created_at")
    list_filter = ("status", "method", "program")
    search_fields = ("code", "donor_name")
