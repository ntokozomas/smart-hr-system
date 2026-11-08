from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from .models import Department, JobPosition, Employee


class MyProfileTests(TestCase):

    def setUp(self):
        self.role, created = Role.objects.get_or_create(
            role_name="Employee",
            defaults={
                "description": "Employee test role",
            },
        )

        self.department = Department.objects.create(
            department_name="Information Technology",
        )

        self.position = JobPosition.objects.create(
            position_title="Backend Developer",
        )

        self.employee = Employee.objects.create(
            first_name="Test",
            last_name="Employee",
            email="test@example.com",
            phone_number="0111234567",
            address="Johannesburg",
            date_of_birth=date(1995, 5, 10),
            date_joined=date(2024, 1, 1),
            department=self.department,
            position=self.position,
        )

        self.user = User.objects.create_user(
            username="testemployee",
            password="TestPassword123!",
            email="test@example.com",
            first_name="Test",
            last_name="Employee",
            role=self.role,
            employee=self.employee,
        )

        self.url = reverse("employees:my_profile")

    def test_profile_page_loads(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "employees/my_profile.html",
        )

    def test_profile_displays_employee_details(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertContains(response, "Test Employee")
        self.assertContains(response, self.employee.employee_number)
        self.assertContains(response, "Information Technology")
        self.assertContains(response, "Backend Developer")

    def test_profile_form_loads_without_validation_errors(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertFalse(response.context["form"].errors)

    def test_employee_can_update_contact_details(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "email": "updated@example.com",
                "phone_number": "0821234567",
                "address": "Pretoria, South Africa",
            },
        )

        self.assertRedirects(response, self.url)

        self.employee.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(
            self.employee.email,
            "updated@example.com",
        )
        self.assertEqual(
            self.employee.phone_number,
            "0821234567",
        )
        self.assertEqual(
            self.employee.address,
            "Pretoria, South Africa",
        )
        self.assertEqual(
            self.user.email,
            "updated@example.com",
        )

    def test_invalid_email_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "email": "not-an-email",
                "phone_number": "0821234567",
                "address": "Johannesburg",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

        self.employee.refresh_from_db()

        self.assertEqual(
            self.employee.email,
            "test@example.com",
        )

    def test_unauthenticated_user_is_redirected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
