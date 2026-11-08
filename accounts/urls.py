from django.urls import path

from . import admin_views, views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password/", views.PasswordChangeView.as_view(), name="password_change"),   
    path("password/done/", views.PasswordChangeDoneView.as_view(), name="password_change_done"),

    path("profile/", views.my_profile, name="profile"),
    # T13: Administrator screens (FR-03, FR-04, Design 4.8.4) and notifications (FR-17)
    path("users/", admin_views.user_list, name="users"),
    path("users/new/", admin_views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", admin_views.user_edit, name="user_edit"),
    path("users/<int:pk>/active/", admin_views.user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/password/", admin_views.user_reset_password, name="user_reset_password"),
    path("roles/", admin_views.role_matrix, name="roles"),
    path("audit/", admin_views.audit_log, name="audit_log"),
    path("notifications/", admin_views.notification_list, name="notifications"),
    path("notifications/<int:pk>/", admin_views.notification_open, name="notification_open"),
    path("notifications/read-all/", admin_views.notification_read_all, name="notification_read_all"),

]
