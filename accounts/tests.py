from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from accounts.models import Role, Permission, RolePermission, UserPermission

User = get_user_model()


class AccountsModelTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(role_name="Test Administrator")
        self.permission = Permission.objects.create(
            permission_name="Manage Employees",
            module="Employees",
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
            role=self.role,
        )

    def test_role_creation_and_timestamps(self):
        self.assertIsNotNone(self.role.pk)
        self.assertIsNotNone(self.role.created_at)
        self.assertIsNotNone(self.role.updated_at)

    def test_permission_creation(self):
        self.assertEqual(self.permission.module, "Employees")

    def test_user_password_is_hashed(self):
        self.assertNotEqual(self.user.password, "SecurePass123!")
        self.assertTrue(self.user.check_password("SecurePass123!"))

    def test_user_has_required_role(self):
        self.assertEqual(self.user.role, self.role)

    def test_user_timestamps_exist(self):
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)

    def test_role_permission_creation(self):
        relation = RolePermission.objects.create(
            role=self.role,
            permission=self.permission,
        )
        self.assertEqual(relation.role, self.role)

    def test_duplicate_role_permission_rejected(self):
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RolePermission.objects.create(
                    role=self.role,
                    permission=self.permission,
                )

    def test_user_permission_creation(self):
        relation = UserPermission.objects.create(
            user=self.user,
            permission=self.permission,
        )
        self.assertEqual(relation.user, self.user)

    def test_duplicate_user_permission_rejected(self):
        UserPermission.objects.create(
            user=self.user,
            permission=self.permission,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserPermission.objects.create(
                    user=self.user,
                    permission=self.permission,
                )

    def test_default_roles_seeded(self):
        expected = ["Administrator", "HR Officer", "Manager", "Employee"]
        for name in expected:
            self.assertTrue(Role.objects.filter(role_name=name).exists())

    def test_user_email_is_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="anotheruser",
                    email=self.user.email,
                    password="SecurePass123!",
                    role=self.role,
                )

# COVERAGE_COMPLETION_TESTS
    def test_role_string_representation(self):
        self.assertEqual(str(self.role), "Test Administrator")

    def test_permission_string_representation(self):
        self.assertEqual(str(self.permission), "Employees - Manage Employees")

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser")

    def test_role_permission_string_representation(self):
        relation = RolePermission.objects.create(
            role=self.role, permission=self.permission
        )
        self.assertEqual(
            str(relation),
            "Test Administrator - Employees - Manage Employees",
        )

    def test_user_permission_string_representation(self):
        relation = UserPermission.objects.create(
            user=self.user, permission=self.permission
        )
        self.assertEqual(
            str(relation),
            "testuser - Employees - Manage Employees",
        )

# Relationship deletion tests for Section 4.5.11.
from datetime import date
from django.db.models.deletion import ProtectedError
from employees.models import Department, JobPosition, Employee


class AccountsRelationshipTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(role_name="Relationship Tester")
        self.permission = Permission.objects.create(
            permission_name="Relationship Permission",
            module="Testing",
        )
        self.user = User.objects.create_user(
            username="relationship_user",
            email="relationship@example.com",
            password="SecurePass123!",
            role=self.role,
        )

    def test_role_deletion_is_protected_when_user_uses_role(self):
        with self.assertRaises(ProtectedError):
            self.role.delete()

    def test_role_permission_cascades_when_role_is_deleted(self):
        role = Role.objects.create(role_name="Cascade Test Role")
        relation = RolePermission.objects.create(
            role=role, permission=self.permission
        )
        role.delete()
        self.assertFalse(RolePermission.objects.filter(pk=relation.pk).exists())

    def test_role_permission_cascades_when_permission_is_deleted(self):
        relation = RolePermission.objects.create(
            role=self.role, permission=self.permission
        )
        self.permission.delete()
        self.assertFalse(RolePermission.objects.filter(pk=relation.pk).exists())

    def test_user_permission_cascades_when_user_is_deleted(self):
        relation = UserPermission.objects.create(
            user=self.user, permission=self.permission
        )
        self.user.delete()
        self.assertFalse(UserPermission.objects.filter(pk=relation.pk).exists())

    def test_user_permission_cascades_when_permission_is_deleted(self):
        relation = UserPermission.objects.create(
            user=self.user, permission=self.permission
        )
        self.permission.delete()
        self.assertFalse(UserPermission.objects.filter(pk=relation.pk).exists())

    def test_user_employee_link_is_set_null_when_employee_is_deleted(self):
        department = Department.objects.create(
            department_name="Accounts Relationship Department"
        )
        position = JobPosition.objects.create(
            position_title="Accounts Relationship Position"
        )
        employee = Employee.objects.create(
            first_name="Linked",
            last_name="Employee",
            email="linked.employee@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )
        self.user.employee = employee
        self.user.save(update_fields=["employee"])

        employee.delete()
        self.user.refresh_from_db()
        self.assertIsNone(self.user.employee_id)
