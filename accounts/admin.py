from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for Smart HR user accounts."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "employee",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Smart HR Access", {"fields": ("role", "employee")}),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Smart HR Access", {"fields": ("role", "employee")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_name", "created_at", "updated_at")
    search_fields = ("role_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("permission_name", "module", "created_at")
    list_filter = ("module",)
    search_fields = ("permission_name", "module")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "created_at")
    list_filter = ("role",)
    search_fields = ("role__role_name", "permission__permission_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ("user", "permission", "created_at")
    search_fields = ("user__username", "permission__permission_name")
    readonly_fields = ("created_at", "updated_at")
