from django import forms
from .models import PerformanceRecord


class PerformanceRecordForm(forms.ModelForm):
    class Meta:
        model = PerformanceRecord
        fields = [
            "employee",
            "review_period",
            "review_date",
            "goals",
            "rating",
            "comments",
        ]

        widgets = {
            "review_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "goals": forms.Textarea(
                attrs={"rows": 3}
            ),
            "comments": forms.Textarea(
                attrs={"rows": 3}
            ),
            "rating": forms.Select(
                choices=[
                    (1, "1 - Poor"),
                    (2, "2 - Below Expectations"),
                    (3, "3 - Meets Expectations"),
                    (4, "4 - Exceeds Expectations"),
                    (5, "5 - Outstanding"),
                ]
            ),
        }