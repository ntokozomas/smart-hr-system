from django.urls import path
from . import views

app_name = "performance"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create_review, name="create_review"),
    path("<int:pk>/edit/", views.edit_review, name="edit_review"),
    path("<int:pk>/delete/", views.delete_review, name="delete_review"),
]