from django.db import models
from django.db.models import F, Q

from config.models import TimeStampedModel


class JobVacancy(TimeStampedModel):
    """A position advertised for recruitment."""

    class Status(models.TextChoices):
        OPEN = "Open", "Open"
        CLOSED = "Closed", "Closed"

    department = models.ForeignKey(
        "employees.Department",
        on_delete=models.PROTECT,
        related_name="vacancies",
    )
    position = models.ForeignKey(
        "employees.JobPosition",
        on_delete=models.PROTECT,
        related_name="vacancies",
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    requirements = models.TextField()
    date_posted = models.DateField()
    closing_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    class Meta:
        ordering = ["-date_posted"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(closing_date__isnull=True)
                    | Q(closing_date__gte=F("date_posted"))
                ),
                name="vacancy_closing_on_or_after_posted",
            ),
            models.CheckConstraint(condition=models.Q(status__in=['Open', 'Closed']), name="vacancy_status_valid"),
        ]

    def __str__(self):
        return self.title


class Applicant(TimeStampedModel):
    """An individual applying for an advertised vacancy."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    cv_path = models.CharField(max_length=255)
    date_applied = models.DateField(auto_now_add=True)
    consent_given = models.BooleanField()
    consent_date = models.DateTimeField()

    class Meta:
        ordering = ["-date_applied"]
        constraints = [
            models.CheckConstraint(
                condition=Q(consent_given=True),
                name="applicant_consent_must_be_given",
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Application(TimeStampedModel):
    """Connects an applicant to a vacancy and stores application-specific data."""

    class Status(models.TextChoices):
        RECEIVED = "Received", "Received"
        SCREENING = "Screening", "Screening"
        INTERVIEW = "Interview", "Interview"
        OFFER = "Offer", "Offer"
        HIRED = "Hired", "Hired"
        REJECTED = "Rejected", "Rejected"

    vacancy = models.ForeignKey(
        JobVacancy, on_delete=models.CASCADE, related_name="applications"
    )
    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="applications"
    )
    application_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    cover_letter = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    match_score = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )

    class Meta:
        ordering = ["-application_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "applicant"],
                name="unique_applicant_per_vacancy",
            ),
            models.CheckConstraint(
                condition=(
                    Q(match_score__isnull=True)
                    | (
                        Q(match_score__gte=0)
                        & Q(match_score__lte=100)
                    )
                ),
                name="application_match_score_between_0_and_100",
            ),
            models.CheckConstraint(condition=models.Q(status__in=['Received', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected']), name="application_status_valid"),
        ]

    def __str__(self):
        return f"{self.applicant} - {self.vacancy}"
