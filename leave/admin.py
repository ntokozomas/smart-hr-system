
from django.contrib import admin

from .models import Attendance, LeaveRequest, LeaveBalance


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "days_requested",
        "status",
        "date_submitted",
    )

    list_filter = (
        "leave_type",
        "status",
        "date_submitted",
    )

    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "leave_type",
        "year",
        "entitlement",
        "used_days",
        "remaining_days",
    )

    list_filter = (
        "leave_type",
        "year",
    )

    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
    )

    readonly_fields = (
        "used_days",
        "remaining_days",
        "created_at",
        "updated_at",
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "date",
        "check_in_time",
        "check_out_time",
        "status",
    )

    list_filter = (
        "status",
        "date",
    )

    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
