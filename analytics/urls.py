from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.reports, name="reports"),
    path("export/<str:file_format>/", views.export_report, name="export"),
]
