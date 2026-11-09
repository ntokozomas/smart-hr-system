
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from employees.models import Department, Employee, JobPosition
from performance.models import PerformanceRecord


class PerformanceViewTests(TestCase):
    """Test performance views and employee record access scoping."""

    def setUp(self):
        self.finance = Department.objects.create(
            department_name="Finance"
        )
        self.marketing = Department.objects.create(
            department_name="Marketing"
        )

        self.position = JobPosition.objects.create(
            position_title="Test Accountant"
        )

        self.employee = self.create_employee(
            "Jane",
            "jane.performance@example.com",
            self.finance,
        )

        self.colleague = self.create_employee(
            "John",
            "john.performance@example.com",
            self.finance,
        )

        self.other_employee = self.create_employee(
            "Mary",
            "mary.performance@example.com",
            self.marketing,
        )

        self.manager_employee = self.create_employee(
            "Manager",
            "manager.performance@example.com",
            self.finance,
        )

        self.hr_user = self.create_user(
            "performance_hr",
            "HR Officer",
        )

        self.manager_user = self.create_user(
            "performance_manager",
            "Manager",
            self.manager_employee,
        )

        self.employee_user = self.create_user(
            "performance_employee",
            "Employee",
            self.employee,
        )

        self.record_own = self.create_record(self.employee)
        self.record_colleague = self.create_record(self.colleague)
        self.record_other = self.create_record(self.other_employee)

    def create_employee(self, first_name, email, department):
        return Employee.objects.create(
            first_name=first_name,
            last_name="Tester",
            email=email,
            date_of_birth=date(1990, 1, 1),
            date_joined=date(2020, 1, 1),
            department=department,
            position=self.position,
        )

    def create_user(self, username, role_name, employee=None):
        role = Role.objects.get(role_name=role_name)

        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="TestPass123!",
            first_name=username,
            last_name="Tester",
            role=role,
            employee=employee,
        )

    def create_record(self, employee):
        return PerformanceRecord.objects.create(
            employee=employee,
            reviewed_by=self.hr_user,
            review_period="2026",
            review_date=date(2026, 11, 1),
            rating=4,
            comments="Performance test record",
        )

    def test_hr_officer_can_view_all_performance_records(self):
        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("performance:home")
        )

        self.assertEqual(response.status_code, 200)

        records = response.context["performance_records"]

        self.assertEqual(records.count(), 3)

    def test_manager_can_only_view_department_records(self):
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse("performance:home")
        )

        self.assertEqual(response.status_code, 200)

        records = response.context["performance_records"]

        self.assertEqual(records.count(), 2)
        self.assertNotIn(self.record_other, records)

    def test_employee_can_only_view_own_performance_record(self):
        self.client.force_login(self.employee_user)

        response = self.client.get(
            reverse("performance:home")
        )

        self.assertEqual(response.status_code, 200)

        records = response.context["performance_records"]

        self.assertEqual(records.count(), 1)
        self.assertIn(self.record_own, records)
        self.assertNotIn(self.record_colleague, records)
        self.assertNotIn(self.record_other, records)

    def test_manager_cannot_edit_record_outside_department(self):
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse(
                "performance:edit_review",
                kwargs={"pk": self.record_other.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_manager_cannot_delete_record_outside_department(self):
        self.client.force_login(self.manager_user)

        response = self.client.post(
            reverse(
                "performance:delete_review",
                kwargs={"pk": self.record_other.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            PerformanceRecord.objects.filter(
                pk=self.record_other.pk
            ).exists()
        )

    def test_employee_cannot_access_performance_create_view(self):
        self.client.force_login(self.employee_user)

        response = self.client.get(
            reverse("performance:create_review")
        )

        self.assertEqual(response.status_code, 403)
