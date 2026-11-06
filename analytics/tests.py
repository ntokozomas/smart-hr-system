from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, Role
from employees.models import Department, Employee, JobPosition
from leave.models import Attendance, LeaveRequest

from .charts import bar_chart, nice_max
from .metrics import EmployeeRow, add_months, build_report, report_tables, working_dates

User = get_user_model()
PASSWORD = "SmartHr2026"


class MetricsTests(SimpleTestCase):
    def setUp(self):
        self.start = date(2026, 3, 1)
        self.end = date(2026, 3, 31)
        self.today = date(2026, 3, 6)
        self.staff = [
            EmployeeRow(1, "Sales", date(2024, 1, 1), "Active"),
            EmployeeRow(2, "Finance", date(2024, 1, 1), "Active"),
        ]

    def test_leave_counts_working_days_only(self):
        leaves = [(1, "Annual", date(2026, 3, 5), date(2026, 3, 9))]
        report = build_report(self.start, self.end, self.today, self.staff, leaves, [])
        self.assertEqual(report.totals.leave["Annual"], 3)

    def test_overlapping_leave_is_counted_once(self):
        leaves = [
            (1, "Annual", date(2026, 3, 2), date(2026, 3, 3)),
            (1, "Sick", date(2026, 3, 3), date(2026, 3, 3)),
        ]
        report = build_report(self.start, self.end, self.today, self.staff, leaves, [])
        self.assertEqual(report.totals.leave_total, 2)

    def test_absence_excludes_attendance_and_leave(self):
        attendance = [(1, date(2026, 3, 2), "Present"), (1, date(2026, 3, 3), "Late")]
        leaves = [(1, "Sick", date(2026, 3, 4), date(2026, 3, 4))]
        report = build_report(self.start, self.end, self.today, self.staff[:1], leaves, attendance)
        self.assertEqual(report.totals.expected, 5)
        self.assertEqual(report.totals.absent, 2)
        self.assertEqual(report.totals.late, 1)
        self.assertEqual(report.totals.absenteeism, 40.0)

    def test_future_days_are_not_counted_as_absent(self):
        report = build_report(self.start, self.end, date(2026, 3, 2), self.staff[:1], [], [])
        self.assertEqual(report.totals.expected, 1)

    def test_leavers_and_inactive_staff_are_not_expected(self):
        staff = [
            EmployeeRow(1, "Sales", date(2024, 1, 1), "Inactive", date(2026, 3, 3)),
            EmployeeRow(2, "Sales", date(2024, 1, 1), "Inactive"),
        ]
        report = build_report(self.start, self.end, self.today, staff, [], [])
        self.assertEqual(report.totals.expected, 2)
        self.assertEqual(report.totals.headcount, 0)

    def test_report_tables_have_total_row_and_departments(self):
        report = build_report(self.start, self.end, self.today, self.staff, [], [])
        monthly, departments = report_tables(report)
        self.assertEqual(monthly[2][-1][0], "Total")
        self.assertEqual([row[0] for row in departments[2]], ["Finance", "Sales"])

    def test_working_dates_skip_weekends(self):
        days = working_dates(date(2026, 3, 6), date(2026, 3, 9))
        self.assertEqual(days, [date(2026, 3, 6), date(2026, 3, 9)])

    def test_add_months_crosses_years(self):
        self.assertEqual(add_months(date(2026, 2, 1), -5), date(2025, 9, 1))

    def test_chart_scale(self):
        self.assertEqual(nice_max(0), 1)
        self.assertEqual(nice_max(37), 50)
        chart = bar_chart(["A", "B"], [{"name": "Days", "css": "x", "values": [0, 0]}])
        self.assertTrue(chart["empty"])


def make_user(username, role_name, employee=None):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        first_name=username.title(),
        last_name="User",
        role=Role.objects.get(role_name=role_name),
        employee=employee,
    )


class ReportData:
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        position = JobPosition.objects.create(position_title="Clerk")
        cls.sales = Department.objects.create(department_name="Sales")
        cls.finance = Department.objects.create(department_name="Finance")

        def employee(email, department):
            return Employee.objects.create(
                first_name="Test",
                last_name=email.split("@")[0],
                email=email,
                date_of_birth=date(1990, 1, 1),
                date_joined=date(2024, 1, 1),
                department=department,
                position=position,
            )

        cls.sales_worker = employee("sipho@example.com", cls.sales)
        cls.sales_manager = employee("lerato@example.com", cls.sales)
        cls.finance_worker = employee("johan@example.com", cls.finance)
        cls.hr = make_user("thandi", "HR Officer")
        cls.manager = make_user("lerato", "Manager", cls.sales_manager)
        cls.worker = make_user("sipho", "Employee", cls.sales_worker)
        cls.admin = make_user("admin", "Administrator")

        day = working_dates(cls.today - timedelta(days=20), cls.today)[0]
        for person in (cls.sales_worker, cls.finance_worker):
            LeaveRequest.objects.create(
                employee=person,
                leave_type="Annual",
                start_date=day,
                end_date=day,
                days_requested=1,
                status="Approved",
            )
        Attendance.objects.create(
            employee=cls.sales_worker,
            date=cls.today,
            check_in_time=time(8, 0),
            status="Present",
        )


class ReportViewTests(ReportData, TestCase):
    def test_FR35_reports_need_permission(self):
        self.client.force_login(self.worker)
        self.assertEqual(self.client.get(reverse("analytics:reports")).status_code, 403)

    def test_FR35_hr_sees_report_for_all_departments(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leave and absenteeism report")
        departments = [row[0] for row in response.context["tables"][1][2]]
        self.assertEqual(departments, ["Finance", "Sales"])
        self.assertEqual(response.context["report"].totals.leave_total, 2)

    def test_FR38_department_filter(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:reports"), {"department": self.finance.pk})
        self.assertEqual(response.context["report"].totals.leave_total, 1)
        self.assertEqual([row[0] for row in response.context["tables"][1][2]], ["Finance"])

    def test_FR38_leave_type_filter(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:reports"), {"leave_type": "Sick"})
        self.assertEqual(response.context["report"].totals.leave_total, 0)

    def test_manager_sees_only_own_department(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("analytics:reports"), {"department": self.finance.pk})
        self.assertEqual([row[0] for row in response.context["tables"][1][2]], ["Sales"])
        self.assertNotIn("department", response.context["form"].fields)

    def test_end_before_start_shows_error(self):
        self.client.force_login(self.hr)
        response = self.client.get(
            reverse("analytics:reports"),
            {"start_date": "2026-05-01", "end_date": "2026-04-01"},
        )
        self.assertContains(response, "The end date must be on or after the start date.")
        self.assertNotIn("report", response.context)

    def test_period_longer_than_a_year_is_rejected(self):
        self.client.force_login(self.hr)
        response = self.client.get(
            reverse("analytics:reports"),
            {"start_date": "2024-01-01", "end_date": "2026-01-01"},
        )
        self.assertContains(response, "Choose a period of one year or less.")

    def test_FR38_csv_export_is_logged(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:export", args=["csv"]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment;", response["Content-Disposition"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("Leave and absenteeism by month", content)
        self.assertIn("Finance", content)
        self.assertTrue(AuditLog.objects.filter(action="Export", user=self.hr).exists())

    def test_FR38_pdf_export(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:export", args=["pdf"]))
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertTrue(response.content.rstrip().endswith(b"%%EOF"))

    def test_unknown_export_format_is_404(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("analytics:export", args=["xlsx"]))
        self.assertEqual(response.status_code, 404)

    def test_export_needs_permission(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse("analytics:export", args=["csv"]))
        self.assertEqual(response.status_code, 403)


class DashboardTests(ReportData, TestCase):
    def dashboard(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("dashboard"))

    def test_FR35_hr_dashboard(self):
        response = self.dashboard(self.hr)
        self.assertContains(response, "Headcount per department")
        self.assertContains(response, "Open vacancies")
        self.assertEqual(response.context["stats"][0]["value"], 3)

    def test_manager_dashboard_is_department_only(self):
        response = self.dashboard(self.manager)
        self.assertContains(response, "Team headcount")
        self.assertEqual(response.context["stats"][0]["value"], 2)
        self.assertEqual(response.context["stats"][3]["value"], "1 of 2")

    def test_employee_dashboard(self):
        response = self.dashboard(self.worker)
        self.assertContains(response, "Annual leave taken")
        self.assertContains(response, "My recent leave requests")
        self.assertEqual(response.context["stats"][4]["value"], "Yes")
        self.assertNotContains(response, "Open full report")

    def test_admin_dashboard(self):
        AuditLog.objects.create(action="Login", username="admin", description="Logged in")
        response = self.dashboard(self.admin)
        self.assertContains(response, "Active users")
        self.assertContains(response, "Recent audit entries")
