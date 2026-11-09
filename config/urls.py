"""Smart HR System URLs. Each module adds one include() line here."""

from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("", account_views.dashboard, name="dashboard"),
    path("help/", account_views.help_page, name="help"),
    path("accounts/", include("accounts.urls")),
    path("leave/", include("leave.urls")),
    path("recruitment/", include("recruitment.urls")),
    path("employees/", include("employees.urls")),
    path("lifecycle/", include("lifecycle.urls")),
    path("performance/", include("performance.urls")),
    path("reports/", include("analytics.urls")),
    path("admin/", admin.site.urls),
]
