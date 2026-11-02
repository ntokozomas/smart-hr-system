from django.contrib import admin

from .models import Department, Employee, JobPosition


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("department_name", "created_at")
    search_fields = ("department_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ("position_title", "created_at")
    search_fields = ("position_title",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number",
        "first_name",
        "last_name",
        "email",
        "department",
        "position",
        "employment_status",
    )
    list_filter = ("employment_status", "department", "position")
    search_fields = (
        "employee_number",
        "first_name",
        "last_name",
        "email",
    )
    readonly_fields = ("employee_number", "created_at", "updated_at")
