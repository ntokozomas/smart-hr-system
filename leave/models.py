
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q, Sum

from config.models import TimeStampedModel


class LeaveRequest(TimeStampedModel):

    class LeaveType(models.TextChoices):
        ANNUAL = "Annual", "Annual"
        SICK = "Sick", "Sick"
        FAMILY = "Family", "Family"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"
        CANCELLED = "Cancelled", "Cancelled"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="leave_requests"
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices
    )

    start_date = models.DateField()
    end_date = models.DateField()

    days_requested = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    reason = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    date_submitted = models.DateField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decided_leave_requests",
        blank=True,
        null=True
    )

    decided_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-date_submitted"]

        constraints = [
            models.CheckConstraint(
                condition=Q(days_requested__gt=0),
                name="leave_days_must_be_positive"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="leave_end_on_or_after_start"
            ),
            models.CheckConstraint(
                condition=Q(leave_type__in=["Annual", "Sick", "Family"]),
                name="leave_type_valid"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "Pending",
                        "Approved",
                        "Rejected",
                        "Cancelled"
                    ]
                ),
                name="leave_status_valid"
            ),
        ]

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"


class LeaveBalance(TimeStampedModel):

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="leave_balances"
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LeaveRequest.LeaveType.choices
    )

    year = models.PositiveIntegerField()

    entitlement = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Total leave days allocated to this employee for the year."
    )

    class Meta:
        ordering = ["employee", "year", "leave_type"]

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "year"],
                name="unique_employee_leave_balance"
            ),
            models.CheckConstraint(
                condition=Q(entitlement__gte=0),
                name="leave_entitlement_non_negative"
            ),
        ]

    @property
    def used_days(self):
        total = LeaveRequest.objects.filter(
            employee=self.employee,
            leave_type=self.leave_type,
            status=LeaveRequest.Status.APPROVED,
            start_date__year=self.year
        ).aggregate(
            total=Sum("days_requested")
        )["total"]

        return total if total is not None else Decimal("0.0")

    @property
    def remaining_days(self):
        return self.entitlement - self.used_days

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.year})"


class Attendance(TimeStampedModel):

    class Status(models.TextChoices):
        PRESENT = "Present", "Present"
        ABSENT = "Absent", "Absent"
        LATE = "Late", "Late"
        ON_LEAVE = "On Leave", "On Leave"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    check_in_time = models.TimeField(blank=True, null=True)
    check_out_time = models.TimeField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"],
                name="unique_employee_attendance_date"
            ),
            models.CheckConstraint(
                condition=(
                    Q(check_out_time__isnull=True)
                    | (
                        Q(check_in_time__isnull=False)
                        & Q(check_out_time__gt=F("check_in_time"))
                    )
                ),
                name="attendance_checkout_after_checkin"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=["Present", "Absent", "Late", "On Leave"]
                ),
                name="attendance_status_valid"
            ),
        ]

    def __str__(self):
        return f"{self.employee} - {self.date}"
