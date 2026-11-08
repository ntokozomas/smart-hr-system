from datetime import date
from django.test import TestCase
from django.db import IntegrityError, transaction
from employees.models import Department, JobPosition, Employee
from lifecycle.models import Onboarding, OnboardingTask, EmployeeExit


class LifecycleModelTests(TestCase):
    def setUp(self):
        department = Department.objects.create(
            department_name="Operations"
        )
        position = JobPosition.objects.create(
            position_title="Operations Officer"
        )
        self.employee = Employee.objects.create(
            first_name="John",
            last_name="Smith",
            email="john@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )

    def test_onboarding_creation(self):
        onboarding = Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        self.assertEqual(onboarding.status, "Pending")

    def test_onboarding_employee_is_one_to_one(self):
        Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Onboarding.objects.create(
                    employee=self.employee,
                    start_date=date.today(),
                )

    def test_onboarding_task_creation(self):
        onboarding = Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        task = OnboardingTask.objects.create(
            onboarding=onboarding,
            task_name="Complete induction",
        )
        self.assertEqual(task.status, "Pending")

    def test_employee_exit_creation(self):
        exit_record = EmployeeExit.objects.create(
            employee=self.employee,
            exit_type="Resignation",
            exit_date=date.today(),
            reason="Personal reasons",
        )
        self.assertFalse(exit_record.procedures_completed)

    def test_employee_exit_is_one_to_one(self):
        EmployeeExit.objects.create(
            employee=self.employee,
            exit_type="Resignation",
            exit_date=date.today(),
            reason="Personal reasons",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmployeeExit.objects.create(
                    employee=self.employee,
                    exit_type="Retirement",
                    exit_date=date.today(),
                    reason="Retirement",
                )

# COVERAGE_COMPLETION_TESTS
    def test_onboarding_string_representation(self):
        onboarding = Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        self.assertEqual(str(onboarding), f"Onboarding - {self.employee}")

    def test_onboarding_task_string_representation(self):
        onboarding = Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        task = OnboardingTask.objects.create(
            onboarding=onboarding,
            task_name="Complete induction",
        )
        self.assertEqual(str(task), "Complete induction - Pending")

    def test_employee_exit_string_representation(self):
        exit_record = EmployeeExit.objects.create(
            employee=self.employee,
            exit_type="Resignation",
            exit_date=date.today(),
            reason="Personal reasons",
        )
        self.assertEqual(
            str(exit_record),
            f"{self.employee} - Resignation",
        )

# Relationship deletion tests for Section 4.5.11.
from django.db.models.deletion import ProtectedError


class LifecycleRelationshipTests(TestCase):
    def setUp(self):
        department = Department.objects.create(
            department_name="Lifecycle Relationship Tests"
        )
        position = JobPosition.objects.create(
            position_title="Lifecycle Test Employee"
        )
        self.employee = Employee.objects.create(
            first_name="Lifecycle",
            last_name="Employee",
            email="lifecycle.relationship@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )

    def test_employee_deletion_cascades_to_onboarding_and_tasks(self):
        onboarding = Onboarding.objects.create(
            employee=self.employee,
            start_date=date.today(),
        )
        task = OnboardingTask.objects.create(
            onboarding=onboarding,
            task_name="Relationship test task",
        )

        self.employee.delete()

        self.assertFalse(
            Onboarding.objects.filter(pk=onboarding.pk).exists()
        )
        self.assertFalse(
            OnboardingTask.objects.filter(pk=task.pk).exists()
        )

    def test_employee_deletion_is_protected_by_exit_record(self):
        exit_record = EmployeeExit.objects.create(
            employee=self.employee,
            exit_type="Resignation",
            exit_date=date.today(),
            reason="Relationship protection test",
        )

        with self.assertRaises(ProtectedError):
            self.employee.delete()

        self.assertTrue(
            EmployeeExit.objects.filter(pk=exit_record.pk).exists()
        )
