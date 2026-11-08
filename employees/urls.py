from django.urls import path

from . import views

app_name = "employees"

urlpatterns = [
    path("", views.employee_list, name="list"),
    path("search/", views.employee_list, name="search"),
    path("add/", views.employee_create, name="create"),
    path("<int:pk>/edit/", views.employee_update, name="edit"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("<int:pk>/deactivate/", views.employee_deactivate, name="deactivate"),
    path("<int:pk>/activate/", views.employee_activate, name="activate"),
]
