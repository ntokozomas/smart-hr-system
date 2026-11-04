# Create your views here.

"""Employee records views (T3–T5)."""

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .forms import EmployeeForm

from accounts.permissions import (
    has_permission,
    require_permission,
    scope_queryset,
)

from .models import Department, Employee


@require_permission("employees.view")
def employee_list(request):
    """Display employees the current user is authorised to see."""

    # Start with employees and retrieve related records efficiently.
    employees = Employee.objects.select_related(
        "department",
        "position",
        "manager",
    )

    # Apply record-level access restrictions.
    employees = scope_queryset(
        employees,
        request.user,
        employee_field="",
    )

    # Read search and filter values from the URL.
    query = request.GET.get("q", "").strip()
    department_filter = request.GET.get("department", "").strip()
    status_filter = request.GET.get("status", "").strip()

    # Search by employee number, name or email.
    if query:
        employees = employees.filter(
            Q(employee_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    # Filter by department.
    if department_filter.isdigit():
        employees = employees.filter(
            department_id=int(department_filter)
        )

    # Filter by a valid employment status.
    valid_statuses = [
        value for value, label in Employee.EmploymentStatus.choices
    ]

    if status_filter in valid_statuses:
        employees = employees.filter(
            employment_status=status_filter
        )
    else:
        status_filter = ""

    # Paginate results: 10 employees per page.
    paginator = Paginator(employees, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "employees": page_obj.object_list,
        "query": query,
        "departments": Department.objects.all(),
        "department_filter": department_filter,
        "status_filter": status_filter,
        "status_choices": Employee.EmploymentStatus.choices,
        "can_manage": has_permission(
            request.user,
            "employees.manage",
        ),
        "total_employees": paginator.count,
    }

    return render(
        request,
        "employees/employee_list.html",
        context,
    )
@require_permission("employees.manage")
def employee_create(request):
    """Create a new employee record."""

    if request.method == "POST":
        form = EmployeeForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("employees:list")
    else:
        form = EmployeeForm()

    return render(
        request,
        "employees/employee_form.html",
        {
            "form": form,
            "page_heading": "Add Employee",
        },
    )
@require_permission("employees.manage")
def employee_update(request, pk):
    """Update an existing employee record."""

    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)

        if form.is_valid():
            form.save()
            return redirect("employees:list")
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employees/employee_form.html",
        {
            "form": form,
            "page_heading": "Edit Employee",
            "employee": employee,
        },
    )
@require_permission("employees.manage")
def employee_deactivate(request, pk):
    """Deactivate an employee without deleting their record."""

    if request.method != "POST":
        return redirect("employees:list")

    employee = get_object_or_404(Employee, pk=pk)

    employee.employment_status = "Inactive"
    employee.save()

    return redirect("employees:list")
@require_permission("employees.manage")
def employee_activate(request, pk):
    """Reactivate a previously deactivated employee."""

    if request.method != "POST":
        return redirect("employees:list")

    employee = get_object_or_404(Employee, pk=pk)

    employee.employment_status = "Active"
    employee.save()

    return redirect("employees:list")