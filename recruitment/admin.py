from django.contrib import admin

from .models import Applicant, Application, JobVacancy


@admin.register(JobVacancy)
class JobVacancyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "department",
        "position",
        "date_posted",
        "closing_date",
        "status",
    )
    list_filter = ("status", "department", "date_posted")
    search_fields = ("title", "department__department_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "date_applied",
        "consent_given",
    )
    list_filter = ("consent_given", "date_applied")
    search_fields = ("first_name", "last_name", "email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "applicant",
        "vacancy",
        "application_date",
        "status",
        "match_score",
    )
    list_filter = ("status", "application_date")
    search_fields = (
        "applicant__first_name",
        "applicant__last_name",
        "applicant__email",
        "vacancy__title",
    )
    readonly_fields = ("created_at", "updated_at")
