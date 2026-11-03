from django.db import models

from config.models import TimeStampedModel


class Onboarding(TimeStampedModel):
    """The onboarding process associated with one new employee."""

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"

    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="onboarding",
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]

        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=['Pending', 'In Progress', 'Completed']), name="onboarding_status_valid"),
        ]
    def __str__(self):
        return f"Onboarding - {self.employee}"


class OnboardingTask(TimeStampedModel):
    """An individual activity within an employee's onboarding."""

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"

    onboarding = models.ForeignKey(
        Onboarding, on_delete=models.CASCADE, related_name="tasks"
    )
    task_name = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    completed_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["task_name"]

        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=['Pending', 'In Progress', 'Completed']), name="onboarding_task_status_valid"),
        ]
    def __str__(self):
        return f"{self.task_name} - {self.status}"


class EmployeeExit(TimeStampedModel):
    """Records an employee departure without deleting their history."""

    class ExitType(models.TextChoices):
        RESIGNATION = "Resignation", "Resignation"
        TERMINATION = "Termination", "Termination"
        RETIREMENT = "Retirement", "Retirement"
        CONTRACT_END = "Contract End", "Contract End"

    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="exit_record",
    )
    exit_type = models.CharField(max_length=20, choices=ExitType.choices)
    exit_date = models.DateField()
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    exit_procedures = models.TextField(blank=True, null=True)
    procedures_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-exit_date"]

        constraints = [
            models.CheckConstraint(condition=models.Q(exit_type__in=['Resignation', 'Termination', 'Retirement', 'Contract End']), name="employee_exit_type_valid"),
        ]
    def __str__(self):
        return f"{self.employee} - {self.exit_type}"
