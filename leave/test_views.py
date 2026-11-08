
from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from employees.models import Department, Employee, JobPosition
from leave.models import Attendance, LeaveRequest, LeaveBalance


class LeaveViewTests(TestCase):
    """Test leave application, approval, balances and department access."""

    def setUp(self):
        self.department = Department.objects.create(department_name="Finance")
        self.other_department = Department.objects.create(department_name="Marketing")
        self.position = JobPosition.objects.create(position_title="HR Test Officer")

        self.employee = self.create_employee("Jane", "jane@example.com", self.department)
        self.colleague = self.create_employee("John", "john@example.com", self.department)
        self.other_employee = self.create_employee(
            "Mary", "mary@example.com", self.other_department
        )
        self.manager_employee = self.create_employee(
            "Peter", "peter@example.com", self.department
        )

        self.employee_user = self.create_user("employee_test", "Employee", self.employee)
        self.manager_user = self.create_user("manager_test", "Manager", self.manager_employee)
        self.hr_user = self.create_user("hr_officer_test", "HR Officer")

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

    def create_leave_balance(
        self,
        employee,
        entitlement=Decimal("20.0"),
        leave_type=LeaveRequest.LeaveType.ANNUAL,
        year=2026,
    ):
        return LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            year=year,
            entitlement=entitlement,
        )

    def create_leave_request(
        self,
        employee,
        status=LeaveRequest.Status.PENDING,
        start_date=date(2026, 11, 9),
        end_date=date(2026, 11, 13),
    ):
        return LeaveRequest.objects.create(
            employee=employee,
            leave_type=LeaveRequest.LeaveType.ANNUAL,
            start_date=start_date,
            end_date=end_date,
            days_requested=Decimal("5.0"),
            status=status,
        )

    def test_employee_can_submit_leave_application(self):
        self.create_leave_balance(self.employee)
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:apply"),
            {
                "leave_type": "Annual",
                "start_date": "2026-11-09",
                "end_date": "2026-11-13",
                "reason": "Annual leave",
            },
        )

        self.assertRedirects(response, reverse("leave:home"))

        leave_request = LeaveRequest.objects.get(employee=self.employee)
        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)
        self.assertEqual(leave_request.days_requested, Decimal("5.0"))

    def test_invalid_leave_dates_are_rejected(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:apply"),
            {
                "leave_type": "Annual",
                "start_date": "2026-11-13",
                "end_date": "2026-11-09",
                "reason": "Invalid date test",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LeaveRequest.objects.filter(employee=self.employee).exists())
        self.assertIn("end_date", response.context["form"].errors)

    def test_overlapping_personal_leave_shows_warning(self):
        self.create_leave_balance(self.employee)
        self.create_leave_request(self.employee)
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:apply"),
            {
                "leave_type": "Annual",
                "start_date": "2026-11-10",
                "end_date": "2026-11-12",
                "reason": "Overlapping leave test",
            },
            follow=True,
        )

        self.assertEqual(
            LeaveRequest.objects.filter(employee=self.employee).count(),
            2,
        )
        self.assertContains(response, "overlaps with these dates")

    def test_employee_cannot_apply_without_configured_leave_balance(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:apply"),
            {
                "leave_type": "Annual",
                "start_date": "2026-11-09",
                "end_date": "2026-11-13",
                "reason": "Leave without configured balance",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LeaveRequest.objects.filter(employee=self.employee).exists())
        self.assertIn("leave_type", response.context["form"].errors)

    def test_employee_cannot_apply_for_more_days_than_available_balance(self):
        self.create_leave_balance(
            self.employee,
            entitlement=Decimal("3.0"),
        )
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:apply"),
            {
                "leave_type": "Annual",
                "start_date": "2026-11-09",
                "end_date": "2026-11-13",
                "reason": "Request exceeds available balance",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LeaveRequest.objects.filter(employee=self.employee).exists())
        self.assertIn("end_date", response.context["form"].errors)
        self.assertContains(response, "Insufficient leave balance")

    def test_employee_can_view_own_leave_balance(self):
        balance = self.create_leave_balance(
            self.employee,
            entitlement=Decimal("20.0"),
        )
        self.create_leave_request(
            self.employee,
            status=LeaveRequest.Status.APPROVED,
        )
        self.client.force_login(self.employee_user)

        response = self.client.get(reverse("leave:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["leave_balances"]), 1)

        displayed_balance = response.context["leave_balances"][0]
        self.assertEqual(displayed_balance.pk, balance.pk)
        self.assertEqual(displayed_balance.used_days, Decimal("5.0"))
        self.assertEqual(displayed_balance.remaining_days, Decimal("15.0"))

    def test_pending_leave_does_not_count_as_used_leave(self):
        balance = self.create_leave_balance(self.employee)
        self.create_leave_request(
            self.employee,
            status=LeaveRequest.Status.PENDING,
        )

        self.assertEqual(balance.used_days, Decimal("0.0"))
        self.assertEqual(balance.remaining_days, Decimal("20.0"))

    def test_hr_officer_can_approve_leave(self):
        leave_request = self.create_leave_request(self.employee)
        self.client.force_login(self.hr_user)

        response = self.client.post(
            reverse("leave:review", kwargs={"pk": leave_request.pk}),
            {"decision": "Approved"},
        )

        self.assertRedirects(response, reverse("leave:home"))

        leave_request.refresh_from_db()

        self.assertEqual(leave_request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave_request.approved_by, self.hr_user)
        self.assertIsNotNone(leave_request.decided_at)

    def test_manager_can_see_department_leave_conflicts(self):
        leave_request = self.create_leave_request(self.employee)

        self.create_leave_request(
            self.colleague,
            status=LeaveRequest.Status.APPROVED,
            start_date=date(2026, 11, 11),
            end_date=date(2026, 11, 13),
        )

        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse("leave:review", kwargs={"pk": leave_request.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["department_conflicts"].count(), 1)

    def test_manager_cannot_review_another_department(self):
        leave_request = self.create_leave_request(self.other_employee)
        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse("leave:review", kwargs={"pk": leave_request.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_manager_cannot_review_own_leave_request(self):
        leave_request = self.create_leave_request(self.manager_employee)
        self.client.force_login(self.manager_user)

        response = self.client.post(
            reverse("leave:review", kwargs={"pk": leave_request.pk}),
            {"decision": "Approved"},
        )

        self.assertEqual(response.status_code, 403)

        leave_request.refresh_from_db()

        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)
        self.assertIsNone(leave_request.approved_by)

    def test_employee_cannot_access_leave_review(self):
        leave_request = self.create_leave_request(self.employee)
        self.client.force_login(self.employee_user)

        response = self.client.get(
            reverse("leave:review", kwargs={"pk": leave_request.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_employee_sees_only_own_leave_requests(self):
        own_request = self.create_leave_request(self.employee)
        self.create_leave_request(self.colleague)

        self.client.force_login(self.employee_user)

        response = self.client.get(reverse("leave:home"))

        self.assertEqual(response.status_code, 200)

        visible_requests = list(response.context["leave_requests"])

        self.assertEqual(len(visible_requests), 1)
        self.assertEqual(visible_requests[0].pk, own_request.pk)


class AttendanceViewTests(TestCase):
    """Test attendance recording, filtering, pagination and access restrictions."""

    def setUp(self):
        self.department = Department.objects.create(department_name="IT Department")
        self.other_department = Department.objects.create(
            department_name="Finance Department"
        )
        self.position = JobPosition.objects.create(position_title="IT Technician")

        self.employee = self.create_employee(
            "Alice", "alice@example.com", self.department
        )
        self.colleague = self.create_employee(
            "Charlie", "charlie@example.com", self.department
        )
        self.other_employee = self.create_employee(
            "Bob", "bob@example.com", self.other_department
        )
        self.manager_employee = self.create_employee(
            "David", "david@example.com", self.department
        )

        self.employee_user = self.create_user(
            "attendance_employee", "Employee", self.employee
        )
        self.manager_user = self.create_user(
            "attendance_manager", "Manager", self.manager_employee
        )
        self.hr_user = self.create_user("attendance_hr", "HR Officer")

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

    def create_attendance(
        self,
        employee,
        attendance_date,
        status=Attendance.Status.PRESENT,
    ):
        return Attendance.objects.create(
            employee=employee,
            date=attendance_date,
            check_in_time=time(8, 0),
            status=status,
        )

    def test_employee_can_check_in(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:attendance"),
            {"action": "check_in"},
        )

        self.assertRedirects(response, reverse("leave:attendance"))

        record = Attendance.objects.get(
            employee=self.employee,
            date=timezone.localdate(),
        )

        self.assertIsNotNone(record.check_in_time)
        self.assertEqual(record.status, Attendance.Status.PRESENT)

    def test_duplicate_check_in_does_not_create_another_record(self):
        self.client.force_login(self.employee_user)

        self.client.post(
            reverse("leave:attendance"),
            {"action": "check_in"},
        )
        self.client.post(
            reverse("leave:attendance"),
            {"action": "check_in"},
        )

        self.assertEqual(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).count(),
            1,
        )

    def test_employee_can_check_out_after_check_in(self):
        self.client.force_login(self.employee_user)

        self.client.post(
            reverse("leave:attendance"),
            {"action": "check_in"},
        )

        record = Attendance.objects.get(
            employee=self.employee,
            date=timezone.localdate(),
        )

        record.check_in_time = time(0, 0)
        record.save(update_fields=["check_in_time", "updated_at"])

        self.client.post(
            reverse("leave:attendance"),
            {"action": "check_out"},
        )

        record.refresh_from_db()

        self.assertIsNotNone(record.check_out_time)
        self.assertGreater(record.check_out_time, record.check_in_time)

    def test_employee_cannot_check_out_without_check_in(self):
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse("leave:attendance"),
            {"action": "check_out"},
        )

        self.assertRedirects(response, reverse("leave:attendance"))
        self.assertFalse(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).exists()
        )

    def test_inactive_employee_cannot_check_in(self):
        self.employee.employment_status = Employee.EmploymentStatus.INACTIVE
        self.employee.save(update_fields=["employment_status", "updated_at"])

        self.client.force_login(self.employee_user)

        self.client.post(
            reverse("leave:attendance"),
            {"action": "check_in"},
        )

        self.assertFalse(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).exists()
        )

    def test_employee_sees_only_own_attendance_records(self):
        own_record = self.create_attendance(self.employee, date(2026, 11, 2))
        self.create_attendance(self.other_employee, date(2026, 11, 2))

        self.client.force_login(self.employee_user)

        response = self.client.get(reverse("leave:attendance"))

        self.assertEqual(response.status_code, 200)

        visible_records = list(response.context["attendance_records"])

        self.assertEqual(len(visible_records), 1)
        self.assertEqual(visible_records[0].pk, own_record.pk)

    def test_hr_officer_can_filter_attendance_by_employee(self):
        alice_record = self.create_attendance(self.employee, date(2026, 11, 2))
        self.create_attendance(self.other_employee, date(2026, 11, 2))

        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"employee": str(self.employee.pk)},
        )

        self.assertEqual(response.status_code, 200)
        records = list(response.context["attendance_records"])
        self.assertEqual([record.pk for record in records], [alice_record.pk])

    def test_hr_officer_can_filter_attendance_by_department(self):
        it_record = self.create_attendance(self.employee, date(2026, 11, 2))
        self.create_attendance(self.other_employee, date(2026, 11, 2))

        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"department": str(self.department.pk)},
        )

        self.assertEqual(response.status_code, 200)
        records = list(response.context["attendance_records"])
        self.assertEqual([record.pk for record in records], [it_record.pk])

    def test_hr_officer_can_filter_attendance_by_date_range(self):
        earlier_record = self.create_attendance(
            self.employee, date(2026, 11, 1)
        )
        selected_record = self.create_attendance(
            self.colleague, date(2026, 11, 3)
        )
        self.create_attendance(self.other_employee, date(2026, 11, 5))

        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {
                "date_from": "2026-11-02",
                "date_to": "2026-11-04",
            },
        )

        self.assertEqual(response.status_code, 200)
        records = list(response.context["attendance_records"])
        self.assertEqual([record.pk for record in records], [selected_record.pk])
        self.assertNotIn(earlier_record, records)

    def test_hr_officer_can_filter_attendance_by_status(self):
        present_record = self.create_attendance(
            self.employee,
            date(2026, 11, 2),
            Attendance.Status.PRESENT,
        )
        self.create_attendance(
            self.other_employee,
            date(2026, 11, 2),
            Attendance.Status.LATE,
        )

        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"status": Attendance.Status.PRESENT},
        )

        self.assertEqual(response.status_code, 200)
        records = list(response.context["attendance_records"])
        self.assertEqual([record.pk for record in records], [present_record.pk])

    def test_impossible_start_date_does_not_cause_server_error(self):
        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"date_from": "2026-02-30"},
        )

        self.assertEqual(response.status_code, 200)

    def test_impossible_end_date_does_not_cause_server_error(self):
        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"date_to": "2026-02-30"},
        )

        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_see_other_department_attendance(self):
        own_record = self.create_attendance(self.employee, date(2026, 11, 2))
        self.create_attendance(self.other_employee, date(2026, 11, 2))

        self.client.force_login(self.manager_user)

        response = self.client.get(reverse("leave:attendance"))

        self.assertEqual(response.status_code, 200)
        records = list(response.context["attendance_records"])
        self.assertEqual([record.pk for record in records], [own_record.pk])

    def test_manager_filter_cannot_show_other_department_records(self):
        own_record = self.create_attendance(self.employee, date(2026, 11, 2))
        self.create_attendance(self.other_employee, date(2026, 11, 2))

        self.client.force_login(self.manager_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {"department": str(self.other_department.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["attendance_records"].paginator.count, 0)

    def test_pagination_preserves_attendance_filters(self):
        for day in range(1, 23):
            self.create_attendance(
                self.employee,
                date(2026, 10, day),
                Attendance.Status.PRESENT,
            )

        self.client.force_login(self.hr_user)

        response = self.client.get(
            reverse("leave:attendance"),
            {
                "status": Attendance.Status.PRESENT,
                "date_from": "2026-10-01",
                "date_to": "2026-10-31",
                "page": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["attendance_records"].number, 2)
        self.assertContains(response, "status=Present")
        self.assertContains(response, "date_from=2026-10-01")
        self.assertContains(response, "date_to=2026-10-31")
