from datetime import timedelta

from django import forms
from django.utils import timezone

from accounts.permissions import HR_OFFICER, has_role
from employees.models import Department
from leave.models import LeaveRequest

from .metrics import add_months, month_start

MAX_DAYS = 366


def default_filters(today=None):
    today = today or timezone.localdate()
    return {
        "start_date": add_months(month_start(today), -5).isoformat(),
        "end_date": today.isoformat(),
        "department": "",
        "leave_type": "",
    }


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(label="From", widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(label="To", widget=forms.DateInput(attrs={"type": "date"}))
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="All departments",
    )
    leave_type = forms.ChoiceField(
        choices=[("", "All leave types"), *LeaveRequest.LeaveType.choices],
        required=False,
    )

    def __init__(self, data=None, *, user, **kwargs):
        merged = default_filters()
        if data:
            merged.update({key: data.get(key) for key in merged if key in data})
        super().__init__(merged, **kwargs)
        self.user = user
        if not has_role(user, HR_OFFICER):
            del self.fields["department"]

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end:
            if end < start:
                self.add_error("end_date", "The end date must be on or after the start date.")
            elif end - start > timedelta(days=MAX_DAYS):
                self.add_error("end_date", "Choose a period of one year or less.")
        return cleaned

    def department_label(self):
        if "department" in self.fields:
            department = self.cleaned_data.get("department")
            return department.department_name if department else "All departments"
        employee = getattr(self.user, "employee", None)
        return employee.department.department_name if employee else "No department"

    def leave_type_label(self):
        return self.cleaned_data.get("leave_type") or "All leave types"
