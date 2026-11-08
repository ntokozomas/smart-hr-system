from django.urls import path

from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.home, name="home"),

    # HR vacancy management
    path("vacancies/", views.vacancy_list, name="vacancy_list"),
    path("vacancies/create/", views.vacancy_create, name="vacancy_create"),
    path("vacancies/<int:pk>/edit/", views.vacancy_edit, name="vacancy_edit"),
    path("vacancies/<int:pk>/status/", views.vacancy_toggle_status, name="vacancy_toggle_status"),

    # Public Careers portal
    path("careers/", views.careers, name="careers"),
    path("careers/<int:pk>/", views.career_detail, name="career_detail"),
    path("careers/<int:pk>/apply/", views.apply, name="apply"),
    path("application-status/", views.application_status, name="application_status"),

    # HR application management
    path("applications/", views.application_list, name="application_list"),
    path("applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("applications/<int:pk>/cv/", views.download_cv, name="download_cv"),
    path("applications/<int:pk>/update/", views.application_update, name="application_update"),
    path("applications/<int:pk>/convert/", views.convert_to_employee, name="convert_to_employee"),
]
