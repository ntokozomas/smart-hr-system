"""Forms for the Administrator's user and role screens (FR-03, FR-04)."""

from django import forms
from django.contrib.auth.password_validation import validate_password

from employees.models import Employee

from .models import Role, User


class EmployeeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, employee):
        return f"{employee.first_name} {employee.last_name} ({employee.employee_number})"


def unlinked_employees(current=None):
    """Employees without a login yet, plus the one already linked to this account."""
    queryset = Employee.objects.exclude(employment_status="Inactive").filter(
        user_account__isnull=True
    )
    if current is not None:
        queryset = queryset | Employee.objects.filter(pk=current.pk)
    return queryset.order_by("first_name", "last_name")


class UserForm(forms.ModelForm):
    """Create or edit an account. Each user has exactly one role (FR-04)."""

    role = forms.ModelChoiceField(queryset=Role.objects.order_by("role_name"), empty_label=None)
    employee = EmployeeChoiceField(
        queryset=Employee.objects.none(),
        required=False,
        empty_label="Not linked (e.g. the Administrator)",
        help_text="Link the account to the person's employee record.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "employee"]

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acting_user = acting_user
        self.fields["employee"].queryset = unlinked_employees(self.instance.employee)

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def clean_role(self):
        role = self.cleaned_data["role"]
        editing_self = self.instance.pk and self.instance.pk == getattr(self.acting_user, "pk", None)
        if editing_self and role.role_name != "Administrator":
            raise forms.ValidationError("You cannot remove your own Administrator role.")
        return role


class NewUserForm(UserForm):
    """Account creation also sets the first password (NFR-06 rules apply)."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, strip=False)

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("password1"), cleaned.get("password2")
        if first and second and first != second:
            self.add_error("password2", "The two passwords do not match.")
        elif first:
            probe = User(
                username=cleaned.get("username", ""),
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                validate_password(first, probe)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ResetPasswordForm(forms.Form):
    """The Administrator sets a temporary password for a user who forgot theirs."""

    password1 = forms.CharField(label="New password", widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, strip=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("password1"), cleaned.get("password2")
        if first and second and first != second:
            self.add_error("password2", "The two passwords do not match.")
        elif first:
            try:
                validate_password(first, self.user)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned
