from django.urls import path

from . import views

app_name = "leave"

urlpatterns = [
    path("", views.home, name="home"),
    path("apply/", views.apply_leave, name="apply"),
    path("review/<int:pk>/", views.review_leave, name="review"),
    path("attendance/", views.attendance, name="attendance"),
]
