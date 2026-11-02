import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from config.models import TimeStampedModel


class Department(TimeStampedModel):
    """A department within the organisation."""

    department_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["department_name"]

    def __str__(self):
        return self.department_name


class JobPosition(TimeStampedModel):
    """A job title that employees and vacancies can reference."""

    position_title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["position_title"]

    def __str__(self):
        return self.position_title


class Employee(TimeStampedModel):
    """Central employee record used by the HR modules."""

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "Active", "Active"
        ONBOARDING = "Onboarding", "Onboarding"
        ON_LEAVE = "On Leave", "On Leave"
        INACTIVE = "Inactive", "Inactive"

    employee_number = models.CharField(
        max_length=20, unique=True, editable=False
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField()
    date_joined = models.DateField()
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="employees"
    )
    position = models.ForeignKey(
        JobPosition, on_delete=models.PROTECT, related_name="employees"
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="direct_reports",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["employee_number"]
        constraints = [
            models.CheckConstraint(
                condition=Q(manager__isnull=True) | ~Q(manager=models.F("id")),
                name="employee_cannot_manage_self",
            ),
            models.CheckConstraint(condition=models.Q(employment_status__in=['Active', 'Onboarding', 'On Leave', 'Inactive']), name="employee_status_valid"),
        ]

    def clean(self):
        """Validate the minimum age and reporting relationship."""
        super().clean()

        if self.date_of_birth:
            today = date.today()

            # Calculate the latest birth date that satisfies the
            # minimum age requirement, including leap-year handling.
            try:
                eighteenth_birthday = today.replace(year=today.year - 18)
            except ValueError:
                eighteenth_birthday = today.replace(
                    year=today.year - 18,
                    day=28,
                )

            if self.date_of_birth > eighteenth_birthday:
                raise ValidationError(
                    {"date_of_birth": "Employees must be at least 18 years old."}
                )

        if self.manager_id and self.pk and self.manager_id == self.pk:
            raise ValidationError(
                {"manager": "An employee cannot be their own manager."}
            )

    def save(self, *args, **kwargs):
        """Generate a unique employee reference when one is not supplied."""
        if not self.employee_number:
            self.employee_number = f"EMP-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name}"
