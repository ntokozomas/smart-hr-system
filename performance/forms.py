
from django import forms

from accounts.permissions import scope_queryset
from employees.models import Employee
from .models import PerformanceRecord


class PerformanceRecordForm(forms.ModelForm):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["employee"].queryset = scope_queryset(
                Employee.objects.all(),
                user,
                employee_field="",
            )
        else:
            self.fields["employee"].queryset = Employee.objects.none()

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
