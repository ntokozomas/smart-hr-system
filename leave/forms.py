
from decimal import Decimal

from django import forms

from .models import LeaveRequest, LeaveBalance
from .utils import calculate_working_days


class LeaveRequestForm(forms.ModelForm):
    """Form for employees to submit leave applications."""

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

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
        """Validate dates, calculate working days and check leave balance."""

        cleaned_data = super().clean()

        leave_type = cleaned_data.get("leave_type")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:

            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "The end date cannot be before the start date.",
                )
                return cleaned_data

            # Leave applications must fall within one calendar year.
            if start_date.year != end_date.year:
                self.add_error(
                    "end_date",
                    "Leave applications cannot cross calendar years. "
                    "Please submit separate applications for each year.",
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

            # Check the employee's individual leave balance.
            if self.employee is not None and leave_type:

                balance = LeaveBalance.objects.filter(
                    employee=self.employee,
                    leave_type=leave_type,
                    year=start_date.year,
                ).first()

                if balance is None:
                    self.add_error(
                        "leave_type",
                        "No leave balance has been configured for this "
                        "leave type and year. Please contact HR.",
                    )

                else:
                    remaining_days = balance.remaining_days

                    if Decimal(str(days)) > remaining_days:
                        self.add_error(
                            "end_date",
                            (
                                f"Insufficient leave balance. You requested "
                                f"{days} working days, but you only have "
                                f"{remaining_days} days remaining."
                            ),
                        )

        return cleaned_data

    def save(self, commit=True):
        """Save the leave request with automatically calculated days."""

        leave_request = super().save(commit=False)

        leave_request.days_requested = self.cleaned_data["days_requested"]

        if commit:
            leave_request.save()

        return leave_request
