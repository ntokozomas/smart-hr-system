"""T6: the seed_demo command loads consistent demo data and can be run again safely."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import User
from employees.models import Employee
from leave.models import Attendance, LeaveRequest
from lifecycle.models import EmployeeExit, Onboarding
from performance.models import PerformanceRecord
from recruitment.models import Application, JobVacancy


def seed(*args):
    out = StringIO()
    call_command("seed_demo", "--no-cv-files", *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def test_loads_45_current_staff_in_four_departments(self):
        seed()
        staff = Employee.objects.exclude(employment_status="Inactive")
        self.assertEqual(staff.count(), 45)
        counts = {
            name: staff.filter(department__department_name=name).count()
            for name in ("Warehouse & Operations", "Sales", "Finance & Admin", "Management")
        }
        self.assertEqual(counts, {
            "Warehouse & Operations": 22, "Sales": 11, "Finance & Admin": 8, "Management": 4,
        })

    def test_a_user_for_every_role_can_log_in(self):
        seed()
        for username, role in (("sysadmin", "Administrator"), ("thandi", "HR Officer"),
                               ("johan", "Manager"), ("sipho", "Employee")):
            user = User.objects.get(username=username)
            self.assertEqual(user.role.role_name, role)
            self.assertTrue(self.client.login(username=username, password="SmartHr2026"))

    def test_next_week_has_a_department_leave_clash(self):
        seed()
        pending = LeaveRequest.objects.get(employee__first_name="Sipho", status="Pending")
        clashes = LeaveRequest.objects.filter(
            employee__department=pending.employee.department,
            status="Approved",
            start_date__lte=pending.end_date,
            end_date__gte=pending.start_date,
        ).exclude(employee=pending.employee)
        # Ayanda and Pieter are the planned clash. Random demo leave can add
        # more on some days, so check for the two names, not an exact count.
        names = set(clashes.values_list("employee__first_name", flat=True))
        self.assertTrue({"Ayanda", "Pieter"} <= names, names)

    def test_every_module_gets_data(self):
        seed()
        self.assertGreater(Attendance.objects.count(), 300)
        self.assertEqual(Onboarding.objects.count(), 1)
        self.assertEqual(EmployeeExit.objects.count(), 1)
        self.assertEqual(PerformanceRecord.objects.count(), 24)
        self.assertEqual(Application.objects.count(), 14)
        self.assertEqual(JobVacancy.objects.filter(status="Open").count(), 2)
        statuses = set(LeaveRequest.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {"Approved", "Pending", "Rejected"})

    def test_running_twice_does_not_duplicate(self):
        seed()
        before = Employee.objects.count()
        output = seed()
        self.assertIn("already loaded", output)
        self.assertEqual(Employee.objects.count(), before)

    def test_reset_reloads_cleanly(self):
        seed()
        seed("--reset")
        self.assertEqual(Employee.objects.exclude(employment_status="Inactive").count(), 45)
        self.assertEqual(Application.objects.count(), 14)
        self.assertEqual(User.objects.filter(username="thandi").count(), 1)

    @override_settings(DEBUG=False)
    def test_refuses_on_a_live_system_without_force(self):
        with self.assertRaises(CommandError):
            seed()
