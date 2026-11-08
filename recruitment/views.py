"""Recruitment module views."""

import os
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import require_permission
from employees.models import Employee
from .forms import (
    JobVacancyForm,
    PublicApplicationForm,
    ApplicationUpdateForm,
    EmployeeConversionForm,
)
from .models import Applicant, Application, JobVacancy


# Private CV storage outside the public MEDIA_ROOT.
cv_storage = FileSystemStorage(location=settings.BASE_DIR / 'private_uploads')


def open_vacancies():
    today = timezone.localdate()
    return JobVacancy.objects.filter(
        status=JobVacancy.Status.OPEN
    ).filter(
        Q(closing_date__isnull=True) | Q(closing_date__gte=today)
    )


@require_permission("recruitment.manage")
def home(request):
    today = timezone.localdate()
    context = {
        "total_vacancies": JobVacancy.objects.count(),
        "open_vacancies": open_vacancies().count(),
        "total_applications": Application.objects.count(),
        "pending_applications": Application.objects.exclude(
            status__in=[Application.Status.HIRED, Application.Status.REJECTED]
        ).count(),
        "recent_vacancies": JobVacancy.objects.select_related(
            "department", "position"
        )[:5],
        "stage_counts": Application.objects.values("status").annotate(
            total=Count("id")
        ),
    }
    return render(request, "recruitment/home.html", context)


@require_permission("recruitment.manage")
def vacancy_list(request):
    vacancies = JobVacancy.objects.select_related("department", "position")
    query = request.GET.get("q", "").strip()

    if query:
        vacancies = vacancies.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(requirements__icontains=query)
        )

    page_obj = Paginator(vacancies, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "recruitment/vacancy_list.html",
        {"page_obj": page_obj, "query": query},
    )


@require_permission("recruitment.manage")
def vacancy_create(request):
    form = JobVacancyForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        vacancy = form.save()
        messages.success(request, f'"{vacancy.title}" was created successfully.')
        return redirect("recruitment:vacancy_list")

    return render(request, "recruitment/vacancy_form.html", {
        "form": form,
        "page_heading": "Create vacancy",
        "recruitment_list_url": "/recruitment/vacancies/",
    })


@require_permission("recruitment.manage")
def vacancy_edit(request, pk):
    vacancy = get_object_or_404(JobVacancy, pk=pk)
    form = JobVacancyForm(
        request.POST if request.method == "POST" else None,
        instance=vacancy,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vacancy updated successfully.")
        return redirect("recruitment:vacancy_list")

    return render(request, "recruitment/vacancy_form.html", {
        "form": form,
        "vacancy": vacancy,
        "page_heading": "Edit vacancy",
        "recruitment_list_url": "/recruitment/vacancies/",
    })


@require_permission("recruitment.manage")
def vacancy_toggle_status(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    vacancy = get_object_or_404(JobVacancy, pk=pk)

    if vacancy.status == JobVacancy.Status.OPEN:
        vacancy.status = JobVacancy.Status.CLOSED
        message = "Vacancy closed."
    else:
        if vacancy.closing_date and vacancy.closing_date < timezone.localdate():
            messages.error(request, "This vacancy has passed its closing date.")
            return redirect("recruitment:vacancy_list")
        vacancy.status = JobVacancy.Status.OPEN
        message = "Vacancy reopened."

    vacancy.save(update_fields=["status", "updated_at"])
    messages.success(request, message)
    return redirect("recruitment:vacancy_list")


@login_not_required
def careers(request):
    return render(request, "recruitment/careers.html", {
        "vacancies": open_vacancies().select_related("department", "position")
    })


@login_not_required
def career_detail(request, pk):
    vacancy = get_object_or_404(open_vacancies(), pk=pk)
    return render(request, "recruitment/career_detail.html", {"vacancy": vacancy})


@login_not_required
def apply(request, pk):
    vacancy = get_object_or_404(open_vacancies(), pk=pk)
    form = PublicApplicationForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        initial={"vacancy": vacancy},
    )

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        uploaded = data["cv_file"]

        extension = os.path.splitext(uploaded.name)[1].lower()
        private_name = f"private/recruitment/cvs/{uuid.uuid4().hex}{extension}"
        saved_path = cv_storage.save(private_name, uploaded)

        try:
            with transaction.atomic():
                applicant, created = Applicant.objects.get_or_create(
                    email=data["email"].lower(),
                    defaults={
                        "first_name": data["first_name"],
                        "last_name": data["last_name"],
                        "phone_number": data["phone_number"],
                        "cv_path": saved_path,
                        "consent_given": True,
                        "consent_date": timezone.now(),
                    },
                )

                if not created:
                    applicant.first_name = data["first_name"]
                    applicant.last_name = data["last_name"]
                    applicant.phone_number = data["phone_number"]
                    applicant.cv_path = saved_path
                    applicant.consent_given = True
                    applicant.consent_date = timezone.now()
                    applicant.save()

                application = Application.objects.create(
                    vacancy=vacancy,
                    applicant=applicant,
                    cover_letter=data.get("cover_letter", ""),
                )
        except IntegrityError:
            if cv_storage.exists(saved_path):
                cv_storage.delete(saved_path)
            form.add_error(None, "An application for this vacancy already exists.")
        else:
            messages.success(
                request,
                "Your application was submitted successfully. "
                "Keep your application reference safe.",
            )
            return render(
                request,
                "recruitment/application_submitted.html",
                {"application": application},
            )

    return render(request, "recruitment/application_form.html", {
        "form": form,
        "vacancy": vacancy,
    })


@login_not_required
def application_status(request):
    application = None
    searched = False
    error = None

    if request.method == "POST":
        searched = True
        reference = request.POST.get("reference", "").strip()
        email = request.POST.get("email", "").strip().lower()

        try:
            application = Application.objects.select_related(
                "applicant", "vacancy"
            ).get(
                public_reference=reference,
                applicant__email__iexact=email,
            )
        except (Application.DoesNotExist, ValueError):
            error = "No application matched those details. Check your reference and email."

    return render(request, "recruitment/application_status.html", {
        "application": application,
        "searched": searched,
        "error": error,
    })


@require_permission("recruitment.manage")
def application_list(request):
    applications = Application.objects.select_related(
        "applicant", "vacancy"
    )
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()

    if status in Application.Status.values:
        applications = applications.filter(status=status)

    if query:
        applications = applications.filter(
            Q(applicant__first_name__icontains=query)
            | Q(applicant__last_name__icontains=query)
            | Q(applicant__email__icontains=query)
            | Q(vacancy__title__icontains=query)
        )

    page_obj = Paginator(applications, 15).get_page(request.GET.get("page"))
    return render(request, "recruitment/application_list.html", {
        "page_obj": page_obj,
        "query": query,
        "selected_status": status,
        "statuses": Application.Status.choices,
    })


@require_permission("recruitment.manage")
def application_detail(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("applicant", "vacancy"),
        pk=pk,
    )
    return render(request, "recruitment/application_detail.html", {
        "application": application,
        "update_form": ApplicationUpdateForm(instance=application),
    })


@require_permission("recruitment.manage")
def download_cv(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("applicant"),
        pk=pk,
    )
    path = application.applicant.cv_path

    if not path or not cv_storage.exists(path):
        raise Http404("CV file not found.")

    file_handle = cv_storage.open(path, "rb")
    extension = os.path.splitext(path)[1].lower()
    content_type = (
        "application/pdf" if extension == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=f"applicant-{application.applicant_id}-cv{extension}",
        content_type=content_type,
    )


@require_permission("recruitment.manage")
def application_update(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    application = get_object_or_404(Application, pk=pk)
    form = ApplicationUpdateForm(request.POST, instance=application)

    if form.is_valid():
        form.save()
        messages.success(request, "Application updated successfully.")
        return redirect("recruitment:application_detail", pk=pk)

    messages.error(request, "Please correct the application details.")
    return render(request, "recruitment/application_detail.html", {
        "application": application,
        "update_form": form,
    })


@require_permission("recruitment.manage")
def convert_to_employee(request, pk):
    application = get_object_or_404(
        Application.objects.select_related(
            "applicant", "vacancy", "vacancy__department", "vacancy__position"
        ),
        pk=pk,
    )

    if application.status != Application.Status.HIRED:
        messages.error(request, "Only applicants with Hired status can be converted.")
        return redirect("recruitment:application_detail", pk=pk)

    applicant = application.applicant
    existing_employee = Employee.objects.filter(email__iexact=applicant.email).first()

    if existing_employee:
        messages.info(
            request,
            f"This applicant already has an employee record: {existing_employee.employee_number}.",
        )
        return redirect("recruitment:application_detail", pk=pk)

    form = EmployeeConversionForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        employee = Employee.objects.create(
            first_name=applicant.first_name,
            last_name=applicant.last_name,
            email=applicant.email,
            phone_number=applicant.phone_number or "",
            address=applicant.address or "",
            date_of_birth=form.cleaned_data["date_of_birth"],
            date_joined=form.cleaned_data["date_joined"],
            department=application.vacancy.department,
            position=application.vacancy.position,
            employment_status="Onboarding",
        )
        messages.success(
            request,
            f"Employee record {employee.employee_number} was created successfully.",
        )
        return redirect("recruitment:application_detail", pk=pk)

    return render(request, "recruitment/convert_employee.html", {
        "application": application,
        "form": form,
    })
