from django import forms
from django.contrib.auth import get_user_model

from .models import Employee

User = get_user_model()


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


class EmployeeProfileForm(forms.ModelForm):
    """Allow employees to update their own contact information."""

    class Meta:
        model = Employee
        fields = ["email", "phone_number", "address"]

        widgets = {
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter your email address",
            }),
            "phone_number": forms.TextInput(attrs={
                "placeholder": "Enter your phone number",
            }),
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter your address",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        if self.user and User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError(
                "This email address is already used by another account."
            )

        return email
