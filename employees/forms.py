from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
    """Form for creating and updating employee records."""

    class Meta:
        model = Employee

        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "date_of_birth",
            "date_joined",
            "employment_status",
            "department",
            "position",
            "manager",
        ]

        widgets = {
            "first_name": forms.TextInput(attrs={
                "placeholder": "Enter first name",
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Enter last name",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter work email",
            }),
            "phone_number": forms.TextInput(attrs={
                "placeholder": "Enter phone number",
            }),
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter residential address",
            }),
            "date_of_birth": forms.DateInput(attrs={
                "type": "date",
            }),
            "date_joined": forms.DateInput(attrs={
                "type": "date",
            }),
        }
