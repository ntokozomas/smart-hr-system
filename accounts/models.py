"""
Smart HR System - Accounts and Access Control Models.

Implements the Role-Based Access Control (RBAC) structure
defined in Section 4.5.11 of the project specification.
"""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from config.models import TimeStampedModel


class Role(TimeStampedModel):
    """Defines a system role such as Administrator or HR Officer."""

    role_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["role_name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.role_name


class Permission(TimeStampedModel):
    """Defines an individual permission within a system module."""

    permission_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    module = models.CharField(max_length=50)

    class Meta:
        ordering = ["module", "permission_name"]
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

    def __str__(self):
        return f"{self.module} - {self.permission_name}"


class SmartHRUserManager(UserManager):
    """Superusers created from the command line get the Administrator role."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.objects.get(role_name="Administrator"))
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom Smart HR user account.

    Extends Django AbstractUser to preserve secure password
    authentication and built-in user management functionality.
    """

    objects = SmartHRUserManager()

    # Required audit timestamps for the User table.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Personal details required by Section 4.5.11.
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, unique=True)

    # Temporarily nullable for the initial role data migration.
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
    )

    # An account can optionally be linked to an employee.
    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.SET_NULL,
        related_name="user_account",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class RolePermission(TimeStampedModel):
    """Connects system roles to their permitted actions."""

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        ordering = ["role", "permission"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            ),
        ]
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

    def __str__(self):
        return f"{self.role} - {self.permission}"


class UserPermission(TimeStampedModel):
    """Connects individual users to additional permissions."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_permissions_extra",
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="user_permissions_extra",
    )

    class Meta:
        ordering = ["user", "permission"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission"],
                name="unique_user_permission",
            ),
        ]
        verbose_name = "User Permission"
        verbose_name_plural = "User Permissions"

    def __str__(self):
        return f"{self.user} - {self.permission}"
