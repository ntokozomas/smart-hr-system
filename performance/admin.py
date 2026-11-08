from django.contrib import admin

from .models import PerformanceRecord


@admin.register(PerformanceRecord)
class PerformanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "reviewed_by",
        "review_period",
        "review_date",
        "rating",
    )
    list_filter = ("rating", "review_date")
    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
        "review_period",
    )
    readonly_fields = ("created_at", "updated_at")
