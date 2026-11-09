
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import require_permission

from .forms import OnboardingForm, OnboardingTaskForm, EmployeeExitForm
from .models import Onboarding, OnboardingTask, EmployeeExit


@require_permission("lifecycle.manage")
def home(request):
    """Display all employee onboarding records."""

    onboarding_records = Onboarding.objects.select_related(
        "employee",
        "employee__department",
    ).prefetch_related("tasks")

    context = {
        "onboarding_records": onboarding_records,
    }

    return render(request, "lifecycle/home.html", context)


@require_permission("lifecycle.manage")
def create_onboarding(request):
    """Create an onboarding record for an employee."""

    if request.method == "POST":
        form = OnboardingForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Onboarding record created successfully.",
            )

            return redirect("lifecycle:home")

    else:
        form = OnboardingForm()

    return render(request, "lifecycle/create.html", {"form": form})


@require_permission("lifecycle.manage")
def edit_onboarding(request, pk):
    """Edit an existing onboarding record."""

    onboarding = get_object_or_404(Onboarding, pk=pk)

    if request.method == "POST":
        form = OnboardingForm(
            request.POST,
            instance=onboarding,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Onboarding record updated successfully.",
            )

            return redirect("lifecycle:home")

    else:
        form = OnboardingForm(instance=onboarding)

    return render(
        request,
        "lifecycle/edit.html",
        {
            "form": form,
            "onboarding": onboarding,
        },
    )


@require_permission("lifecycle.manage")
def delete_onboarding(request, pk):
    """Delete an existing onboarding record."""

    onboarding = get_object_or_404(Onboarding, pk=pk)

    if request.method == "POST":
        onboarding.delete()

        messages.success(
            request,
            "Onboarding record deleted successfully.",
        )

        return redirect("lifecycle:home")

    return render(
        request,
        "lifecycle/delete.html",
        {"onboarding": onboarding},
    )


@require_permission("lifecycle.manage")
def create_onboarding_task(request, onboarding_id):
    """Create a task for an onboarding record."""

    onboarding = get_object_or_404(Onboarding, pk=onboarding_id)

    if request.method == "POST":
        form = OnboardingTaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.onboarding = onboarding
            task.save()

            messages.success(
                request,
                "Onboarding task created successfully.",
            )

            return redirect("lifecycle:home")

    else:
        form = OnboardingTaskForm()

    return render(
        request,
        "lifecycle/create_task.html",
        {"form": form, "onboarding": onboarding},
    )


@require_permission("lifecycle.manage")
def edit_onboarding_task(request, pk):
    """Edit an onboarding task and update its completion status."""

    task = get_object_or_404(
        OnboardingTask.objects.select_related("onboarding"),
        pk=pk,
    )

    if request.method == "POST":
        form = OnboardingTaskForm(
            request.POST,
            instance=task,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Onboarding task updated successfully.",
            )

            return redirect("lifecycle:home")

    else:
        form = OnboardingTaskForm(instance=task)

    return render(
        request,
        "lifecycle/edit_task.html",
        {
            "form": form,
            "task": task,
        },
    )


@require_permission("lifecycle.manage")
def exit_management(request):
    """Display all employee exit records."""

    exit_records = EmployeeExit.objects.select_related(
        "employee",
        "employee__department",
    )

    context = {
        "exit_records": exit_records,
    }

    return render(
        request,
        "lifecycle/exit_management.html",
        context,
    )


@require_permission("lifecycle.manage")
def create_employee_exit(request):
    """Create an employee exit record and mark employee inactive."""

    if request.method == "POST":
        form = EmployeeExitForm(request.POST)

        if form.is_valid():
            exit_record = form.save()

            exit_record.employee.employment_status = "Inactive"
            exit_record.employee.save(
                update_fields=["employment_status"]
            )

            messages.success(
                request,
                "Employee exit record created successfully.",
            )

            return redirect("lifecycle:exit_management")

    else:
        form = EmployeeExitForm()

    return render(
        request,
        "lifecycle/create_exit.html",
        {"form": form},
    )


@require_permission("lifecycle.manage")
def edit_employee_exit(request, pk):
    """Edit an exit record and ensure employee is marked inactive."""

    exit_record = get_object_or_404(EmployeeExit, pk=pk)

    if request.method == "POST":
        form = EmployeeExitForm(
            request.POST,
            instance=exit_record,
        )

        if form.is_valid():
            exit_record = form.save()

            exit_record.employee.employment_status = "Inactive"
            exit_record.employee.save(
                update_fields=["employment_status"]
            )

            messages.success(
                request,
                "Employee exit record updated successfully.",
            )

            return redirect("lifecycle:exit_management")

    else:
        form = EmployeeExitForm(instance=exit_record)

    return render(
        request,
        "lifecycle/edit_exit.html",
        {
            "form": form,
            "exit_record": exit_record,
        },
    )


@require_permission("lifecycle.manage")
def delete_employee_exit(request, pk):
    """Delete an existing employee exit record."""

    exit_record = get_object_or_404(EmployeeExit, pk=pk)

    if request.method == "POST":
        exit_record.delete()

        messages.success(
            request,
            "Employee exit record deleted successfully.",
        )

        return redirect("lifecycle:exit_management")

    return render(
        request,
        "lifecycle/delete_exit.html",
        {"exit_record": exit_record},
    )
