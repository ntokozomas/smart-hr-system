from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from employees.models import Department, JobPosition, Employee
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import Role


class EmployeeModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            department_name="Engineering"
        )
        self.position = JobPosition.objects.create(
            position_title="Software Developer"
        )

    def create_employee(self, email="employee@example.com", **kwargs):
        defaults = {
            "first_name": "Test",
            "last_name": "Employee",
            "email": email,
            "date_of_birth": date(1995, 1, 1),
            "date_joined": date.today(),
            "department": self.department,
            "position": self.position,
        }
        defaults.update(kwargs)
        return Employee.objects.create(**defaults)

    def test_department_creation(self):
        self.assertEqual(self.department.department_name, "Engineering")

    def test_position_creation(self):
        self.assertEqual(self.position.position_title, "Software Developer")

    def test_employee_creation(self):
        employee = self.create_employee()
        self.assertIsNotNone(employee.pk)

    def test_employee_number_generated(self):
        employee = self.create_employee()
        self.assertTrue(employee.employee_number.startswith("EMP-"))

    def test_employee_number_is_unique(self):
        first = self.create_employee()
        second = self.create_employee(email="second@example.com")
        self.assertNotEqual(first.employee_number, second.employee_number)

    def test_employee_timestamps(self):
        employee = self.create_employee()
        self.assertIsNotNone(employee.created_at)
        self.assertIsNotNone(employee.updated_at)

    def test_employee_email_is_unique(self):
        self.create_employee()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_employee()

    def test_employee_under_18_fails_validation(self):
        # Build an unsaved employee so model validation runs before
        # PostgreSQL's database-level age trigger.
        employee = Employee(
            first_name="Underage",
            last_name="Employee",
            email="minor@example.com",
            date_of_birth=date.today() - timedelta(days=365 * 17),
            date_joined=date.today(),
            department=self.department,
            position=self.position,
        )

        with self.assertRaises(ValidationError):
            employee.full_clean()

    def test_adult_employee_passes_validation(self):
        employee = self.create_employee()
        employee.full_clean()

    def test_employee_cannot_manage_themselves(self):
        employee = self.create_employee()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.filter(pk=employee.pk).update(
                    manager_id=employee.pk
                )

# COVERAGE_COMPLETION_TESTS
    def test_department_string_representation(self):
        self.assertEqual(str(self.department), "Engineering")

    def test_position_string_representation(self):
        self.assertEqual(str(self.position), "Software Developer")

    def test_employee_string_representation(self):
        employee = self.create_employee()
        self.assertEqual(
            str(employee),
            f"{employee.employee_number} - Test Employee",
        )

    def test_employee_cannot_manage_themselves_validation(self):
        from django.core.exceptions import ValidationError

        employee = self.create_employee()
        employee.manager = employee
        with self.assertRaises(ValidationError):
            employee.full_clean()

# Relationship and database-trigger tests for Section 4.5.11.
from django.db.models.deletion import ProtectedError


class EmployeeRelationshipAndDatabaseTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            department_name="Relationship Engineering"
        )
        self.position = JobPosition.objects.create(
            position_title="Relationship Developer"
        )

    def make_employee(self, email, **extra):
        values = {
            "first_name": "Test",
            "last_name": "Person",
            "email": email,
            "date_of_birth": date(1990, 1, 1),
            "date_joined": date.today(),
            "department": self.department,
            "position": self.position,
        }
        values.update(extra)
        return Employee.objects.create(**values)

    def test_department_deletion_is_protected_by_employee(self):
        self.make_employee("department.protect@example.com")
        with self.assertRaises(ProtectedError):
            self.department.delete()

    def test_position_deletion_is_protected_by_employee(self):
        self.make_employee("position.protect@example.com")
        with self.assertRaises(ProtectedError):
            self.position.delete()

    def test_manager_deletion_sets_subordinate_manager_to_null(self):
        manager = self.make_employee("manager@example.com")
        subordinate = self.make_employee(
            "subordinate@example.com",
            manager=manager,
        )
        manager.delete()
        subordinate.refresh_from_db()
        self.assertIsNone(subordinate.manager_id)

    def test_database_trigger_rejects_employee_under_18(self):
        underage_dob = date.today().replace(
            year=date.today().year - 17
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_employee(
                    "underage.database@example.com",
                    date_of_birth=underage_dob,
                )
class EmployeeProfileTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(
            department_name="Profile Engineering"
        )

        self.position = JobPosition.objects.create(
            position_title="Administrator"
        )

        self.employee = Employee.objects.create(
            first_name="Angilique",
            last_name="West",
            email="angilique@example.com",
            phone_number="0123456789",
            address="Johannesburg",
            date_of_birth=date(1995, 5, 10),
            date_joined=date(2024, 1, 15),
            employment_status="Active",
            department=self.department,
            position=self.position,
        )

        self.role = Role.objects.create(
            role_name="Profile Test Employee"
        )

        User = get_user_model()

        self.user = User.objects.create_user(
            username="profiletest",
            email="angilique@example.com",
            password="TestPassword123!",
            first_name="Angilique",
            last_name="West",
            role=self.role,
            employee=self.employee,
        )

        self.profile_url = reverse("employees:my_profile")
        self.client.login(
            username="profiletest",
            password="TestPassword123!",
        )

    def test_employee_can_view_own_profile(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["employee"],
            self.employee,
        )

    def test_profile_displays_employee_details(self):
        response = self.client.get(self.profile_url)

        self.assertContains(response, "Angilique")
        self.assertContains(response, "West")
        self.assertContains(response, self.employee.employee_number)
        self.assertContains(response, "Profile Engineering")

    def test_employee_can_update_contact_details(self):
        response = self.client.post(
            self.profile_url,
            {
                "email": "updated@example.com",
                "phone_number": "0821234567",
                "address": "Pretoria",
            },
            follow=True,
        )

        self.employee.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.employee.email, "updated@example.com")
        self.assertEqual(self.employee.phone_number, "0821234567")
        self.assertEqual(self.employee.address, "Pretoria")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertContains(
            response,
            "Your profile was updated successfully.",
        )

    def test_employee_cannot_use_another_accounts_email(self):
        User = get_user_model()

        User.objects.create_user(
            username="anotheruser",
            email="taken@example.com",
            password="TestPassword123!",
            role=self.role,
        )

        response = self.client.post(
            self.profile_url,
            {
                "email": "taken@example.com",
                "phone_number": "0821234567",
                "address": "Pretoria",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.employee.refresh_from_db()
        self.assertEqual(
            self.employee.email,
            "angilique@example.com",
        )

    def test_user_without_employee_record_sees_assistance_message(self):
        User = get_user_model()

        unlinked_user = User.objects.create_user(
            username="unlinkeduser",
            email="unlinked@example.com",
            password="TestPassword123!",
            role=self.role,
        )

        self.client.force_login(unlinked_user)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["employee"])
        self.assertContains(
            response,
            "No employee record is linked to your account.",
        )