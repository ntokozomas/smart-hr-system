"""T13 tests: login lockout, audit log, notifications and the Administrator screens."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, Notification, Role, User
from employees.models import Department, Employee, JobPosition
from leave.models import LeaveRequest

PASSWORD = "SmartHr2026"


def make_employee(department, name):
    return Employee.objects.create(
        first_name=name,
        last_name="Test",
        email=f"{name.lower()}@example.com",
        date_of_birth=date(1990, 1, 1),
        date_joined=date(2024, 1, 1),
        department=department,
        position=JobPosition.objects.get_or_create(position_title="Clerk")[0],
    )


def make_user(username, role, employee=None):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        first_name=username.title(),
        last_name="Test",
        role=Role.objects.get(role_name=role),
        employee=employee,
    )


def login(client, username, password=PASSWORD):
    return client.post(reverse("accounts:login"), {"username": username, "password": password})


class LockoutTests(TestCase):
    """Design 4.8.1: 5 failed attempts lock the account for 15 minutes."""

    def setUp(self):
        self.user = make_user("thandi", "HR Officer")

    def test_five_failures_lock_the_account(self):
        for _ in range(5):
            login(self.client, "thandi", "wrong-pass1")
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)

        response = login(self.client, "thandi")  # right password, still locked
        self.assertContains(response, "locked")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="Account locked").exists())

    def test_four_failures_do_not_lock(self):
        for _ in range(4):
            login(self.client, "thandi", "wrong-pass1")
        self.assertRedirects(login(self.client, "thandi"), reverse("dashboard"))

    def test_lock_ends_after_15_minutes(self):
        self.user.locked_until = timezone.now() - timedelta(seconds=1)
        self.user.save()
        self.assertRedirects(login(self.client, "thandi"), reverse("dashboard"))

    def test_successful_login_resets_the_counter(self):
        for _ in range(3):
            login(self.client, "thandi", "wrong-pass1")
        login(self.client, "thandi")
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_lock_works_with_email_too(self):
        for _ in range(5):
            login(self.client, "thandi@example.com", "wrong-pass1")
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)


class AuditLogTests(TestCase):
    """Design 4.8.4: security events are recorded automatically."""

    def setUp(self):
        self.admin = make_user("sysadmin", "Administrator")

    def test_logins_and_failed_logins_are_recorded(self):
        login(self.client, "sysadmin", "wrong-pass1")
        login(self.client, "sysadmin")
        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn("Login failed", actions)
        self.assertIn("Login", actions)
        self.assertEqual(AuditLog.objects.filter(action="Login").first().ip_address, "127.0.0.1")

    def test_role_change_is_recorded_with_who_did_it(self):
        target = make_user("lerato", "Employee")
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_edit", args=[target.pk]), {
            "username": "lerato", "first_name": "Lerato", "last_name": "Test",
            "email": "lerato@example.com", "role": Role.objects.get(role_name="Manager").pk,
        })
        entry = AuditLog.objects.get(action="Role change")
        self.assertIn("from Employee to Manager", entry.description)
        self.assertEqual(entry.user, self.admin)

    def test_employee_create_and_deactivate_are_recorded(self):
        employee = make_employee(Department.objects.create(department_name="Ops"), "Ayanda")
        employee.employment_status = "Inactive"
        employee.save()
        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn("Create", actions)
        self.assertIn("Deactivate", actions)

    def test_only_the_administrator_can_view_the_log(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:audit_log")).status_code, 200)
        self.client.force_login(make_user("hr", "HR Officer"))
        self.assertEqual(self.client.get(reverse("accounts:audit_log")).status_code, 403)

    def test_log_can_be_filtered_by_action(self):
        login(self.client, "sysadmin", "wrong-pass1")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:audit_log"), {"action": "Login failed"})
        self.assertContains(response, "Failed login")


class NotificationTests(TestCase):
    """FR-17: managers hear about new requests, employees about decisions."""

    def setUp(self):
        ops = Department.objects.create(department_name="Ops")
        self.worker = make_employee(ops, "Sipho")
        self.boss = make_employee(ops, "Johan")
        self.employee_user = make_user("sipho", "Employee", self.worker)
        self.manager_user = make_user("johan", "Manager", self.boss)

    def request_leave(self):
        return LeaveRequest.objects.create(
            employee=self.worker, leave_type="Annual", start_date=date(2026, 11, 16),
            end_date=date(2026, 11, 17), days_requested=2,
        )

    def test_manager_is_told_about_a_new_request(self):
        self.request_leave()
        note = Notification.objects.get(recipient=self.manager_user)
        self.assertIn("Sipho Test requested annual leave", note.message)

    def test_employee_is_told_about_the_decision(self):
        leave = self.request_leave()
        self.client.force_login(self.manager_user)
        self.client.post(reverse("leave:review", args=[leave.pk]), {"decision": "Approved"})
        note = Notification.objects.get(recipient=self.employee_user)
        self.assertIn("was approved", note.message)
        self.assertTrue(AuditLog.objects.filter(action="Leave decision").exists())

    def test_bell_shows_unread_count_and_opening_marks_read(self):
        self.request_leave()
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, 'class="bell-count">1<')
        note = Notification.objects.get(recipient=self.manager_user)
        self.client.get(reverse("accounts:notification_open", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_users_cannot_open_other_peoples_notifications(self):
        self.request_leave()
        note = Notification.objects.get(recipient=self.manager_user)
        self.client.force_login(self.employee_user)
        response = self.client.get(reverse("accounts:notification_open", args=[note.pk]))
        self.assertEqual(response.status_code, 404)

    def test_mark_all_as_read(self):
        self.request_leave()
        self.request_leave()
        self.client.force_login(self.manager_user)
        self.client.post(reverse("accounts:notification_read_all"))
        self.assertFalse(Notification.objects.filter(is_read=False).exists())


class UserAdminTests(TestCase):
    """FR-03, FR-04: only the Administrator manages accounts and roles."""

    def setUp(self):
        self.admin = make_user("sysadmin", "Administrator")
        self.client.force_login(self.admin)

    def test_other_roles_get_403(self):
        for role in ("HR Officer", "Manager", "Employee"):
            self.client.force_login(make_user(role.lower().replace(" ", ""), role))
            self.assertEqual(self.client.get(reverse("accounts:users")).status_code, 403, role)

    def test_create_user_with_one_role_and_employee_link(self):
        employee = make_employee(Department.objects.create(department_name="Sales"), "Lerato")
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "lerato", "first_name": "Lerato", "last_name": "Test",
            "email": "Lerato@Example.com", "role": Role.objects.get(role_name="Employee").pk,
            "employee": employee.pk, "password1": "Harbour2026", "password2": "Harbour2026",
        })
        self.assertRedirects(response, reverse("accounts:users"))
        user = User.objects.get(username="lerato")
        self.assertEqual((user.role.role_name, user.employee, user.email),
                         ("Employee", employee, "lerato@example.com"))
        self.assertTrue(user.check_password("Harbour2026"))

    def test_weak_password_is_refused(self):
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "weak", "first_name": "W", "last_name": "P", "email": "w@example.com",
            "role": Role.objects.get(role_name="Employee").pk,
            "password1": "password", "password2": "password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_deactivate_and_reactivate(self):
        target = make_user("gone", "Employee")
        self.client.post(reverse("accounts:user_toggle_active", args=[target.pk]))
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.client.post(reverse("accounts:user_toggle_active", args=[target.pk]))
        target.refresh_from_db()
        self.assertTrue(target.is_active)

    def test_cannot_deactivate_or_demote_yourself(self):
        self.client.post(reverse("accounts:user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.client.post(reverse("accounts:user_edit", args=[self.admin.pk]), {
            "username": "sysadmin", "first_name": "S", "last_name": "A",
            "email": "sysadmin@example.com", "role": Role.objects.get(role_name="Employee").pk,
        })
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role.role_name, "Administrator")

    def test_reset_password_also_unlocks(self):
        target = make_user("locked", "Employee")
        target.locked_until = timezone.now() + timedelta(minutes=10)
        target.save()
        self.client.post(reverse("accounts:user_reset_password", args=[target.pk]),
                         {"password1": "Temporary2026", "password2": "Temporary2026"})
        target.refresh_from_db()
        self.assertIsNone(target.locked_until)
        self.assertTrue(target.check_password("Temporary2026"))
        self.assertTrue(AuditLog.objects.filter(action="Password reset").exists())

    def test_role_matrix_shows_seeded_permissions(self):
        response = self.client.get(reverse("accounts:roles"))
        self.assertContains(response, "leave.approve")
        self.assertContains(response, "Administrator")

    def test_user_list_search(self):
        make_user("kagiso", "Manager")
        response = self.client.get(reverse("accounts:users"), {"q": "kagiso"})
        self.assertContains(response, "kagiso@example.com")
        self.assertNotContains(response, "sysadmin@example.com")
