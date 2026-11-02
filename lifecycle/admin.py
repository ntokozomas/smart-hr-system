from django.contrib import admin

from .models import EmployeeExit, Onboarding, OnboardingTask


@admin.register(Onboarding)
class OnboardingAdmin(admin.ModelAdmin):
    list_display = ("employee", "start_date", "end_date", "status")
    list_filter = ("status", "start_date")
    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_name",
        "onboarding",
        "status",
        "completed_date",
    )
    list_filter = ("status",)
    search_fields = ("task_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmployeeExit)
class EmployeeExitAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "exit_type",
        "exit_date",
        "procedures_completed",
    )
    list_filter = ("exit_type", "procedures_completed")
    search_fields = (
        "employee__employee_number",
        "employee__first_name",
        "employee__last_name",
    )
    readonly_fields = ("created_at", "updated_at")
