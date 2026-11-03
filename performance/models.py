from django.conf import settings
from django.db import models
from django.db.models import Q

from config.models import TimeStampedModel


class PerformanceRecord(TimeStampedModel):
    """A performance review for an employee."""

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="performance_records",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conducted_reviews",
    )
    review_period = models.CharField(max_length=30)
    review_date = models.DateField()
    goals = models.TextField(blank=True, null=True)
    rating = models.SmallIntegerField()
    comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-review_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="performance_rating_between_1_and_5",
            )
        ]

    def __str__(self):
        return f"{self.employee} - {self.review_period}"
