"""Login form (FR-01)."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from . import lockout


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

    def clean(self):
        """Refuse locked accounts with a clear message before checking the password."""
        user = lockout.find_user(self.cleaned_data.get("username"))
        if lockout.is_locked(user):
            raise forms.ValidationError(
                "Too many failed login attempts. This account is locked for "
                f"{lockout.minutes_left(user)} more minute(s).",
                code="locked",
            )
        return super().clean()
