from datetime import date
from django.test import TestCase
from django.db import IntegrityError, transaction
from accounts.models import Role, User
from employees.models import Department, JobPosition, Employee
from performance.models import PerformanceRecord


class PerformanceModelTests(TestCase):
    def setUp(self):
        role = Role.objects.create(role_name="Reviewer")
        self.reviewer = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="SecurePass123!",
            role=role,
        )
        department = Department.objects.create(
            department_name="Finance"
        )
        position = JobPosition.objects.create(
            position_title="Accountant"
        )
        self.employee = Employee.objects.create(
            first_name="Alex",
            last_name="Jones",
            email="alex@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )

    def test_performance_record_creation(self):
        record = PerformanceRecord.objects.create(
            employee=self.employee,
            reviewed_by=self.reviewer,
            review_period="2026 Annual Review",
            review_date=date.today(),
            rating=4,
        )
        self.assertEqual(record.rating, 4)

    def test_rating_below_one_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PerformanceRecord.objects.create(
                    employee=self.employee,
                    reviewed_by=self.reviewer,
                    review_period="Invalid",
                    review_date=date.today(),
                    rating=0,
                )

    def test_rating_above_five_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PerformanceRecord.objects.create(
                    employee=self.employee,
                    reviewed_by=self.reviewer,
                    review_period="Invalid",
                    review_date=date.today(),
                    rating=6,
                )

# COVERAGE_COMPLETION_TESTS
    def test_performance_record_string_representation(self):
        record = PerformanceRecord.objects.create(
            employee=self.employee,
            reviewed_by=self.reviewer,
            review_period="2026 Annual Review",
            review_date=date.today(),
            rating=4,
        )
        self.assertEqual(
            str(record),
            f"{self.employee} - 2026 Annual Review",
        )

# Relationship deletion tests for Section 4.5.11.
from django.db.models.deletion import ProtectedError


class PerformanceRelationshipTests(TestCase):
    def setUp(self):
        role = Role.objects.create(role_name="Relationship Reviewer")
        self.reviewer = User.objects.create_user(
            username="relationship_reviewer",
            email="relationship.reviewer@example.com",
            password="SecurePass123!",
            role=role,
        )
        department = Department.objects.create(
            department_name="Performance Relationship Tests"
        )
        position = JobPosition.objects.create(
            position_title="Performance Test Employee"
        )
        self.employee = Employee.objects.create(
            first_name="Performance",
            last_name="Employee",
            email="performance.relationship@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )

    def make_record(self):
        return PerformanceRecord.objects.create(
            employee=self.employee,
            reviewed_by=self.reviewer,
            review_period="Relationship Test",
            review_date=date.today(),
            rating=4,
        )

    def test_employee_deletion_cascades_to_performance_records(self):
        record = self.make_record()
        self.employee.delete()
        self.assertFalse(
            PerformanceRecord.objects.filter(pk=record.pk).exists()
        )

    def test_reviewer_deletion_is_protected_by_performance_record(self):
        self.make_record()
        with self.assertRaises(ProtectedError):
            self.reviewer.delete()
