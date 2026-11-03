"""Tests for login (T2), the shared layout (T4) and role-based access (T5)."""

from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.context_processors import visible_menu
from accounts.models import Permission, Role, UserPermission
from accounts.permissions import (
    has_permission,
    has_role,
    require_permission,
    scope_queryset,
)
from accounts.templatetags.ui import status_class
from employees.models import Department, Employee, JobPosition

User = get_user_model()
PASSWORD = "SmartHr2026"


def make_employee(department, email, position):
    return Employee.objects.create(
        first_name="Test",
        last_name=email.split("@")[0],
        email=email,
        date_of_birth=date(1990, 1, 1),
        date_joined=date(2024, 1, 1),
        department=department,
        position=position,
    )


def make_user(username, role_name, employee=None, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        first_name=username.title(),
        last_name="User",
        role=Role.objects.get(role_name=role_name),
        employee=employee,
        **extra,
    )


class LoginTests(TestCase):
    """FR-01, FR-02, FR-06, NFR-05, NFR-06."""

    def setUp(self):
        self.user = make_user("thandi", "HR Officer")

    def test_FR01_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "thandi", "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_FR01_login_with_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "THANDI@example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_FR01_wrong_password_shows_generic_error(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "thandi", "password": "wrong-pass1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password.")

    def test_FR01_unknown_user_shows_same_error(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "nobody", "password": PASSWORD}
        )
        self.assertContains(response, "Invalid username or password.")

    def test_FR10_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("accounts:login"), {"username": "thandi", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_FR02_pages_need_login(self):
        for name in ("dashboard", "help", "accounts:password_change"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), response["Location"])

    def test_FR02_login_page_is_public(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_FR06_logout_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_FR06_change_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "NewPass2026x",
                "new_password2": "NewPass2026x",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass2026x"))

    def test_NFR05_session_expires_after_30_minutes_idle(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 30 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)

    def test_NFR06_password_needs_letters_and_numbers(self):
        for weak in ("short1", "lettersonlyhere", "1234567890"):
            with self.assertRaises(ValidationError):
                validate_password(weak)
        validate_password("Harbour2026")  # long enough, letters and numbers


class PermissionSeedTests(TestCase):
    """The access matrix in Design Table 4.8.1 is loaded by migration 0008."""

    def test_permissions_seeded_for_each_role(self):
        expected = {
            "Administrator": {"accounts.manage_users", "audit.view"},
            "HR Officer": {"employees.manage", "recruitment.manage", "lifecycle.manage"},
            "Manager": {"leave.approve", "performance.manage", "reports.view"},
            "Employee": {"leave.apply", "attendance.record_own", "performance.view_own"},
        }
        for role_name, codes in expected.items():
            user = make_user(role_name.lower().replace(" ", ""), role_name)
            for code in codes:
                self.assertTrue(has_permission(user, code), f"{role_name}: {code}")

    def test_employee_cannot_manage_records(self):
        user = make_user("sipho", "Employee")
        for code in ("employees.manage", "leave.approve", "recruitment.manage", "audit.view"):
            self.assertFalse(has_permission(user, code), code)

    def test_administrator_has_no_hr_record_access(self):
        user = make_user("admin2", "Administrator")
        self.assertFalse(has_permission(user, "employees.view"))

    def test_user_permission_adds_an_extra_permission(self):
        user = make_user("lerato", "Employee")
        UserPermission.objects.create(
            user=user, permission=Permission.objects.get(permission_name="reports.view")
        )
        self.assertTrue(has_permission(User.objects.get(pk=user.pk), "reports.view"))

    def test_superuser_passes_every_check(self):
        admin = User.objects.create_superuser("root", "root@example.com", PASSWORD)
        self.assertTrue(has_permission(admin, "recruitment.manage"))
        self.assertTrue(has_role(admin, "Manager"))

    def test_inactive_user_has_no_permissions(self):
        user = make_user("gone", "HR Officer", is_active=False)
        self.assertFalse(has_permission(user, "employees.view"))


class RequirePermissionTests(TestCase):
    """NFR-03: a restricted URL returns access denied, not the page."""

    def setUp(self):
        self.factory = RequestFactory()

        @require_permission("recruitment.manage")
        def vacancies(request):
            return HttpResponse("ok")

        self.view = vacancies

    def _request(self, user):
        request = self.factory.get("/recruitment/")
        request.user = user
        return request

    def test_allowed_role_gets_the_page(self):
        self.assertEqual(self.view(self._request(make_user("hr", "HR Officer"))).content, b"ok")

    def test_other_role_gets_403(self):
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            self.view(self._request(make_user("emp", "Employee")))

    def test_anonymous_user_is_sent_to_login(self):
        from django.contrib.auth.models import AnonymousUser

        response = self.view(self._request(AnonymousUser()))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


class ScopeQuerysetTests(TestCase):
    """Record-level rules (4.8.2): managers see their department, employees themselves."""

    def setUp(self):
        position = JobPosition.objects.create(position_title="Clerk")
        warehouse = Department.objects.create(department_name="Warehouse")
        sales = Department.objects.create(department_name="Sales")
        self.mgr_emp = make_employee(warehouse, "boss@example.com", position)
        self.worker = make_employee(warehouse, "worker@example.com", position)
        self.seller = make_employee(sales, "seller@example.com", position)
        self.all = Employee.objects.all()

    def test_hr_officer_sees_everyone(self):
        self.assertEqual(scope_queryset(self.all, make_user("hr", "HR Officer"), "").count(), 3)

    def test_manager_sees_own_department(self):
        manager = make_user("boss", "Manager", employee=self.mgr_emp)
        visible = set(scope_queryset(self.all, manager, ""))
        self.assertEqual(visible, {self.mgr_emp, self.worker})

    def test_employee_sees_only_themselves(self):
        employee = make_user("worker", "Employee", employee=self.worker)
        self.assertEqual(list(scope_queryset(self.all, employee, "")), [self.worker])

    def test_user_without_employee_record_sees_nothing(self):
        self.assertEqual(scope_queryset(self.all, make_user("lost", "Employee"), "").count(), 0)

    def test_scope_follows_a_relation(self):
        from leave.models import LeaveRequest

        for emp in (self.worker, self.seller):
            LeaveRequest.objects.create(
                employee=emp,
                leave_type="Annual",
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 12),
                days_requested=3,
            )
        manager = make_user("boss", "Manager", employee=self.mgr_emp)
        visible = scope_queryset(LeaveRequest.objects.all(), manager)
        self.assertEqual([lr.employee for lr in visible], [self.worker])


class LayoutTests(TestCase):
    """T4: shared layout, role-based sidebar (FR-05) and status colours (4.7.3)."""

    def test_dashboard_renders_with_layout(self):
        user = make_user("thandi", "HR Officer")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Smart<span>HR</span>", html=False)
        self.assertContains(response, "HR Officer")
        self.assertContains(response, reverse("accounts:logout"))

    @override_settings(DEBUG=True)  # unbuilt modules only appear (greyed out) in DEBUG
    def test_sidebar_hides_items_the_role_cannot_use(self):
        factory = RequestFactory()

        def labels(user):
            request = factory.get("/")
            request.user = user
            return {item["label"] for group in visible_menu(request) for item in group["items"]}

        hr = labels(make_user("hr", "HR Officer"))
        employee = labels(make_user("emp", "Employee"))
        admin = labels(make_user("adm", "Administrator"))

        self.assertIn("Recruitment", hr)
        self.assertNotIn("Recruitment", employee)
        self.assertNotIn("Employees", employee)
        self.assertIn("Leave", employee)
        self.assertIn("Users & roles", admin)
        self.assertNotIn("Users & roles", hr)

    def test_status_colours(self):
        self.assertEqual(status_class("Approved"), "ok")
        self.assertEqual(status_class("Pending"), "pend")
        self.assertEqual(status_class("Rejected"), "rej")
        self.assertEqual(status_class("Something else"), "neutral")
