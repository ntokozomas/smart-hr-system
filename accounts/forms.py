"""Login form (FR-01)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User


class LoginForm(AuthenticationForm):
    """Username or email plus password, with one generic error message.

    The message never says which part was wrong, so it does not reveal which
    accounts exist (Design 4.7.2).
    """

    username = forms.CharField(
        label="Username or email",
        max_length=254,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Invalid username or password.",
        "inactive": "This account is inactive. Please contact the administrator.",
    }

class ProfileForm(forms.ModelForm):
    """Allow users to update their own personal account details."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "placeholder": "Enter your first name",
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Enter your last name",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter your email address",
            }),
        }