from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from employees.models import Department, JobPosition, Employee


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
