"""Forms for vacancy management, applications and employee conversion."""

import zipfile

from django import forms
from django.utils import timezone

from employees.models import Department, JobPosition
from .models import Applicant, Application, JobVacancy


MAX_CV_SIZE = 5 * 1024 * 1024


class JobVacancyForm(forms.ModelForm):
    class Meta:
        model = JobVacancy
        fields = (
            "department", "position", "title", "description",
            "requirements", "date_posted", "closing_date", "status",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 5}),
            "date_posted": forms.DateInput(attrs={"type": "date"}),
            "closing_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.all()
        self.fields["position"].queryset = JobPosition.objects.all()
        if not self.instance.pk:
            self.fields["date_posted"].initial = timezone.localdate()

    def clean(self):
        cleaned = super().clean()
        posted = cleaned.get("date_posted")
        closing = cleaned.get("closing_date")
        if posted and closing and closing < posted:
            self.add_error("closing_date", "Closing date cannot be before the posting date.")
        return cleaned


class PublicApplicationForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)
    cv_file = forms.FileField(
        help_text="PDF or DOCX only. Maximum file size: 5 MB."
    )
    cover_letter = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    consent_given = forms.BooleanField(
        required=True,
        label="I consent to Smart HR processing my personal information "
              "for recruitment purposes in accordance with the POPIA notice.",
    )

    def clean_cv_file(self):
        uploaded = self.cleaned_data["cv_file"]
        filename = uploaded.name.lower()

        if not (filename.endswith(".pdf") or filename.endswith(".docx")):
            raise forms.ValidationError("Only PDF and DOCX files are accepted.")

        if uploaded.size > MAX_CV_SIZE:
            raise forms.ValidationError("The CV must be smaller than 5 MB.")

        uploaded.seek(0)
        header = uploaded.read(8)
        uploaded.seek(0)

        if filename.endswith(".pdf"):
            if not header.startswith(b"%PDF-"):
                raise forms.ValidationError("The uploaded file is not a valid PDF.")
        else:
            try:
                with zipfile.ZipFile(uploaded) as archive:
                    names = archive.namelist()
                    if (
                        "[Content_Types].xml" not in names
                        or "word/document.xml" not in names
                    ):
                        raise forms.ValidationError("The uploaded file is not a valid DOCX.")
            except (zipfile.BadZipFile, OSError):
                raise forms.ValidationError("The uploaded file is not a valid DOCX.")
            finally:
                uploaded.seek(0)

        return uploaded

    def clean(self):
        cleaned = super().clean()
        vacancy = self.initial.get("vacancy")
        email = cleaned.get("email")

        if vacancy and email:
            applicant = Applicant.objects.filter(email__iexact=email).first()
            if applicant and Application.objects.filter(
                vacancy=vacancy, applicant=applicant
            ).exists():
                raise forms.ValidationError(
                    "You have already applied for this vacancy."
                )
        return cleaned


class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("status", "match_score", "interview_date", "interview_feedback", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
            "interview_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "interview_feedback": forms.Textarea(attrs={"rows": 4}),
            "match_score": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
        }


class EmployeeConversionForm(forms.Form):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_joined = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_date_of_birth(self):
        value = self.cleaned_data["date_of_birth"]
        today = timezone.localdate()
        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )
        if age < 18:
            raise forms.ValidationError("The employee must be at least 18 years old.")
        return value
