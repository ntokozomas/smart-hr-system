from django.db import models


class TimeStampedModel(models.Model):
    """Shared timestamps required by Section 4.5.11."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
