from django.urls import path

from . import views

app_name = "lifecycle"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create_onboarding, name="create"),
    path(
        "<int:pk>/edit/",
        views.edit_onboarding,
        name="edit_onboarding",
    ),
    path(
        "<int:pk>/delete/",
        views.delete_onboarding,
        name="delete_onboarding",
    ),
    path(
        "<int:onboarding_id>/tasks/create/",
        views.create_onboarding_task,
        name="create_task",
    ),
    path(
        "exit/",
        views.exit_management,
        name="exit_management",
    ),
    path(
        "exit/create/",
        views.create_employee_exit,
        name="create_exit",
    ),
    path(
        "exit/<int:pk>/edit/",
        views.edit_employee_exit,
        name="edit_exit",
    ),
    path(
        "exit/<int:pk>/delete/",
        views.delete_employee_exit,
        name="delete_exit",
    ),
]