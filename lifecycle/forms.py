from django import forms

from .models import Onboarding, OnboardingTask, EmployeeExit


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = Onboarding
        fields = [
            "employee",
            "start_date",
            "end_date",
            "status",
            "notes",
        ]

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class OnboardingTaskForm(forms.ModelForm):
    class Meta:
        model = OnboardingTask
        fields = [
            "task_name",
            "status",
            "completed_date",
        ]

        widgets = {
            "completed_date": forms.DateInput(attrs={"type": "date"}),
        }


class EmployeeExitForm(forms.ModelForm):
    class Meta:
        model = EmployeeExit
        fields = [
            "employee",
            "exit_type",
            "exit_date",
            "reason",
            "notes",
            "exit_procedures",
            "procedures_completed",
        ]

        widgets = {
            "exit_date": forms.DateInput(attrs={"type": "date"}),
        }