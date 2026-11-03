from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction
from employees.models import Department, JobPosition, Employee
from leave.models import LeaveRequest, Attendance


class LeaveModelTests(TestCase):
    def setUp(self):
        department = Department.objects.create(
            department_name="Human Resources"
        )
        position = JobPosition.objects.create(
            position_title="HR Officer"
        )
        self.employee = Employee.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )

    def test_leave_request_creation(self):
        request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="Annual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
            days_requested=Decimal("3.0"),
        )
        self.assertEqual(request.status, "Pending")

    def test_leave_days_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LeaveRequest.objects.create(
                    employee=self.employee,
                    leave_type="Annual",
                    start_date=date(2026, 12, 1),
                    end_date=date(2026, 12, 3),
                    days_requested=Decimal("0.0"),
                )

    def test_leave_end_date_cannot_precede_start(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LeaveRequest.objects.create(
                    employee=self.employee,
                    leave_type="Annual",
                    start_date=date(2026, 12, 5),
                    end_date=date(2026, 12, 1),
                    days_requested=Decimal("2.0"),
                )

    def test_attendance_creation(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            check_in_time=time(8, 0),
            check_out_time=time(17, 0),
            status="Present",
        )
        self.assertEqual(attendance.status, "Present")

    def test_duplicate_attendance_rejected(self):
        Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            status="Present",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(
                    employee=self.employee,
                    date=date.today(),
                    status="Absent",
                )

    def test_checkout_before_checkin_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(
                    employee=self.employee,
                    date=date.today(),
                    check_in_time=time(17, 0),
                    check_out_time=time(8, 0),
                    status="Present",
                )

# COVERAGE_COMPLETION_TESTS
    def test_leave_request_string_representation(self):
        request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="Annual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
            days_requested=Decimal("3.0"),
        )
        self.assertEqual(
            str(request),
            f"{self.employee} - Annual (Pending)",
        )

    def test_attendance_string_representation(self):
        attendance_date = date.today()
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=attendance_date,
            status="Present",
        )
        self.assertEqual(
            str(attendance),
            f"{self.employee} - {attendance_date}",
        )

# Relationship and database-constraint tests for Section 4.5.11.
from django.db.models.deletion import ProtectedError
from accounts.models import Role, User


class LeaveRelationshipAndDatabaseTests(TestCase):
    def setUp(self):
        department = Department.objects.create(
            department_name="Leave Relationship Tests"
        )
        position = JobPosition.objects.create(
            position_title="Leave Test Employee"
        )
        self.employee = Employee.objects.create(
            first_name="Leave",
            last_name="Employee",
            email="leave.relationship@example.com",
            date_of_birth=date(1990, 1, 1),
            date_joined=date.today(),
            department=department,
            position=position,
        )
        role = Role.objects.create(role_name="Leave Approver")
        self.approver = User.objects.create_user(
            username="leave_approver",
            email="leave.approver@example.com",
            password="SecurePass123!",
            role=role,
        )

    def test_employee_deletion_cascades_to_leave_and_attendance(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="Annual",
            start_date=date.today(),
            end_date=date.today(),
            days_requested=Decimal("1.0"),
        )
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            check_in_time=time(8, 0),
            status="Present",
        )

        self.employee.delete()

        self.assertFalse(
            LeaveRequest.objects.filter(pk=leave_request.pk).exists()
        )
        self.assertFalse(
            Attendance.objects.filter(pk=attendance.pk).exists()
        )

    def test_approver_deletion_sets_leave_approved_by_to_null(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="Annual",
            start_date=date.today(),
            end_date=date.today(),
            days_requested=Decimal("1.0"),
            approved_by=self.approver,
        )

        self.approver.delete()
        leave_request.refresh_from_db()
        self.assertIsNone(leave_request.approved_by_id)

    def test_checkout_without_checkin_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(
                    employee=self.employee,
                    date=date.today(),
                    check_in_time=None,
                    check_out_time=time(17, 0),
                    status="Present",
                )
