from django import forms

from .models import LeaveRequest
from .utils import calculate_working_days


class LeaveRequestForm(forms.ModelForm):
    """Form for employees to submit leave applications."""

    class Meta:
        model = LeaveRequest

        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]

        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"},
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date"},
            ),
            "reason": forms.Textarea(
                attrs={"rows": 3},
            ),
        }

        labels = {
            "leave_type": "Type of Leave",
            "start_date": "Start Date",
            "end_date": "End Date",
            "reason": "Reason for Leave",
        }

        help_texts = {
            "reason": "Provide a reason for your leave application.",
        }

    def clean(self):
        """Validate dates and calculate the requested working days."""

        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "The end date cannot be before the start date.",
                )
                return cleaned_data

            days = calculate_working_days(
                start_date,
                end_date,
            )

            if days == 0:
                self.add_error(
                    "end_date",
                    "The selected period contains no working days.",
                )
                return cleaned_data

            cleaned_data["days_requested"] = days

        return cleaned_data

    def save(self, commit=True):
        """Save the leave request with automatically calculated days."""

        leave_request = super().save(commit=False)

        leave_request.days_requested = self.cleaned_data["days_requested"]

        if commit:
            leave_request.save()

        return leave_request
